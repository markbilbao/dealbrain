"""Sprint 37.1 — PH MarketContext + truthful cost completeness."""

from __future__ import annotations

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.fixtures import DATA_CLASSIFICATION
from app.consumer.location import (
    DeliveryContext,
    LocationValidationError,
    context_from_manual,
    parse_delivery_cookie,
    skipped_context,
)
from app.consumer.pricing import (
    MoneyComponent,
    format_money,
    format_php,
    select_price_state,
    shipping_display,
    tax_display,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.entities.research_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
)
from app.domain.exceptions import DealScoreValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.dealscore.enrichment import (
    MOCK_DEAL_ATTRIBUTES,
    mock_deal_enrichment_is_production_evidence,
    resolve_deal_attributes,
)
from app.market.completeness import mixed_currency_blocks_compare, select_dominant_price_state
from app.market.context import (
    DEFAULT_DISPLAY_CURRENCY,
    DEFAULT_DISPLAY_LOCALE,
    INTENDED_FIRST_MARKET_COUNTRY,
    compose_market_context,
    intended_ph_product_defaults,
    require_trusted_market,
)
from app.market.invalidation import (
    DESTINATION_SENSITIVE_COMPONENT_KINDS,
    assert_destination_reevaluation_not_implemented,
    invalidate_for_destination_change,
)
from app.market.support import (
    production_certified_shopping_markets,
    shopping_markets_for_tests,
)
from app.services.canonical_offer_economics import capture_money_line

from tests.unit.intelligence.test_dealscore_engine import _listing as _score_listing
from tests.unit.test_canonical_uuid_consumer_presentation import _economics_snapshot


def _ship(status: str, amount: float | None, currency: str = "PHP") -> MoneyComponent:
    return MoneyComponent(
        kind="shipping",
        label="Shipping",
        amount=amount,
        currency=currency,
        status=status,  # type: ignore[arg-type]
    )


def _tax(status: str, amount: float | None = None) -> MoneyComponent:
    return MoneyComponent(
        kind="tax",
        label="Taxes / duties",
        amount=amount,
        status=status,  # type: ignore[arg-type]
    )


def test_ph_market_context_defaults_are_not_certification() -> None:
    context = intended_ph_product_defaults()
    assert context.country_code == INTENDED_FIRST_MARKET_COUNTRY == "PH"
    assert context.display_currency == DEFAULT_DISPLAY_CURRENCY == "PHP"
    assert context.display_locale == DEFAULT_DISPLAY_LOCALE == "en-PH"
    payload = context.to_dict()
    assert payload["shopping_market_certified"] is False
    assert payload["intended_first_market"] == "PH"
    assert production_certified_shopping_markets().is_certified("PH") is False


def test_missing_trusted_market_is_not_fabricated() -> None:
    context = compose_market_context(trusted_market=None, delivery=skipped_context())
    assert context.trusted_market is None
    assert context.country_code is None
    with pytest.raises(ValueError, match="must not be fabricated"):
        require_trusted_market(context)


def test_destination_states_and_optional_postal() -> None:
    absent = compose_market_context(trusted_market=None)
    skipped = compose_market_context(trusted_market=None, delivery=skipped_context())
    known = compose_market_context(
        trusted_market=None,
        delivery=context_from_manual("Cebu City", None),
    )
    with_postal = compose_market_context(
        trusted_market=None,
        delivery=context_from_manual("Taguig City", "1630"),
    )
    assert absent.destination_state == "absent"
    assert skipped.destination_state == "skipped"
    assert known.destination_state == "known"
    assert known.postal_code is None
    assert with_postal.postal_code == "1630"


def test_privacy_no_street_or_gps_persistence() -> None:
    context = intended_ph_product_defaults(delivery=context_from_manual("Taguig City", "1630"))
    payload = context.to_dict()
    cookie = context.delivery.to_cookie_payload()
    forbidden = {
        "street",
        "address",
        "building",
        "unit",
        "house",
        "latitude",
        "longitude",
        "gps",
        "coordinates",
        "history",
    }
    assert forbidden.isdisjoint(payload)
    assert forbidden.isdisjoint(cookie)
    leaked = parse_delivery_cookie(
        '{"city":"Taguig City","postal_code":"1630","skipped":false,'
        '"source":"manual","street":"1 Main","latitude":14.5,"history":["x"]}'
    )
    leaked_payload = leaked.to_cookie_payload()
    assert "street" not in leaked_payload
    assert "latitude" not in leaked_payload
    assert "history" not in leaked_payload
    with pytest.raises(LocationValidationError):
        context_from_manual("12 Main Street Apt 4", None)


def test_unknown_shipping_never_zero_or_free() -> None:
    unknown = _ship("unknown", None)
    captured = capture_money_line(unknown)
    assert captured.amount_minor is None
    assert shipping_display(unknown) == "Not verified"
    assert shipping_display(unknown) != "FREE"
    zero_unknown = _ship("unknown", 0.0)
    assert shipping_display(zero_unknown) == "Not verified"
    estimated_zero = _ship("estimated", 0.0)
    assert shipping_display(estimated_zero) != "FREE"
    free = _ship("verified", 0.0)
    assert shipping_display(free) == "FREE"


def test_unknown_tax_and_import_remain_unknown() -> None:
    tax = _tax("unknown")
    imports = MoneyComponent(kind="import", label="Import", amount=None, status="unknown")
    assert tax_display(tax) == "Not verified"
    assert tax_display(imports) == "Not verified"
    assert capture_money_line(tax).amount_minor is None
    assert capture_money_line(imports).amount_minor is None


