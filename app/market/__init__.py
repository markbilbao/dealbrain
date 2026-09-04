"""Sprint 37.1 PH MarketContext package.

Composes existing trusted-market and delivery types. Does not execute live
merchant research, certify PH, or convert currencies.
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
from app.market.invalidation import (
    DESTINATION_SENSITIVE_COMPONENT_KINDS,
    DestinationInvalidation,
    assert_destination_reevaluation_not_implemented,
    invalidate_for_destination_change,
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
    "CertifiedShoppingMarketCatalog",
    "DestinationInvalidation",
    "MarketContext",
    "assert_destination_reevaluation_not_implemented",
    "compose_market_context",
    "intended_ph_product_defaults",
    "invalidate_for_destination_change",
    "mixed_currency_blocks_compare",
    "production_certified_shopping_markets",
    "require_trusted_market",
    "select_dominant_price_state",
    "shopping_markets_for_tests",
]
