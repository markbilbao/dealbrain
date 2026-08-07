"""API and integration tests for DealScore search endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from app.core.dependencies import get_deal_recommendation_service
from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealRating,
    DealScore,
    DealScoreComponents,
    ListingEvaluation,
    RankingResult,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.exceptions import DealScoreValidationError
from app.main import create_app
from app.services.deal_recommendation_service import DealRecommendationService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def deal_service() -> MagicMock:
    return MagicMock(spec=DealRecommendationService)


@pytest.fixture
async def dealscore_client(deal_service: MagicMock) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_deal_recommendation_service] = lambda: deal_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _sample_ranking() -> RankingResult:
    listing = MarketplaceListing(
        marketplace="shopee",
        product_id="1001001",
        title="Apple iPhone 17 Pro Max 256GB Black Titanium",
        price=74_999.0,
        currency="PHP",
        seller="Apple Authorized PH",
        rating=4.9,
        url="https://shopee.ph/product/88001/1001001",
        availability=AvailabilityStatus.IN_STOCK,
    )
    deal_score = DealScore(
        listing_id="1001001",
        marketplace="shopee",
        score=92.5,
        rating=DealRating.EXCELLENT,
        rank=1,
        total_cost=74_999.0,
        components=DealScoreComponents(
            price_score=96.0,
            seller_score=90.0,
            shipping_score=100.0,
            availability_score=100.0,
            official_store_score=100.0,
            warranty_score=80.0,
            return_policy_score=75.0,
        ),
        explanation=("Total cost is 4.2% below the market average.", "Shipping is free."),
        warnings=(),
        applied_weights={
            "price": 0.35,
            "seller": 0.20,
            "shipping": 0.10,
            "availability": 0.10,
            "official_store": 0.10,
            "warranty": 0.10,
            "return_policy": 0.05,
        },
    )
    return RankingResult(
        query="iPhone 17 Pro Max",
        currency="PHP",
        market_average_total_cost=72_500.0,
        recommended_listing_id="1001001",
        evaluations=(
            ListingEvaluation(
                listing=listing,
                attributes=DealListingAttributes(
                    shipping_cost=0.0,
                    is_official_store=True,
                    warranty_months=12,
                    return_policy_days=7,
                ),
                deal_score=deal_score,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_dealscore_search_endpoint_success(
    dealscore_client: AsyncClient,
    deal_service: MagicMock,
) -> None:
    deal_service.recommend.return_value = _sample_ranking()

    response = await dealscore_client.get(
        "/api/v1/dealscore/search",
        params={"q": "iPhone 17 Pro Max"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "iPhone 17 Pro Max"
    assert data["currency"] == "PHP"
    assert data["market_average_total_cost"] == 72500.0
    assert data["recommended_listing_id"] == "1001001"
    assert len(data["results"]) == 1
    row = data["results"][0]
    assert row["rank"] == 1
    assert row["listing"]["product_id"] == "1001001"
    assert row["listing"]["total_cost"] == 74999.0
    assert row["deal_score"]["score"] == 92.5
    assert row["deal_score"]["rating"] == "excellent"
    assert row["deal_score"]["components"]["price_score"] == 96.0
    assert row["deal_score"]["explanation"]
    deal_service.recommend.assert_called_once_with("iPhone 17 Pro Max")


@pytest.mark.asyncio
async def test_dealscore_search_requires_query(dealscore_client: AsyncClient) -> None:
    response = await dealscore_client.get("/api/v1/dealscore/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_dealscore_mixed_currency_maps_to_400(
    dealscore_client: AsyncClient,
    deal_service: MagicMock,
) -> None:
    deal_service.recommend.side_effect = DealScoreValidationError(
        "Mixed currencies cannot be compared directly (PHP, USD)."
    )
    response = await dealscore_client.get(
        "/api/v1/dealscore/search",
        params={"q": "mixed"},
    )
    assert response.status_code == 400
    assert "Mixed currencies" in response.json()["detail"]


@pytest.mark.asyncio
async def test_dealscore_live_mocked_connectors(client: AsyncClient) -> None:
    """End-to-end against real DI-wired mock Shopee/Lazada connectors."""
    response = await client.get(
        "/api/v1/dealscore/search",
        params={"q": "iPhone 17 Pro Max"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "iPhone 17 Pro Max"
    assert data["currency"] == "PHP"
    assert data["recommended_listing_id"]
    assert len(data["results"]) >= 2

    ranks = [item["rank"] for item in data["results"]]
    assert ranks == list(range(1, len(ranks) + 1))
    assert data["results"][0]["deal_score"]["listing_id"] == data["recommended_listing_id"]

    for item in data["results"]:
        listing = item["listing"]
        deal = item["deal_score"]
        assert listing["currency"] == "PHP"
        assert "total_cost" in listing
        assert {"price_score", "seller_score", "shipping_score"} <= set(deal["components"])
        assert isinstance(deal["explanation"], list)
        assert isinstance(deal["warnings"], list)
        if listing["shipping_cost"] is not None:
            assert deal["total_cost"] == pytest.approx(
                listing["price"] + listing["shipping_cost"], abs=0.01
            )


@pytest.mark.asyncio
async def test_dealscore_airpods_deterministic(client: AsyncClient) -> None:
    first = await client.get("/api/v1/dealscore/search", params={"q": "AirPods"})
    second = await client.get("/api/v1/dealscore/search", params={"q": "AirPods"})
    assert first.status_code == 200
    assert first.json() == second.json()


@pytest.mark.asyncio
async def test_demo_page_includes_dealscore_section(client: AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    body = response.text
    assert "PiqScore Engine" in body
    assert "/api/v1/dealscore/search" in body
    assert "Product Parsing" in body
    assert "Product Matching" in body
    assert "Marketplace Intelligence" in body
