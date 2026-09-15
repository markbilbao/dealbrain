"""In-memory Early Access repository for tests and local development."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime

from app.domain.entities.early_access import EarlyAccessRegistration, EmailConfirmationStatus
from app.domain.interfaces.early_access_repository import EarlyAccessRepository


class InMemoryEarlyAccessRepository(EarlyAccessRepository):
    """Process-local store with a lock around normalized-email uniqueness."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, EarlyAccessRegistration] = {}
        self._by_email: dict[str, str] = {}

    def get_by_normalized_email(self, normalized_email: str) -> EarlyAccessRegistration | None:
        with self._lock:
            entity_id = self._by_email.get(normalized_email)
            if entity_id is None:
                return None
            return self._by_id.get(entity_id)

    def create_if_absent(
        self, registration: EarlyAccessRegistration
    ) -> tuple[EarlyAccessRegistration, bool]:
        with self._lock:
            existing_id = self._by_email.get(registration.normalized_email)
            if existing_id is not None:
                return self._by_id[existing_id], False
            self._by_id[registration.id] = registration
            self._by_email[registration.normalized_email] = registration.id
            return registration, True

    def update_email_confirmation(
        self,
        registration_id: str,
        *,
        status: EmailConfirmationStatus,
        sent_at: datetime | None,
        updated_at: datetime,
    ) -> EarlyAccessRegistration:
        with self._lock:
            current = self._by_id.get(registration_id)
            if current is None:
                raise KeyError(registration_id)
            updated = replace(
                current,
                email_confirmation_status=status,
                email_confirmation_sent_at=sent_at,
                updated_at=updated_at,
            )
            self._by_id[registration_id] = updated
            return updated

    def list_all(self) -> list[EarlyAccessRegistration]:
        with self._lock:
            return sorted(self._by_id.values(), key=lambda item: item.created_at)
