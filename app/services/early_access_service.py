"""Early Access registration application service."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from app.auth.email import EmailMessage, EmailSender, NullEmailSender
from app.core.countries import is_valid_country_code, normalize_country_code
from app.core.logging import log_extra
from app.domain.entities.early_access import EarlyAccessRegistration
from app.domain.exceptions import EarlyAccessValidationError
from app.domain.interfaces.early_access_repository import EarlyAccessRepository

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

MAX_FULL_NAME = 120
MAX_EMAIL = 254
MAX_SHOPPING_INTEREST = 500
MAX_UTM = 200
MAX_REFERRER = 500
MAX_SOURCE = 64

RegisterOutcome = Literal["success", "already_registered"]
EmailConfirmationStatus = Literal["not_sent", "pending", "sent", "failed"]


@dataclass(frozen=True, slots=True)
class EarlyAccessRegisterResult:
    outcome: RegisterOutcome
    email_confirmation_status: EmailConfirmationStatus
    registration: EarlyAccessRegistration


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    """Trim and lowercase using the existing user-platform convention."""
    return email.strip().lower()


def _reject_controls(label: str, value: str) -> str:
    if _CONTROL_RE.search(value):
        raise EarlyAccessValidationError(f"{label} contains invalid characters.")
    return value


def _bounded_optional(label: str, value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = _reject_controls(label, value.strip())
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise EarlyAccessValidationError(f"{label} must be at most {max_length} characters.")
    return cleaned


class EarlyAccessService:
    """Validate and persist Early Access interest registrations."""

    def __init__(
        self,
        repository: EarlyAccessRepository,
        *,
        email_sender: EmailSender | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._email = email_sender or NullEmailSender()
        self._clock = clock or _now
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def register(
        self,
        *,
        full_name: str,
        email: str,
        country: str,
        shopping_interest: str | None = None,
        source: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        utm_content: str | None = None,
        utm_term: str | None = None,
        referrer: str | None = None,
        request_id: str | None = None,
    ) -> EarlyAccessRegisterResult:
        cleaned_name = self._validate_full_name(full_name)
        cleaned_email = self._validate_email(email)
        cleaned_country = self._validate_country(country)
        cleaned_interest = _bounded_optional(
            "shopping_interest", shopping_interest, MAX_SHOPPING_INTEREST
        )
        cleaned_source = _bounded_optional("source", source, MAX_SOURCE) or "early_access_landing"
        now = self._clock()
        pending = EarlyAccessRegistration(
            id=self._id_factory(),
            full_name=cleaned_name,
            email=cleaned_email,
            normalized_email=cleaned_email,
            country=cleaned_country,
            shopping_interest=cleaned_interest,
            source=cleaned_source,
            utm_source=_bounded_optional("utm_source", utm_source, MAX_UTM),
            utm_medium=_bounded_optional("utm_medium", utm_medium, MAX_UTM),
            utm_campaign=_bounded_optional("utm_campaign", utm_campaign, MAX_UTM),
            utm_content=_bounded_optional("utm_content", utm_content, MAX_UTM),
            utm_term=_bounded_optional("utm_term", utm_term, MAX_UTM),
            referrer=_bounded_optional("referrer", referrer, MAX_REFERRER),
            email_confirmation_status="not_sent",
            email_confirmation_sent_at=None,
            created_at=now,
            updated_at=now,
        )
        stored, created = self._repository.create_if_absent(pending)
        outcome: RegisterOutcome = "success" if created else "already_registered"
        event_name = "early_access_signup_success" if created else "early_access_signup_duplicate"
        logger.info(
            "early_access_register",
            extra={
                "structured": log_extra(
                    event=event_name,
                    outcome=outcome,
                    country=stored.country,
                    source=stored.source,
                    utm_source=stored.utm_source,
                    request_id=request_id,
                )
            },
        )
        if created:
            self._attempt_confirmation(stored, request_id=request_id)
        return EarlyAccessRegisterResult(
            outcome=outcome,
            email_confirmation_status=stored.email_confirmation_status,
            registration=stored,
        )

    def list_registrations(self) -> list[EarlyAccessRegistration]:
        return self._repository.list_all()

    def _attempt_confirmation(
        self,
        registration: EarlyAccessRegistration,
        *,
        request_id: str | None,
    ) -> None:
        """Best-effort confirmation. Never rolls back a successful registration."""
        if isinstance(self._email, NullEmailSender):
            return
        try:
            self._email.send(
                EmailMessage(
                    to_address=registration.email,
                    subject="PiqSavi Early Access",
                    body_text="You are on the PiqSavi Early Access list.",
                )
            )
        except Exception:
            logger.warning(
                "early_access_confirmation_failed",
                extra={
                    "structured": log_extra(
                        event="early_access_confirmation_failed",
                        country=registration.country,
                        request_id=request_id,
                    )
                },
            )

    @staticmethod
    def _validate_full_name(full_name: str) -> str:
        cleaned = _reject_controls("full_name", (full_name or "").strip())
        if not cleaned:
            raise EarlyAccessValidationError("Please enter your full name.")
        if len(cleaned) > MAX_FULL_NAME:
            raise EarlyAccessValidationError(
                f"full_name must be at most {MAX_FULL_NAME} characters."
            )
        return cleaned

    @staticmethod
    def _validate_email(email: str) -> str:
        cleaned = normalize_email(email or "")
        cleaned = _reject_controls("email", cleaned)
        if not cleaned or not _EMAIL_RE.match(cleaned) or len(cleaned) > MAX_EMAIL:
            raise EarlyAccessValidationError("Please enter a valid email address.")
        return cleaned

    @staticmethod
    def _validate_country(country: str) -> str:
        code = normalize_country_code(country)
        if not code or not is_valid_country_code(code):
            raise EarlyAccessValidationError("Please select your country.")
        return code
