"""Notification delivery port — all implementations must remain mock/simulated.

``notify`` is the Sprint 10 contract and remains the sole abstract method so
that ``app.intelligence.watchlists.notifications.MockNotificationService``
(a protected Sprint 10 module) continues to satisfy this interface unchanged.
``notify_event`` is a Sprint 19 addition with a default no-op implementation;
override it only in new adapters that fan alert-rule events out to the
Notification Center.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.alerts import AlertEvent
from app.domain.entities.watchlist import Alert, NotificationReceipt


class NotificationService(ABC):
    """Queue notifications for alerts. Implementations must not send real mail/SMS."""

    @abstractmethod
    def notify(self, alert: Alert) -> NotificationReceipt:
        """Queue a notification for an alert and return a receipt."""

    def notify_event(self, event: AlertEvent) -> NotificationReceipt | None:
        """Optional richer delivery hook for Sprint 19 rule-driven alert events.

        Default implementation is a no-op (returns ``None``) so existing
        ``NotificationService`` implementations — including the Sprint 10
        mock — remain valid without overriding it.
        """
        return None
