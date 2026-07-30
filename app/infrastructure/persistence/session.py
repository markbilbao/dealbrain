"""Sync database engine and session helpers for Sprint 23 operational stores.

Sprint 7 price/registry adapters remain async. Sprint 17–21 repository ports are
synchronous; these helpers provide a matching sync SQLAlchemy surface on the
same PostgreSQL database (or SQLite for isolated tests).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.infrastructure.persistence.errors import (
    PersistenceConflictError,
    PersistenceForeignKeyError,
    PersistenceRetryableError,
    PersistenceUnavailableError,
)

_sync_engine: Engine | None = None
_sync_session_factory: sessionmaker[Session] | None = None


def to_sync_database_url(url: str) -> str:
    """Convert an async SQLAlchemy URL into a sync driver URL."""
    replacements = (
        ("postgresql+asyncpg://", "postgresql+psycopg://"),
        ("postgres+asyncpg://", "postgresql+psycopg://"),
        ("sqlite+aiosqlite://", "sqlite://"),
    )
    for old, new in replacements:
        if url.startswith(old):
            return new + url[len(old) :]
    return url


def get_sync_engine(*, url: str | None = None, echo: bool | None = None) -> Engine:
    """Return the process sync engine (lazy singleton unless url override)."""
    global _sync_engine
    if url is not None:
        return create_engine(
            to_sync_database_url(url),
            echo=bool(settings.database_echo if echo is None else echo),
            pool_pre_ping=True,
            future=True,
        )
    if _sync_engine is None:
        _sync_engine = create_engine(
            to_sync_database_url(str(settings.database_url)),
            echo=settings.database_echo,
            pool_pre_ping=True,
            future=True,
        )
    return _sync_engine


def get_sync_session_factory(*, engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a sync session factory bound to the sync engine."""
    global _sync_session_factory
    if engine is not None:
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _sync_session_factory


def reset_sync_engine() -> None:
    """Dispose and clear sync engine singletons (tests)."""
    global _sync_engine, _sync_session_factory
    if _sync_engine is not None:
        _sync_engine.dispose()
    _sync_engine = None
    _sync_session_factory = None


@contextmanager
def sync_session(*, factory: sessionmaker[Session] | None = None) -> Iterator[Session]:
    """Yield a sync session that commits on success and rolls back on error."""
    session_factory = factory or get_sync_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def transaction(session: Session) -> Iterator[Session]:
    """Explicit nested transaction/savepoint helper for multi-step unit-of-work."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


def translate_db_error(exc: Exception) -> Exception:
    """Map SQLAlchemy/DBAPI errors into stable persistence exceptions."""
    if isinstance(exc, IntegrityError):
        message = str(getattr(exc, "orig", exc))
        lowered = message.lower()
        if "foreign key" in lowered:
            return PersistenceForeignKeyError(message)
        return PersistenceConflictError(message)
    if isinstance(exc, OperationalError):
        return PersistenceUnavailableError(str(getattr(exc, "orig", exc)))
    if isinstance(exc, DBAPIError) and getattr(exc, "connection_invalidated", False):
        return PersistenceRetryableError(str(getattr(exc, "orig", exc)))
    return exc


def ping_sync_database(*, engine: Engine | None = None) -> bool:
    """Return True when ``SELECT 1`` succeeds."""
    eng = engine or get_sync_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def require_operational_schema(*, engine: Engine | None = None) -> None:
    """Ensure the Sprint 23 operational_entities table exists."""
    eng = engine or get_sync_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1 FROM operational_entities LIMIT 1"))
    except Exception as exc:
        raise PersistenceUnavailableError(
            "operational_entities schema missing or database unavailable; "
            "run `alembic upgrade head`"
        ) from exc