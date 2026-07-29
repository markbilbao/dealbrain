"""Watchlists & Price Alerts domain entities and value objects.

Identifiers and timestamps are injected by callers — core types never generate
random UUIDs or wall-clock times.

Sprint 10 established the base Watchlist / WatchlistItem / Alert / mock
notification types; existing callers and tests continue to work unmodified.
Sprint 19 extends these types with status lifecycles, richer item metadata,
a wider alert taxonomy, additional (still mock-only) notification channels,
and watchlist history tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class AlertType(StrEnum):
    """Kinds of price / deal alerts that can be raised.

    The first four values are Sprint 10 originals and must not change.
    """

    PRICE_DROP = "price_drop"
    TARGET_PRICE_REACHED = "target_price_reached"
    DEALSCORE_IMPROVED = "dealscore_improved"
    HISTORICAL_LOW = "historical_low"

    # Sprint 19 additions.
    PERCENTAGE_PRICE_DECREASE = "percentage_price_decrease"
    ABSOLUTE_PRICE_DECREASE = "absolute_price_decrease"
    PRICE_INCREASE = "price_increase"
    RESTOCKED = "restocked"
    UNAVAILABLE = "unavailable"
    LOW_INVENTORY = "low_inventory"
    BETTER_OFFER = "better_offer"
    PREFERRED_SELLER_AVAILABLE = "preferred_seller_available"
    PREFERRED_MARKETPLACE_AVAILABLE = "preferred_marketplace_available"
    STALE_DATA = "stale_data"
    FRESHNESS_RESTORED = "freshness_restored"
    DEALSCORE_THRESHOLD = "dealscore_threshold"


class AlertStatus(StrEnum):
    """Lifecycle status for a generated alert."""

    PENDING = "pending"
    NOTIFIED = "notified"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


class NotificationStatus(StrEnum):
    """Outcome of a mock notification attempt.

    ``QUEUED`` and ``SKIPPED`` are Sprint 10 originals.
    """

    QUEUED = "queued"
    SKIPPED = "skipped"

    # Sprint 19 additions.
    DELIVERED = "delivered"
    FAILED = "failed"
    SIMULATED = "simulated"


class NotificationChannel(StrEnum):
    """Notification delivery channel.

    All channels remain mock/simulated only — no real email/SMS/push is sent.
    ``MOCK`` is the Sprint 10 original default.
    """

    MOCK = "mock"

    # Sprint 19 additions (still simulated — see NotificationDelivery.simulated).
    IN_APP = "in_app"
    EMAIL = "email"


class WatchlistStatus(StrEnum):
    """Lifecycle status of a watchlist."""

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ItemKind(StrEnum):
    """What a watchlist item tracks — a canonical product or a specific offer."""

    PRODUCT = "product"
    OFFER = "offer"


@dataclass(frozen=True, slots=True)
class Watchlist:
    """Named collection of tracked products for one owner/context."""

    watchlist_id: str
    name: str
    created_at: datetime
    owner_id: str | None = None
    description: str | None = None
    enabled: bool = True
    updated_at: datetime | None = None

    # Sprint 19 additions.
    is_default: bool = False
    status: WatchlistStatus = WatchlistStatus.ACTIVE
    paused_at: datetime | None = None
    archived_at: datetime | None = None
    preferred_sellers: tuple[str, ...] = ()
    preferred_marketplaces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "watchlist_id": self.watchlist_id,
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at or self.created_at).isoformat(),
            "is_default": self.is_default,
            "status": self.status.value,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "preferred_sellers": list(self.preferred_sellers),
            "preferred_marketplaces": list(self.preferred_marketplaces),
        }


@dataclass(frozen=True, slots=True)
class WatchlistItem:
    """A tracked canonical product (or marketplace offer) within a watchlist."""

    item_id: str
    watchlist_id: str
    canonical_product_id: str
    created_at: datetime
    product_label: str | None = None
    target_price: float | None = None
    currency: str = "PHP"
    search_query: str | None = None
    last_known_price: float | None = None
    last_known_dealscore: float | None = None
    last_historical_low: float | None = None
    enabled: bool = True
    updated_at: datetime | None = None

    # Sprint 19 additions.
    marketplace_offer_id: str | None = None
    notes: str | None = None
    item_kind: ItemKind = ItemKind.PRODUCT
    monitoring_paused: bool = False
    preferred_sellers: tuple[str, ...] = ()
    preferred_marketplaces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "watchlist_id": self.watchlist_id,
            "canonical_product_id": self.canonical_product_id,
            "product_label": self.product_label,
            "target_price": self.target_price,
            "currency": self.currency,
            "search_query": self.search_query,
            "last_known_price": self.last_known_price,
            "last_known_dealscore": self.last_known_dealscore,
            "last_historical_low": self.last_historical_low,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at or self.created_at).isoformat(),
            "marketplace_offer_id": self.marketplace_offer_id,
            "notes": self.notes,
            "item_kind": self.item_kind.value,
            "monitoring_paused": self.monitoring_paused,
            "preferred_sellers": list(self.preferred_sellers),
            "preferred_marketplaces": list(self.preferred_marketplaces),
        }


@dataclass(frozen=True, slots=True)
class Alert:
    """An evaluated price or deal condition for a watchlist item."""

    alert_id: str
    watchlist_id: str
    item_id: str
    canonical_product_id: str
    alert_type: AlertType
    message: str
    created_at: datetime
    previous_value: float | None = None
    current_value: float | None = None
    currency: str | None = None
    dealscore: float | None = None
    status: AlertStatus = AlertStatus.PENDING
    notified_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "watchlist_id": self.watchlist_id,
            "item_id": self.item_id,
            "canonical_product_id": self.canonical_product_id,
            "alert_type": self.alert_type.value,
            "message": self.message,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "currency": self.currency,
            "dealscore": self.dealscore,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }


@dataclass(frozen=True, slots=True)
class NotificationReceipt:
    """Mock notification outcome — never delivers to real channels."""

    notification_id: str
    alert_id: str
    channel: NotificationChannel
    status: NotificationStatus
    created_at: datetime
    detail: str = "Queued for mock delivery (no email/SMS/push sent)."

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "alert_id": self.alert_id,
            "channel": self.channel.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class WatchlistItemSnapshot:
    """Enriched view of a watchlist item with live price / DealScore context."""

    item: WatchlistItem
    current_price: float | None = None
    historical_low: float | None = None
    dealscore: float | None = None
    currency: str | None = None
    observation_count: int = 0
    price_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = self.item.to_dict()
        payload.update(
            {
                "current_price": self.current_price,
                "historical_low": self.historical_low,
                "dealscore": self.dealscore,
                "observed_currency": self.currency,
                "observation_count": self.observation_count,
                "price_available": self.price_available,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class AlertEvaluationResult:
    """Outcome of a manual alert evaluation pass."""

    watchlist_ids: tuple[str, ...]
    items_checked: int
    alerts_created: tuple[Alert, ...]
    notifications: tuple[NotificationReceipt, ...]
    evaluated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "watchlist_ids": list(self.watchlist_ids),
            "items_checked": self.items_checked,
            "alerts_created": [alert.to_dict() for alert in self.alerts_created],
            "notifications": [note.to_dict() for note in self.notifications],
            "alerts_count": len(self.alerts_created),
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class WatchlistHistoryEntry:
    """Audit trail entry for a watchlist lifecycle or membership change.

    Covers status transitions (pause/resume/archive), item add/remove, and
    preference edits — used to power an activity feed without mutating the
    watchlist itself.
    """

    history_id: str
    watchlist_id: str
    event_type: str
    description: str
    created_at: datetime
    actor_id: str | None = None
    item_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_id": self.history_id,
            "watchlist_id": self.watchlist_id,
            "event_type": self.event_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "actor_id": self.actor_id,
            "item_id": self.item_id,
            "metadata": dict(self.metadata) if self.metadata else {},
        }
