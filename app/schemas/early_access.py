"""Early Access API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.early_access_service import (
    MAX_EMAIL,
    MAX_FULL_NAME,
    MAX_REFERRER,
    MAX_SHOPPING_INTEREST,
    MAX_SOURCE,
    MAX_UTM,
)

EarlyAccessOutcome = Literal["success", "already_registered"]
EarlyAccessEventName = Literal[
    "early_access_cta_clicked",
    "early_access_form_started",
    "early_access_form_submitted",
    "how_it_works_viewed",
]
EarlyAccessEventSource = Literal["header", "hero"]


class EarlyAccessRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=MAX_FULL_NAME)
    email: str = Field(..., min_length=3, max_length=MAX_EMAIL)
    country: str = Field(..., min_length=2, max_length=2)
    shopping_interest: str | None = Field(default=None, max_length=MAX_SHOPPING_INTEREST)
    source: str | None = Field(default=None, max_length=MAX_SOURCE)
    utm_source: str | None = Field(default=None, max_length=MAX_UTM)
    utm_medium: str | None = Field(default=None, max_length=MAX_UTM)
    utm_campaign: str | None = Field(default=None, max_length=MAX_UTM)
    utm_content: str | None = Field(default=None, max_length=MAX_UTM)
    utm_term: str | None = Field(default=None, max_length=MAX_UTM)
    referrer: str | None = Field(default=None, max_length=MAX_REFERRER)


class EarlyAccessRegisterResponse(BaseModel):
    outcome: EarlyAccessOutcome
    email_confirmation_status: Literal["not_sent", "pending", "sent", "failed"]
    message: str


class EarlyAccessEventRequest(BaseModel):
    event: EarlyAccessEventName
    source: EarlyAccessEventSource | None = None
