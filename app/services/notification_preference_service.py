"""Notification Preference application service — Sprint 19.

Thin, validated CRUD over ``UserNotificationPreferences``. Marketing
communications are opt-in only: ``get_preferences`` always returns
``marketing_enabled=False`` for a brand-new user, and no code path here (or
anywhere in this service) ever *implicitly* flips it on — it can only change
via an explicit ``marketing_enabled=`` argument to :meth:`update_preferences`,
i.e. a deliberate user action.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from app.domain.entities.notifications import UserNotificationPreferences
from app.domain.exceptions import NotificationValidationError
from app.domain.interfaces.notification_center_repository import NotificationCenterRepository
from app.notifications.preferences import (
    channel_enabled,
    default_preferences,
    is_within_quiet_hours,
    should_suppress_immediate_alert,
)

# Sentinel distinguishing "not supplied" from "explicitly cleared to None"
# for the nullable quiet-hours fields.
_UNSET = object()


class NotificationPreferenceService:
    """Get/update per-user notification preferences with safe defaults."""

    def __init__(
        self,
        repository: NotificationCenterRepository,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_preferences(self, user_id: str) -> UserNotificationPreferences:
        """Return stored preferences, creating opt-in-only defaults if unset."""
        existing = self._repository.get_preferences(user_id)
        if existing is not None:
            return existing
        created = default_preferences(user_id, created_at=self._clock())
        return self._repository.save_preferences(created)

    def update_preferences(
        self,
        user_id: str,
        *,
        in_app_enabled: bool | None = None,
        email_enabled: bool | None = None,
        immediate_alerts: bool | None = None,
        daily_digest: bool | None = None,
        weekly_digest: bool | None = None,
        quiet_hours_start: object = _UNSET,
        quiet_hours_end: object = _UNSET,
        timezone: str | None = None,
        price_alerts: bool | None = None,
        stock_alerts: bool | None = None,
        freshness_warnings: bool | None = None,
        marketing_enabled: bool | None = None,
    ) -> UserNotificationPreferences:
        current = self.get_preferences(user_id)
        updates: dict[str, object] = {"updated_at": self._clock()}

        if in_app_enabled is not None:
            updates["in_app_enabled"] = in_app_enabled
        if email_enabled is not None:
            updates["email_enabled"] = email_enabled
        if immediate_alerts is not None:
            updates["immediate_alerts"] = immediate_alerts
        if daily_digest is not None:
            updates["daily_digest"] = daily_digest
        if weekly_digest is not None:
            updates["weekly_digest"] = weekly_digest
        if quiet_hours_start is not _UNSET:
            updates["quiet_hours_start"] = quiet_hours_start
        if quiet_hours_end is not _UNSET:
            updates["quiet_hours_end"] = quiet_hours_end
        if timezone is not None:
            cleaned = timezone.strip()
            if not cleaned:
                raise NotificationValidationError("timezone must not be blank.")
            updates["timezone"] = cleaned
        if price_alerts is not None:
            updates["price_alerts"] = price_alerts
        if stock_alerts is not None:
            updates["stock_alerts"] = stock_alerts
        if freshness_warnings is not None:
            updates["freshness_warnings"] = freshness_warnings
        if marketing_enabled is not None:
            # Only ever set via this explicit, named argument — never as a
            # side effect of any other preference change.
            updates["marketing_enabled"] = marketing_enabled

        updated = replace(current, **updates)  # type: ignore[arg-type]
        return self._repository.save_preferences(updated)

    def is_quiet_hours(self, user_id: str, *, now: datetime | None = None) -> bool:
        prefs = self.get_preferences(user_id)
        return is_within_quiet_hours(prefs, now=now or self._clock())

    def should_suppress_immediate(self, user_id: str, *, now: datetime | None = None) -> bool:
        prefs = self.get_preferences(user_id)
        return should_suppress_immediate_alert(prefs, now=now or self._clock())

    def channel_enabled(self, user_id: str, channel: str) -> bool:
        prefs = self.get_preferences(user_id)
        return channel_enabled(prefs, channel)
