"""PostgreSQL (and test SQLite) failed-login lock store.

Increments are a single conditional UPDATE so concurrent failures cannot lose
counts. The first writer to cross the threshold sets ``locked_until_ms`` from
that statement's clock. Later failures in the same lock keep that deadline.
An expired lock is replaced by a fresh count of 1, not by an increment of the
old total. Store errors raise FailedLoginLockUnavailable and never switch to
process memory.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import and_, case, delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.infrastructure.database.models.failed_login_lock import FailedLoginLockModel
from app.launch.failed_login_lock import (
    FailedLoginLockState,
    FailedLoginLockUnavailable,
    epoch_ms,
    from_epoch_ms,
    require_opaque_login_identity,
)

logger = get_logger(__name__)

_TABLE = FailedLoginLockModel.__table__
_MAX_ATTEMPTS = 16


def _state_from_row(
    identity: str,
    failure_count: int,
    locked_until_ms: int | None,
    first_failure_ms: int,
    last_failure_ms: int,
) -> FailedLoginLockState:
    locked_until = None if locked_until_ms is None else from_epoch_ms(int(locked_until_ms))
    return FailedLoginLockState(
        identity_key=identity,
        failure_count=int(failure_count),
        locked_until=locked_until,
        first_failure_at=from_epoch_ms(int(first_failure_ms)),
        last_failure_at=from_epoch_ms(int(last_failure_ms)),
    )


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, IntegrityError):
        return True
    if not isinstance(exc, OperationalError):
        return False
    message = str(getattr(exc, "orig", exc)).lower()
    return any(
        token in message
        for token in ("locked", "busy", "deadlock", "serialization", "could not serialize")
    )


class SqlFailedLoginLockStore:
    """Shared failed-login memory. One row per opaque identity."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory

    def _factory(self) -> sessionmaker[Session]:
        if self._session_factory is not None:
            return self._session_factory
        from app.infrastructure.persistence.session import get_sync_session_factory

        return get_sync_session_factory()

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._factory()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, identity: str) -> FailedLoginLockState | None:
        identity = require_opaque_login_identity(identity)
        stmt = select(
            _TABLE.c.failure_count,
            _TABLE.c.locked_until_ms,
            _TABLE.c.first_failure_ms,
            _TABLE.c.last_failure_ms,
        ).where(_TABLE.c.identity_key == identity)
        try:
            with self._session() as session:
                row = session.execute(stmt).first()
        except FailedLoginLockUnavailable:
            raise
        except Exception as exc:
            logger.warning("failed login lock store unavailable: %s", type(exc).__name__)
            raise FailedLoginLockUnavailable("failed login lock store unavailable") from exc
        if row is None:
            return None
        return _state_from_row(identity, row[0], row[1], row[2], row[3])

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
    ) -> FailedLoginLockState:
        identity = require_opaque_login_identity(identity)
        if threshold < 1 or lock_duration_seconds < 1:
            raise FailedLoginLockUnavailable("failed login lock store unavailable")
        now_ms = epoch_ms(now)
        lock_until_ms = now_ms + lock_duration_seconds * 1000
        last: Exception | None = None
        for _ in range(_MAX_ATTEMPTS):
            try:
                updated = self._increment_active(
                    identity,
                    now_ms=now_ms,
                    threshold=threshold,
                    lock_until_ms=lock_until_ms,
                )
                if updated is not None:
                    return updated
                reset = self._reset_expired(
                    identity,
                    now_ms=now_ms,
                    threshold=threshold,
                    lock_until_ms=lock_until_ms,
                )
                if reset is not None:
                    return reset
                return self._insert_first(
                    identity,
                    now_ms=now_ms,
                    threshold=threshold,
                    lock_until_ms=lock_until_ms,
                )
            except IntegrityError as exc:
                last = exc
                continue
            except FailedLoginLockUnavailable:
                raise
            except Exception as exc:
                if _retryable(exc):
                    last = exc
                    continue
                logger.warning("failed login lock store unavailable: %s", type(exc).__name__)
                raise FailedLoginLockUnavailable("failed login lock store unavailable") from exc
        logger.warning("failed login lock store unavailable: retries exhausted")
        raise FailedLoginLockUnavailable("failed login lock store unavailable") from last

    def _increment_active(
        self,
        identity: str,
        *,
        now_ms: int,
        threshold: int,
        lock_until_ms: int,
    ) -> FailedLoginLockState | None:
        """Add one failure when the identity is unlocked or already locked.

        An expired ``locked_until_ms`` does not match. The caller then starts
        a fresh sequence. A lock that is already in the future is preserved,
        so a later failure cannot move the deadline.
        """

        new_count = _TABLE.c.failure_count + 1
        stmt = (
            update(_TABLE)
            .where(
                _TABLE.c.identity_key == identity,
                or_(
                    _TABLE.c.locked_until_ms.is_(None),
                    _TABLE.c.locked_until_ms > now_ms,
                ),
            )
            .values(
                failure_count=new_count,
                last_failure_ms=now_ms,
                locked_until_ms=case(
                    (
                        and_(_TABLE.c.locked_until_ms.is_(None), new_count >= threshold),
                        lock_until_ms,
                    ),
                    else_=_TABLE.c.locked_until_ms,
                ),
            )
            .returning(
                _TABLE.c.failure_count,
                _TABLE.c.locked_until_ms,
                _TABLE.c.first_failure_ms,
                _TABLE.c.last_failure_ms,
            )
        )
        with self._session() as session:
            row = session.execute(stmt).first()
        if row is None:
            return None
        return _state_from_row(identity, row[0], row[1], row[2], row[3])

    def _reset_expired(
        self,
        identity: str,
        *,
        now_ms: int,
        threshold: int,
        lock_until_ms: int,
    ) -> FailedLoginLockState | None:
        """Replace an expired lock with failure 1 of a new sequence."""

        fresh_lock = lock_until_ms if threshold <= 1 else None
        stmt = (
            update(_TABLE)
            .where(
                _TABLE.c.identity_key == identity,
                _TABLE.c.locked_until_ms.is_not(None),
                _TABLE.c.locked_until_ms <= now_ms,
            )
            .values(
                failure_count=1,
                first_failure_ms=now_ms,
                last_failure_ms=now_ms,
                locked_until_ms=fresh_lock,
            )
            .returning(
                _TABLE.c.failure_count,
                _TABLE.c.locked_until_ms,
                _TABLE.c.first_failure_ms,
                _TABLE.c.last_failure_ms,
            )
        )
        with self._session() as session:
            row = session.execute(stmt).first()
        if row is None:
            return None
        return _state_from_row(identity, row[0], row[1], row[2], row[3])

    def _insert_first(
        self,
        identity: str,
        *,
        now_ms: int,
        threshold: int,
        lock_until_ms: int,
    ) -> FailedLoginLockState:
        fresh_lock = lock_until_ms if threshold <= 1 else None
        stmt = insert(_TABLE).values(
            identity_key=identity,
            failure_count=1,
            locked_until_ms=fresh_lock,
            first_failure_ms=now_ms,
            last_failure_ms=now_ms,
        )
        with self._session() as session:
            session.execute(stmt)
        return _state_from_row(identity, 1, fresh_lock, now_ms, now_ms)

    def clear(self, identity: str) -> None:
        identity = require_opaque_login_identity(identity)
        try:
            with self._session() as session:
                session.execute(delete(_TABLE).where(_TABLE.c.identity_key == identity))
        except FailedLoginLockUnavailable:
            raise
        except Exception as exc:
            logger.warning("failed login lock store unavailable: %s", type(exc).__name__)
            raise FailedLoginLockUnavailable("failed login lock store unavailable") from exc
