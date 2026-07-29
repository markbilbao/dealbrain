"""Product matching package."""

from app.marketplace.matching.matcher import (
    AMBIGUOUS_THRESHOLD,
    SAFE_MATCH_THRESHOLD,
    CatalogEntry,
    MarketplaceProductMatcher,
)

__all__ = [
    "AMBIGUOUS_THRESHOLD",
    "SAFE_MATCH_THRESHOLD",
    "CatalogEntry",
    "MarketplaceProductMatcher",
]
