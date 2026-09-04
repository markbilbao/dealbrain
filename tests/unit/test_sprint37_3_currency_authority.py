"""Sprint 37.3 — currency authority + conversion-unavailable foundation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.currency_presentation import attach_currency_presentation
from app.consumer.location import DeliveryContext, context_from_manual, skipped_context
from app.consumer.pages import render_page
from app.consumer.presentation import build_page_view
from app.consumer.pricing import format_money, shipping_display, tax_display
from app.domain.entities.deal_score import (
    DealRating,
    DealScore,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
)
from app.domain.entities.recommendation import PurchaseDecision
from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.domain.exceptions import DealScoreValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.market.completeness import mixed_currency_blocks_compare
from app.market.context import DEFAULT_DISPLAY_LOCALE, intended_ph_product_defaults
from app.market.coverage import assess_shopping_coverage, connector_invocation_eligible
from app.market.currency import (
    CONVERSION_UNAVAILABLE_DISCLOSURE,
    MIXED_SOURCE_CURRENCY_DISCLOSURE,
    assess_offer_currencies,
    resolve_currency_presentation,
    resolve_production_currency_presentation,
)
from app.market.fx import (
    PRODUCTION_FX_CONVERSION_ENABLED,
    TEST_FX_PROVIDER,
    CurrencyAuthorityError,
    FxQuote,
    fx_quote_for_tests,
    production_fx_conversion_enabled,
    production_fx_quotes,
    resolve_production_fx_quote,
)
from app.market.invalidation import invalidate_for_destination_change
from app.market.selection import (
    intended_default_shopping_market,
    selected_shopping_market_from_code,
)
from app.market.support import production_certified_shopping_markets
from app.research.registry import production_research_provider_registry

from tests.unit.intelligence import test_recommendation_engine as reco_tests
from tests.unit.intelligence.test_dealscore_engine import _listing as _score_listing
from tests.unit.test_canonical_uuid_consumer_presentation import _economics_snapshot


def _usd_card(view, amount: float = 25.0):
    listing = replace(view.best_piq.economics.listing, amount=amount, currency="USD")
    economics = replace(view.best_piq.economics, listing=listing, dominant_amount=amount)
    return replace(view.best_piq, economics=economics)


def test_php_source_remains_php() -> None:
    resolved = resolve_production_currency_presentation(
        source_currency="PHP",
        source_amount=1299.0,
        preferred_currency="PHP",
    )
    assert resolved.source_currency == "PHP"
    assert resolved.preferred_currency == "PHP"
    assert resolved.state == "same_currency"
    assert resolved.source_amount == 1299.0
    assert resolved.converted_amount == 1299.0
    assert resolved.quote is None
    assert resolved.disclosure is None
    assert format_money(1299, "PHP") == "₱1,299"


def test_usd_source_remains_usd() -> None:
    resolved = resolve_production_currency_presentation(
        source_currency="USD",
        source_amount=25.0,
        preferred_currency="PHP",
    )
    assert resolved.source_currency == "USD"
    assert resolved.state == "conversion_unavailable"
    assert resolved.converted_amount is None
    assert resolved.quote is None
    assert format_money(25, "USD") == "25 USD"
    assert "₱" not in format_money(25, "USD")


def test_selected_ph_locale_and_delivery_do_not_mutate_usd() -> None:
    selected = selected_shopping_market_from_code("PH")
    delivery = context_from_manual("Taguig City", "1630")
    context = intended_ph_product_defaults(delivery=delivery)
    assert selected.country_code == "PH"
    assert context.display_locale == DEFAULT_DISPLAY_LOCALE == "en-PH"
    assert context.display_currency == "PHP"
    assert delivery.city == "Taguig City"
    resolved = resolve_production_currency_presentation(
        source_currency="USD",
        source_amount=25.0,
        preferred_currency=context.display_currency,
    )
    assert resolved.source_currency == "USD"
    assert resolved.converted_amount is None
    assert resolve_production_fx_quote("USD", "PHP") is None


def test_missing_source_currency_fails_closed() -> None:
    with pytest.raises(CurrencyAuthorityError, match="source currency"):
        resolve_currency_presentation(source_currency=None, source_amount=25.0)
    with pytest.raises(CurrencyAuthorityError, match="source currency"):
        resolve_currency_presentation(source_currency="", source_amount=25.0)
    with pytest.raises(CurrencyAuthorityError, match="must not be assumed"):
        resolve_currency_presentation(source_currency="12", source_amount=25.0)


def test_same_currency_php_requires_no_fx_quote() -> None:
    quote = fx_quote_for_tests(base_currency="USD", quote_currency="PHP", rate=56.0)
    resolved = resolve_currency_presentation(
        source_currency="php",
        source_amount=1299.0,
        preferred_currency="PHP",
        quote=quote,
    )
    assert resolved.state == "same_currency"
    assert resolved.source_amount == 1299.0
    assert resolved.converted_amount == 1299.0
    assert resolved.quote is None


def test_usd_to_php_without_quote_is_explicitly_unavailable() -> None:
    resolved = resolve_production_currency_presentation(
        source_currency="USD",
        source_amount=25.0,
        preferred_currency="PHP",
    )
    assert resolved.state == "conversion_unavailable"
    assert resolved.converted_amount is None
    assert resolved.quote is None
    assert resolved.disclosure == CONVERSION_UNAVAILABLE_DISCLOSURE
    payload = resolved.to_dict()
    assert payload["converted_amount"] is None
    assert payload["quote"] is None
    assert "1400" not in str(payload)


def test_mixed_php_usd_comparison_remains_fail_closed() -> None:
    assert mixed_currency_blocks_compare("PHP", "USD") is True
    assert mixed_currency_blocks_compare("PHP", "PHP") is False
    mixed = assess_offer_currencies(("PHP", "USD"), preferred_currency="PHP")
    assert mixed.mixed_source_currencies is True
    assert mixed.conversion_available is False
    assert mixed.state == "conversion_unavailable"
    assert mixed.disclosure == MIXED_SOURCE_CURRENCY_DISCLOSURE
    engine = WeightedDealScoreEngine()
    with pytest.raises(DealScoreValidationError, match="Mixed currencies"):
        engine.rank(
            "mixed",
            [
                _score_listing("php", price=1299.0, currency="PHP"),
                _score_listing("usd", price=25.0, currency="USD"),
            ],
        )


def test_test_only_quote_converts_deterministically_and_stays_out_of_production() -> None:
    quote = fx_quote_for_tests(
        base_currency="USD",
        quote_currency="PHP",
        rate=56.0,
        as_of=datetime(2030, 1, 1, tzinfo=UTC),
        quote_id="test-fx-usd-php",
    )
    assert quote.provider == TEST_FX_PROVIDER
    assert quote.live is False
    assert quote.production_eligible is False
    assert quote.freshness == "test_only"
    resolved = resolve_currency_presentation(
        source_currency="USD",
        source_amount=25.0,
        preferred_currency="PHP",
        quote=quote,
    )
    assert resolved.state == "conversion_available"
    assert resolved.converted_amount == 1400.0
    assert resolved.quote is not None
    assert resolved.quote.to_dict()["quote_id"] == "test-fx-usd-php"
    assert production_fx_quotes() == ()
    assert production_fx_conversion_enabled() is False
    assert PRODUCTION_FX_CONVERSION_ENABLED is False
    assert quote not in production_fx_quotes()
    with pytest.raises(CurrencyAuthorityError, match="production eligible"):
        FxQuote(
            base_currency="USD",
            quote_currency="PHP",
            rate=56.0,
            as_of=datetime(2030, 1, 1, tzinfo=UTC),
            provider=TEST_FX_PROVIDER,
            quote_id="leak",
            freshness="test_only",
            live=False,
            production_eligible=True,
        )
    with pytest.raises(CurrencyAuthorityError, match="cannot be marked live"):
        FxQuote(
            base_currency="USD",
            quote_currency="PHP",
            rate=56.0,
            as_of=datetime(2030, 1, 1, tzinfo=UTC),
            provider=TEST_FX_PROVIDER,
            quote_id="live-leak",
            freshness="test_only",
            live=True,
            production_eligible=False,
        )


def test_piqscore_and_recommendation_do_not_use_silent_fx() -> None:
    reco_tests.test_mixed_currencies_insufficient_information()
    a = ListingEvaluation(
        listing=reco_tests._listing("php", price=1299.0, currency="PHP"),
        attributes=reco_tests._attrs(),
        deal_score=DealScore(
            listing_id="php",
            marketplace="shopee",
            score=90.0,
            rating=DealRating.EXCELLENT,
            rank=1,
            total_cost=1299.0,
            components=DealScoreComponents(
                price_score=80,
                seller_score=90,
                shipping_score=100,
                availability_score=100,
                official_store_score=100,
                warranty_score=100,
                return_policy_score=100,
            ),
        ),
    )
    b = ListingEvaluation(
        listing=reco_tests._listing("usd", price=25.0, currency="USD", marketplace="lazada"),
        attributes=reco_tests._attrs(),
        deal_score=DealScore(
            listing_id="usd",
            marketplace="lazada",
            score=99.0,
            rating=DealRating.EXCELLENT,
            rank=2,
            total_cost=25.0,
            components=DealScoreComponents(
                price_score=100,
                seller_score=90,
                shipping_score=100,
                availability_score=100,
                official_store_score=100,
                warranty_score=100,
                return_policy_score=100,
            ),
        ),
    )
    rec = RuleBasedRecommendationEngine().recommend(
        RankingResult(
            query="mixed",
            currency="",
            market_average_total_cost=0.0,
            recommended_listing_id=None,
            evaluations=(a, b),
        )
    )
    assert rec.decision is PurchaseDecision.INSUFFICIENT_INFORMATION
    text = reco_tests._all_text(rec)
    assert "mixed currencies" in text
    assert "₱1,400" not in text
    assert "cheaper" not in text
    assert "saves" not in text


def test_results_compare_why_keep_source_currency_and_disclose() -> None:
    php_view = build_page_view(
        decision_id="headphones-standard",
        page="results",
        location=DeliveryContext(),
        selected_market=intended_default_shopping_market(),
    )
    assert php_view.currency_conversion_state == "same_currency"
    assert php_view.currency_conversion_disclosure is None
    assert php_view.source_currencies == ("PHP",)
    php_html = render_page(php_view)
    assert "currency-status" not in php_html
    assert 'data-currency-conversion-state="same_currency"' in php_html
    assert "₱" in php_html

    usd_card = _usd_card(php_view)
    usd_view = attach_currency_presentation(
        replace(php_view, best_piq=usd_card, alternatives=(), compared=(usd_card,))
    )
    usd_html = render_page(usd_view)
    assert usd_view.currency_conversion_state == "conversion_unavailable"
    assert usd_view.preferred_display_currency == "PHP"
    assert usd_view.source_currencies == ("USD",)
    assert "25 USD" in usd_html
    assert CONVERSION_UNAVAILABLE_DISCLOSURE in usd_html
    assert "₱1,400" not in usd_html
    assert "estimated" not in (usd_view.currency_conversion_disclosure or "").lower()

    php_card = php_view.best_piq
    mixed_view = attach_currency_presentation(
        replace(
            php_view,
            page="compare",
            best_piq=php_card,
            alternatives=(usd_card,),
            compared=(php_card, usd_card),
        )
    )
    mixed_html = render_page(mixed_view)
    assert mixed_view.currency_conversion_state == "conversion_unavailable"
    assert MIXED_SOURCE_CURRENCY_DISCLOSURE in mixed_html
    assert "25 USD" in mixed_html
    assert "this is cheaper" not in mixed_html.lower()
    assert "best price" not in mixed_html.lower()
    assert "saves ₱" not in mixed_html

    why_view = attach_currency_presentation(replace(mixed_view, page="why"))
    why_html = render_page(why_view)
    assert MIXED_SOURCE_CURRENCY_DISCLOSURE in why_html
    assert "saves ₱" not in why_html
    assert "this is cheaper" not in why_html.lower()


def test_sprint_37_1_shipping_and_destination_regressions() -> None:
    unknown_ship = php_view_component("shipping", None, "unknown")
    assert shipping_display(unknown_ship) == "Not verified"
    assert "FREE" not in shipping_display(unknown_ship)
    unknown_tax = php_view_component("tax", None, "unknown")
    assert tax_display(unknown_tax) == "Not verified"
    verified_zero = php_view_component("shipping", 0, "verified")
    assert shipping_display(verified_zero) == "FREE"
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    previous = intended_ph_product_defaults(delivery=context_from_manual("Taguig City", "1630"))
    current = intended_ph_product_defaults(delivery=context_from_manual("Cebu City", "6000"))
    result = invalidate_for_destination_change(previous, current)
    assert result.live_reevaluation_attempted is False
    assert result.piqscore_rewritten is False
    assert result.recommendation_rewritten is False
    skipped = intended_ph_product_defaults(delivery=skipped_context())
    assert skipped.destination_state == "skipped"
    assert skipped.destination_is_known_for_cost is False


def php_view_component(kind: str, amount: float | None, status: str):
    from app.consumer.pricing import MoneyComponent

    return MoneyComponent(kind=kind, label=kind, amount=amount, currency="PHP", status=status)


def test_sprint_37_2_market_and_certification_regressions() -> None:
    selected = intended_default_shopping_market()
    coverage = assess_shopping_coverage(selected)
    assert production_certified_shopping_markets().to_tuple() == ()
    assert production_certified_shopping_markets().is_certified("PH") is False
    assert coverage.certified is False
    assert coverage.connector_invocation_eligible is False
    assert connector_invocation_eligible(selected, display_currency="PHP") is False
    delivery = context_from_manual("Cebu City", "6000")
    assert selected.country_code == "PH"
    assert delivery.city == "Cebu City"
    assert "country" not in delivery.to_cookie_payload()
    assert production_research_provider_registry().list_providers() == ()


def test_production_fx_path_remains_zero() -> None:
    assert production_fx_quotes() == ()
    assert production_fx_conversion_enabled() is False
    assert resolve_production_fx_quote("USD", "PHP") is None
    assert production_certified_shopping_markets().to_tuple() == ()
    assert production_research_provider_registry().list_providers() == ()


def test_canonical_uuid_presentation_stays_php_same_currency() -> None:
    snapshot = _economics_snapshot()
    view = page_view_from_snapshot(
        snapshot,
        page="results",
        session_location=DeliveryContext(city="Cebu City", postal_code="6000", source="manual"),
    )
    assert view.preferred_display_currency == "PHP"
    assert view.currency_conversion_state == "same_currency"
    assert view.currency_conversion_disclosure is None
    assert view.shopping_market_certified is False
    assert view.best_piq.economics.listing.currency == "PHP"
    html = render_page(view)
    assert "conversion is not currently available" not in html
    assert view.destination_reevaluation_required is True
