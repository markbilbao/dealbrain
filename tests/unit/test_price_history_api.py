"""API tests for Price History endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from app.core.dependencies import get_price_history_service
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import (
    MarketplacePriceSummary,
    PriceHistory,
    PriceHistorySearchResult,
    PriceSnapshot,
    PriceStatistics,
    PriceTrend,
)
from app.main import create_app
from app.services.price_history_service import PriceHistoryService
from httpx import ASGITransport, AsyncClient


def _sample_snapshot() -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id=UUID("aaaaaaaa-0001-4000-8000-000000000001"),
        canonical_product_id="00000000-0000-4000-8000-000000000017",
        marketplace="shopee",
        listing_id="1001001",
        seller_name="Apple Authorized PH",
        currency="PHP",
        item_price=74_999.0,
        shipping_cost=0.0,
        total_cost=74_999.0,
        availability=AvailabilityStatus.IN_STOCK,
        observed_at=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
    )


def _sample_stats() -> PriceStatistics:
    return PriceStatistics(
        currency="PHP",
        current_total_cost=74_500.0,
        lowest_recorded_total_cost=73_990.0,
        highest_recorded_total_cost=76_990.0,
        average_total_cost=75_120.0,
        median_total_cost=74_999.0,
        observation_count=12,
        first_observed=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        last_observed=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
        absolute_change=-2490.0,
        percentage_change=-3.23,
        trend=PriceTrend.FALLING,
    )


@pytest.fixture
def price_history_service() -> MagicMock:
    service = MagicMock(spec=PriceHistoryService)
    service.record_snapshots = AsyncMock()
    service.get_product_history = AsyncMock()
    service.get_listing_history = AsyncMock()
    service.search_and_record = AsyncMock()
    service.get_history_in_range = AsyncMock()
    return service


@pytest.fixture
async def price_history_client(
    price_history_service: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    app.dependency_overrides[get_price_history_service] = lambda: price_history_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_snapshots(
    price_history_client: AsyncClient,
    price_history_service: MagicMock,
) -> None:
    snap = _sample_snapshot()
    price_history_service.record_snapshots.return_value = [snap]
    response = await price_history_client.post(
        "/api/v1/price-history/snapshots",
        json={
            "snapshots": [
                {
                    "canonical_product_id": snap.canonical_product_id,
                    "marketplace": snap.marketplace,
                    "listing_id": snap.listing_id,
                    "currency": snap.currency,
                    "item_price": snap.item_price,
                    "shipping_cost": snap.shipping_cost,
                    "availability": snap.availability.value,
                    "observed_at": snap.observed_at.isoformat(),
                    "seller_name": snap.seller_name,
                    "snapshot_id": str(snap.snapshot_id),
                }
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["saved"]) == 1
    assert data["saved"][0]["total_cost"] == 74999.0


@pytest.mark.asyncio
async def test_get_product_history(
    price_history_client: AsyncClient,
    price_history_service: MagicMock,
) -> None:
    snap = _sample_snapshot()
    stats = _sample_stats()
    price_history_service.get_product_history.return_value = PriceHistory(
        canonical_product_id=snap.canonical_product_id,
        listing_id=None,
        currency="PHP",
        snapshots=(snap,),
        statistics=stats,
        marketplace_summaries=(
            MarketplacePriceSummary(
                marketplace="shopee",
                latest_total_cost=74_999.0,
                lowest_recorded_total_cost=73_990.0,
                average_total_cost=75_000.0,
                observation_count=6,
                latest_availability=AvailabilityStatus.IN_STOCK,
                last_observed=snap.observed_at,
            ),
        ),
    )
    response = await price_history_client.get(
        f"/api/v1/price-history/products/{snap.canonical_product_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["statistics"]["trend"] == "falling"
    assert "available PiqSavi history" in data["disclaimer"]
    assert data["marketplace_summaries"][0]["marketplace"] == "shopee"


@pytest.mark.asyncio
async def test_get_listing_history(
    price_history_client: AsyncClient,
    price_history_service: MagicMock,
) -> None:
    snap = _sample_snapshot()
    price_history_service.get_listing_history.return_value = PriceHistory(
        canonical_product_id=snap.canonical_product_id,
        listing_id=snap.listing_id,
        currency="PHP",
        snapshots=(snap,),
        statistics=_sample_stats(),
        marketplace_summaries=(),
    )
    response = await price_history_client.get("/api/v1/price-history/listings/1001001")
    assert response.status_code == 200
    assert response.json()["listing_id"] == "1001001"


@pytest.mark.asyncio
async def test_search_price_history(
    price_history_client: AsyncClient,
    price_history_service: MagicMock,
) -> None:
    snap = _sample_snapshot()
    price_history_service.search_and_record.return_value = PriceHistorySearchResult(
        query="iPhone 17 Pro Max",
        currency="PHP",
        statistics=_sample_stats(),
        history=(snap,),
        marketplace_summaries=(),
        canonical_product_id=snap.canonical_product_id,
        is_mock_history=True,
    )
    response = await price_history_client.get(
        "/api/v1/price-history/search",
        params={"q": "iPhone 17 Pro Max"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "iPhone 17 Pro Max"
    assert data["statistics"]["observation_count"] == 12
    assert data["statistics"]["trend"] == "falling"
    assert data["development_note"] == "Development history uses mocked observations."
    blob = str(data).lower()
    assert "forecast" not in blob
    assert "prediction" not in blob


@pytest.mark.asyncio
async def test_search_requires_query(price_history_client: AsyncClient) -> None:
    response = await price_history_client.get("/api/v1/price-history/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_live_price_history_search(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/price-history/search",
        params={"q": "iPhone 17 Pro Max"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "PHP"
    assert data["statistics"] is not None
    assert data["statistics"]["observation_count"] >= 3
    assert data["history"]
    assert data["marketplace_summaries"]
    assert "Lowest recorded price in the available PiqSavi history" in data["disclaimer"]


@pytest.mark.asyncio
async def test_demo_page_includes_price_intelligence(client: AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    body = response.text
    assert "Price Intelligence" in body
    assert "Development history uses mocked observations." in body
    assert "/api/v1/price-history/search" in body
    assert "Current recorded price" in body or "Load history" in body
    # No prediction features in the demo.
    assert "best future purchase date" not in body.lower()
    assert "buy next week" not in body.lower()
    assert "price-drop probability" not in body.lower()
    assert "expected sale date" not in body.lower()


@pytest.mark.asyncio
async def test_docs_lists_price_history(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/price-history/snapshots" in paths
    assert "/api/v1/price-history/search" in paths
    assert "/api/v1/price-history/products/{canonical_product_id}" in paths
    assert "/api/v1/price-history/listings/{listing_id}" in paths
