"""Unit tests for the Sprint 19 User Dashboard.

Covers the pure ``app.dashboard.assembler`` functions directly (summaries,
cards) and the ``UserDashboardService`` orchestration layer (source-mode
freshness labels, potential-savings caveats, activity feed).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from app.alerts.memory import InMemoryAlertRuleRepository
from app.dashboard.assembler import assemble_dashboard, build_summary
from app.domain.entities.alerts import AlertCondition, AlertConditionType
from app.domain.entities.dashboard import DASHBOARD_LIMITATIONS_NOTE, DashboardCardType
from app.domain.entities.marketplace_data import SOURCE_MODE_LABELS, SourceMode
from app.domain.entities.watchlist import WatchlistItem, WatchlistItemSnapshot
from app.domain.exceptions import DashboardValidationError
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.services.alert_rule_service import AlertRuleService
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.price_history_service import PriceHistoryService
from app.services.user_dashboard_service import UserDashboardService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.watchlists.memory import InMemoryWatchlistStore

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _item(
    item_id: str, *, last_known_price: float | None, watchlist_id: str = "wl-1"
) -> WatchlistItem:
    return WatchlistItem(
        item_id=item_id,
        watchlist_id=watchlist_id,
        canonical_product_id=f"prod-{item_id}",
        created_at=FIXED_NOW,
        updated_at=FIXED_NOW,
        last_known_price=last_known_price,
    )


def _snapshot(
    item: WatchlistItem, *, current_price: float | None, price_available: bool = True
) -> WatchlistItemSnapshot:
    return WatchlistItemSnapshot(
        item=item,
        current_price=current_price,
        historical_low=current_price,
        currency="PHP",
        observation_count=1 if price_available else 0,
        price_available=price_available,
    )


# --------------------------------------------------------------------- build_summary


def test_build_summary_computes_potential_savings_conservatively() -> None:
    dropped = _snapshot(_item("i1", last_known_price=100.0), current_price=80.0)
    unchanged = _snapshot(_item("i2", last_known_price=50.0), current_price=50.0)
    increased = _snapshot(_item("i3", last_known_price=30.0), current_price=40.0)

    summary = build_summary(
        watchlist_items=[dropped, unchanged, increased], alert_rules=[], notifications=[]
    )
    assert summary.watched_products == 3
    assert summary.potential_savings == 20.0  # only the dropped item counts, never negative
    assert summary.potential_savings_currency == "PHP"
    assert summary.savings_freshness_note == DASHBOARD_LIMITATIONS_NOTE


def test_build_summary_counts_stale_items() -> None:
    stale = _snapshot(
        _item("i1", last_known_price=100.0), current_price=None, price_available=False
    )
    fresh = _snapshot(_item("i2", last_known_price=100.0), current_price=90.0, price_available=True)
    summary = build_summary(watchlist_items=[stale, fresh], alert_rules=[], notifications=[])
    assert summary.stale_data_count == 1


def test_build_summary_counts_unread_notifications_and_active_rules() -> None:
    from app.domain.entities.alerts import AlertRule, AlertRuleStatus
    from app.domain.entities.notifications import (
        Notification,
        NotificationSeverity,
        NotificationType,
    )

    active_rule = AlertRule(
        rule_id="r1",
        user_id="u1",
        name="Active",
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        created_at=FIXED_NOW,
        enabled=True,
        status=AlertRuleStatus.ENABLED,
    )
    disabled_rule = AlertRule(
        rule_id="r2",
        user_id="u1",
        name="Disabled",
        conditions=(AlertCondition(condition_type=AlertConditionType.PRICE_DROP),),
        created_at=FIXED_NOW,
        enabled=False,
        status=AlertRuleStatus.DISABLED,
    )
    unread = Notification(
        notification_id="n1",
        user_id="u1",
        title="Hi",
        body="body",
        type=NotificationType.SYSTEM,
        severity=NotificationSeverity.INFO,
        created_at=FIXED_NOW,
    )
    summary = build_summary(
        watchlist_items=[],
        alert_rules=[active_rule, disabled_rule],
        notifications=[unread],
    )
    assert summary.active_alert_rules == 1
    assert summary.unread_notifications == 1


# --------------------------------------------------------------------- assemble_dashboard


def test_assemble_dashboard_produces_all_expected_cards() -> None:
    id_counter = {"n": 0}

    def next_id() -> str:
        id_counter["n"] += 1
        return f"card-{id_counter['n']}"

    dashboard = assemble_dashboard(user_id="user-1", generated_at=FIXED_NOW, id_factory=next_id)
    card_types = {card.card_type for card in dashboard.cards}
    assert card_types == set(DashboardCardType)
    assert dashboard.limitations == DASHBOARD_LIMITATIONS_NOTE
    assert dashboard.user_id == "user-1"


# --------------------------------------------------------------------- UserDashboardService


@dataclass
class _FakeOffer:
    source_mode: SourceMode
    simulated: bool


class _FakeMarketplaceData:
    def __init__(self, offers: list[_FakeOffer]) -> None:
        self._offers = offers

    def list_offers(self, *, limit: int = 200) -> list[_FakeOffer]:
        return self._offers


def _build_dashboard_service(
    *, marketplace_data: object | None = None
) -> tuple[
    UserDashboardService, ExtendedWatchlistService, AlertRuleService, NotificationCenterService
]:
    watchlist_store = InMemoryWatchlistStore()
    price_store = InMemoryPriceHistoryStore()
    price_service = PriceHistoryService(price_store, app_env="development")
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"id-{counter['n']}"

    watchlists = ExtendedWatchlistService(
        watchlist_store,
        price_history_service=price_service,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    rule_repo = InMemoryAlertRuleRepository()
    alert_rules = AlertRuleService(
        rule_repo, watchlist_repository=watchlist_store, clock=lambda: FIXED_NOW, id_factory=next_id
    )
    from app.notifications.memory import InMemoryNotificationCenterRepository

    notif_repo = InMemoryNotificationCenterRepository()
    notif_prefs = NotificationPreferenceService(notif_repo, clock=lambda: FIXED_NOW)
    notifications = NotificationCenterService(
        notif_repo, preference_service=notif_prefs, clock=lambda: FIXED_NOW, id_factory=next_id
    )

    dashboard_service = UserDashboardService(
        watchlists,
        alert_rule_service=alert_rules,
        alert_repository=watchlist_store,
        alert_event_repository=rule_repo,
        notification_center_service=notifications,
        marketplace_data_service=marketplace_data,  # type: ignore[arg-type]
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    return dashboard_service, watchlists, alert_rules, notifications


@pytest.mark.asyncio
async def test_get_dashboard_requires_user_id() -> None:
    dashboard_service, _, _, _ = _build_dashboard_service()
    with pytest.raises(DashboardValidationError):
        await dashboard_service.get_dashboard("  ")


@pytest.mark.asyncio
async def test_get_dashboard_uses_default_limitations_note_without_marketplace_data() -> None:
    dashboard_service, watchlists, _, _ = _build_dashboard_service(marketplace_data=None)
    watchlists.create_watchlist(name="Phones", owner_id="user-1")
    dashboard = await dashboard_service.get_dashboard("user-1")
    assert dashboard.summary.savings_freshness_note == DASHBOARD_LIMITATIONS_NOTE


@pytest.mark.asyncio
async def test_get_dashboard_source_mode_label_overlays_when_simulated() -> None:
    fake_marketplace = _FakeMarketplaceData(
        [_FakeOffer(source_mode=SourceMode.FIXTURE, simulated=True)]
    )
    dashboard_service, watchlists, _, _ = _build_dashboard_service(
        marketplace_data=fake_marketplace
    )
    watchlists.create_watchlist(name="Phones", owner_id="user-1")
    dashboard = await dashboard_service.get_dashboard("user-1")
    note = dashboard.summary.savings_freshness_note
    # A simulated offer never surfaces its raw source_mode label unchanged —
    # the freshness overlay always resolves it via the SourceMode.LIVE entry.
    assert note != DASHBOARD_LIMITATIONS_NOTE
    assert SOURCE_MODE_LABELS[SourceMode.LIVE] in note
    assert SOURCE_MODE_LABELS[SourceMode.FIXTURE] not in note


@pytest.mark.asyncio
async def test_get_dashboard_source_mode_label_reports_fixture_data() -> None:
    fake_marketplace = _FakeMarketplaceData(
        [_FakeOffer(source_mode=SourceMode.FIXTURE, simulated=False)]
    )
    dashboard_service, watchlists, _, _ = _build_dashboard_service(
        marketplace_data=fake_marketplace
    )
    watchlists.create_watchlist(name="Phones", owner_id="user-1")
    dashboard = await dashboard_service.get_dashboard("user-1")
    assert SOURCE_MODE_LABELS[SourceMode.FIXTURE] in dashboard.summary.savings_freshness_note


@pytest.mark.asyncio
async def test_get_dashboard_reports_potential_savings_and_watchlists_card() -> None:
    dashboard_service, watchlists, _, _ = _build_dashboard_service()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(
        wl.watchlist_id, canonical_product_id="prod-1", last_known_price=100.0
    )
    dashboard = await dashboard_service.get_dashboard("user-1")
    watchlists_card = next(
        c for c in dashboard.cards if c.card_type == DashboardCardType.WATCHLISTS
    )
    assert watchlists_card.summary == "1 watchlist(s)"
    # No price snapshots recorded -> item counts as stale/unavailable, not a savings source.
    assert dashboard.summary.potential_savings == 0.0


@pytest.mark.asyncio
async def test_get_dashboard_activity_feed_includes_watchlist_history() -> None:
    dashboard_service, watchlists, _, _ = _build_dashboard_service()
    wl = watchlists.create_watchlist(name="Phones", owner_id="user-1")
    await watchlists.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")
    dashboard = await dashboard_service.get_dashboard("user-1")
    activity_card = next(c for c in dashboard.cards if c.card_type == DashboardCardType.ACTIVITY)
    activity_types = {item["activity_type"] for item in activity_card.items}
    assert "watchlist_created" in activity_types
    assert "item_added" in activity_types


@pytest.mark.asyncio
async def test_get_dashboard_dict_includes_personalization_context() -> None:
    dashboard_service, watchlists, _, _ = _build_dashboard_service()
    watchlists.create_watchlist(name="Phones", owner_id="user-1")
    payload = await dashboard_service.get_dashboard_dict("user-1")
    assert "personalization" in payload
    assert "limitations" in payload
