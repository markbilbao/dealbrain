"""Daily/weekly notification digest builders — Sprint 19.

Pure functions assembling a :class:`NotificationDigest` from a user's pending
(unread, non-archived) notifications. No I/O — callers persist the result via
``NotificationCenterRepository.save_digest`` and simulate delivery via
``MockEmailNotificationProvider``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from app.domain.entities.notifications import (
    DigestPeriod,
    DigestStatus,
    Notification,
    NotificationDigest,
)


def select_pending_notifications(
    notifications: Sequence[Notification],
    *,
    since: datetime | None = None,
) -> list[Notification]:
    """Return unread, non-archived notifications eligible for a digest.

    When ``since`` is provided, only notifications created at or after that
    timestamp are included (used to scope a daily/weekly window).
    """
    selected = [n for n in notifications if n.read_at is None and n.archived_at is None]
    if since is not None:
        selected = [n for n in selected if n.created_at >= since]
    return selected


def build_digest(
    *,
    user_id: str,
    period: DigestPeriod,
    notifications: Sequence[Notification],
    created_at: datetime,
    since: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> NotificationDigest:
    """Build a :class:`NotificationDigest` from a user's pending notifications.

    Always returns ``status=DigestStatus.PENDING`` — callers should check
    :func:`has_content` before persisting/simulating delivery of an empty
    digest, and use :func:`mark_simulated`/:func:`mark_failed` afterward.
    """
    id_factory = id_factory or (lambda: str(uuid4()))
    pending = select_pending_notifications(notifications, since=since)
    return NotificationDigest(
        digest_id=id_factory(),
        user_id=user_id,
        period=period,
        notification_ids=tuple(n.notification_id for n in pending),
        status=DigestStatus.PENDING,
        created_at=created_at,
    )


def build_daily_digest(
    *,
    user_id: str,
    notifications: Sequence[Notification],
    created_at: datetime,
    since: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> NotificationDigest:
    """Build a daily-cadence digest. See :func:`build_digest`."""
    return build_digest(
        user_id=user_id,
        period=DigestPeriod.DAILY,
        notifications=notifications,
        created_at=created_at,
        since=since,
        id_factory=id_factory,
    )


def build_weekly_digest(
    *,
    user_id: str,
    notifications: Sequence[Notification],
    created_at: datetime,
    since: datetime | None = None,
    id_factory: Callable[[], str] | None = None,
) -> NotificationDigest:
    """Build a weekly-cadence digest. See :func:`build_digest`."""
    return build_digest(
        user_id=user_id,
        period=DigestPeriod.WEEKLY,
        notifications=notifications,
        created_at=created_at,
        since=since,
        id_factory=id_factory,
    )


def has_content(digest: NotificationDigest) -> bool:
    """Return True if a digest has at least one notification worth sending."""
    return len(digest.notification_ids) > 0


def mark_simulated(digest: NotificationDigest) -> NotificationDigest:
    """Return a copy of ``digest`` marked as simulate-sent.

    ``NotificationDigest`` is frozen; call this after "sending" (simulating)
    a digest via the email provider to update its persisted status.
    """
    return replace(digest, status=DigestStatus.SIMULATED)


def mark_failed(digest: NotificationDigest) -> NotificationDigest:
    """Return a copy of ``digest`` marked as failed to simulate-send."""
    return replace(digest, status=DigestStatus.FAILED)
