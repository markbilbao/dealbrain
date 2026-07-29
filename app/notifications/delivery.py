"""Parallel ``NotificationService`` adapter — Sprint 19.

``app.intelligence.watchlists.notifications.MockNotificationService`` is
documented (see ``app/domain/interfaces/notification_service.py``) as a
protected Sprint 10 module and is left untouched. :class:`EnhancedNotificationService`
implements the same :class:`NotificationService` port as a standalone, parallel
adapter: it satisfies the Sprint 10 ``notify(alert)`` contract (by default
delegating to a fresh, unmodified ``MockNotificationService`` instance) and
additionally implements ``notify_event`` to fan alert-rule events out into the
Notification Center when one is configured. All delivery remains
mock/simulated — no real email/SMS/push transport exists here or anywhere
else in this codebase.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.alerts import AlertEvent
from app.domain.entities.watchlist import (
    Alert,
    NotificationChannel,
    NotificationReceipt,
    NotificationStatus,
)
from app.domain.interfaces.notification_service import NotificationService
from app.intelligence.watchlists.notifications import MockNotificationService


class EnhancedNotificationService(NotificationService):
    """Sprint 19 notification adapter — wraps a Sprint 10 ``NotificationService``.

    Every ``notify``/``notify_event`` call remains a mock/simulated receipt;
    the only "enhancement" is optionally also creating an in-app Notification
    Center entry via an injected ``notification_center_service`` collaborator
    (duck-typed: any object exposing ``create_notification``/
    ``create_from_alert_event`` works, so this module never imports the
    Notification Center service directly and stays free of import cycles).
    """

    def __init__(
        self,
        *,
        inner: NotificationService | None = None,
        notification_center_service: Any | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._inner = inner or MockNotificationService(clock=clock, id_factory=id_factory)
        self._notification_center = notification_center_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def notify(self, alert: Alert) -> NotificationReceipt:
        receipt = self._inner.notify(alert)
        self._fan_out_alert(alert)
        return receipt

    def notify_event(self, event: AlertEvent) -> NotificationReceipt | None:
        self._fan_out_event(event)
        return NotificationReceipt(
            notification_id=self._id_factory(),
            alert_id=event.alert_id or event.event_id,
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SIMULATED,
            created_at=self._clock(),
            detail=(
                f"Queued mock in-app notification for event {event.event_id} "
                f"({event.event_type.value}). No email/SMS/push sent."
            ),
        )

    def _fan_out_alert(self, alert: Alert) -> None:
        if self._notification_center is None:
            return
        create = getattr(self._notification_center, "create_notification", None)
        if not callable(create):
            return
        try:
            from app.domain.entities.notifications import NotificationSeverity, NotificationType

            create(
                user_id="",  # Sprint 10 Alert has no user_id; callers with a
                # known user should prefer notify_event/create_from_alert_event.
                title=f"Alert: {alert.alert_type.value}",
                body=alert.message,
                type=NotificationType.SYSTEM,
                severity=NotificationSeverity.INFO,
                watchlist_id=alert.watchlist_id,
                alert_id=alert.alert_id,
            )
        except Exception:  # noqa: BLE001 - never let notification fan-out break alerting.
            return

    def _fan_out_event(self, event: AlertEvent) -> None:
        if self._notification_center is None:
            return
        create_from_event = getattr(self._notification_center, "create_from_alert_event", None)
        if not callable(create_from_event):
            return
        try:
            create_from_event(event)
        except Exception:  # noqa: BLE001
            return

    @property
    def inner(self) -> NotificationService:
        """The wrapped Sprint 10 notification service (tests / introspection)."""
        return self._inner