def test_skipped_or_absent_cannot_be_final_effective_cost() -> None:
    unknown_ship = _ship("unknown", None)
    na_tax = _tax("not_applicable")
    for delivery in (DeliveryContext(), skipped_context()):
        market = intended_ph_product_defaults(delivery=delivery)
        state = select_dominant_price_state(
            market=market,
            shipping=unknown_ship,
            taxes=na_tax,
            import_charges=None,
            savings=(),
            international=False,
            shipping_material=True,
        )
        assert state == "price_before_shipping"
        assert state != "final_effective_cost"


def test_destination_change_invalidates_without_rewriting_decision() -> None:
    previous = intended_ph_product_defaults(delivery=context_from_manual("Taguig City", "1630"))
    current = intended_ph_product_defaults(delivery=context_from_manual("Cebu City", "6000"))
    result = invalidate_for_destination_change(previous, current)
    assert result.destination_changed is True
    assert result.destination_sensitive_economics_stale is True
    assert result.reevaluation_required is True
    assert result.canonical_snapshot_rewritten is False
    assert result.piqscore_rewritten is False
    assert result.recommendation_rewritten is False
    assert result.live_reevaluation_attempted is False
    assert frozenset({"shipping", "tax", "import"}) == DESTINATION_SENSITIVE_COMPONENT_KINDS


def test_destination_reevaluation_flag_remains_false() -> None:
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert_destination_reevaluation_not_implemented()


def test_unsupported_market_catalog_is_empty_and_blocks_connectors() -> None:
    production = production_certified_shopping_markets()
    assert production.to_tuple() == ()
    assert production.may_invoke_connector("PH") is False
    assert production.is_certified("PH") is False
    assert DATA_CLASSIFICATION == "non_live_contract_fixture"
    tests = shopping_markets_for_tests({"PH"})
    assert tests.is_certified("PH") is True
    assert production.is_certified("PH") is False


def test_source_currency_preserved_without_fx() -> None:
    assert format_money(1299, "USD") == "1,299 USD"
    assert format_money(1299, "PHP") == format_php(1299) == "₱1,299"
    assert mixed_currency_blocks_compare("USD", "PHP") is True
    assert mixed_currency_blocks_compare("PHP", "PHP") is False
    usd_ship = _ship("verified", 15, currency="USD")
    assert "₱" not in shipping_display(usd_ship)
    assert shipping_display(usd_ship) == "+15 USD"


def test_mixed_currency_still_fail_closed() -> None:
    engine = WeightedDealScoreEngine()
    with pytest.raises(DealScoreValidationError, match="Mixed currencies"):
        engine.rank(
            "mixed",
            [
                _score_listing("php", price=10_000.0, currency="PHP"),
                _score_listing("usd", price=200.0, currency="USD"),
            ],
        )
    assert mixed_currency_blocks_compare("USD", "PHP") is True


def test_canonical_uuid_session_change_does_not_rewrite_economics() -> None:
    snapshot = _economics_snapshot()
    digest = snapshot.content_sha256
    piq = snapshot.evaluated_products[0].canonical_piqscore.value
    reco = snapshot.recommendation.best_piq_product_id
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Cebu City", postal_code="6000", source="manual"),
    )
    assert view.location.city == "Taguig City"
    assert view.best_piq.economics.dominant_amount == 18990
    assert view.best_piq.piqscore.value == piq
    assert view.best_piq.product_id == reco
    assert view.session_location_differs is True
    assert view.destination_reevaluation_required is True
    assert view.shopping_market_certified is False
    assert snapshot.content_sha256 == digest
    assert snapshot.recommendation.best_piq_product_id == reco


def test_mock_shipping_zero_is_not_live_ph_evidence() -> None:
    assert mock_deal_enrichment_is_production_evidence() is False
    assert ("shopee", "1001001") in MOCK_DEAL_ATTRIBUTES
    assert MOCK_DEAL_ATTRIBUTES[("shopee", "1001001")].shipping_cost == 0.0
    unknown = MarketplaceListing(
        marketplace="shopee",
        product_id="not-a-mock-sku",
        title="Unknown listing",
        price=1000.0,
        currency="PHP",
        seller="Some Seller",
        rating=4.0,
        url="https://example.com/x",
        availability=AvailabilityStatus.IN_STOCK,
    )
    attrs = resolve_deal_attributes(unknown)
    assert attrs.shipping_cost is None
    mapped = MarketplaceListing(
        marketplace="shopee",
        product_id="1001001",
        title="Mock",
        price=1000.0,
        currency="PHP",
        seller="Apple Authorized PH",
        rating=4.9,
        url="https://example.com/m",
        availability=AvailabilityStatus.IN_STOCK,
    )
    fixture_attrs = resolve_deal_attributes(mapped)
    assert fixture_attrs.shipping_cost == 0.0
    assert mock_deal_enrichment_is_production_evidence() is False


def test_select_price_state_still_authoritative_for_known_complete_cost() -> None:
    state = select_price_state(
        shipping=_ship("verified", 0.0),
        taxes=_tax("not_applicable"),
        import_charges=None,
        savings=(),
        international=False,
        location_known=True,
        shipping_material=True,
    )
    assert state == "final_effective_cost"
