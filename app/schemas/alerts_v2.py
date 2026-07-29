"""Alert Rules & Alert Events (Sprint 19) API request and response schemas.

Distinct from the Sprint 10 ``AlertPayload``/``AlertListResponse`` in
``app.schemas.watchlists`` (kept unchanged there) — these back the new
rule-driven, user-owned alert configuration and evaluation surface.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AlertConditionPayload(BaseModel):
    condition_type: str
    threshold_value: float | None = None
    threshold_percent: float | None = None
    comparison: str | None = None


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    conditions: list[AlertConditionPayload] = Field(..., min_length=1)
    watchlist_id: str | None = None
    item_id: str | None = None
    enabled: bool = True
    status: str = "enabled"
    cooldown_seconds: int = Field(default=0, ge=0)
    repeat_policy: str = "recurring"
    severity: str = "info"
    timezone: str = "UTC"
    channel_preferences: list[str] = Field(default_factory=list)
    # Sprint 10 backward-compat demo path: only honored when no bearer token
    # is supplied AND ``settings.watchlists_require_auth`` is False.
    user_id: str | None = None


class AlertRuleUpdateRequest(BaseModel):
    name: str | None = None
    conditions: list[AlertConditionPayload] | None = None
    watchlist_id: str | None = None
    clear_watchlist_id: bool = False
    item_id: str | None = None
    clear_item_id: bool = False
    enabled: bool | None = None
    status: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)
    repeat_policy: str | None = None
    severity: str | None = None
    timezone: str | None = None
    channel_preferences: list[str] | None = None


class AlertRulePayload(BaseModel):
    rule_id: str
    user_id: str
    name: str
    conditions: list[AlertConditionPayload] = Field(default_factory=list)
    watchlist_id: str | None = None
    item_id: str | None = None
    enabled: bool = True
    status: str
    cooldown_seconds: int = 0
    last_triggered_at: str | None = None
    repeat_policy: str
    severity: str
    timezone: str = "UTC"
    channel_preferences: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    one_time_fired: bool = False


class AlertRuleListResponse(BaseModel):
    rules: list[AlertRulePayload] = Field(default_factory=list)


class AlertEvaluateRequest(BaseModel):
    """Scope for a manual evaluation pass. All fields optional/mutually exclusive."""

    watchlist_id: str | None = None
    rule_id: str | None = None
    # Sprint 10 backward-compat demo path: only honored when no bearer token
    # is supplied AND ``settings.watchlists_require_auth`` is False.
    user_id: str | None = None


class AlertEvaluationPayload(BaseModel):
    evaluation_id: str
    rule_id: str | None = None
    watchlist_id: str | None = None
    item_id: str | None = None
    triggered: bool
    reason: str
    observation_fingerprint: str | None = None
    evaluated_at: str
    partial_failure: bool = False
    error: str | None = None


class AlertEventPayload(BaseModel):
    event_id: str
    user_id: str
    rule_id: str | None = None
    alert_id: str | None = None
    event_type: str
    severity: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    dedupe_key: str


class AlertRuleEvaluateResponse(BaseModel):
    evaluated_at: str
    rules_evaluated: int = 0
    triggered_count: int = 0
    events_created: list[AlertEventPayload] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Notifications remain mock/simulated only. No email, SMS, or push "
        "notifications are sent."
    )


class AlertEventListResponse(BaseModel):
    events: list[AlertEventPayload] = Field(default_factory=list)
