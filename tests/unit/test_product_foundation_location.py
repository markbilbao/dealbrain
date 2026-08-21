"""Product Foundation location and delivery-context tests."""

from __future__ import annotations

import pytest
from app.consumer.location import (
    DELIVERY_COOKIE,
    LocationValidationError,
    context_from_manual,
    parse_delivery_cookie,
    skipped_context,
)
from app.consumer.presentation import build_page_view
from httpx import AsyncClient


def test_manual_city_does_not_require_street_or_unit() -> None:
    context = context_from_manual("Taguig City", "1630")
    assert context.is_known
    assert context.city == "Taguig City"
    assert context.postal_code == "1630"
    assert context.delivering_to_label == "Delivering to Taguig City 1630"


def test_postal_code_is_optional() -> None:
    context = context_from_manual("Cebu City", None)
    assert context.is_known
    assert context.postal_code is None
    assert context.delivering_to_label == "Delivering to Cebu City"


def test_skip_is_session_unknown() -> None:
    context = skipped_context()
    assert context.is_skipped
    assert not context.is_known
    assert context.delivering_to_label == ""


def test_parse_cookie_ignores_coordinates_if_present() -> None:
    raw = (
        '{"city":"Taguig City","postal_code":"1630","skipped":false,'
        '"source":"manual","latitude":14.5,"longitude":121.0}'
    )
    context = parse_delivery_cookie(raw)
    assert context.city == "Taguig City"
    assert "14.5" not in context.display_place
    assert context.to_cookie_payload() == {
        "city": "Taguig City",
        "postal_code": "1630",
        "skipped": False,
        "source": "manual",
    }


def test_invalid_city_is_rejected() -> None:
    with pytest.raises(LocationValidationError):
        context_from_manual("12 Main Street Apt 4", None)
    with pytest.raises(LocationValidationError):
        context_from_manual("", None)


@pytest.mark.asyncio
async def test_known_destination_label_on_results(client: AsyncClient) -> None:
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
    page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert "Delivering to Taguig City 1630" in page.text
    assert "Change" in page.text
    assert 'data-location-state="known"' in page.text
    assert "Final effective cost" in page.text
    assert "We don’t need your exact home address" in page.text
    assert "street" not in page.text.lower() or "Street address" not in page.text
    assert "House number" not in page.text
    assert "Unit number" not in page.text


@pytest.mark.asyncio
async def test_unknown_destination_does_not_claim_known_shipping(
    client: AsyncClient,
) -> None:
    page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert 'data-location-state="absent"' in page.text
    assert "Price before shipping" in page.text
    assert 'data-price-state="price_before_shipping"' in page.text
    assert "Shipping to your area not yet verified" in page.text
    assert "Costs calculated for this delivery area" not in page.text


@pytest.mark.asyncio
async def test_skip_uses_price_before_shipping(client: AsyncClient) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "skip",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert 'data-location-state="skipped"' in page.text
    assert "Price before shipping" in page.text
    assert "No delivery location set" in page.text
    assert 'data-price-state="final_effective_cost"' not in page.text


@pytest.mark.asyncio
async def test_change_destination_does_not_keep_old_shipping(
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
    assert "Delivering to Taguig City 1630" in first.text
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
    assert "Delivering to Davao City 8000" in changed.text
    assert "Delivering to Taguig City 1630" not in changed.text
    assert "Shipping to Davao City 8000" in changed.text
    assert "Not verified" in changed.text
    assert "Shipping to Taguig" not in changed.text


@pytest.mark.asyncio
async def test_location_is_consistent_across_results_compare_why(
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
    results = await client.get("/results/headphones-standard")
    compare = await client.get("/compare/headphones-standard")
    why = await client.get("/why-best-piq/headphones-standard")
    for page in (results, compare, why):
        assert page.status_code == 200
        assert "Delivering to Taguig City 1630" in page.text
        assert page.headers.get("set-cookie") is None or DELIVERY_COOKIE not in (
            page.headers.get("set-cookie") or ""
        )


@pytest.mark.asyncio
async def test_browser_location_denial_still_has_manual_entry(
    client: AsyncClient,
) -> None:
    page = await client.get("/results/headphones-standard")
    assert "Use my location" in page.text
    assert "City / municipality" in page.text
    assert "Postal code — optional" in page.text
    assert "Skip for now" in page.text
    js = (await client.get("/static/consumer/js/consumer.js")).text
    assert "getCurrentPosition" in js
    assert "Location permission denied" in js
    assert js.index("getCurrentPosition") > js.index("js-use-location")


def test_location_prompt_copy_matches_approved_design() -> None:
    from app.consumer.location import DeliveryContext
    from app.consumer.pages import render_page

    html = render_page(
        build_page_view(
            decision_id="headphones-standard",
            page="results",
            location=DeliveryContext(),
            location_prompt=True,
        )
    )
    assert "Where should we calculate delivery to?" in html
    assert "Postal code helps improve shipping accuracy." in html
    assert "We don’t need your exact home address." in html
    assert 'name="street"' not in html
    assert 'name="house"' not in html
    assert 'name="unit"' not in html
