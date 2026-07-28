"""Integration tests: real parser + registry through the HTTP API."""

from collections.abc import AsyncGenerator

import pytest
from app.core.dependencies import get_product_intelligence_service
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.main import create_app
from app.services.product_intelligence_service import ProductIntelligenceService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def live_intelligence_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with real parser, matcher, and in-memory canonical registry."""
    app = create_app()
    parser = RuleBasedProductParser()
    service = ProductIntelligenceService(
        parser=parser,
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    app.dependency_overrides[get_product_intelligence_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_golden_listing_parse_and_registry(
    live_intelligence_client: AsyncClient,
) -> None:
    first = await live_intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "Apple IP17PM 256 BT"},
    )
    assert first.status_code == 200
    data = first.json()

    assert data["original_title"] == "Apple IP17PM 256 BT"
    assert data["canonical_product"]["brand"] == "Apple"
    assert data["canonical_product"]["family"] == "iPhone"
    assert data["canonical_product"]["model"] == "17 Pro Max"
    assert data["canonical_product"]["storage"] == "256GB"
    assert data["canonical_product"]["color"] == "Black Titanium"
    assert data["confidence"] == 0.98
    assert data["is_new_product"] is True
    assert data["canonical_product"]["id"]
    assert any(item["field"] == "family" for item in data["evidence"])
    assert any(item["matched_text"] == "IP17PM" for item in data["evidence"])

    second = await live_intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "Apple IP17PM 256 BT"},
    )
    assert second.status_code == 200
    again = second.json()
    assert again["is_new_product"] is False
    assert again["canonical_product"]["id"] == data["canonical_product"]["id"]


@pytest.mark.asyncio
async def test_unsupported_listing_returns_clear_error(
    live_intelligence_client: AsyncClient,
) -> None:
    response = await live_intelligence_client.post(
        "/api/v1/intelligence/parse",
        json={"title": "Totally unknown gadget XYZ"},
    )
    assert response.status_code == 422
    assert "Unsupported product listing" in response.json()["detail"]


@pytest.mark.asyncio
async def test_demo_and_docs_available(live_intelligence_client: AsyncClient) -> None:
    demo = await live_intelligence_client.get("/demo")
    docs = await live_intelligence_client.get("/docs")
    openapi = await live_intelligence_client.get("/openapi.json")

    assert demo.status_code == 200
    assert "Product Intelligence Demo" in demo.text
    assert docs.status_code == 200
    assert "/api/v1/intelligence/parse" in openapi.json()["paths"]
    assert "/api/v1/intelligence/match" in openapi.json()["paths"]


@pytest.mark.asyncio
async def test_match_endpoint_golden_pair(live_intelligence_client: AsyncClient) -> None:
    response = await live_intelligence_client.post(
        "/api/v1/intelligence/match",
        json={
            "title_a": "Apple iPhone 17 Pro Max 256GB Black Titanium",
            "title_b": "Apple IP17PM 256 BT",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_match"] is True
    assert data["match_type"] == "exact_variant"
    assert data["confidence"] >= 0.9
    assert "brand" in data["matched_fields"]
    assert "model" in data["matched_fields"]
    assert data["conflicts"] == []
    assert data["explanation"]
