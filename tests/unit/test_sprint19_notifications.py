"""Unit tests for the Sprint 19 Notification Center, preferences, and
(simulated) email delivery.

Covers creation, unread counting, mark-read/mark-all-read/archive/delete,
filtering, preferences (including quiet hours), daily/weekly digest
architecture, mock email delivery, and email failure handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.entities.notifications import (
    DigestStatus,
    NotificationSeverity,
    NotificationType,
)
from app.domain.exceptions import NotificationNotFoundError, NotificationValidationError
from app.notifications.email.provider import (
    SIMULATED_EMAIL_MARKER,
    EmailMessage,
    EmailNotificationProvider,
    EmailSendResult,
    MockEmailNotificationProvider,
)
from app.notifications.memory import InMemoryNotificationCenterRepository
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _build_service(
    *, email_provider: EmailNotificationProvider | None = None
) -> tuple[NotificationCenterService, InMemoryNotificationCenterRepository]:
    repo = InMemoryNotificationCenterRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"id-{counter['n']}"

    service = NotificationCenterService(
        repo,
        email_provider=email_provider,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )
    return service, repo


# --------------------------------------------------------------------- creation


def test_create_notification_defaults_to_unread_in_app() -> None:
    service, _ = _build_service()
    notification = service.create_notification(
        user_id="user-1", title="Price drop", body="It dropped!", type=NotificationType.PRICE_DROP
    )
    assert notification.read_at is None
    assert notification.archived_at is None
    assert notification.severity == NotificationSeverity.INFO


def test_create_notification_rejects_blank_title() -> None:
    service, _ = _build_service()
    with pytest.raises(NotificationValidationError):
        service.create_notification(
            user_id="user-1", title="   ", body="x", type=NotificationType.SYSTEM
        )


# --------------------------------------------------------------------- unread / read


def test_unread_count_and_mark_read() -> None:
    service, _ = _build_service()
    n1 = service.create_notification(
        user_id="user-1", title="A", body="a", type=NotificationType.PRICE_DROP
    )
    service.create_notification(
        user_id="user-1", title="B", body="b", type=NotificationType.RESTOCK
    )
    assert service.unread_count("user-1") == 2

    read = service.mark_read(n1.notification_id, user_id="user-1")
    assert read.read_at is not None
    assert service.unread_count("user-1") == 1


def test_mark_all_read_updates_every_unread_notification() -> None:
    service, _ = _build_service()
    for i in range(3):
        service.create_notification(
            user_id="user-1", title=f"N{i}", body="body", type=NotificationType.SYSTEM
        )
    count = service.mark_all_read("user-1")
    assert count == 3
    assert service.unread_count("user-1") == 0


def test_mark_read_raises_for_wrong_owner() -> None:
    service, _ = _build_service()
    n1 = service.create_notification(
        user_id="user-1", title="A", body="a", type=NotificationType.SYSTEM
    )
    with pytest.raises(NotificationNotFoundError):
        service.mark_read(n1.notification_id, user_id="someone-else")


# --------------------------------------------------------------------- archive / delete


def test_archive_notification() -> None:
    service, _ = _build_service()
    n1 = service.create_notification(
        user_id="user-1", title="A", body="a", type=NotificationType.SYSTEM
    )
    archived = service.archive(n1.notification_id, user_id="user-1")
    assert archived.archived_at is not None
    # Archived notifications no longer count as unread.
    assert service.unread_count("user-1") == 0


def test_delete_notification_removes_it() -> None:
    service, _ = _build_service()
    n1 = service.create_notification(
        user_id="user-1", title="A", body="a", type=NotificationType.SYSTEM
    )
    service.delete(n1.notification_id, user_id="user-1")
    with pytest.raises(NotificationNotFoundError):
        service.get_notification(n1.notification_id)


# --------------------------------------------------------------------- filtering


def test_list_notifications_filters_by_type_and_unread() -> None:
    service, _ = _build_service()
    price = service.create_notification(
        user_id="user-1", title="Price", body="p", type=NotificationType.PRICE_DROP
    )
    restock = service.create_notification(
        user_id="user-1", title="Restock", body="r", type=NotificationType.RESTOCK
    )
    service.mark_read(restock.notification_id, user_id="user-1")

    price_only = service.list_notifications("user-1", type=NotificationType.PRICE_DROP)
    assert [n.notification_id for n in price_only] == [price.notification_id]

    unread_only = service.list_notifications("user-1", unread=True)
    assert [n.notification_id for n in unread_only] == [price.notification_id]


def test_list_notifications_respects_pagination() -> None:
    service, _ = _build_service()
    for i in range(5):
        service.create_notification(
            user_id="user-1", title=f"N{i}", body="body", type=NotificationType.SYSTEM
        )
    page = service.list_notifications("user-1", limit=2, offset=1)
    assert len(page) == 2


# --------------------------------------------------------------------- preferences / suppression


def test_type_suppression_via_preferences_skips_in_app_delivery() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", price_alerts=False)
    service = NotificationCenterService(repo, preference_service=prefs, clock=lambda: FIXED_NOW)

    notification = service.create_notification(
        user_id="user-1", title="Price", body="p", type=NotificationType.PRICE_DROP
    )
    # Notification is still recorded, but not counted as an actionable unread
    # item once its type is disabled for in-app delivery... it is still
    # stored, but delivery_status reflects the skip.
    from app.domain.entities.watchlist import NotificationStatus

    assert notification.delivery_status == NotificationStatus.SKIPPED


def test_quiet_hours_suppress_immediate_email_delivery() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences(
        "user-1", email_enabled=True, quiet_hours_start="00:00", quiet_hours_end="23:59"
    )
    provider = MockEmailNotificationProvider(clock=lambda: FIXED_NOW)
    service = NotificationCenterService(
        repo, preference_service=prefs, email_provider=provider, clock=lambda: FIXED_NOW
    )

    service.create_notification(
        user_id="user-1", title="Price", body="p", type=NotificationType.PRICE_DROP
    )
    # Entire day is quiet hours -> no simulated email should have been sent.
    assert provider.sent_messages == []


def test_marketing_disabled_by_default() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    fresh = prefs.get_preferences("new-user")
    assert fresh.marketing_enabled is False

    updated = prefs.update_preferences("new-user", marketing_enabled=True)
    assert updated.marketing_enabled is True


def test_is_quiet_hours_and_should_suppress_immediate() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", quiet_hours_start="22:00", quiet_hours_end="07:00")

    late_night = datetime(2026, 7, 29, 23, 0, tzinfo=UTC)
    daytime = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
    assert prefs.is_quiet_hours("user-1", now=late_night) is True
    assert prefs.is_quiet_hours("user-1", now=daytime) is False
    assert prefs.should_suppress_immediate("user-1", now=late_night) is True


# --------------------------------------------------------------------- mock email


def test_mock_email_provider_marks_every_send_as_simulated() -> None:
    provider = MockEmailNotificationProvider(clock=lambda: FIXED_NOW, id_factory=lambda: "msg-1")
    result = provider.send(
        EmailMessage(to_address="user-1@example.invalid", subject="Hi", body_text="Body")
    )
    assert result.simulated is True
    assert SIMULATED_EMAIL_MARKER in result.detail
    assert provider.sent_messages == [result]


def test_email_delivery_happens_when_enabled_and_not_quiet_hours() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", email_enabled=True)
    provider = MockEmailNotificationProvider(clock=lambda: FIXED_NOW)
    service = NotificationCenterService(
        repo, preference_service=prefs, email_provider=provider, clock=lambda: FIXED_NOW
    )

    service.create_notification(
        user_id="user-1", title="Price drop!", body="It dropped.", type=NotificationType.PRICE_DROP
    )
    assert len(provider.sent_messages) == 1
    assert SIMULATED_EMAIL_MARKER in provider.sent_messages[0].detail
    assert provider.sent_messages[0].to_address == "user-1@example.invalid"


def test_email_failure_does_not_corrupt_already_saved_notification() -> None:
    """A raising email provider still leaves the in-app notification intact.

    The notification row is persisted *before* channel fan-out runs, so a
    failing (mis-)configured email provider cannot roll back or corrupt the
    already-saved in-app notification — only the email side effect is lost.
    """

    class FailingEmailProvider(EmailNotificationProvider):
        def send(self, message: EmailMessage) -> EmailSendResult:
            raise RuntimeError("simulated transport failure")

    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", email_enabled=True)
    service = NotificationCenterService(
        repo,
        preference_service=prefs,
        email_provider=FailingEmailProvider(),
        clock=lambda: FIXED_NOW,
    )

    with pytest.raises(RuntimeError):
        service.create_notification(
            user_id="user-1", title="Oops", body="body", type=NotificationType.PRICE_DROP
        )

    # The notification itself is still retrievable — only email delivery failed.
    saved = [n for n in repo.list_notifications(user_id="user-1", limit=10)]
    assert len(saved) == 1
    assert saved[0].title == "Oops"


# --------------------------------------------------------------------- digests


def test_daily_digest_has_no_content_when_nothing_pending() -> None:
    service, _ = _build_service()
    digest = service.build_daily_digest("user-1")
    assert digest.notification_ids == ()

    delivered = service.deliver_digest(digest)
    assert delivered.status == DigestStatus.FAILED


def test_daily_digest_includes_unread_notifications_and_simulates_send() -> None:
    provider = MockEmailNotificationProvider(clock=lambda: FIXED_NOW)
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", email_enabled=True, daily_digest=True)
    service = NotificationCenterService(
        repo, preference_service=prefs, email_provider=provider, clock=lambda: FIXED_NOW
    )
    # Suppress immediate email (quiet hours) so provider.sent_messages only
    # reflects the digest send below, keeping the assertion unambiguous.
    prefs.update_preferences("user-1", quiet_hours_start="00:00", quiet_hours_end="23:59")

    service.create_notification(
        user_id="user-1", title="Price drop", body="p", type=NotificationType.PRICE_DROP
    )
    service.create_notification(
        user_id="user-1", title="Restock", body="r", type=NotificationType.RESTOCK
    )

    digest = service.build_daily_digest("user-1")
    assert len(digest.notification_ids) == 2

    delivered = service.deliver_digest(digest)
    assert delivered.status == DigestStatus.SIMULATED
    assert len(provider.sent_messages) == 1
    assert SIMULATED_EMAIL_MARKER in provider.sent_messages[0].detail


def test_weekly_digest_respects_since_window() -> None:
    service, repo = _build_service()
    old = service.create_notification(
        user_id="user-1", title="Old", body="old", type=NotificationType.SYSTEM
    )
    _ = old
    digest = service.build_weekly_digest("user-1", since=FIXED_NOW + timedelta(days=1))
    # The only notification created is from before `since`, so nothing qualifies.
    assert digest.notification_ids == ()


def test_deliver_digest_fails_when_email_not_enabled() -> None:
    service, _ = _build_service()
    service.create_notification(user_id="user-1", title="A", body="a", type=NotificationType.SYSTEM)
    digest = service.build_daily_digest("user-1")
    assert digest.notification_ids != ()
    delivered = service.deliver_digest(digest)
    assert delivered.status == DigestStatus.FAILED


# --------------------------------------------------------------------- unsubscribe


def test_unsubscribe_token_disables_email_and_digests() -> None:
    repo = InMemoryNotificationCenterRepository()
    prefs = NotificationPreferenceService(repo, clock=lambda: FIXED_NOW)
    prefs.update_preferences("user-1", email_enabled=True, daily_digest=True, weekly_digest=True)
    service = NotificationCenterService(repo, preference_service=prefs, clock=lambda: FIXED_NOW)

    raw_token, _ = service.create_unsubscribe_token("user-1")
    updated = service.unsubscribe(raw_token)
    assert updated is not None
    assert updated.email_enabled is False
    assert updated.daily_digest is False
    assert updated.weekly_digest is False

    # Token is single-use.
    assert service.unsubscribe(raw_token) is None
