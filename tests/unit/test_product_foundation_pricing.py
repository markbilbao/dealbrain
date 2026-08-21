"""Product Foundation pricing-state and voucher/source truth tests."""

from __future__ import annotations

import pytest
from app.consumer.fixtures import CATALOG, _negative_voucher_examples
from app.consumer.location import DeliveryContext, skipped_context
from app.consumer.presentation import build_page_view
from app.consumer.pricing import (
    MoneyComponent,
    applicable_adjustment,
    evaluate_offer_total,
    select_price_state,
    shipping_display,
    tax_display,
)
from httpx import AsyncClient


def test_unknown_shipping_is_never_displayed_as_free() -> None:
    unknown = MoneyComponent(kind="shipping", label="Shipping", amount=None, status="unknown")
    assert shipping_display(unknown) == "Not verified"
    assert shipping_display(unknown) != "FREE"
    free = MoneyComponent(kind="shipping", label="Shipping", amount=0.0, status="verified")
    assert shipping_display(free) == "FREE"


def test_unknown_tax_is_not_automatically_zero() -> None:
    unknown = MoneyComponent(kind="tax", label="Taxes / duties", amount=None, status="unknown")
    assert tax_display(unknown) == "Not verified"
    assert tax_display(unknown) != "₱0"
    assert applicable_adjustment(unknown) == 0.0


def test_expired_and_unsupported_vouchers_are_not_applied() -> None:
    examples = _negative_voucher_examples()
    expired = examples["expired"]
    unsupported = examples["unsupported"]
    assert expired.voucher is not None
    assert unsupported.voucher is not None
    assert applicable_adjustment(expired.voucher) == 0.0
    assert applicable_adjustment(unsupported.voucher) == 0.0
    expired_total = evaluate_offer_total(
        expired.listing, (expired.voucher, expired.shipping, expired.taxes)
    )
    assert expired_total == expired.listing.amount
    unsupported_total = evaluate_offer_total(
        unsupported.listing,
        (unsupported.voucher, unsupported.shipping, unsupported.taxes),
    )
    assert unsupported_total == unsupported.listing.amount


def test_verified_voucher_changes_evaluated_cost_without_bonus_points() -> None:
    sony = CATALOG["headphones-standard"].offers[0]
    assert sony.voucher is not None
    total = evaluate_offer_total(sony.listing, (sony.voucher, sony.shipping, sony.taxes))
    assert total == 18990
    assert sony.piqscore == 92


def test_price_state_selection() -> None:
    known_ship = MoneyComponent(kind="shipping", label="Shipping", amount=0.0, status="verified")
    unknown_ship = MoneyComponent(kind="shipping", label="Shipping", amount=None, status="unknown")
    na_tax = MoneyComponent(
        kind="tax", label="Taxes / duties", amount=None, status="not_applicable"
    )
    estimated_ship = MoneyComponent(
        kind="shipping", label="International shipping", amount=1800, status="estimated"
    )
    estimated_import = MoneyComponent(
        kind="import", label="Estimated import charges", amount=1950, status="estimated"
    )
    unknown_import = MoneyComponent(
        kind="import", label="Estimated import charges", amount=None, status="unknown"
    )
    unverified_voucher = MoneyComponent(
        kind="voucher", label="Unverified checkout voucher", amount=-1000, status="unverified"
    )
    assert (
        select_price_state(
            shipping=known_ship,
            taxes=na_tax,
            import_charges=None,
            savings=(),
            international=False,
            location_known=True,
            shipping_material=True,
        )
        == "final_effective_cost"
    )
    assert (
        select_price_state(
            shipping=unknown_ship,
            taxes=na_tax,
            import_charges=None,
            savings=(),
            international=False,
            location_known=False,
            shipping_material=True,
        )
        == "price_before_shipping"
    )
    assert (
        select_price_state(
            shipping=estimated_ship,
            taxes=na_tax,
            import_charges=estimated_import,
            savings=(),
            international=True,
            location_known=True,
            shipping_material=True,
        )
        == "estimated_landed_cost"
    )
    assert (
        select_price_state(
            shipping=estimated_ship,
            taxes=na_tax,
            import_charges=unknown_import,
            savings=(),
            international=True,
            location_known=True,
            shipping_material=True,
        )
        == "before_unverified_import_charges"
    )
    assert (
        select_price_state(
            shipping=known_ship,
            taxes=na_tax,
            import_charges=None,
            savings=(unverified_voucher,),
            international=False,
            location_known=True,
            shipping_material=True,
        )
        == "potential_checkout_price"
    )


def test_skip_location_forces_price_before_shipping_on_standard_catalog() -> None:
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=skipped_context(),
    )
    assert view.best_piq.economics.dominant_state == "price_before_shipping"
    assert view.best_piq.economics.dominant_label == "Price before shipping"
    assert view.best_piq.economics.shipping.status == "unknown"
    assert view.best_piq.economics.breakdown_lines[2][1] != "FREE"


def test_known_taguig_keeps_verified_final_cost() -> None:
    view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.economics.dominant_state == "final_effective_cost"
    assert view.best_piq.economics.dominant_amount == 18990


def test_cross_border_estimated_landed_cost() -> None:
    view = build_page_view(
        decision_id="headphones-cross-border",
        page="why",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.economics.dominant_state == "estimated_landed_cost"
    assert view.best_piq.economics.dominant_amount == 20250
    assert view.best_piq.economics.import_charges is not None
    assert view.best_piq.economics.import_charges.status == "estimated"


def test_qualified_recommendation_price_before_shipping() -> None:
    view = build_page_view(
        decision_id="headphones-qualified",
        page="why",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.is_qualified
    assert view.best_piq.economics.dominant_state == "price_before_shipping"
    assert view.why_variant == "qualified"


def test_unverified_source_is_not_listed() -> None:
    view = build_page_view(
        decision_id="headphones-qualified",
        page="why",
        location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    names = {item.name for item in view.sources}
    assert names == {"Shopee"}
    assert "Reddit" not in names
    assert "YouTube" not in names


@pytest.mark.asyncio
async def test_pricing_labels_render_on_pages(client: AsyncClient) -> None:
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
    standard = await client.get("/results/headphones-standard")
    landed = await client.get("/why-best-piq/headphones-cross-border")
    qualified = await client.get("/why-best-piq/headphones-qualified")
    potential = await client.get("/why-best-piq/headphones-potential-checkout")
    unverified = await client.get("/why-best-piq/headphones-import-unverified")
    assert "Final effective cost" in standard.text
    assert "Estimated landed cost" in landed.text
    assert "Price before shipping" in qualified.text
    assert "Best Piq for You — Qualified" in qualified.text
    assert "Potential checkout price" in potential.text
    assert "Before unverified import charges" in unverified.text
    assert "Reddit" not in qualified.text
    assert "YouTube" not in qualified.text
    assert "Shopee" in qualified.text
