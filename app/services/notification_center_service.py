"""Notification Center application service — Sprint 19.

Full in-app notification inbox: creation (direct or from an
``AlertEvent``), listing/filtering/pagination, read/archive/delete,
preference-aware channel fan-out (IN_APP always when allowed; EMAIL via
``MockEmailNotificationProvider`` when the user opted in — always labeled
simulated), quiet-hours suppression, unsubscribe tokens, and daily/weekly
digests. All delivery is mock/simulated; no real email/SMS/push transport
exists anywhere in this codebase.
"""

from __future__ import annotations

import hashlib
import html
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.alerts import AlertEvent, AlertEventType, AlertSeverity
from app.domain.entities.notifications import (
    DigestPeriod,
    Notification,
    NotificationDelivery,
    NotificationDigest,
    NotificationSeverity,
    NotificationTemplate,
    NotificationType,
    UnsubscribeToken,
    UserNotificationPreferences,
)
from app.domain.entities.watchlist import (
    NotificationChannel,
    NotificationStatus,
    Watchlist,
    WatchlistItem,
)
from app.domain.exceptions import NotificationNotFoundError, NotificationValidationError
from app.domain.interfaces.notification_center_repository import NotificationCenterRepository
from app.notifications.digest.builder import (
    build_daily_digest,
    build_weekly_digest,
    has_content,
    mark_failed,
    mark_simulated,
)
from app.notifications.email.provider import (
    EmailMessage,
    EmailNotificationProvider,
    MockEmailNotificationProvider,
)
from app.notifications.email.renderer import render_template
from app.notifications.preferences import should_suppress_immediate_alert
from app.services.notification_preference_service import NotificationPreferenceService

# Alert-rule event type -> Notification Center category. Kept 1:1 where the
# two enums share a concept; every AlertEventType has a mapping.
_EVENT_TO_NOTIFICATION_TYPE: dict[AlertEventType, NotificationType] = {
    AlertEventType.PRICE_DROP: NotificationType.PRICE_DROP,
    AlertEventType.PRICE_INCREASE: NotificationType.PRICE_INCREASE,
    AlertEventType.RESTOCK: NotificationType.RESTOCK,
    AlertEventType.OUT_OF_STOCK: NotificationType.OUT_OF_STOCK,
    AlertEventType.AVAILABILITY_CHANGE: NotificationType.AVAILABILITY_CHANGE,
    AlertEventType.SELLER_CHANGE: NotificationType.SELLER_CHANGE,
    AlertEventType.BETTER_OFFER: NotificationType.BETTER_OFFER,
    AlertEventType.FRESHNESS_WARNING: NotificationType.FRESHNESS_WARNING,
    AlertEventType.LOW_INVENTORY: NotificationType.LOW_INVENTORY,
    AlertEventType.DEALSCORE_CHANGE: NotificationType.DEALSCORE_THRESHOLD,
}

# Notification categories gated behind the user's "price_alerts" preference.
_PRICE_TYPES = frozenset(
    {
        NotificationType.PRICE_DROP,
        NotificationType.PRICE_INCREASE,
        NotificationType.BETTER_OFFER,
        NotificationType.DEALSCORE_THRESHOLD,
    }
)
# Notification categories gated behind the user's "stock_alerts" preference.
_STOCK_TYPES = frozenset(
    {
        NotificationType.RESTOCK,
        NotificationType.OUT_OF_STOCK,
        NotificationType.LOW_INVENTORY,
        NotificationType.AVAILABILITY_CHANGE,
        NotificationType.SELLER_CHANGE,
    }
)


