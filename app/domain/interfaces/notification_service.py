"""Notification delivery port — Sprint 10 uses a mock implementation only."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.watchlist import Alert, NotificationReceipt


class NotificationService(ABC):
    """Queue notifications for alerts. Implementations must not send real mail/SMS."""

    @abstractmethod
    def notify(self, alert: Alert) -> NotificationReceipt:
        """Queue a notification for an alert and return a receipt."""
