"""Unit tests for DealRecommendationService."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.entities.deal_score import DealListingAttributes
from app.domain.entities.marketplace_listing import (
    AvailabilityStatus,
    MarketplaceListing,
    MarketplaceSearchResult,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService


def _listing(
    product_id: str,
    *,
    price: float,
    marketplace: str = "shopee",
    rating: float | None = 4.8,
    availability: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
    seller: str = "Official Store",
) -> MarketplaceListing:
    return MarketplaceListing(
        marketplace=marketplace,
        product_id=product_id,
        title=f"Listing {product_id}",
        price=price,
        currency="PHP",
        seller=seller,
        rating=rating,
        url=f"https://example.com/{product_id}",
        availability=availability,
    )


def test_recommend_searches_and_ranks() -> None:
    marketplace = MagicMock(spec=MarketplaceIntelligenceService)
    marketplace.search.return_value = MarketplaceSearchResult(
        query="iPhone 17 Pro Max",
        results=(
            _listing("1001001", price=74_999.0, seller="Apple Authorized PH"),
            _listing(
                "2002001",
                price=74_500.0,
                marketplace="lazada",
                rating=4.95,
                seller="Lazada Apple Store",
            ),
        ),
    )
    service = DealRecommendationService(marketplace, WeightedDealScoreEngine())

    result = service.recommend("iPhone 17 Pro Max")

    marketplace.search.assert_called_once_with("iPhone 17 Pro Max")
    assert result.query == "iPhone 17 Pro Max"
    assert result.currency == "PHP"
    assert len(result.evaluations) == 2
    assert result.recommended_listing_id is not None
    assert result.evaluations[0].deal_score.rank == 1
    assert result.evaluations[1].deal_score.rank == 2


def test_evaluate_listings_preserves_all_alternatives() -> None:
    service = DealRecommendationService(
        MagicMock(spec=MarketplaceIntelligenceService),
        WeightedDealScoreEngine(),
    )
    listings = (
        _listing("a", price=10_000.0),
        _listing("b", price=10_500.0),
        _listing("c", price=11_000.0, availability=AvailabilityStatus.OUT_OF_STOCK),
    )
    attrs = {
        "a": DealListingAttributes(
            shipping_cost=0.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=7,
        ),
        "b": DealListingAttributes(
            shipping_cost=200.0,
            is_official_store=True,
            warranty_months=12,
            return_policy_days=7,
        ),
        "c": DealListingAttributes(
            shipping_cost=0.0,
            is_official_store=False,
            warranty_months=None,
            return_policy_days=None,
        ),
    }

    result = service.evaluate_listings("phones", listings, attrs)

    assert len(result.evaluations) == 3
    assert {e.deal_score.listing_id for e in result.evaluations} == {"a", "b", "c"}
    assert result.recommended_listing_id == "a"
