"""Mock notification adapter — queues receipts without delivering."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.watchlist import (
    Alert,
    NotificationChannel,
    NotificationReceipt,
    NotificationStatus,
)
from app.domain.interfaces.notification_service import NotificationService


class MockNotificationService(NotificationService):
    """Return queued mock receipts. Never sends email, SMS, or push."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._receipts: list[NotificationReceipt] = []

    def notify(self, alert: Alert) -> NotificationReceipt:
        receipt = NotificationReceipt(
            notification_id=self._id_factory(),
            alert_id=alert.alert_id,
            channel=NotificationChannel.MOCK,
            status=NotificationStatus.QUEUED,
            created_at=self._clock(),
            detail=(
                f"Queued mock notification for alert {alert.alert_id} "
                f"({alert.alert_type.value}). No email/SMS/push sent."
            ),
        )
        self._receipts.append(receipt)
        return receipt

    @property
    def receipts(self) -> list[NotificationReceipt]:
        """All receipts queued in this process (tests / demo)."""
        return list(self._receipts)

    def clear(self) -> None:
        self._receipts.clear()
