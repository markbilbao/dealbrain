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
from app.domain.entities.price_history import (
    MarketplacePriceSummary,
    PriceHistory,
    PriceHistorySearchResult,
    PriceSnapshot,
    PriceStatistics,
    PriceTrend,
)
from app.domain.entities.product_relation import (
    ProductRelation,
    ProductRelationType,
    RelationDirection,
)
from app.domain.entities.recommendation import (
    AlternativeRecommendation,
    PurchaseDecision,
    Recommendation,
    RecommendationConfidence,
    RecommendationReason,
    RecommendationTradeoff,
    RecommendationWarning,
    ShoppingRecommendationResult,
)
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    ParseListingResult,
    RegisteredCanonicalProduct,
    RegistryResolveResult,
)

__all__ = [
    "AlternativeRecommendation",
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
    "PriceHistory",
    "PriceHistorySearchResult",
    "PriceSnapshot",
    "PriceStatistics",
    "PriceTrend",
    "MarketplacePriceSummary",
    "ProductMatchResult",
    "ProductRelation",
    "ProductRelationType",
    "PurchaseDecision",
    "RankingResult",
    "Recommendation",
    "RecommendationConfidence",
    "RecommendationReason",
    "RecommendationTradeoff",
    "RecommendationWarning",
    "RegisteredCanonicalProduct",
    "RegistryResolveResult",
    "RelationDirection",
    "ScoreableListing",
    "ShoppingRecommendationResult",
    "rating_for_score",
]
