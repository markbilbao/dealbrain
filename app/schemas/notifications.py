"""Notification Center & Preferences (Sprint 19) API request and response schemas.

All delivery remains mock/simulated — no real email/SMS/push transport
exists anywhere in this codebase.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NotificationPayload(BaseModel):
    notification_id: str
    user_id: str
    title: str
    body: str
    type: str
    severity: str
    watchlist_id: str | None = None
    alert_id: str | None = None
    alert_event_id: str | None = None
    channel: str
    read_at: str | None = None
    archived_at: str | None = None
    delivery_status: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_read: bool = False
    is_archived: bool = False


class NotificationListResponse(BaseModel):
    notifications: list[NotificationPayload] = Field(default_factory=list)


class UnreadCountResponse(BaseModel):
    unread_count: int = 0


class MarkAllReadResponse(BaseModel):
    marked_read: int = 0


class NotificationPreferencesPayload(BaseModel):
    user_id: str
    in_app_enabled: bool = True
    email_enabled: bool = False
    immediate_alerts: bool = True
    daily_digest: bool = False
    weekly_digest: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str = "UTC"
    price_alerts: bool = True
    stock_alerts: bool = True
    freshness_warnings: bool = True
    marketing_enabled: bool = False
    created_at: str
    updated_at: str


class NotificationPreferencesUpdateRequest(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    immediate_alerts: bool | None = None
    daily_digest: bool | None = None
    weekly_digest: bool | None = None
    quiet_hours_start: str | None = None
    clear_quiet_hours_start: bool = False
    quiet_hours_end: str | None = None
    clear_quiet_hours_end: bool = False
    timezone: str | None = None
    price_alerts: bool | None = None
    stock_alerts: bool | None = None
    freshness_warnings: bool | None = None
    marketing_enabled: bool | None = None
