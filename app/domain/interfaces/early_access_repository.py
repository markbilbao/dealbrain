"""Persistence port for Early Access registrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.early_access import EarlyAccessRegistration, EmailConfirmationStatus


class EarlyAccessRepository(ABC):
    """Durable store for Early Access interest registrations."""

    @abstractmethod
    def get_by_normalized_email(self, normalized_email: str) -> EarlyAccessRegistration | None:
        """Return the registration for a normalized email, if any."""

    @abstractmethod
    def create_if_absent(
        self, registration: EarlyAccessRegistration
    ) -> tuple[EarlyAccessRegistration, bool]:
        """Insert ``registration`` atomically.

        Returns ``(entity, created)``. When a row already exists for the
        normalized email, returns the existing entity and ``False`` without
        creating a second row. Uniqueness must be enforced by an atomic
        unique key, not check-then-insert alone.
        """

    @abstractmethod
    def update_email_confirmation(
        self,
        registration_id: str,
        *,
        status: EmailConfirmationStatus,
        sent_at: datetime | None,
        updated_at: datetime,
    ) -> EarlyAccessRegistration:
        """Persist confirmation delivery status for an existing registration.

        Does not create a row, change uniqueness identity, or rewrite
        legal-acknowledgement fields. Returns the updated persisted entity.
        """

    @abstractmethod
    def list_all(self) -> list[EarlyAccessRegistration]:
        """Return all registrations (operator export)."""
