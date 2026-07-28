"""Integration tests for the shopping recommendation flow."""

from __future__ import annotations

import pytest
from app.core.dependencies import get_shopping_recommendation_service
from app.domain.entities.recommendation import PurchaseDecision
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.recommendation import RuleBasedRecommendationEngine
from app.main import create_app
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.shopping_recommendation_service import ShoppingRecommendationService
from httpx import ASGITransport, AsyncClient


def _build_service() -> ShoppingRecommendationService:
    marketplace = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()]
    )
    deal_service = DealRecommendationService(marketplace, WeightedDealScoreEngine())
    return ShoppingRecommendationService(deal_service, RuleBasedRecommendationEngine())


@pytest.mark.asyncio
async def test_recommendation_search_iphone_end_to_end() -> None:
    app = create_app()
    service = _build_service()
    app.dependency_overrides[get_shopping_recommendation_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get(
            "/api/v1/recommendations/search",
            params={"q": "iPhone 17 Pro Max 256GB"},
        )
        second = await client.get(
            "/api/v1/recommendations/search",
            params={"q": "iPhone 17 Pro Max 256GB"},
        )

    app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    payload = first.json()
    assert payload["currency"] == "PHP"
    assert payload["recommendation"]["decision"] in {
        d.value for d in PurchaseDecision
    }
    assert payload["recommendation"]["recommended_listing_id"] == "2002001"
    assert payload["recommendation"]["headline"]
    assert payload["recommendation"]["summary"]
    assert payload["recommendation"]["reasoning"]
    assert "confidence" in payload["recommendation"]
    assert payload["ranked_results"]
    corpus = " ".join(
        [
            payload["recommendation"]["headline"],
            payload["recommendation"]["summary"],
            *payload["recommendation"]["reasoning"],
            *payload["recommendation"]["tradeoffs"],
            *payload["recommendation"]["warnings"],
        ]
    ).lower()
    for fragment in ("will fall", "historically high", "price history", "sale is expected"):
        assert fragment not in corpus


@pytest.mark.asyncio
async def test_recommendation_search_no_matches() -> None:
    app = create_app()
    service = _build_service()
    app.dependency_overrides[get_shopping_recommendation_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/recommendations/search",
            params={"q": "zzzz-no-such-product-xyz"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"]["decision"] == "insufficient_information"
    assert payload["ranked_results"] == []


@pytest.mark.asyncio
async def test_openapi_includes_recommendations_route() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/recommendations/search" in paths


@pytest.mark.asyncio
async def test_demo_page_includes_shopping_recommendation_section() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/demo")
    assert response.status_code == 200
    html = response.text
    assert "Shopping Recommendation" in html
    assert "/api/v1/recommendations/search" in html
    assert "DealScore Engine" in html
