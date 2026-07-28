"""API tests for shopping recommendation search endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from app.core.dependencies import get_shopping_recommendation_service
from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealRating,
    DealScore,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.entities.recommendation import (
    PurchaseDecision,
    Recommendation,
    RecommendationConfidence,
    RecommendationReason,
    ShoppingRecommendationResult,
)
from app.main import create_app
from app.services.shopping_recommendation_service import ShoppingRecommendationService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def shopping_service() -> MagicMock:
    return MagicMock(spec=ShoppingRecommendationService)


@pytest.fixture
async def recommendation_client(
    shopping_service: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_shopping_recommendation_service] = lambda: shopping_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _sample_result() -> ShoppingRecommendationResult:
    listing = MarketplaceListing(
        marketplace="lazada",
        product_id="2002001",
        title="Apple iPhone 17 Pro Max 256GB",
        price=74_500.0,
        currency="PHP",
        seller="Lazada Apple Store",
        rating=4.95,
        url="https://www.lazada.com.ph/products/i2002001.html",
        availability=AvailabilityStatus.IN_STOCK,
    )
    deal_score = DealScore(
        listing_id="2002001",
        marketplace="lazada",
        score=93.0,
        rating=DealRating.EXCELLENT,
        rank=1,
        total_cost=74_500.0,
        components=DealScoreComponents(
            price_score=80.7,
            seller_score=99.0,
            shipping_score=100.0,
            availability_score=100.0,
            official_store_score=100.0,
            warranty_score=100.0,
            return_policy_score=100.0,
        ),
        explanation=("Shipping is free.",),
        warnings=(),
    )
    ranking = RankingResult(
        query="iPhone 17 Pro Max 256GB",
        currency="PHP",
        market_average_total_cost=74_749.5,
        recommended_listing_id="2002001",
        evaluations=(
            ListingEvaluation(
                listing=listing,
                attributes=DealListingAttributes(
                    shipping_cost=0.0,
                    is_official_store=True,
                    warranty_months=12,
                    return_policy_days=14,
                ),
                deal_score=deal_score,
            ),
        ),
    )
    recommendation = Recommendation(
        decision=PurchaseDecision.BUY,
        recommended_listing_id="2002001",
        headline="Best overall value",
        summary="The Lazada official-store listing is the strongest overall purchase.",
        reasoning=(
            RecommendationReason(
                text="It has a DealScore of 93.0, the highest among the available listings.",
                rank=1,
            ),
        ),
        tradeoffs=(),
        warnings=(),
        confidence=RecommendationConfidence(value=0.94, factors=("comparable_listings:2",)),
        alternatives=(),
    )
    return ShoppingRecommendationResult(
        query="iPhone 17 Pro Max 256GB",
        currency="PHP",
        recommendation=recommendation,
        ranking=ranking,
    )


@pytest.mark.asyncio
async def test_recommendations_search_endpoint(
    recommendation_client: AsyncClient,
    shopping_service: MagicMock,
) -> None:
    shopping_service.recommend.return_value = _sample_result()

    response = await recommendation_client.get(
        "/api/v1/recommendations/search",
        params={"q": "iPhone 17 Pro Max 256GB"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "iPhone 17 Pro Max 256GB"
    assert payload["currency"] == "PHP"
    assert payload["recommendation"]["decision"] == "buy"
    assert payload["recommendation"]["recommended_listing_id"] == "2002001"
    assert payload["recommendation"]["confidence"] == 0.94
    assert payload["ranked_results"]
    shopping_service.recommend.assert_called_once_with("iPhone 17 Pro Max 256GB")


@pytest.mark.asyncio
async def test_recommendations_search_requires_query(
    recommendation_client: AsyncClient,
) -> None:
    response = await recommendation_client.get("/api/v1/recommendations/search")
    assert response.status_code == 422
