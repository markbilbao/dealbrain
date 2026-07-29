"""User Dashboard domain entities — Sprint 19.

Aggregates Watchlists, Alert Rules, and the Notification Center into a single
per-user read model. Dashboards only summarize existing fixture/imported data
(see ``UserDashboard.limitations``) and never claim live marketplace pricing.

Identifiers and timestamps are injected by callers — core types never
generate random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

DASHBOARD_LIMITATIONS_NOTE = (
    "Dashboard figures summarize fixture and imported watchlist/marketplace "
    "data only; they do not reflect live marketplace pricing."
)


class DashboardCardType(StrEnum):
    """Kinds of summary cards a user dashboard may render."""

    SUMMARY = "summary"
    RECENT_ALERTS = "recent_alerts"
    PRICE_DROPS = "price_drops"
    RESTOCKS = "restocks"
    BETTER_OFFERS = "better_offers"
    STALE_DATA = "stale_data"
    WATCHLISTS = "watchlists"
    ACTIVITY = "activity"


@dataclass(frozen=True, slots=True)
class DashboardCard:
    """A single renderable dashboard card."""

    card_id: str
    card_type: DashboardCardType
    title: str
    summary: str = ""
    items: tuple[dict[str, Any], ...] = ()
    source_mode_label: str | None = None
    freshness_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_type": self.card_type.value,
            "title": self.title,
            "summary": self.summary,
            "items": [dict(item) for item in self.items],
            "source_mode_label": self.source_mode_label,
            "freshness_label": self.freshness_label,
        }


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """Headline counters shown at the top of a user's dashboard."""

    watched_products: int = 0
    active_alert_rules: int = 0
    unread_notifications: int = 0
    recent_price_drops: int = 0
    restocked_items: int = 0
    better_offers: int = 0
    stale_data_count: int = 0
    potential_savings: float = 0.0
    potential_savings_currency: str = "PHP"
    savings_freshness_note: str = DASHBOARD_LIMITATIONS_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "watched_products": self.watched_products,
            "active_alert_rules": self.active_alert_rules,
            "unread_notifications": self.unread_notifications,
            "recent_price_drops": self.recent_price_drops,
            "restocked_items": self.restocked_items,
            "better_offers": self.better_offers,
            "stale_data_count": self.stale_data_count,
            "potential_savings": self.potential_savings,
            "potential_savings_currency": self.potential_savings_currency,
            "savings_freshness_note": self.savings_freshness_note,
        }


@dataclass(frozen=True, slots=True)
class UserActivity:
    """A single entry in a user's recent activity feed."""

    activity_id: str
    user_id: str
    activity_type: str
    message: str
    created_at: datetime
    watchlist_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "user_id": self.user_id,
            "activity_type": self.activity_type,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "watchlist_id": self.watchlist_id,
        }


@dataclass(frozen=True, slots=True)
class UserDashboard:
    """Aggregated per-user dashboard view."""

    user_id: str
    summary: DashboardSummary
    generated_at: datetime
    cards: tuple[DashboardCard, ...] = ()
    recent_activity: tuple[UserActivity, ...] = ()
    limitations: str = DASHBOARD_LIMITATIONS_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "summary": self.summary.to_dict(),
            "cards": [card.to_dict() for card in self.cards],
            "recent_activity": [activity.to_dict() for activity in self.recent_activity],
            "generated_at": self.generated_at.isoformat(),
            "limitations": self.limitations,
        }
