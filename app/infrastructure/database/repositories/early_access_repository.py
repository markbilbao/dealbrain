"""SQLAlchemy Early Access adapter using the Sprint 23 operational store.

Uniqueness is enforced by ``uq_operational_store_secondary`` on
``(store, secondary_key)`` where ``secondary_key`` is the normalized email.
``OperationalStore._next_seq`` is an ordering hint only and is not used as
the uniqueness key.
"""

from __future__ import annotations

from app.domain.entities.early_access import EarlyAccessRegistration
from app.domain.interfaces.early_access_repository import EarlyAccessRepository
from app.infrastructure.persistence.errors import PersistenceConflictError
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

    def list_all(self) -> list[EarlyAccessRegistration]:
        with self._ops() as ops:
            items = ops.list(EARLY_ACCESS_REGISTRATIONS, EarlyAccessRegistration)
            return sorted(items, key=lambda item: item.created_at)
