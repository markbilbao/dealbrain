"""Sprint 37 MarketContext package.

Composes trusted-market, delivery, selected-shopping-market, coverage, and
currency-authority types. Does not execute live merchant research, certify PH,
or convert currencies in production.
"""

from app.market.completeness import mixed_currency_blocks_compare, select_dominant_price_state
from app.market.context import (
    DEFAULT_DISPLAY_CURRENCY,
    DEFAULT_DISPLAY_LOCALE,
    INTENDED_FIRST_MARKET_COUNTRY,
    MarketContext,
    compose_market_context,
    intended_ph_product_defaults,
    require_trusted_market,
)
from app.market.coverage import (
    ShoppingMarketCoverage,
    assess_shopping_coverage,
    connector_invocation_eligible,
    plan_authorized_research_if_coverage_allows,
)
from app.market.currency import (
    CONVERSION_UNAVAILABLE_DISCLOSURE,
    MIXED_SOURCE_CURRENCY_DISCLOSURE,
    CurrencyConversion,
    OfferCurrencyAssessment,
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
    require_source_currency,
    resolve_production_fx_quote,
)
from app.market.invalidation import (
    DESTINATION_SENSITIVE_COMPONENT_KINDS,
    DestinationInvalidation,
    assert_destination_reevaluation_not_implemented,
    invalidate_for_destination_change,
)
from app.market.selection import (
    PRODUCT_FACING_SHOPPING_MARKETS,
    SelectedShoppingMarket,
    ShoppingMarketValidationError,
    intended_default_shopping_market,
    resolve_selected_shopping_market,
    selected_shopping_market_from_code,
    trusted_market_from_selected,
)
from app.market.support import (
    CertifiedShoppingMarketCatalog,
    production_certified_shopping_markets,
    shopping_markets_for_tests,
)

__all__ = [
    "CONVERSION_UNAVAILABLE_DISCLOSURE",
    "DEFAULT_DISPLAY_CURRENCY",
    "DEFAULT_DISPLAY_LOCALE",
    "DESTINATION_SENSITIVE_COMPONENT_KINDS",
    "INTENDED_FIRST_MARKET_COUNTRY",
    "MIXED_SOURCE_CURRENCY_DISCLOSURE",
    "PRODUCTION_FX_CONVERSION_ENABLED",
    "PRODUCT_FACING_SHOPPING_MARKETS",
    "TEST_FX_PROVIDER",
    "CertifiedShoppingMarketCatalog",
    "CurrencyAuthorityError",
    "CurrencyConversion",
    "DestinationInvalidation",
    "FxQuote",
    "MarketContext",
    "OfferCurrencyAssessment",
    "SelectedShoppingMarket",
    "ShoppingMarketCoverage",
    "ShoppingMarketValidationError",
    "assert_destination_reevaluation_not_implemented",
    "assess_offer_currencies",
    "assess_shopping_coverage",
    "compose_market_context",
    "connector_invocation_eligible",
    "fx_quote_for_tests",
    "intended_default_shopping_market",
    "intended_ph_product_defaults",
    "invalidate_for_destination_change",
    "mixed_currency_blocks_compare",
    "plan_authorized_research_if_coverage_allows",
    "production_certified_shopping_markets",
    "production_fx_conversion_enabled",
    "production_fx_quotes",
    "require_source_currency",
    "require_trusted_market",
    "resolve_currency_presentation",
    "resolve_production_currency_presentation",
    "resolve_production_fx_quote",
    "resolve_selected_shopping_market",
    "select_dominant_price_state",
    "selected_shopping_market_from_code",
    "shopping_markets_for_tests",
    "trusted_market_from_selected",
]
