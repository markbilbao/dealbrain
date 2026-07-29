"""Notification Center persistence port — Sprint 19.

Covers in-app notifications, per-delivery-attempt tracking, templates,
digests, preferences, and unsubscribe tokens. Distinct from the Sprint 10
``NotificationService`` (queues a single mock receipt per alert); this port
backs a full notification inbox/history experience.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.notifications import (
    Notification,
    NotificationDelivery,
    NotificationDigest,
    NotificationTemplate,
    UnsubscribeToken,
    UserNotificationPreferences,
)


class NotificationCenterRepository(ABC):
    """Persistence for the in-app Notification Center."""

    # ------------------------------------------------------------- notifications
    @abstractmethod
    def save_notification(self, notification: Notification) -> Notification:
        """Create or replace a notification."""

    @abstractmethod
    def get_notification(self, notification_id: str) -> Notification | None:
        """Return a notification by id, or None."""

    @abstractmethod
    def list_notifications(
        self,
        *,
        user_id: str,
        unread_only: bool = False,
        include_archived: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Return a user's notifications newest-first, optionally filtered."""

    @abstractmethod
    def mark_read(self, notification_id: str) -> Notification:
        """Mark a notification as read and return the updated record."""

    @abstractmethod
    def archive_notification(self, notification_id: str) -> Notification:
        """Archive a notification and return the updated record."""

    @abstractmethod
    def count_unread(self, user_id: str) -> int:
        """Return the number of unread, non-archived notifications for a user."""

    def delete_notification(self, notification_id: str) -> bool:
        """Permanently delete a notification. Returns False if missing.

        Sprint 19 addition with a safe default (no-op returning False) so any
        pre-existing implementation of this port remains valid without
        overriding hard deletion.
        """
        return False

    # ------------------------------------------------------------------ deliveries
    @abstractmethod
    def save_delivery(self, delivery: NotificationDelivery) -> NotificationDelivery:
        """Record a delivery attempt for a notification."""

    @abstractmethod
    def list_deliveries(self, notification_id: str) -> list[NotificationDelivery]:
        """Return delivery attempts for a notification, oldest-first."""

    # ------------------------------------------------------------------ templates
    @abstractmethod
    def save_template(self, template: NotificationTemplate) -> NotificationTemplate:
        """Create or replace a notification template."""

    @abstractmethod
    def get_template(self, template_id: str) -> NotificationTemplate | None:
        """Return a template by id, or None."""

    @abstractmethod
    def list_templates(self) -> list[NotificationTemplate]:
        """Return all registered templates."""

    # -------------------------------------------------------------------- digests
    @abstractmethod
    def save_digest(self, digest: NotificationDigest) -> NotificationDigest:
        """Create or replace a notification digest."""

    @abstractmethod
    def get_digest(self, digest_id: str) -> NotificationDigest | None:
        """Return a digest by id, or None."""

    @abstractmethod
    def list_digests(self, user_id: str, *, limit: int = 20) -> list[NotificationDigest]:
        """Return a user's digests newest-first."""

    # --------------------------------------------------------------- preferences
    @abstractmethod
    def save_preferences(
        self, preferences: UserNotificationPreferences
    ) -> UserNotificationPreferences:
        """Create or replace a user's notification preferences."""

    @abstractmethod
    def get_preferences(self, user_id: str) -> UserNotificationPreferences | None:
        """Return a user's notification preferences, or None if unset."""

    # ------------------------------------------------------------- unsubscribe
    @abstractmethod
    def save_unsubscribe_token(self, token: UnsubscribeToken) -> UnsubscribeToken:
        """Create or replace an unsubscribe token (identified by its hash)."""

    @abstractmethod
    def get_unsubscribe_token(self, token_hash: str) -> UnsubscribeToken | None:
        """Return an unsubscribe token by its hash, or None."""

    @abstractmethod
    def revoke_unsubscribe_token(self, token_hash: str) -> bool:
        """Revoke an unsubscribe token. Returns False if missing."""
