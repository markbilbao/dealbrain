"""API tests for Product Intelligence parse endpoint and demo page."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.core.dependencies import get_product_intelligence_service
from app.domain.entities.canonical_product import ParseSignal
from app.domain.entities.registered_product import (
    CanonicalProductStatus,
    ParseListingResult,
    RegisteredCanonicalProduct,
)
from app.domain.exceptions import UnsupportedProductError
from app.main import create_app
from app.services.product_intelligence_service import ProductIntelligenceService
from httpx import ASGITransport, AsyncClient


PRODUCT_ID = uuid4()


def _sample_parse_result() -> ParseListingResult:
    return ParseListingResult(
        original_title="Apple IP17PM 256 BT",
        product=RegisteredCanonicalProduct(
            id=PRODUCT_ID,
            identity_key="apple/iphone/17-pro-max/256gb/black-titanium",
            brand="Apple",
            family="iPhone",
            model="17 Pro Max",
            storage="256GB",
            color="Black Titanium",
            display_name="Apple iPhone 17 Pro Max 256GB Black Titanium",
            status=CanonicalProductStatus.ACTIVE,
        ),
        confidence=0.98,
        is_new_product=True,
        signals=(
            ParseSignal("family", "iPhone", "family_model.apple", 1.0, "IP17PM"),
            ParseSignal("model", "17 Pro Max", "family_model.apple", 1.0, "IP17PM"),
        ),
    )


@pytest.fixture
def intelligence_service() -> AsyncMock:
    return AsyncMock(spec=ProductIntelligenceService)


@pytest.fixture
async def intelligence_client(
    intelligence_service: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_product_intelligence_service] = lambda: intelligence_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_parse_endpoint_success(
    intelligence_client: AsyncClient,
    intelligence_service: AsyncMock,
) -> None:
    intelligence_service.parse_listing.return_value = _sample_parse_result()

    response = await intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "Apple IP17PM 256 BT"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["original_title"] == "Apple IP17PM 256 BT"
    assert data["canonical_product"]["brand"] == "Apple"
    assert data["canonical_product"]["family"] == "iPhone"
    assert data["canonical_product"]["model"] == "17 Pro Max"
    assert data["canonical_product"]["storage"] == "256GB"
    assert data["canonical_product"]["color"] == "Black Titanium"
    assert data["confidence"] == 0.98
    assert data["is_new_product"] is True
    assert data["evidence"][0]["field"] == "family"
    intelligence_service.parse_listing.assert_awaited_once_with("Apple IP17PM 256 BT")


@pytest.mark.asyncio
async def test_parse_endpoint_blank_title_validation(
    intelligence_client: AsyncClient,
) -> None:
    response = await intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "   "},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("blank" in str(item.get("msg", "")).lower() for item in detail)


@pytest.mark.asyncio
async def test_parse_endpoint_unsupported_product(
    intelligence_client: AsyncClient,
    intelligence_service: AsyncMock,
) -> None:
    intelligence_service.parse_listing.side_effect = UnsupportedProductError(
        "Random junk",
        "Unsupported product listing: could not determine family, model",
    )

    response = await intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "Random junk"},
    )

    assert response.status_code == 422
    assert "Unsupported product listing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_demo_page_served(intelligence_client: AsyncClient) -> None:
    response = await intelligence_client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "DealBrain" in body
    assert "Product Intelligence Demo" in body
    assert "Product Matching" in body
    assert "Marketplace Intelligence" in body
    assert "/api/v1/intelligence/parse" in body
    assert "/api/v1/intelligence/match" in body
    assert "/api/v1/marketplace/search" in body
    assert "#0F172A" in body
    assert "#10B981" in body
