"""Notification Center domain entities — Sprint 19.

In-app notifications, delivery tracking, digests, and preferences layered on
top of the Sprint 10 mock ``NotificationReceipt``/``NotificationChannel``
types (``app.domain.entities.watchlist``). All delivery remains simulated —
no real email/SMS/push is ever sent; ``NotificationDelivery.simulated`` and
``NotificationDigest.simulated_email_detail`` make that explicit in payloads.

Identifiers and timestamps are injected by callers — core types never
generate random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.entities.watchlist import NotificationChannel, NotificationStatus


class NotificationType(StrEnum):
    """Categorizes an in-app notification for filtering and iconography."""

    PRICE_DROP = "price_drop"
    PRICE_INCREASE = "price_increase"
    RESTOCK = "restock"
    OUT_OF_STOCK = "out_of_stock"
    LOW_INVENTORY = "low_inventory"
    BETTER_OFFER = "better_offer"
    DEALSCORE_THRESHOLD = "dealscore_threshold"
    FRESHNESS_WARNING = "freshness_warning"
    SYSTEM = "system"
    DIGEST = "digest"

    # Sprint 19 application-service additions — mirror AlertEventType members
    # that lacked a Notification Center counterpart.
    AVAILABILITY_CHANGE = "availability_change"
    SELLER_CHANGE = "seller_change"


class NotificationSeverity(StrEnum):
    """Relative importance of a notification."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class DigestPeriod(StrEnum):
    """Cadence of a notification digest."""

    DAILY = "daily"
    WEEKLY = "weekly"


class DigestStatus(StrEnum):
    """Lifecycle of a notification digest (always simulated delivery)."""

    PENDING = "pending"
    SIMULATED = "simulated"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Notification:
    """A single in-app notification surfaced to a user."""

    notification_id: str
    user_id: str
    title: str
    body: str
    type: NotificationType
    severity: NotificationSeverity
    created_at: datetime
    watchlist_id: str | None = None
    alert_id: str | None = None
    alert_event_id: str | None = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    read_at: datetime | None = None
    archived_at: datetime | None = None
    delivery_status: NotificationStatus = NotificationStatus.QUEUED
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "title": self.title,
            "body": self.body,
            "type": self.type.value,
            "severity": self.severity.value,
            "watchlist_id": self.watchlist_id,
            "alert_id": self.alert_id,
            "alert_event_id": self.alert_event_id,
            "channel": self.channel.value,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "delivery_status": self.delivery_status.value,
            "created_at": self.created_at.isoformat(),
            "metadata": dict(self.metadata),
            "is_read": self.read_at is not None,
            "is_archived": self.archived_at is not None,
        }


@dataclass(frozen=True, slots=True)
class UserNotificationPreferences:
    """Per-user notification delivery and content preferences."""

    user_id: str
    created_at: datetime
    in_app_enabled: bool = True
    email_enabled: bool = False
    immediate_alerts: bool = True
    daily_digest: bool = False
    weekly_digest: bool = False
    quiet_hours_start: str | None = None  # "HH:MM", interpreted in ``timezone``.
    quiet_hours_end: str | None = None
    timezone: str = "UTC"
    price_alerts: bool = True
    stock_alerts: bool = True
    freshness_warnings: bool = True
    marketing_enabled: bool = False
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "in_app_enabled": self.in_app_enabled,
            "email_enabled": self.email_enabled,
            "immediate_alerts": self.immediate_alerts,
            "daily_digest": self.daily_digest,
            "weekly_digest": self.weekly_digest,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "timezone": self.timezone,
            "price_alerts": self.price_alerts,
            "stock_alerts": self.stock_alerts,
            "freshness_warnings": self.freshness_warnings,
            "marketing_enabled": self.marketing_enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at or self.created_at).isoformat(),
        }


@dataclass(frozen=True, slots=True)
class NotificationDelivery:
    """A single delivery attempt for a notification on a given channel.

    ``simulated`` is always ``True`` in this codebase — no live email/SMS/push
    transport exists; this field exists so downstream consumers never need to
    infer that fact from channel alone.
    """

    delivery_id: str
    notification_id: str
    channel: NotificationChannel
    status: NotificationStatus
    created_at: datetime
    attempt: int = 1
    error: str | None = None
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "notification_id": self.notification_id,
            "channel": self.channel.value,
            "status": self.status.value,
            "attempt": self.attempt,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "simulated": self.simulated,
        }


@dataclass(frozen=True, slots=True)
class NotificationTemplate:
    """Reusable subject/body template for a notification type and channel."""

    template_id: str
    name: str
    subject_template: str
    body_template: str
    channel: NotificationChannel

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "channel": self.channel.value,
        }


@dataclass(frozen=True, slots=True)
class NotificationDigest:
    """A batched daily/weekly rollup of notifications for one user."""

    digest_id: str
    user_id: str
    period: DigestPeriod
    notification_ids: tuple[str, ...]
    status: DigestStatus
    created_at: datetime
    simulated_email_detail: str | None = (
        "SIMULATED EMAIL — no real message was sent (mock channel only)."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "digest_id": self.digest_id,
            "user_id": self.user_id,
            "period": self.period.value,
            "notification_ids": list(self.notification_ids),
            "notification_count": len(self.notification_ids),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "simulated_email_detail": self.simulated_email_detail,
        }


@dataclass(frozen=True, slots=True)
class UnsubscribeToken:
    """Opaque, hashed unsubscribe token — the raw token is never stored."""

    token_hash: str
    user_id: str
    created_at: datetime
    revoked_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_hash": self.token_hash,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "active": self.revoked_at is None,
        }
