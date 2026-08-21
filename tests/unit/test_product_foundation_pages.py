"""Results / Compare / Why canonical consistency and Product Foundation rendering."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.consumer.location import DeliveryContext
from app.consumer.presentation import build_page_view
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


def _attrs(html: str, name: str) -> str:
    needle = f'data-{name}="'
    start = html.index(needle) + len(needle)
    end = html.index('"', start)
    return html[start:end]


@pytest.mark.asyncio
async def test_results_compare_why_share_canonical_decision(client: AsyncClient) -> None:
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
    results = await client.get("/results/headphones-standard")
    compare = await client.get("/compare/headphones-standard")
    why = await client.get("/why-best-piq/headphones-standard")
    keys = (
        "best-piq",
        "piqscore",
        "highest-piqscore-id",
        "price-state",
        "canonical-piqscore-set",
        "recommendation-sha",
        "location-state",
    )
    for key in keys:
        assert _attrs(results.text, key) == _attrs(compare.text, key) == _attrs(why.text, key)
    assert _attrs(results.text, "best-piq") == "sony-wh-1000xm5-lazada"
    assert _attrs(results.text, "highest-piqscore-id") == "sony-wh-1000xm5-lazada"
    assert "Best Piq for You" in results.text
    assert "See full reasoning" in results.text
    assert "/why-best-piq/headphones-standard" in results.text
    assert "Ask PiqSavi" in results.text
    assert "Ask PiqSavi" in compare.text
    assert "Ask PiqSavi" in why.text
    assert "WHAT YOU'LL PAY" in compare.text
    assert "PRODUCT FIT" in compare.text
    assert "Why PiqSavi recommends this" in why.text
    assert "What to know before you buy" in why.text
    assert "Best for" in why.text
    assert "When an alternative may be better" in why.text
    assert "What PiqSavi considered" in why.text
    assert "What we don’t know" in why.text
    assert "Price PiqSavi evaluated" in why.text
    assert "DealBrain" not in results.text
    assert "DealBrain" not in compare.text
    assert "DealBrain" not in why.text
    assert "answer_from_evidence" not in results.text
    assert "refine_session_recommendation" not in results.text
    assert "propose_research" not in results.text


def test_highest_piqscore_can_differ_from_best_piq() -> None:
    location = DeliveryContext(city="Taguig City", postal_code="1630", source="manual")
    why = build_page_view(
        decision_id="headphones-score-diff",
        page="why",
        location=location,
    )
    results = build_page_view(
        decision_id="headphones-score-diff",
        page="results",
        location=location,
    )
    compare = build_page_view(
        decision_id="headphones-score-diff",
        page="compare",
        location=location,
    )
    for view in (why, results, compare):
        assert view.best_piq.product_id == "bose-qc45-lazada"
        assert view.highest_piqscore_product_id == "sony-wh-1000xm5-lazada"
        assert view.best_piq.piqscore.value == 90
        assert view.highest_piqscore_name.startswith("Sony")
        assert view.best_piq.piqscore.value != 93
    assert why.why_sections[0].callout is not None
    assert "highest objective PiqScore" in why.why_sections[0].callout


def test_ordinary_best_piq_matches_highest_score() -> None:
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.product_id == view.highest_piqscore_product_id
    assert view.best_piq.piqscore.value == 92


def test_qualified_best_piq_is_labeled() -> None:
    view = build_page_view(
        decision_id="headphones-qualified",
        page="why",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.is_qualified
    html_needed = "Best Piq for You — Qualified"
    from app.consumer.pages import render_page

    html = render_page(view)
    assert html_needed in html
    assert "Shipping to Taguig City 1630 is not yet verified" in view.why_sections[0].callout or (
        view.why_sections[0].callout and "not yet verified" in view.why_sections[0].callout
    )


@pytest.mark.asyncio
async def test_score_diff_and_cross_border_pages_render(client: AsyncClient) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": "headphones-score-diff",
            "next": "/why-best-piq/headphones-score-diff",
        },
        follow_redirects=True,
    )
    why = await client.get("/why-best-piq/headphones-score-diff")
    compare = await client.get("/compare/headphones-score-diff")
    cross = await client.get("/why-best-piq/headphones-cross-border")
    assert why.status_code == 200
    assert "highest objective PiqScore" in why.text
    assert _attrs(why.text, "best-piq") == "bose-qc45-lazada"
    assert _attrs(why.text, "highest-piqscore-id") == "sony-wh-1000xm5-lazada"
    assert "Compare up to 4 options" in compare.text
    assert compare.text.count('class="compare-card"') == 4
    assert "Estimated landed cost" in cross.text
    assert "Item price" in cross.text
    assert "International shipping" in cross.text
    assert "Estimated import charges" in cross.text


@pytest.mark.asyncio
async def test_search_redirects_to_results(client: AsyncClient) -> None:
    response = await client.get("/search", params={"q": "headphones"})
    assert response.status_code == 303
    assert response.headers["location"] == "/results/headphones-standard"


@pytest.mark.asyncio
async def test_static_assets_and_no_phase_29_4_actions(client: AsyncClient) -> None:
    css = await client.get("/static/consumer/css/piqsavi.css")
    js = await client.get("/static/consumer/js/consumer.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "answer_from_evidence" not in js.text
    assert "refine_session_recommendation" not in js.text
    assert "propose_research" not in js.text
    assert "/api/v1/shopping-assistant/query" in js.text
    assert "min-height: var(--ask-h)" in css.text
    source = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "DealBrain" not in source
    assert "DealBrain" not in (ROOT / "app/static/consumer/css/piqsavi.css").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_cebu_explicit_snapshot_can_change_recommendation(
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
    assert "Your recommendation changed" in page.text
    assert "Delivering to Cebu City 6000" in page.text
    assert "Taguig City 1630" not in page.text
