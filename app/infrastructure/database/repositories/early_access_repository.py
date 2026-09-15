"""SQLAlchemy Early Access adapter using the Sprint 23 operational store.

Uniqueness is enforced by ``uq_operational_store_secondary`` on
``(store, secondary_key)`` where ``secondary_key`` is the normalized email.
``OperationalStore._next_seq`` is an ordering hint only and is not used as
the uniqueness key.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from app.domain.entities.early_access import EarlyAccessRegistration, EmailConfirmationStatus
from app.domain.interfaces.early_access_repository import EarlyAccessRepository
from app.infrastructure.persistence.errors import PersistenceConflictError, PersistenceError
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import EARLY_ACCESS_REGISTRATIONS


class SqlAlchemyEarlyAccessRepository(EarlyAccessRepository, SessionBound):
    """Durable Early Access registrations in ``operational_entities``."""

    def get_by_normalized_email(self, normalized_email: str) -> EarlyAccessRegistration | None:
        with self._ops() as ops:
            return ops.get_by_secondary(
                EARLY_ACCESS_REGISTRATIONS,
                normalized_email,
                EarlyAccessRegistration,
            )

    def create_if_absent(
        self, registration: EarlyAccessRegistration
    ) -> tuple[EarlyAccessRegistration, bool]:
        try:
            with self._ops() as ops:
                ops.upsert(
                    EARLY_ACCESS_REGISTRATIONS,
                    registration.id,
                    registration,
                    secondary_key=registration.normalized_email,
                )
                return registration, True
        except PersistenceConflictError:
            existing = self.get_by_normalized_email(registration.normalized_email)
            if existing is None:
                raise
            return existing, False

    def update_email_confirmation(
        self,
        registration_id: str,
        *,
        status: EmailConfirmationStatus,
        sent_at: datetime | None,
        updated_at: datetime,
    ) -> EarlyAccessRegistration:
        with self._ops() as ops:
            current = ops.get(
                EARLY_ACCESS_REGISTRATIONS,
                registration_id,
                EarlyAccessRegistration,
            )
            if current is None:
                raise PersistenceError(
                    "Early Access registration was not found for confirmation update."
                )
            updated = replace(
                current,
                email_confirmation_status=status,
                email_confirmation_sent_at=sent_at,
                updated_at=updated_at,
            )
            ops.upsert(
                EARLY_ACCESS_REGISTRATIONS,
                updated.id,
                updated,
                secondary_key=updated.normalized_email,
            )
            return updated

    def list_all(self) -> list[EarlyAccessRegistration]:
        with self._ops() as ops:
            items = ops.list(EARLY_ACCESS_REGISTRATIONS, EarlyAccessRegistration)
            return sorted(items, key=lambda item: item.created_at)