def _build_default_templates() -> dict[NotificationType, NotificationTemplate]:
    specs: dict[NotificationType, tuple[str, str]] = {
        NotificationType.PRICE_DROP: (
            "Price drop: {{product_label}}",
            "{{product_label}} dropped to {{current_price}} {{currency}} (was {{previous_price}}).",
        ),
        NotificationType.PRICE_INCREASE: (
            "Price increase: {{product_label}}",
            "{{product_label}} rose to {{current_price}} {{currency}} (was {{previous_price}}).",
        ),
        NotificationType.RESTOCK: (
            "Back in stock: {{product_label}}",
            "{{product_label}} is back in stock.",
        ),
        NotificationType.OUT_OF_STOCK: (
            "Out of stock: {{product_label}}",
            "{{product_label}} became unavailable.",
        ),
        NotificationType.LOW_INVENTORY: (
            "Low stock: {{product_label}}",
            "{{product_label}} has limited stock remaining ({{inventory}} left).",
        ),
        NotificationType.AVAILABILITY_CHANGE: (
            "Availability changed: {{product_label}}",
            "{{product_label}} availability changed.",
        ),
        NotificationType.SELLER_CHANGE: (
            "Preferred seller available: {{product_label}}",
            "{{product_label}} is now offered by {{seller_name}}.",
        ),
        NotificationType.BETTER_OFFER: (
            "Better offer found: {{product_label}}",
            "A better offer for {{product_label}} was found at {{total_price}} {{currency}}.",
        ),
        NotificationType.DEALSCORE_THRESHOLD: (
            "DealScore update: {{product_label}}",
            "{{product_label}} DealScore is now {{dealscore}} (was {{previous_dealscore}}).",
        ),
        NotificationType.FRESHNESS_WARNING: (
            "Data freshness update: {{product_label}}",
            "{{product_label}} pricing data freshness changed (age: {{age_hours}}h).",
        ),
        NotificationType.SYSTEM: ("DealBrain notification", "{{product_label}}"),
        NotificationType.DIGEST: ("Your DealBrain digest", "You have new updates."),
    }
    return {
        notification_type: NotificationTemplate(
            template_id=f"default-{notification_type.value}",
            name=f"Default {notification_type.value} template",
            subject_template=subject,
            body_template=body,
            channel=NotificationChannel.IN_APP,
        )
        for notification_type, (subject, body) in specs.items()
    }


_DEFAULT_TEMPLATES = _build_default_templates()


