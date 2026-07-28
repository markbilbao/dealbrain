"""Unit tests for WatchlistService and AlertService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.domain.entities.watchlist import AlertStatus, AlertType, NotificationStatus
from app.domain.exceptions import (
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
    WatchlistValidationError,
)
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.price_history.mock_fixture import IPHONE_DEMO_CANONICAL_PRODUCT_ID
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.intelligence.watchlists import InMemoryWatchlistRepository, MockNotificationService
from app.services.alert_service import AlertService
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from app.services.watchlist_service import WatchlistService

FIXED_NOW = datetime(2026, 7, 28, 21, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_CANONICAL_PRODUCT_ID


def _build_stack() -> tuple[
    WatchlistService,
    AlertService,
    InMemoryWatchlistRepository,
    InMemoryPriceHistoryStore,
    MockNotificationService,
]:
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
    registry = CanonicalProductRegistryService(InMemoryCanonicalProductStore())
    ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=registry,
        matcher=ExactVariantProductMatcher(),
    )
    watchlists = WatchlistService(
        repo,
        price_history_service=price,
        deal_recommendation_service=deal,
        canonical_registry=registry,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "fixed-id",
    )
    # Deterministic but unique IDs for items/alerts in multi-create tests.
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"id-{counter['n']}"

    watchlists._id_factory = next_id  # noqa: SLF001
    alerts = AlertService(
        repo,
        repo,
        price_history_service=price,
        notification_service=notifications,
        deal_recommendation_service=deal,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    return watchlists, alerts, repo, store, notifications


async def _seed_snapshots(
    store: InMemoryPriceHistoryStore,
    *,
    prices: list[float],
    product_id: str = PRODUCT_ID,
) -> None:
    price_svc = PriceHistoryService(store, app_env="development")
    for idx, amount in enumerate(prices):
        await price_svc.record_snapshot(
            PriceSnapshot(
                snapshot_id=UUID(f"bbbbbbbb-0001-4000-8000-{idx + 1:012d}"),
                canonical_product_id=product_id,
                marketplace="shopee",
                listing_id=f"list-{idx}",
                currency="PHP",
                item_price=amount,
                shipping_cost=0.0,
                total_cost=amount,
                availability=AvailabilityStatus.IN_STOCK,
                observed_at=datetime(2026, 6, 1 + idx, 12, 0, tzinfo=UTC),
                seller_name="Demo Seller",
            )
        )


@pytest.mark.asyncio
async def test_watchlist_crud() -> None:
    watchlists, _, _, _, _ = _build_stack()
    created = watchlists.create_watchlist(name="Phones", owner_id="u1")
    assert created.name == "Phones"
    assert created.enabled is True

    fetched = watchlists.get_watchlist(created.watchlist_id)
    assert fetched.watchlist_id == created.watchlist_id

    updated = watchlists.update_watchlist(created.watchlist_id, name="Phones v2")
    assert updated.name == "Phones v2"

    listed = watchlists.list_watchlists()
    assert len(listed) == 1

    watchlists.delete_watchlist(created.watchlist_id)
    with pytest.raises(WatchlistNotFoundError):
        watchlists.get_watchlist(created.watchlist_id)


@pytest.mark.asyncio
async def test_watchlist_validation() -> None:
    watchlists, _, _, _, _ = _build_stack()
    with pytest.raises(WatchlistValidationError, match="blank"):
        watchlists.create_watchlist(name="  ")


@pytest.mark.asyncio
async def test_item_crud_and_duplicate_protection() -> None:
    watchlists, _, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[76000.0, 74500.0])
    wl = watchlists.create_watchlist(name="Track")
    item = await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        product_label="iPhone",
        target_price=74000,
        last_known_price=76000,
    )
    assert item.canonical_product_id == PRODUCT_ID

    with pytest.raises(WatchlistValidationError, match="already on watchlist"):
        await watchlists.add_item(
            wl.watchlist_id,
            canonical_product_id=PRODUCT_ID,
        )

    updated = watchlists.update_item(item.item_id, target_price=73000)
    assert updated.target_price == 73000

    watchlists.delete_item(item.item_id)
    with pytest.raises(WatchlistItemNotFoundError):
        watchlists.get_item(item.item_id)


@pytest.mark.asyncio
async def test_enrich_item_reads_price_history() -> None:
    watchlists, _, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[76000.0, 74500.0, 73990.0])
    wl = watchlists.create_watchlist(name="Enrich")
    item = await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        product_label="iPhone",
    )
    snapshot = await watchlists.enrich_item(item)
    assert snapshot.price_available is True
    assert snapshot.current_price == 73990.0
    assert snapshot.historical_low == 73990.0
    assert snapshot.observation_count == 3


@pytest.mark.asyncio
async def test_price_drop_and_target_alerts() -> None:
    watchlists, alerts, _, store, notifications = _build_stack()
    await _seed_snapshots(store, prices=[78000.0, 75000.0, 72000.0])
    wl = watchlists.create_watchlist(name="Drops")
    await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        product_label="iPhone",
        target_price=73000,
        last_known_price=75000,
        last_historical_low=75000,
    )
    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    types = {a.alert_type for a in result.alerts_created}
    assert AlertType.PRICE_DROP in types
    assert AlertType.TARGET_PRICE_REACHED in types
    assert all(n.status == NotificationStatus.QUEUED for n in result.notifications)
    assert all(a.status == AlertStatus.NOTIFIED for a in result.alerts_created)
    assert notifications.receipts


@pytest.mark.asyncio
async def test_historical_low_alert() -> None:
    watchlists, alerts, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[80000.0, 77000.0, 71000.0])
    wl = watchlists.create_watchlist(name="Lows")
    await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        last_known_price=77000,
        last_historical_low=77000,
    )
    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    types = {a.alert_type for a in result.alerts_created}
    assert AlertType.HISTORICAL_LOW in types


@pytest.mark.asyncio
async def test_dealscore_improved_alert() -> None:
    watchlists, alerts, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[75000.0, 74500.0])
    wl = watchlists.create_watchlist(name="Score")
    await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        search_query="iPhone 17 Pro Max",
        last_known_dealscore=1.0,  # artificially low so any real score improves
        last_known_price=74500,
    )
    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    types = {a.alert_type for a in result.alerts_created}
    assert AlertType.DEALSCORE_IMPROVED in types


@pytest.mark.asyncio
async def test_evaluate_all_skips_disabled_watchlists() -> None:
    watchlists, alerts, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[76000.0, 70000.0])
    enabled = watchlists.create_watchlist(name="On")
    disabled = watchlists.create_watchlist(name="Off", enabled=False)
    await watchlists.add_item(
        enabled.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        last_known_price=76000,
        target_price=71000,
    )
    await watchlists.add_item(
        disabled.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        last_known_price=76000,
        target_price=71000,
    )
    result = await alerts.evaluate_all()
    assert enabled.watchlist_id in result.watchlist_ids
    assert disabled.watchlist_id not in result.watchlist_ids
    assert result.items_checked == 1


@pytest.mark.asyncio
async def test_acknowledge_and_list_alerts() -> None:
    watchlists, alerts, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[76000.0, 70000.0])
    wl = watchlists.create_watchlist(name="Ack")
    await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        last_known_price=76000,
        target_price=71000,
    )
    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    assert result.alerts_created
    alert_id = result.alerts_created[0].alert_id
    acked = alerts.acknowledge_alert(alert_id)
    assert acked.status == AlertStatus.ACKNOWLEDGED
    listed = alerts.list_alerts(watchlist_id=wl.watchlist_id)
    assert any(a.alert_id == alert_id for a in listed)


@pytest.mark.asyncio
async def test_dismiss_alert_and_disabled_item_skipped() -> None:
    watchlists, alerts, _, store, _ = _build_stack()
    await _seed_snapshots(store, prices=[76000.0, 70000.0])
    wl = watchlists.create_watchlist(name="Dismiss")
    item = await watchlists.add_item(
        wl.watchlist_id,
        canonical_product_id=PRODUCT_ID,
        last_known_price=76000,
        target_price=71000,
    )
    result = await alerts.evaluate_watchlist(wl.watchlist_id)
    alert_id = result.alerts_created[0].alert_id
    dismissed = alerts.dismiss_alert(alert_id)
    assert dismissed.status == AlertStatus.DISMISSED

    # Disabled items are skipped on subsequent evaluation.
    watchlists.update_item(item.item_id, enabled=False)
    again = await alerts.evaluate_watchlist(wl.watchlist_id)
    assert again.items_checked == 0
    assert again.alerts_created == ()


@pytest.mark.asyncio
async def test_negative_target_price_rejected() -> None:
    watchlists, _, _, _, _ = _build_stack()
    wl = watchlists.create_watchlist(name="Bad target")
    with pytest.raises(WatchlistValidationError, match="non-negative"):
        await watchlists.add_item(
            wl.watchlist_id,
            canonical_product_id=PRODUCT_ID,
            target_price=-1,
        )


@pytest.mark.asyncio
async def test_evaluate_missing_watchlist_raises() -> None:
    _, alerts, _, _, _ = _build_stack()
    with pytest.raises(WatchlistNotFoundError):
        await alerts.evaluate_watchlist("missing-wl")
