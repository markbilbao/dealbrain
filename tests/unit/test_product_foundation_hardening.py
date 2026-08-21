"""Pre-merge Product Foundation hardening: fixtures, geolocation, destination."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.consumer.location import DeliveryContext, skipped_context
from app.consumer.mode import fixture_catalogs_permitted
from app.consumer.pages import render_page
from app.consumer.presentation import build_page_view
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
JS_PATH = ROOT / "app/static/consumer/js/consumer.js"
FIXTURE_MARKERS = (
    "WH-1000XM5",
    "18,990",
    "sony-wh-1000xm5-lazada",
    "Lazada",
    "QC45",
    "QuietComfort",
)


def _attrs(html: str, name: str) -> str:
    needle = f'data-{name}="'
    start = html.index(needle) + len(needle)
    end = html.index('"', start)
    return html[start:end]


def test_fixture_catalogs_permitted_by_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        def __init__(self, app_env: str) -> None:
            self.app_env = app_env

    monkeypatch.setattr("app.consumer.mode.get_settings", lambda: _Settings("development"))
    assert fixture_catalogs_permitted() is True
    monkeypatch.setattr("app.consumer.mode.get_settings", lambda: _Settings("staging"))
    assert fixture_catalogs_permitted() is True
    monkeypatch.setattr("app.consumer.mode.get_settings", lambda: _Settings("production"))
    assert fixture_catalogs_permitted() is False


def test_production_mode_does_not_substitute_fixture_offers() -> None:
    location = DeliveryContext(city="Taguig City", postal_code="1630", source="manual")
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=location,
        allow_fixtures=False,
    )
    assert view.data_unavailable is True
    assert view.best_piq.product_id == ""
    assert view.best_piq.merchant == ""
    assert view.best_piq.economics.dominant_amount is None
    html = render_page(view)
    assert 'data-unavailable="true"' in html
    assert "Offer details are not available" in html
    assert view.data_classification == "canonical_offer_economics_unavailable"
    assert 'data-classification="canonical_offer_economics_unavailable"' in html
    for marker in FIXTURE_MARKERS:
        assert marker not in html
    assert "non_live_contract_fixture" not in html


@pytest.mark.asyncio
async def test_production_http_cannot_fall_back_to_fixture_offers(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.consumer.mode.fixture_catalogs_permitted", lambda: False)
    results = await client.get("/results/headphones-standard")
    compare = await client.get("/compare/headphones-standard")
    why = await client.get("/why-best-piq/headphones-standard")
    search = await client.get("/search", params={"q": "headphones"})
    assert search.status_code == 303
    assert search.headers["location"] == "/results/unavailable"
    for page in (results, compare, why):
        assert page.status_code == 200
        assert _attrs(page.text, "unavailable") == "true"
        assert "Offer details are not available" in page.text
        for marker in FIXTURE_MARKERS:
            assert marker not in page.text
        assert "WH-1000XM5" not in page.text
        assert "₱18,990" not in page.text


def test_use_my_location_is_truthful_when_geocoding_is_unavailable() -> None:
    html = render_page(
        build_page_view(
            decision_id="headphones-standard",
            page="results",
            location=DeliveryContext(),
            location_prompt=True,
        )
    )
    js = JS_PATH.read_text(encoding="utf-8")
    assert 'data-geocode-available="false"' in html
    assert "cannot determine your city from a map pin" in html
    assert "Precise coordinates are not stored" in html
    assert "City / municipality" in html
    assert "Use my location" in html
    assert "getCurrentPosition" in js
    assert js.index("getCurrentPosition") > js.index("js-use-location")
    assert "Location received" not in js
    assert "detected your city" not in js
    assert "detected your city" not in html
    assert ".coords" not in js
    assert "latitude" not in js
    assert "longitude" not in js
    assert 'name="lat"' not in html
    assert 'name="lng"' not in html
    assert 'name="latitude"' not in html
    assert 'name="longitude"' not in html


@pytest.mark.asyncio
async def test_unsupported_destination_qualifies_recommendation_and_drops_stale_shipping(
    client: AsyncClient,
) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    first = await client.get("/results/headphones-standard")
    assert _attrs(first.text, "recommendation-qualified") == "false"
    assert _attrs(first.text, "destination-snapshot") == "true"
    assert "Best Piq for You — Qualified" not in first.text
    assert "FREE" in first.text
    assert _attrs(first.text, "best-piq") == "sony-wh-1000xm5-lazada"
    first_score = _attrs(first.text, "piqscore")

    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Davao City",
            "postal_code": "8000",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    changed = await client.get("/results/headphones-standard")
    compare = await client.get("/compare/headphones-standard")
    why = await client.get("/why-best-piq/headphones-standard")
    assert "Delivering to Davao City 8000" in changed.text
    assert "Delivering to Taguig City 1630" not in changed.text
    assert "Shipping to Taguig" not in changed.text
    assert "FREE shipping" not in changed.text
    assert "Price before shipping" in changed.text
    assert "Best Piq for You — Qualified" in changed.text
    assert "may change this recommendation" in changed.text
    assert _attrs(changed.text, "recommendation-qualified") == "true"
    assert _attrs(changed.text, "destination-snapshot") == "false"
    assert _attrs(changed.text, "best-piq") == "sony-wh-1000xm5-lazada"
    assert _attrs(changed.text, "piqscore") == first_score
    assert _attrs(compare.text, "recommendation-qualified") == "true"
    assert "Best Piq for You — Qualified" in compare.text
    assert "Best Piq for You — Qualified" in why.text
    assert "may change this recommendation" in why.text
    assert "answer_from_evidence" not in changed.text


@pytest.mark.asyncio
async def test_cebu_explicit_destination_snapshot_remains_valid(
    client: AsyncClient,
) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Cebu City",
            "postal_code": "6000",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert _attrs(page.text, "best-piq") == "bose-qc45-lazada"
    assert _attrs(page.text, "recommendation-qualified") == "false"
    assert _attrs(page.text, "destination-snapshot") == "true"
    assert "Your recommendation changed" in page.text
    assert "Best Piq for You — Qualified" not in page.text
    assert "Price before shipping" not in page.text
    assert "Delivering to Cebu City 6000" in page.text


def test_skip_does_not_use_qualified_unsupported_destination_state() -> None:
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=skipped_context(),
    )
    assert view.best_piq.is_qualified is False
    assert view.best_piq.economics.dominant_state == "price_before_shipping"
    assert view.recommendation_qualified_message is None
    assert view.destination_snapshot_known is False
