"""Notification preference helpers — Sprint 19.

Quiet-hours evaluation and a default-preferences factory. Marketing
communications are opt-in only — every default factory here sets
``marketing_enabled=False`` regardless of any other setting.
"""

from __future__ import annotations

from datetime import datetime, time

from app.domain.entities.notifications import UserNotificationPreferences


def default_preferences(user_id: str, *, created_at: datetime) -> UserNotificationPreferences:
    """Return a new user's default notification preferences.

    Uses the entity's own field defaults for everything except
    ``marketing_enabled``, which is set explicitly here (and defaults to
    False on the entity itself) to make the opt-in-only policy unmistakable
    at the call site.
    """
    return UserNotificationPreferences(
        user_id=user_id,
        created_at=created_at,
        marketing_enabled=False,
    )


def _parse_hhmm(value: str) -> time:
    hour_str, _, minute_str = value.strip().partition(":")
    return time(hour=int(hour_str), minute=int(minute_str or "0"))


def is_within_quiet_hours(preferences: UserNotificationPreferences, *, now: datetime) -> bool:
    """Return True if ``now`` falls within the user's configured quiet hours.

    ``now`` is assumed to already be expressed in the user's local time (this
    helper performs no timezone conversion — callers own that). Supports
    windows that wrap past midnight (e.g. ``22:00`` -> ``07:00``). Returns
    False when quiet hours are not configured.
    """
    if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
        return False
    start = _parse_hhmm(preferences.quiet_hours_start)
    end = _parse_hhmm(preferences.quiet_hours_end)
    current = now.time()
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def should_suppress_immediate_alert(
    preferences: UserNotificationPreferences,
    *,
    now: datetime,
) -> bool:
    """Return True if an immediate alert should be held back right now.

    Suppressed when the user disabled immediate alerts outright, or when
    ``now`` falls inside their quiet hours window — in either case the
    notification should instead surface via the next digest.
    """
    if not preferences.immediate_alerts:
        return True
    return is_within_quiet_hours(preferences, now=now)


def channel_enabled(preferences: UserNotificationPreferences, channel: str) -> bool:
    """Return True if the given channel name ('in_app' / 'email') is enabled."""
    if channel == "in_app":
        return preferences.in_app_enabled
    if channel == "email":
        return preferences.email_enabled
    return False
