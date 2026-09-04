"""Sprint 37 MarketContext package.

Composes trusted-market, delivery, selected-shopping-market, and coverage
types. Does not execute live merchant research, certify PH, or convert
currencies.
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
    "DEFAULT_DISPLAY_CURRENCY",
    "DEFAULT_DISPLAY_LOCALE",
    "DESTINATION_SENSITIVE_COMPONENT_KINDS",
    "INTENDED_FIRST_MARKET_COUNTRY",
    "PRODUCT_FACING_SHOPPING_MARKETS",
    "CertifiedShoppingMarketCatalog",
    "DestinationInvalidation",
    "MarketContext",
    "SelectedShoppingMarket",
    "ShoppingMarketCoverage",
    "ShoppingMarketValidationError",
    "assert_destination_reevaluation_not_implemented",
    "assess_shopping_coverage",
    "compose_market_context",
    "connector_invocation_eligible",
    "intended_default_shopping_market",
    "intended_ph_product_defaults",
    "invalidate_for_destination_change",
    "mixed_currency_blocks_compare",
    "plan_authorized_research_if_coverage_allows",
    "production_certified_shopping_markets",
    "require_trusted_market",
    "resolve_selected_shopping_market",
    "select_dominant_price_state",
    "selected_shopping_market_from_code",
    "shopping_markets_for_tests",
    "trusted_market_from_selected",
]
