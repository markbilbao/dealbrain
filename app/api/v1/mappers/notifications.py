"""Map Notification Center domain objects (Sprint 19) to HTTP schemas."""

from __future__ import annotations

from app.core.public_brand import present_consumer_text
from app.domain.entities.notifications import Notification, UserNotificationPreferences
from app.schemas.notifications import NotificationPayload, NotificationPreferencesPayload


def to_notification_payload(notification: Notification) -> NotificationPayload:
    return NotificationPayload(
        notification_id=notification.notification_id,
        user_id=notification.user_id,
        title=present_consumer_text(notification.title),
        body=present_consumer_text(notification.body),
        type=notification.type.value,
        severity=notification.severity.value,
        watchlist_id=notification.watchlist_id,
        alert_id=notification.alert_id,
        alert_event_id=notification.alert_event_id,
        channel=notification.channel.value,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        archived_at=notification.archived_at.isoformat() if notification.archived_at else None,
        delivery_status=notification.delivery_status.value,
        created_at=notification.created_at.isoformat(),
        metadata=dict(notification.metadata),
        is_read=notification.read_at is not None,
        is_archived=notification.archived_at is not None,
    )


def to_preferences_payload(
    preferences: UserNotificationPreferences,
) -> NotificationPreferencesPayload:
    return NotificationPreferencesPayload(
        user_id=preferences.user_id,
        in_app_enabled=preferences.in_app_enabled,
        email_enabled=preferences.email_enabled,
        immediate_alerts=preferences.immediate_alerts,
        daily_digest=preferences.daily_digest,
        weekly_digest=preferences.weekly_digest,
        quiet_hours_start=preferences.quiet_hours_start,
        quiet_hours_end=preferences.quiet_hours_end,
        timezone=preferences.timezone,
        price_alerts=preferences.price_alerts,
        stock_alerts=preferences.stock_alerts,
        freshness_warnings=preferences.freshness_warnings,
        marketing_enabled=preferences.marketing_enabled,
        created_at=preferences.created_at.isoformat(),
        updated_at=(preferences.updated_at or preferences.created_at).isoformat(),
    )
