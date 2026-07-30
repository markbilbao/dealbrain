"""SQLAlchemy Notification Center repository — Sprint 23."""

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
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import (
    NC_DELIVERIES,
    NC_DIGESTS,
    NC_NOTIFICATIONS,
    NC_PREFERENCES,
    NC_TEMPLATES,
    NC_UNSUBSCRIBE,
    NOTIFICATION_STORES,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _delivery_entity_id(delivery: NotificationDelivery) -> str:
    if delivery.delivery_id:
        return delivery.delivery_id
    return f"{delivery.notification_id}:{delivery.channel.value}:{delivery.attempt}"


class SqlAlchemyNotificationCenterRepository(NotificationCenterRepository, SessionBound):
    # -------------------------------------------------------------- notifications
    def save_notification(self, notification: Notification) -> Notification:
        with self._ops() as ops:
            return ops.upsert(
                NC_NOTIFICATIONS,
                notification.notification_id,
                notification,
                owner_id=notification.user_id,
            )

    def get_notification(self, notification_id: str) -> Notification | None:
        with self._ops() as ops:
            return ops.get(NC_NOTIFICATIONS, notification_id, Notification)

    def list_notifications(
        self,
        *,
        user_id: str,
        unread_only: bool = False,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        def _matches(notification: Notification) -> bool:
            if notification.user_id != user_id:
                return False
            if not include_archived and notification.archived_at is not None:
                return False
            if unread_only and notification.read_at is not None:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                NC_NOTIFICATIONS,
                Notification,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    def mark_read(self, notification_id: str) -> Notification:
        with self._ops() as ops:
            notification = ops.get(NC_NOTIFICATIONS, notification_id, Notification)
            if notification is None:
                raise NotificationNotFoundError(notification_id)
            if notification.read_at is not None:
                return notification
            updated = replace(notification, read_at=_now())
            return ops.upsert(
                NC_NOTIFICATIONS,
                notification_id,
                updated,
                owner_id=updated.user_id,
            )

    def archive_notification(self, notification_id: str) -> Notification:
        with self._ops() as ops:
            notification = ops.get(NC_NOTIFICATIONS, notification_id, Notification)
            if notification is None:
                raise NotificationNotFoundError(notification_id)
            if notification.archived_at is not None:
                return notification
            updated = replace(notification, archived_at=_now())
            return ops.upsert(
                NC_NOTIFICATIONS,
                notification_id,
                updated,
                owner_id=updated.user_id,
            )

    def count_unread(self, user_id: str) -> int:
        with self._ops() as ops:
            notifications = ops.list(NC_NOTIFICATIONS, Notification, owner_id=user_id)
        return sum(
            1
            for n in notifications
            if n.read_at is None and n.archived_at is None
        )

    def delete_notification(self, notification_id: str) -> bool:
        with self._ops() as ops:
            if ops.get(NC_NOTIFICATIONS, notification_id, Notification) is None:
                return False
            ops.delete(NC_NOTIFICATIONS, notification_id)
            for delivery in ops.list(NC_DELIVERIES, NotificationDelivery, owner_id=notification_id):
                ops.delete(NC_DELIVERIES, _delivery_entity_id(delivery))
            return True

    # ------------------------------------------------------------------ deliveries
    def save_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        entity_id = _delivery_entity_id(delivery)
        with self._ops() as ops:
            return ops.upsert(
                NC_DELIVERIES,
                entity_id,
                delivery,
                owner_id=delivery.notification_id,
            )

    def list_deliveries(self, notification_id: str) -> list[NotificationDelivery]:
        with self._ops() as ops:
            return ops.list(NC_DELIVERIES, NotificationDelivery, owner_id=notification_id)

    # ------------------------------------------------------------------- templates
    def save_template(self, template: NotificationTemplate) -> NotificationTemplate:
        with self._ops() as ops:
            return ops.upsert(NC_TEMPLATES, template.template_id, template)

    def get_template(self, template_id: str) -> NotificationTemplate | None:
        with self._ops() as ops:
            return ops.get(NC_TEMPLATES, template_id, NotificationTemplate)

    def list_templates(self) -> list[NotificationTemplate]:
        with self._ops() as ops:
            return ops.list(NC_TEMPLATES, NotificationTemplate)

    # --------------------------------------------------------------------- digests
    def save_digest(self, digest: NotificationDigest) -> NotificationDigest:
        with self._ops() as ops:
            return ops.upsert(
                NC_DIGESTS,
                digest.digest_id,
                digest,
                owner_id=digest.user_id,
            )

    def get_digest(self, digest_id: str) -> NotificationDigest | None:
        with self._ops() as ops:
            return ops.get(NC_DIGESTS, digest_id, NotificationDigest)

    def list_digests(self, user_id: str, *, limit: int = 20) -> list[NotificationDigest]:
        with self._ops() as ops:
            return ops.list(
                NC_DIGESTS,
                NotificationDigest,
                owner_id=user_id,
                reverse=True,
                limit=limit,
            )

    # ----------------------------------------------------------------- preferences
    def save_preferences(
        self, preferences: UserNotificationPreferences
    ) -> UserNotificationPreferences:
        with self._ops() as ops:
            return ops.upsert(
                NC_PREFERENCES,
                preferences.user_id,
                preferences,
                owner_id=preferences.user_id,
            )

    def get_preferences(self, user_id: str) -> UserNotificationPreferences | None:
        with self._ops() as ops:
            return ops.get(NC_PREFERENCES, user_id, UserNotificationPreferences)

    # --------------------------------------------------------------- unsubscribe
    def save_unsubscribe_token(self, token: UnsubscribeToken) -> UnsubscribeToken:
        with self._ops() as ops:
            return ops.upsert(
                NC_UNSUBSCRIBE,
                token.token_hash,
                token,
                secondary_key=token.token_hash,
                owner_id=token.user_id,
            )

    def get_unsubscribe_token(self, token_hash: str) -> UnsubscribeToken | None:
        with self._ops() as ops:
            return ops.get(NC_UNSUBSCRIBE, token_hash, UnsubscribeToken)

    def revoke_unsubscribe_token(self, token_hash: str) -> bool:
        with self._ops() as ops:
            token = ops.get(NC_UNSUBSCRIBE, token_hash, UnsubscribeToken)
            if token is None:
                return False
            if token.revoked_at is not None:
                return True
            updated = replace(token, revoked_at=_now())
            ops.upsert(
                NC_UNSUBSCRIBE,
                token_hash,
                updated,
                secondary_key=token_hash,
                owner_id=updated.user_id,
            )
            return True

    # -------------------------------------------------------------------------- misc
    def clear(self) -> None:
        with self._ops() as ops:
            ops.clear_stores(NOTIFICATION_STORES)
