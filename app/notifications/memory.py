"""In-memory Notification Center repository — Sprint 19."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities.notifications import (
    Notification,
    NotificationDelivery,
    NotificationDigest,
    NotificationTemplate,
    UnsubscribeToken,
    UserNotificationPreferences,
)
from app.domain.exceptions import NotificationNotFoundError
from app.domain.interfaces.notification_center_repository import NotificationCenterRepository


def _now() -> datetime:
    """Wall-clock timestamp for read/archive/revoke transitions.

    Domain entities never generate timestamps themselves; this repository —
    an infrastructure adapter — is the sole source of "now" for state
    transitions it performs on stored records.
    """
    return datetime.now(UTC)


class InMemoryNotificationCenterRepository(NotificationCenterRepository):
    """Process-local store backing the in-app Notification Center."""

    def __init__(self) -> None:
        self._notifications: dict[str, Notification] = {}
        self._notification_order: list[str] = []
        self._deliveries: dict[str, list[NotificationDelivery]] = {}
        self._templates: dict[str, NotificationTemplate] = {}
        self._template_order: list[str] = []
        self._digests: dict[str, NotificationDigest] = {}
        self._digest_order: list[str] = []
        self._preferences: dict[str, UserNotificationPreferences] = {}
        self._unsubscribe_tokens: dict[str, UnsubscribeToken] = {}

    # -------------------------------------------------------------- notifications
    def save_notification(self, notification: Notification) -> Notification:
        if notification.notification_id not in self._notifications:
            self._notification_order.append(notification.notification_id)
        self._notifications[notification.notification_id] = notification
        return notification

    def get_notification(self, notification_id: str) -> Notification | None:
        return self._notifications.get(notification_id)

    def list_notifications(
        self,
        *,
        user_id: str,
        unread_only: bool = False,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        ordered = [
            self._notifications[nid]
            for nid in reversed(self._notification_order)
            if nid in self._notifications
        ]
        ordered = [n for n in ordered if n.user_id == user_id]
        if not include_archived:
            ordered = [n for n in ordered if n.archived_at is None]
        if unread_only:
            ordered = [n for n in ordered if n.read_at is None]
        return ordered[: max(0, limit)]

    def mark_read(self, notification_id: str) -> Notification:
        notification = self._require_notification(notification_id)
        if notification.read_at is not None:
            return notification
        updated = replace(notification, read_at=_now())
        self._notifications[notification_id] = updated
        return updated

    def archive_notification(self, notification_id: str) -> Notification:
        notification = self._require_notification(notification_id)
        if notification.archived_at is not None:
            return notification
        updated = replace(notification, archived_at=_now())
        self._notifications[notification_id] = updated
        return updated

    def count_unread(self, user_id: str) -> int:
        return sum(
            1
            for n in self._notifications.values()
            if n.user_id == user_id and n.read_at is None and n.archived_at is None
        )

    def _require_notification(self, notification_id: str) -> Notification:
        notification = self._notifications.get(notification_id)
        if notification is None:
            raise NotificationNotFoundError(notification_id)
        return notification

    def delete_notification(self, notification_id: str) -> bool:
        if notification_id not in self._notifications:
            return False
        del self._notifications[notification_id]
        self._notification_order = [
            nid for nid in self._notification_order if nid != notification_id
        ]
        self._deliveries.pop(notification_id, None)
        return True

    # ------------------------------------------------------------------ deliveries
    def save_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        bucket = self._deliveries.setdefault(delivery.notification_id, [])
        bucket.append(delivery)
        return delivery

    def list_deliveries(self, notification_id: str) -> list[NotificationDelivery]:
        return list(self._deliveries.get(notification_id, []))

    # ------------------------------------------------------------------- templates
    def save_template(self, template: NotificationTemplate) -> NotificationTemplate:
        if template.template_id not in self._templates:
            self._template_order.append(template.template_id)
        self._templates[template.template_id] = template
        return template

    def get_template(self, template_id: str) -> NotificationTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[NotificationTemplate]:
        return [self._templates[tid] for tid in self._template_order if tid in self._templates]

    # --------------------------------------------------------------------- digests
    def save_digest(self, digest: NotificationDigest) -> NotificationDigest:
        if digest.digest_id not in self._digests:
            self._digest_order.append(digest.digest_id)
        self._digests[digest.digest_id] = digest
        return digest

    def get_digest(self, digest_id: str) -> NotificationDigest | None:
        return self._digests.get(digest_id)

    def list_digests(self, user_id: str, *, limit: int = 20) -> list[NotificationDigest]:
        ordered = [
            self._digests[did] for did in reversed(self._digest_order) if did in self._digests
        ]
        ordered = [d for d in ordered if d.user_id == user_id]
        return ordered[: max(0, limit)]

    # ----------------------------------------------------------------- preferences
    def save_preferences(
        self, preferences: UserNotificationPreferences
    ) -> UserNotificationPreferences:
        self._preferences[preferences.user_id] = preferences
        return preferences

    def get_preferences(self, user_id: str) -> UserNotificationPreferences | None:
        return self._preferences.get(user_id)

    # --------------------------------------------------------------- unsubscribe
    def save_unsubscribe_token(self, token: UnsubscribeToken) -> UnsubscribeToken:
        self._unsubscribe_tokens[token.token_hash] = token
        return token

    def get_unsubscribe_token(self, token_hash: str) -> UnsubscribeToken | None:
        return self._unsubscribe_tokens.get(token_hash)

    def revoke_unsubscribe_token(self, token_hash: str) -> bool:
        token = self._unsubscribe_tokens.get(token_hash)
        if token is None:
            return False
        if token.revoked_at is not None:
            return True
        self._unsubscribe_tokens[token_hash] = replace(token, revoked_at=_now())
        return True

    # -------------------------------------------------------------------------- misc
    def clear(self) -> None:
        """Reset all stored notifications, deliveries, templates, digests,
        preferences, and unsubscribe tokens (tests).
        """
        self._notifications.clear()
        self._notification_order.clear()
        self._deliveries.clear()
        self._templates.clear()
        self._template_order.clear()
        self._digests.clear()
        self._digest_order.clear()
        self._preferences.clear()
        self._unsubscribe_tokens.clear()
