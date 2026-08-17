"""Persistence port for Early Access registrations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.early_access import EarlyAccessRegistration


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
    def list_all(self) -> list[EarlyAccessRegistration]:
        """Return all registrations (operator export)."""
