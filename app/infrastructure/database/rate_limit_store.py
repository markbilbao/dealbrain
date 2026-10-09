"""PostgreSQL (and test SQLite) atomic rate-limit counters.

Increments are a single conditional UPDATE. A concurrent insert race retries.
Store errors raise RateLimitUnavailable and never switch to process memory.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.infrastructure.database.models.rate_limit_counter import RateLimitCounterModel
from app.launch.rate_limit_backend import RateLimitConsumption, RateLimitUnavailable

logger = get_logger(__name__)

_TABLE = RateLimitCounterModel.__table__
_MAX_ATTEMPTS = 8


class _Retry(Exception):
    """Another writer committed the row first. Retry the consume."""


def _epoch_ms(now: datetime) -> int:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return int(now.timestamp() * 1000)


def _storage_identity(identity: str) -> str:
    if len(identity) <= 128 and "\x00" not in identity:
        return identity
    return "h:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


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


class SqlRateLimitStore:
    """Shared fixed-window counter. One row per scope and identity."""

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

    def consume(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
        now: datetime,
    ) -> RateLimitConsumption:
        if limit < 1 or window_seconds < 1 or not scope or len(scope) > 64:
            raise RateLimitUnavailable("rate limit store unavailable")
        stored_identity = _storage_identity(identity)
        now_ms = _epoch_ms(now)
        last: Exception | None = None
        for _ in range(_MAX_ATTEMPTS):
            try:
                return self._consume_once(
                    scope=scope,
                    identity=stored_identity,
                    limit=limit,
                    window_seconds=window_seconds,
                    now_ms=now_ms,
                )
            except _Retry as exc:
                last = exc
                continue
            except RateLimitUnavailable:
                raise
            except Exception as exc:
                if _retryable(exc):
                    last = exc
                    continue
                logger.warning("rate limit store unavailable: %s", type(exc).__name__)
                raise RateLimitUnavailable("rate limit store unavailable") from exc
        logger.warning("rate limit store unavailable: retries exhausted")
        raise RateLimitUnavailable("rate limit store unavailable") from last

    def _consume_once(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
        now_ms: int,
    ) -> RateLimitConsumption:
        expires_ms = now_ms + window_seconds * 1000
        with self._session() as session:
            session.execute(delete(_TABLE).where(_TABLE.c.expires_at_ms < now_ms))
            updated = session.execute(
                update(_TABLE)
                .where(
                    _TABLE.c.scope == scope,
                    _TABLE.c.identity_key == identity,
                    _TABLE.c.hits < limit,
                    _TABLE.c.expires_at_ms >= now_ms,
                )
                .values(hits=_TABLE.c.hits + 1)
                .returning(_TABLE.c.hits, _TABLE.c.expires_at_ms)
            ).first()
            if updated is not None:
                hits = int(updated[0])
                return RateLimitConsumption(
                    allowed=True,
                    limit=limit,
                    remaining=max(0, limit - hits),
                    retry_after_seconds=0,
                    hits=hits,
                )
            try:
                with session.begin_nested():
                    session.execute(
                        insert(_TABLE).values(
                            scope=scope,
                            identity_key=identity,
                            window_started_ms=now_ms,
                            hits=1,
                            expires_at_ms=expires_ms,
                        )
                    )
            except IntegrityError:
                existing = session.execute(
                    select(_TABLE.c.hits, _TABLE.c.expires_at_ms).where(
                        _TABLE.c.scope == scope,
                        _TABLE.c.identity_key == identity,
                    )
                ).first()
                if existing is None or int(existing[1]) < now_ms:
                    raise _Retry() from None
                hits = int(existing[0])
                if hits < limit:
                    raise _Retry() from None
                retry = max(1, int((int(existing[1]) - now_ms) / 1000) + 1)
                return RateLimitConsumption(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry,
                    hits=hits,
                )
            return RateLimitConsumption(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - 1),
                retry_after_seconds=0,
                hits=1,
            )

    def reset(self, *, scope: str | None = None, identity: str | None = None) -> None:
        stored_identity = _storage_identity(identity) if identity is not None else None
        try:
            with self._session() as session:
                stmt = delete(_TABLE)
                if scope is not None:
                    stmt = stmt.where(_TABLE.c.scope == scope)
                if stored_identity is not None:
                    stmt = stmt.where(_TABLE.c.identity_key == stored_identity)
                session.execute(stmt)
        except RateLimitUnavailable:
            raise
        except Exception as exc:
            logger.warning("rate limit store reset unavailable: %s", type(exc).__name__)
            raise RateLimitUnavailable("rate limit store unavailable") from exc