class NotificationCenterService:
    """Application service backing the in-app Notification Center."""

    def __init__(
        self,
        repository: NotificationCenterRepository,
        *,
        preference_service: NotificationPreferenceService | None = None,
        email_provider: EmailNotificationProvider | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._preferences = preference_service or NotificationPreferenceService(
            repository, clock=self._clock
        )
        self._email_provider = email_provider or MockEmailNotificationProvider(
            clock=self._clock, id_factory=self._id_factory
        )

    # ------------------------------------------------------------------- creation
    def create_notification(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        type: NotificationType,  # noqa: A002 - matches domain field name
        severity: NotificationSeverity = NotificationSeverity.INFO,
        watchlist_id: str | None = None,
        alert_id: str | None = None,
        alert_event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        cleaned_title = title.strip()
        cleaned_body = body.strip()
        if not cleaned_title:
            raise NotificationValidationError("Notification title must not be blank.")
        prefs = self._preferences.get_preferences(user_id)
        now = self._clock()
        allow_in_app = prefs.in_app_enabled and self._type_allowed(prefs, type)
        notification = Notification(
            notification_id=self._id_factory(),
            user_id=user_id,
            title=cleaned_title,
            body=cleaned_body,
            type=type,
            severity=severity,
            created_at=now,
            watchlist_id=watchlist_id,
            alert_id=alert_id,
            alert_event_id=alert_event_id,
            channel=NotificationChannel.IN_APP,
            delivery_status=(
                NotificationStatus.SIMULATED if allow_in_app else NotificationStatus.SKIPPED
            ),
            metadata=dict(metadata or {}),
        )
        saved = self._repository.save_notification(notification)
        self._deliver_channels(saved, prefs, now=now)
        return saved

    def create_from_alert_event(
        self,
        event: AlertEvent,
        *,
        watchlist: Watchlist | None = None,
        item: WatchlistItem | None = None,
    ) -> Notification:
        notification_type = _EVENT_TO_NOTIFICATION_TYPE.get(
            event.event_type, NotificationType.SYSTEM
        )
        title, body = self._render_event_content(
            event, notification_type, watchlist=watchlist, item=item
        )
        watchlist_id = None
        if watchlist is not None:
            watchlist_id = watchlist.watchlist_id
        elif item is not None:
            watchlist_id = item.watchlist_id
        metadata = {"rule_id": event.rule_id, "dedupe_key": event.dedupe_key, **event.payload}
        return self.create_notification(
            user_id=event.user_id,
            title=title,
            body=body,
            type=notification_type,
            severity=self._map_severity(event.severity),
            watchlist_id=watchlist_id,
            alert_id=event.alert_id,
            alert_event_id=event.event_id,
            metadata=metadata,
        )

    def _map_severity(self, severity: AlertSeverity) -> NotificationSeverity:
        return NotificationSeverity(severity.value)

    def _type_allowed(self, prefs: UserNotificationPreferences, type: NotificationType) -> bool:  # noqa: A002
        if type in _PRICE_TYPES:
            return prefs.price_alerts
        if type in _STOCK_TYPES:
            return prefs.stock_alerts
        if type == NotificationType.FRESHNESS_WARNING:
            return prefs.freshness_warnings
        return True

    def _deliver_channels(
        self, notification: Notification, prefs: UserNotificationPreferences, *, now: datetime
    ) -> list[NotificationDelivery]:
        deliveries: list[NotificationDelivery] = []
        type_allowed = self._type_allowed(prefs, notification.type)

        if prefs.in_app_enabled:
            deliveries.append(
                self._record_delivery(
                    notification,
                    NotificationChannel.IN_APP,
                    status=NotificationStatus.SIMULATED
                    if type_allowed
                    else NotificationStatus.SKIPPED,
                )
            )

        if not prefs.email_enabled or not type_allowed:
            return deliveries

        if should_suppress_immediate_alert(prefs, now=now):
            deliveries.append(
                self._record_delivery(
                    notification,
                    NotificationChannel.EMAIL,
                    status=NotificationStatus.SKIPPED,
                    error=(
                        "Suppressed by quiet hours / immediate_alerts preference; "
                        "will surface in the next digest instead."
                    ),
                )
            )
            return deliveries

        body_html = html.escape(notification.body)
        self._email_provider.send(
            EmailMessage(
                to_address=f"{notification.user_id}@example.invalid",
                subject=notification.title,
                body_text=notification.body,
                body_html=body_html,
            )
        )
        deliveries.append(
            self._record_delivery(
                notification, NotificationChannel.EMAIL, status=NotificationStatus.SIMULATED
            )
        )
        return deliveries

    def _record_delivery(
        self,
        notification: Notification,
        channel: NotificationChannel,
        *,
        status: NotificationStatus,
        error: str | None = None,
    ) -> NotificationDelivery:
        delivery = NotificationDelivery(
            delivery_id=self._id_factory(),
            notification_id=notification.notification_id,
            channel=channel,
            status=status,
            created_at=self._clock(),
            error=error,
            simulated=True,
        )
        return self._repository.save_delivery(delivery)

    def _render_event_content(
        self,
        event: AlertEvent,
        notification_type: NotificationType,
        *,
        watchlist: Watchlist | None,
        item: WatchlistItem | None,
    ) -> tuple[str, str]:
        label = None
        if item is not None:
            label = item.product_label or item.canonical_product_id
        elif watchlist is not None:
            label = watchlist.name
        context: dict[str, Any] = {"product_label": label or "your tracked item", **event.payload}
        template = _DEFAULT_TEMPLATES.get(
            notification_type, _DEFAULT_TEMPLATES[NotificationType.SYSTEM]
        )
        # escape_html=True: event payload values (seller/marketplace names,
        # product labels) may originate from untrusted marketplace listing
        # text — never interpolate them unescaped.
        subject = render_template(template.subject_template, context, escape_html=True)
        body = render_template(template.body_template, context, escape_html=True)
        return subject, body

    # ------------------------------------------------------------------- reading
    def get_notification(self, notification_id: str, *, user_id: str | None = None) -> Notification:
        notification = self._repository.get_notification(notification_id)
        if notification is None or (user_id is not None and notification.user_id != user_id):
            raise NotificationNotFoundError(notification_id)
        return notification

    def list_notifications(
        self,
        user_id: str,
        *,
        type: NotificationType | None = None,  # noqa: A002
        severity: NotificationSeverity | None = None,
        watchlist_id: str | None = None,
        unread: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        if limit < 0 or offset < 0:
            raise NotificationValidationError("limit and offset must be non-negative.")
        items = self._repository.list_notifications(
            user_id=user_id, unread_only=False, include_archived=True, limit=1_000_000
        )
        if type is not None:
            items = [n for n in items if n.type == type]
        if severity is not None:
            items = [n for n in items if n.severity == severity]
        if watchlist_id is not None:
            items = [n for n in items if n.watchlist_id == watchlist_id]
        if unread is True:
            items = [n for n in items if n.read_at is None and n.archived_at is None]
        elif unread is False:
            items = [n for n in items if n.read_at is not None]
        return items[offset : offset + limit]

    def unread_count(self, user_id: str) -> int:
        return self._repository.count_unread(user_id)

    # ------------------------------------------------------------- state changes
    def mark_read(self, notification_id: str, *, user_id: str | None = None) -> Notification:
        self.get_notification(notification_id, user_id=user_id)
        return self._repository.mark_read(notification_id)

    def mark_all_read(self, user_id: str) -> int:
        unread = self.list_notifications(user_id, unread=True, limit=1_000_000)
        for notification in unread:
            self._repository.mark_read(notification.notification_id)
        return len(unread)

    def archive(self, notification_id: str, *, user_id: str | None = None) -> Notification:
        self.get_notification(notification_id, user_id=user_id)
        return self._repository.archive_notification(notification_id)

    def delete(self, notification_id: str, *, user_id: str | None = None) -> None:
        self.get_notification(notification_id, user_id=user_id)  # existence + ownership
        self._repository.delete_notification(notification_id)

    # ------------------------------------------------------------------ unsubscribe
    def create_unsubscribe_token(self, user_id: str) -> tuple[str, UnsubscribeToken]:
        """Return ``(raw_token, record)``. Only the hash of ``raw_token`` is persisted."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        token = UnsubscribeToken(token_hash=token_hash, user_id=user_id, created_at=self._clock())
        return raw_token, self._repository.save_unsubscribe_token(token)

    def validate_unsubscribe_token(self, raw_token: str) -> UnsubscribeToken | None:
        token = self._repository.get_unsubscribe_token(self._hash_token(raw_token))
        if token is None or token.revoked_at is not None:
            return None
        return token

    def revoke_unsubscribe_token(self, raw_token: str) -> bool:
        return self._repository.revoke_unsubscribe_token(self._hash_token(raw_token))

    def unsubscribe(self, raw_token: str) -> UserNotificationPreferences | None:
        """Apply an unsubscribe token: disable email + digests, then revoke it."""
        token = self.validate_unsubscribe_token(raw_token)
        if token is None:
            return None
        updated = self._preferences.update_preferences(
            token.user_id, email_enabled=False, daily_digest=False, weekly_digest=False
        )
        self.revoke_unsubscribe_token(raw_token)
        return updated

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # ---------------------------------------------------------------------- digests
    def build_daily_digest(
        self, user_id: str, *, since: datetime | None = None
    ) -> NotificationDigest:
        return self._build_digest(user_id, period=DigestPeriod.DAILY, since=since)

    def build_weekly_digest(
        self, user_id: str, *, since: datetime | None = None
    ) -> NotificationDigest:
        return self._build_digest(user_id, period=DigestPeriod.WEEKLY, since=since)

    def _build_digest(
        self, user_id: str, *, period: DigestPeriod, since: datetime | None
    ) -> NotificationDigest:
        notifications = self._repository.list_notifications(
            user_id=user_id, unread_only=True, include_archived=False, limit=10_000
        )
        builder = build_daily_digest if period == DigestPeriod.DAILY else build_weekly_digest
        digest = builder(
            user_id=user_id,
            notifications=notifications,
            created_at=self._clock(),
            since=since,
            id_factory=self._id_factory,
        )
        return self._repository.save_digest(digest)

    def deliver_digest(self, digest: NotificationDigest) -> NotificationDigest:
        """Simulate sending ``digest`` via email if the user allows it."""
        if not has_content(digest):
            return self._repository.save_digest(mark_failed(digest))

        prefs = self._preferences.get_preferences(digest.user_id)
        if not prefs.email_enabled:
            return self._repository.save_digest(mark_failed(digest))

        notifications = [
            n
            for n in (self._repository.get_notification(nid) for nid in digest.notification_ids)
            if n is not None
        ]
        subject = f"DealBrain {digest.period.value.title()} Digest — {len(notifications)} update(s)"
        lines = [f"{n.title}: {n.body}" for n in notifications] or ["No updates."]
        body_text = "\n".join(lines)
        body_html = "<br/>".join(html.escape(line) for line in lines)
        self._email_provider.send(
            EmailMessage(
                to_address=f"{digest.user_id}@example.invalid",
                subject=subject,
                body_text=body_text,
                body_html=body_html,
            )
        )
        return self._repository.save_digest(mark_simulated(digest))
