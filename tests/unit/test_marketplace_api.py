"""API tests for Marketplace Intelligence search endpoint."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from app.core.dependencies import get_marketplace_intelligence_service
from app.domain.entities.marketplace_listing import (
    AvailabilityStatus,
    MarketplaceListing,
    MarketplaceSearchResult,
)
from app.main import create_app
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def marketplace_service() -> MagicMock:
    return MagicMock(spec=MarketplaceIntelligenceService)


@pytest.fixture
async def marketplace_client(
    marketplace_service: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_marketplace_intelligence_service] = lambda: marketplace_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_marketplace_search_endpoint_success(
    marketplace_client: AsyncClient,
    marketplace_service: MagicMock,
) -> None:
    marketplace_service.search.return_value = MarketplaceSearchResult(
        query="iPhone 17 Pro Max",
        results=(
            MarketplaceListing(
                marketplace="shopee",
                product_id="1001001",
                title="Apple iPhone 17 Pro Max 256GB Black Titanium",
                price=74_999.0,
                currency="PHP",
                seller="Apple Authorized PH",
                rating=4.9,
                url="https://shopee.ph/product/88001/1001001",
                availability=AvailabilityStatus.IN_STOCK,
            ),
            MarketplaceListing(
                marketplace="lazada",
                product_id="2002001",
                title="Apple iPhone 17 Pro Max 256GB Black Titanium Official",
                price=74_500.0,
                currency="PHP",
                seller="Lazada Apple Store",
                rating=4.95,
                url="https://www.lazada.com.ph/products/i2002001.html",
                availability=AvailabilityStatus.IN_STOCK,
            ),
        ),
    )

    response = await marketplace_client.get(
        "/api/v1/marketplace/search",
        params={"q": "iPhone 17 Pro Max"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "iPhone 17 Pro Max"
    assert len(data["results"]) == 2
    assert data["results"][0] == {
        "marketplace": "shopee",
        "title": "Apple iPhone 17 Pro Max 256GB Black Titanium",
        "price": 74999.0,
        "currency": "PHP",
        "seller": "Apple Authorized PH",
        "rating": 4.9,
        "url": "https://shopee.ph/product/88001/1001001",
    }
    assert data["results"][1]["marketplace"] == "lazada"
    marketplace_service.search.assert_called_once_with("iPhone 17 Pro Max")


@pytest.mark.asyncio
async def test_marketplace_search_requires_query(
    marketplace_client: AsyncClient,
) -> None:
    response = await marketplace_client.get("/api/v1/marketplace/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_marketplace_search_live_mocked_connectors(client: AsyncClient) -> None:
    """Hit the real DI-wired mock connectors end-to-end."""
    response = await client.get(
        "/api/v1/marketplace/search",
        params={"q": "AirPods"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "AirPods"
    assert len(data["results"]) >= 2
    marketplaces = {item["marketplace"] for item in data["results"]}
    assert marketplaces == {"shopee", "lazada"}
    for item in data["results"]:
        assert {"marketplace", "title", "price", "currency", "seller", "rating", "url"} <= set(
            item
        )


@pytest.mark.asyncio
async def test_demo_page_includes_marketplace_search(client: AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    body = response.text
    assert "Marketplace Intelligence" in body
    assert "/api/v1/marketplace/search" in body
