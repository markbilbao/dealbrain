"""Pure Dashboard assembly functions — Sprint 19.

Builds :class:`DashboardCard`/:class:`DashboardSummary`/:class:`UserDashboard`
from already-fetched input collections (watchlists, items, alert rules,
alerts, alert events, notifications, activity). No I/O of any kind —
repository/service calls happen entirely in the caller; these functions only
transform in-memory data. Identifiers and timestamps are always supplied by
the caller (an ``id_factory``/``generated_at`` argument), never generated
here, keeping every function referentially transparent and easy to test.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from app.domain.entities.alerts import AlertEvent, AlertEventType, AlertRule, AlertRuleStatus
from app.domain.entities.dashboard import (
    DashboardCard,
    DashboardCardType,
    DashboardSummary,
    UserActivity,
    UserDashboard,
)
from app.domain.entities.notifications import Notification
from app.domain.entities.watchlist import Alert, Watchlist, WatchlistItemSnapshot

IdFactory = Callable[[], str]


def build_summary(
    *,
    watchlist_items: Sequence[WatchlistItemSnapshot],
    alert_rules: Sequence[AlertRule],
    notifications: Sequence[Notification],
    alert_events: Sequence[AlertEvent] = (),
    currency: str = "PHP",
) -> DashboardSummary:
    """Compute headline counters from raw collections.

    ``potential_savings`` sums, per item, the observed drop from its last
    known price to its current snapshot price (never negative per item) —
    a conservative, already-realized-savings estimate, not a projection.
    """
    active_rules = sum(
        1 for rule in alert_rules if rule.enabled and rule.status == AlertRuleStatus.ENABLED
    )
    unread_notifications = sum(
        1 for n in notifications if n.read_at is None and n.archived_at is None
    )
    price_drops = sum(1 for e in alert_events if e.event_type == AlertEventType.PRICE_DROP)
    restocks = sum(1 for e in alert_events if e.event_type == AlertEventType.RESTOCK)
    better_offers = sum(1 for e in alert_events if e.event_type == AlertEventType.BETTER_OFFER)
    stale_count = sum(1 for snap in watchlist_items if not snap.price_available)

    potential_savings = 0.0
    for snap in watchlist_items:
        last_known = snap.item.last_known_price
        current = snap.current_price
        if last_known is not None and current is not None and current < last_known:
            potential_savings += last_known - current

    return DashboardSummary(
        watched_products=len(watchlist_items),
        active_alert_rules=active_rules,
        unread_notifications=unread_notifications,
        recent_price_drops=price_drops,
        restocked_items=restocks,
        better_offers=better_offers,
        stale_data_count=stale_count,
        potential_savings=round(potential_savings, 2),
        potential_savings_currency=currency,
    )


def build_card(
    *,
    card_type: DashboardCardType,
    title: str,
    items: Sequence[dict],
    id_factory: IdFactory,
    summary: str = "",
    source_mode_label: str | None = None,
    freshness_label: str | None = None,
) -> DashboardCard:
    """Generic card builder — wraps already-shaped item dicts."""
    return DashboardCard(
        card_id=id_factory(),
        card_type=card_type,
        title=title,
        summary=summary,
        items=tuple(items),
        source_mode_label=source_mode_label,
        freshness_label=freshness_label,
    )


def build_summary_card(
    summary: DashboardSummary, *, id_factory: IdFactory, title: str = "Overview"
) -> DashboardCard:
    return build_card(
        card_type=DashboardCardType.SUMMARY,
        title=title,
        items=(summary.to_dict(),),
        id_factory=id_factory,
        summary=summary.savings_freshness_note,
    )


def build_recent_alerts_card(
    alerts: Sequence[Alert],
    *,
    id_factory: IdFactory,
    limit: int = 10,
    title: str = "Recent Alerts",
) -> DashboardCard:
    selected = list(alerts)[:limit]
    return build_card(
        card_type=DashboardCardType.RECENT_ALERTS,
        title=title,
        items=[alert.to_dict() for alert in selected],
        id_factory=id_factory,
        summary=f"{len(selected)} alert(s)",
    )


def _events_card(
    events: Sequence[AlertEvent],
    event_type: AlertEventType,
    *,
    card_type: DashboardCardType,
    title: str,
    id_factory: IdFactory,
    limit: int,
) -> DashboardCard:
    matched = [e for e in events if e.event_type == event_type][:limit]
    return build_card(
        card_type=card_type,
        title=title,
        items=[event.to_dict() for event in matched],
        id_factory=id_factory,
        summary=f"{len(matched)} {title.lower()}",
    )


def build_price_drops_card(
    events: Sequence[AlertEvent], *, id_factory: IdFactory, limit: int = 10
) -> DashboardCard:
    return _events_card(
        events,
        AlertEventType.PRICE_DROP,
        card_type=DashboardCardType.PRICE_DROPS,
        title="Price Drops",
        id_factory=id_factory,
        limit=limit,
    )


def build_restocks_card(
    events: Sequence[AlertEvent], *, id_factory: IdFactory, limit: int = 10
) -> DashboardCard:
    return _events_card(
        events,
        AlertEventType.RESTOCK,
        card_type=DashboardCardType.RESTOCKS,
        title="Restocks",
        id_factory=id_factory,
        limit=limit,
    )


def build_better_offers_card(
    events: Sequence[AlertEvent], *, id_factory: IdFactory, limit: int = 10
) -> DashboardCard:
    return _events_card(
        events,
        AlertEventType.BETTER_OFFER,
        card_type=DashboardCardType.BETTER_OFFERS,
        title="Better Offers",
        id_factory=id_factory,
        limit=limit,
    )


def build_stale_data_card(
    watchlist_items: Sequence[WatchlistItemSnapshot],
    *,
    id_factory: IdFactory,
    limit: int = 10,
) -> DashboardCard:
    stale = [snap for snap in watchlist_items if not snap.price_available][:limit]
    return build_card(
        card_type=DashboardCardType.STALE_DATA,
        title="Stale Data",
        items=[snap.to_dict() for snap in stale],
        id_factory=id_factory,
        summary=f"{len(stale)} item(s) missing fresh price data",
    )


def build_watchlists_card(
    watchlists: Sequence[Watchlist], *, id_factory: IdFactory
) -> DashboardCard:
    return build_card(
        card_type=DashboardCardType.WATCHLISTS,
        title="Watchlists",
        items=[wl.to_dict() for wl in watchlists],
        id_factory=id_factory,
        summary=f"{len(watchlists)} watchlist(s)",
    )


def build_activity_card(
    activity: Sequence[UserActivity], *, id_factory: IdFactory, limit: int = 20
) -> DashboardCard:
    selected = list(activity)[:limit]
    return build_card(
        card_type=DashboardCardType.ACTIVITY,
        title="Recent Activity",
        items=[a.to_dict() for a in selected],
        id_factory=id_factory,
        summary=f"{len(selected)} recent event(s)",
    )


def assemble_dashboard(
    *,
    user_id: str,
    generated_at: datetime,
    id_factory: IdFactory,
    watchlists: Sequence[Watchlist] = (),
    watchlist_items: Sequence[WatchlistItemSnapshot] = (),
    alert_rules: Sequence[AlertRule] = (),
    alerts: Sequence[Alert] = (),
    alert_events: Sequence[AlertEvent] = (),
    notifications: Sequence[Notification] = (),
    recent_activity: Sequence[UserActivity] = (),
    currency: str = "PHP",
) -> UserDashboard:
    """Assemble a full :class:`UserDashboard` from raw input collections.

    Pure orchestration over the individual ``build_*`` helpers — no
    repository or service calls happen here; callers fetch every collection
    ahead of time and pass it in.
    """
    summary = build_summary(
        watchlist_items=watchlist_items,
        alert_rules=alert_rules,
        notifications=notifications,
        alert_events=alert_events,
        currency=currency,
    )
    cards = (
        build_summary_card(summary, id_factory=id_factory),
        build_recent_alerts_card(alerts, id_factory=id_factory),
        build_price_drops_card(alert_events, id_factory=id_factory),
        build_restocks_card(alert_events, id_factory=id_factory),
        build_better_offers_card(alert_events, id_factory=id_factory),
        build_stale_data_card(watchlist_items, id_factory=id_factory),
        build_watchlists_card(watchlists, id_factory=id_factory),
        build_activity_card(recent_activity, id_factory=id_factory),
    )
    return UserDashboard(
        user_id=user_id,
        summary=summary,
        generated_at=generated_at,
        cards=cards,
        recent_activity=tuple(recent_activity),
    )
