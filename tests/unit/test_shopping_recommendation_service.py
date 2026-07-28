"""Unit tests for ShoppingRecommendationService."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.entities.deal_score import DealListingAttributes, RankingResult
from app.domain.entities.marketplace_listing import (
    AvailabilityStatus,
    MarketplaceListing,
)
from app.domain.entities.recommendation import PurchaseDecision
from app.domain.exceptions import DealScoreValidationError
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.shopping_recommendation_service import ShoppingRecommendationService


def _listing(
    product_id: str,
    *,
    price: float,
    marketplace: str = "shopee",
    rating: float | None = 4.8,
    currency: str = "PHP",
    availability: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
) -> MarketplaceListing:
    return MarketplaceListing(
        marketplace=marketplace,
        product_id=product_id,
        title=f"Listing {product_id}",
        price=price,
        currency=currency,
        seller="Store",
        rating=rating,
        url=f"https://example.com/{product_id}",
        availability=availability,
    )


def test_recommend_from_listings_returns_recommendation_and_ranking() -> None:
    deal_service = DealRecommendationService(
        MagicMock(spec=MarketplaceIntelligenceService),
        WeightedDealScoreEngine(),
    )
    service = ShoppingRecommendationService(deal_service, RuleBasedRecommendationEngine())
    listings = (
        _listing("a", price=40_000.0, rating=4.9),
        _listing("b", price=41_000.0, marketplace="lazada", rating=4.6),
    )
    attrs = {
        "a": DealListingAttributes(
            shipping_cost=0.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=14,
        ),
        "b": DealListingAttributes(
            shipping_cost=0.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=7,
        ),
    }

    result = service.recommend_from_listings("phones", listings, attrs)

    assert result.query == "phones"
    assert result.currency == "PHP"
    assert result.recommendation.decision in PurchaseDecision
    assert len(result.ranking.evaluations) == 2
    assert result.recommendation.recommended_listing_id is not None


def test_mixed_currency_validation_maps_to_insufficient_information() -> None:
    deal_service = MagicMock(spec=DealRecommendationService)
    deal_service.recommend.side_effect = DealScoreValidationError(
        "Mixed currencies cannot be compared directly (PHP, USD)."
    )
    service = ShoppingRecommendationService(deal_service, RuleBasedRecommendationEngine())

    result = service.recommend("mixed query")

    assert result.recommendation.decision is PurchaseDecision.INSUFFICIENT_INFORMATION
    assert result.recommendation.recommended_listing_id is None
    assert "currency" in result.recommendation.summary.lower() or any(
        "currency" in w.text.lower() for w in result.recommendation.warnings
    )


def test_recommend_from_ranking_delegates_to_engine() -> None:
    engine = MagicMock(spec=RuleBasedRecommendationEngine)
    engine.recommend.return_value = MagicMock()
    service = ShoppingRecommendationService(
        MagicMock(spec=DealRecommendationService),
        engine,
    )
    ranking = RankingResult(
        query="q",
        currency="PHP",
        market_average_total_cost=0.0,
        recommended_listing_id=None,
        evaluations=(),
    )

    result = service.recommend_from_ranking(ranking)

    engine.recommend.assert_called_once_with(ranking)
    assert result.ranking is ranking
    assert result.recommendation is engine.recommend.return_value
