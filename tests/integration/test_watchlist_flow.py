"""Integration flow: watchlist → price history → alert evaluation → mock notify."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.domain.entities.watchlist import AlertType, NotificationStatus
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.price_history.mock_fixture import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    load_iphone_demo_mock_history,
)
from app.intelligence.watchlists import InMemoryWatchlistRepository, MockNotificationService
from app.services.alert_service import AlertService
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.watchlist_service import WatchlistService

FIXED_NOW = datetime(2026, 7, 28, 23, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_CANONICAL_PRODUCT_ID


@pytest.mark.asyncio
async def test_watchlist_to_alerts_with_price_history_and_dealscore() -> None:
    repo = InMemoryWatchlistRepository()
    store = InMemoryPriceHistoryStore()
    await load_iphone_demo_mock_history(store, app_env="development")
    # Append a new low observation so historical-low / price-drop fire vs baselines.
    price = PriceHistoryService(store, app_env="development")
    await price.record_snapshot(
        PriceSnapshot(
            snapshot_id=UUID("dddddddd-0001-4000-8000-000000000099"),
            canonical_product_id=PRODUCT_ID,
            marketplace="shopee",
            listing_id="integration-low",
            currency="PHP",
            item_price=70000.0,
            shipping_cost=0.0,
            total_cost=70000.0,
            availability=AvailabilityStatus.IN_STOCK,
            observed_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
        )
    )

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
        return f"flow-{counter['n']}"

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

    wl = watchlists.create_watchlist(
        name="Integration watch",
        owner_id="demo",
        description="End-to-end Sprint 10 flow",
    )
    item = await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        product_label="iPhone 17 Pro Max 256GB",
        target_price=72000,
        currency="PHP",
        search_query="iPhone 17 Pro Max",
        last_known_price=74999,
        last_known_dealscore=1.0,
        last_historical_low=73990,
    )

    enriched = await watchlists.enrich_item(item)
    assert enriched.price_available is True
    assert enriched.current_price == 70000.0
    assert enriched.historical_low == 70000.0

    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    assert result.items_checked == 1
    assert len(result.alerts_created) >= 4
    types = {a.alert_type for a in result.alerts_created}
    assert AlertType.PRICE_DROP in types
    assert AlertType.TARGET_PRICE_REACHED in types
    assert AlertType.HISTORICAL_LOW in types
    assert AlertType.DEALSCORE_IMPROVED in types
    assert all(n.status == NotificationStatus.QUEUED for n in result.notifications)
    assert len(notifications.receipts) == len(result.alerts_created)

    # Baselines updated after evaluation.
    refreshed = watchlists.get_item(item.item_id)
    assert refreshed.last_known_price == 70000.0
    assert refreshed.last_historical_low == 70000.0
    assert refreshed.last_known_dealscore is not None
    assert refreshed.last_known_dealscore > 1.0

    # Second evaluation with unchanged prices should not re-fire price_drop.
    second = await alerts.evaluate_watchlist(wl.watchlist_id)
    second_types = {a.alert_type for a in second.alerts_created}
    assert AlertType.PRICE_DROP not in second_types

    listed = alerts.list_alerts(watchlist_id=wl.watchlist_id, limit=20)
    assert len(listed) >= 4
