"""User Dashboard (Sprint 19) API response schemas.

Read-only aggregation of watchlists, alert rules, and notifications. Figures
only ever summarize fixture/imported data — see ``limitations``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DashboardSummaryPayload(BaseModel):
    watched_products: int = 0
    active_alert_rules: int = 0
    unread_notifications: int = 0
    recent_price_drops: int = 0
    restocked_items: int = 0
    better_offers: int = 0
    stale_data_count: int = 0
    potential_savings: float = 0.0
    potential_savings_currency: str = "PHP"
    savings_freshness_note: str = ""


class DashboardCardPayload(BaseModel):
    card_id: str
    card_type: str
    title: str
    summary: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
    source_mode_label: str | None = None
    freshness_label: str | None = None


class DashboardActivityPayload(BaseModel):
    activity_id: str
    user_id: str
    activity_type: str
    message: str
    created_at: str
    watchlist_id: str | None = None


class UserDashboardResponse(BaseModel):
    user_id: str
    summary: DashboardSummaryPayload
    cards: list[DashboardCardPayload] = Field(default_factory=list)
    recent_activity: list[DashboardActivityPayload] = Field(default_factory=list)
    generated_at: str
    limitations: str = ""
    personalization: dict[str, Any] = Field(default_factory=dict)
