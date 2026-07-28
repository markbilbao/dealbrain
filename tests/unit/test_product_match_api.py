"""API tests for Product Intelligence match endpoint."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.dependencies import get_product_intelligence_service
from app.domain.entities.product_match import MatchType, ProductMatchResult
from app.main import create_app
from app.services.product_intelligence_service import ProductIntelligenceService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def intelligence_service() -> MagicMock:
    service = MagicMock(spec=ProductIntelligenceService)
    service.parse_listing = AsyncMock()
    return service


@pytest.fixture
async def intelligence_client(
    intelligence_service: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_product_intelligence_service] = lambda: intelligence_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_match_endpoint_success(
    intelligence_client: AsyncClient,
    intelligence_service: MagicMock,
) -> None:
    intelligence_service.match_listings.return_value = ProductMatchResult(
        is_match=True,
        confidence=0.97,
        match_type=MatchType.EXACT_VARIANT,
        matched_fields=("brand", "family", "model", "storage", "color"),
        conflicts=(),
        explanation=(
            "Both listings resolve to Apple iPhone 17 Pro Max.",
            "Storage matches at 256GB.",
            "BT was normalized to Black Titanium.",
        ),
    )

    response = await intelligence_client.post(
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
    assert data["confidence"] == 0.97
    assert data["matched_fields"] == ["brand", "family", "model", "storage", "color"]
    assert data["conflicts"] == []
    assert len(data["explanation"]) == 3
    intelligence_service.match_listings.assert_called_once()


@pytest.mark.asyncio
async def test_match_endpoint_blank_title_validation(
    intelligence_client: AsyncClient,
) -> None:
    response = await intelligence_client.post(
        "/api/v1/intelligence/match",
        json={"title_a": "Apple IP17PM 256 BT", "title_b": "   "},
    )
    assert response.status_code == 422
