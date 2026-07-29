"""API tests for Watchlists & Price Alerts endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.core.config import settings
from app.core.dependencies import (
    get_alert_repository,
    get_alert_service,
    get_notification_service,
    get_price_history_service,
    get_watchlist_repository,
    get_watchlist_service,
)
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.price_history.mock_fixture import IPHONE_DEMO_CANONICAL_PRODUCT_ID
from app.intelligence.watchlists import InMemoryWatchlistRepository, MockNotificationService
from app.main import create_app
from app.services.alert_service import AlertService
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.watchlist_service import WatchlistService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 28, 22, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_CANONICAL_PRODUCT_ID


@pytest.fixture
async def wl_client(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    # Sprint 19 adds Bearer-auth + ownership enforcement to these endpoints,
    # gated by ``settings.watchlists_require_auth`` (default True). These
    # Sprint 10 tests exercise the API without any Authorization header, so
    # disable the requirement here to keep them green without weakening the
    # production default.
    monkeypatch.setattr(settings, "watchlists_require_auth", False)
    repo = InMemoryWatchlistRepository()
    store = InMemoryPriceHistoryStore()
    price = PriceHistoryService(store, app_env="development")
    notifications = MockNotificationService(clock=lambda: FIXED_NOW)
    marketplace = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()]
    )
    deal = DealRecommendationService(
        marketplace_service=marketplace,
        deal_score_engine=WeightedDealScoreEngine(),
    )
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"api-id-{counter['n']}"

    watchlists = WatchlistService(
        repo,
        price_history_service=price,
        deal_recommendation_service=deal,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    alerts = AlertService(
        repo,
        repo,
        price_history_service=price,
        notification_service=notifications,
        deal_recommendation_service=deal,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )

    # Seed two price points so evaluation can detect drops / lows.
    for idx, amount in enumerate([76000.0, 72000.0]):
        await price.record_snapshot(
            PriceSnapshot(
                snapshot_id=UUID(f"cccccccc-0001-4000-8000-{idx + 1:012d}"),
                canonical_product_id=PRODUCT_ID,
                marketplace="shopee",
                listing_id=f"api-list-{idx}",
                currency="PHP",
                item_price=amount,
                shipping_cost=0.0,
                total_cost=amount,
                availability=AvailabilityStatus.IN_STOCK,
                observed_at=datetime(2026, 6, 10 + idx, 12, 0, tzinfo=UTC),
            )
        )

    app = create_app()
    app.dependency_overrides[get_watchlist_repository] = lambda: repo
    app.dependency_overrides[get_alert_repository] = lambda: repo
    app.dependency_overrides[get_notification_service] = lambda: notifications
    app.dependency_overrides[get_price_history_service] = lambda: price
    app.dependency_overrides[get_watchlist_service] = lambda: watchlists
    app.dependency_overrides[get_alert_service] = lambda: alerts

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_watchlist_crud_and_items(wl_client: AsyncClient) -> None:
    created = await wl_client.post(
        "/api/v1/watchlists",
        json={"name": "API phones", "owner_id": "demo", "enabled": True},
    )
    assert created.status_code == 200
    watchlist = created.json()
    assert watchlist["name"] == "API phones"
    watchlist_id = watchlist["watchlist_id"]

    item = await wl_client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={
            "canonical_product_id": PRODUCT_ID,
            "product_label": "iPhone 17 Pro Max",
            "target_price": 73000,
            "currency": "PHP",
            "search_query": "iPhone 17 Pro Max",
            "last_known_price": 76000,
            "last_known_dealscore": 70,
            "last_historical_low": 76000,
        },
    )
    assert item.status_code == 200
    payload = item.json()
    assert payload["canonical_product_id"] == PRODUCT_ID
    assert payload["price_available"] is True
    assert payload["current_price"] == 72000.0
    item_id = payload["item_id"]

    listed = await wl_client.get(f"/api/v1/watchlists/{watchlist_id}/items")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    patched = await wl_client.patch(
        f"/api/v1/watchlists/{watchlist_id}/items/{item_id}",
        json={"target_price": 71000},
    )
    assert patched.status_code == 200
    assert patched.json()["target_price"] == 71000

    deleted_item = await wl_client.delete(
        f"/api/v1/watchlists/{watchlist_id}/items/{item_id}"
    )
    assert deleted_item.status_code == 204

    # Re-add for later alert tests in other cases — create again.
    again = await wl_client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={
            "canonical_product_id": PRODUCT_ID,
            "target_price": 73000,
            "last_known_price": 76000,
            "last_historical_low": 76000,
        },
    )
    assert again.status_code == 200

    deleted = await wl_client.delete(f"/api/v1/watchlists/{watchlist_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_check_alerts_and_list(wl_client: AsyncClient) -> None:
    created = await wl_client.post(
        "/api/v1/watchlists",
        json={"name": "Alert list"},
    )
    watchlist_id = created.json()["watchlist_id"]
    await wl_client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={
            "canonical_product_id": PRODUCT_ID,
            "product_label": "iPhone",
            "target_price": 73000,
            "search_query": "iPhone 17 Pro Max",
            "last_known_price": 76000,
            "last_known_dealscore": 1.0,
            "last_historical_low": 76000,
        },
    )

    checked = await wl_client.post(f"/api/v1/watchlists/{watchlist_id}/check-alerts")
    assert checked.status_code == 200
    body = checked.json()
    assert body["items_checked"] == 1
    assert body["alerts_count"] >= 1
    assert body["notifications"]
    assert body["notifications"][0]["status"] == "queued"
    assert "No email" in body["disclaimer"] or "mock" in body["disclaimer"].lower()

    alerts = await wl_client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    assert alerts.json()["alerts"]

    alert_id = body["alerts_created"][0]["alert_id"]
    got = await wl_client.get(f"/api/v1/alerts/{alert_id}")
    assert got.status_code == 200

    acked = await wl_client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert acked.status_code == 200
    assert acked.json()["status"] == "acknowledged"

    wl_alerts = await wl_client.get(f"/api/v1/watchlists/{watchlist_id}/alerts")
    assert wl_alerts.status_code == 200


@pytest.mark.asyncio
async def test_check_all_alerts_endpoint(wl_client: AsyncClient) -> None:
    created = await wl_client.post("/api/v1/watchlists", json={"name": "Global"})
    watchlist_id = created.json()["watchlist_id"]
    await wl_client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={
            "canonical_product_id": PRODUCT_ID,
            "last_known_price": 76000,
            "target_price": 73000,
        },
    )
    response = await wl_client.post("/api/v1/watchlists/check-alerts")
    assert response.status_code == 200
    assert response.json()["items_checked"] == 1


@pytest.mark.asyncio
async def test_dismiss_alert_endpoint(wl_client: AsyncClient) -> None:
    created = await wl_client.post("/api/v1/watchlists", json={"name": "Dismiss API"})
    watchlist_id = created.json()["watchlist_id"]
    await wl_client.post(
        f"/api/v1/watchlists/{watchlist_id}/items",
        json={
            "canonical_product_id": PRODUCT_ID,
            "last_known_price": 76000,
            "target_price": 73000,
        },
    )
    checked = await wl_client.post(f"/api/v1/watchlists/{watchlist_id}/check-alerts")
    alert_id = checked.json()["alerts_created"][0]["alert_id"]
    dismissed = await wl_client.post(f"/api/v1/alerts/{alert_id}/dismiss")
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"
