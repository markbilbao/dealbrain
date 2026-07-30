"""Shared session-scoped OperationalStore helper for Sprint 23 adapters."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker


class SessionBound:
    """Mixin providing sync session / factory wiring for operational stores."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        session: Session | None = None,
    ) -> None:
        from app.infrastructure.persistence.session import get_sync_session_factory

        self._factory = session_factory or get_sync_session_factory()
        self._session = session

    @contextmanager
    def _ops(self) -> Iterator:
        from app.infrastructure.persistence.operational_store import OperationalStore
        from app.infrastructure.persistence.session import sync_session

        if self._session is not None:
            yield OperationalStore(self._session)
            return
        with sync_session(factory=self._factory) as session:
            yield OperationalStore(session)
