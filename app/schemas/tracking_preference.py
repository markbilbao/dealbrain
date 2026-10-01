"""Public tracking-preference API models. Advertising cannot be enabled."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrackingPreferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: Literal["essential_only", "analytics_allowed"]
    analytics_allowed: bool
    advertising_allowed: bool = False
    consent_schema: str
    consent_version: str
    selected_at: str | None = None
    explicit: bool


class TrackingPreferenceUpdate(BaseModel):
    """Only the two explicit choices. No vendor list and no advertising flag."""

    model_config = ConfigDict(extra="forbid")

    choice: Literal["essential_only", "analytics_allowed"] = Field(
        description="essential_only keeps analytics off. analytics_allowed is optional."
    )
