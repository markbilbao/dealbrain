"""Domain entities and value objects for Product Identity."""

from app.domain.entities.canonical_product import CanonicalProduct, ParseSignal
from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealRating,
    DealScore,
    DealScoreComponent,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
    ScoreableListing,
    rating_for_score,
)
from app.domain.entities.marketplace_listing import (
    AvailabilityStatus,
    MarketplaceListing,
    MarketplaceSearchResult,
)
from app.domain.entities.product_match import (
    FieldCompareStatus,
    FieldConflict,
    MatchType,
    ProductMatchResult,
)
from app.domain.entities.product_relation import (
    ProductRelation,
    ProductRelationType,
    RelationDirection,
)
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    ParseListingResult,
    RegisteredCanonicalProduct,
    RegistryResolveResult,
)

__all__ = [
    "AvailabilityStatus",
    "CanonicalProduct",
    "CanonicalProductStatus",
    "DealListingAttributes",
    "DealRating",
    "DealScore",
    "DealScoreComponent",
    "DealScoreComponents",
    "FieldCompareStatus",
    "FieldConflict",
    "ListingEvaluation",
    "MarketplaceListing",
    "MarketplaceSearchResult",
    "MatchType",
    "ParseListingResult",
    "ParseSignal",
    "ProductMatchResult",
    "ProductRelation",
    "ProductRelationType",
    "RankingResult",
    "RegisteredCanonicalProduct",
    "RegistryResolveResult",
    "RelationDirection",
    "ScoreableListing",
    "rating_for_score",
]
