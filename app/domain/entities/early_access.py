"""Early Access registration entity — interest list, not a user account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

EmailConfirmationStatus = Literal["not_sent", "pending", "sent", "failed"]
RegistrationOutcome = Literal["success", "already_registered"]


@dataclass(frozen=True, slots=True)
class EarlyAccessRegistration:
    """A single Early Access interest registration.

    Uniqueness identity is ``normalized_email``. This is not a PiqSavi user
    account and must not be stored on the User table.
    """

    id: str
    full_name: str
    email: str
    normalized_email: str
    country: str
    shopping_interest: str | None
    source: str
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    utm_term: str | None
    referrer: str | None
    email_confirmation_status: EmailConfirmationStatus
    email_confirmation_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
