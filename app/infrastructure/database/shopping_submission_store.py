"""PostgreSQL (and test SQLite) shopping-assistant submission ledger.

The first insert of a scoped key hash wins. A concurrent insert hits the
primary key and does not become a second execution. Store errors raise
``ShoppingSubmissionUnavailable`` and never switch to process memory.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging import get_logger
from app.infrastructure.database.models.shopping_submission import (
    ShoppingAssistantSubmissionModel,
)
from app.shopping.submission_idempotency import (
    MAX_RESPONSE_CHARS,
    PROCESSING_HORIZON_SECONDS,
    SUBMISSION_RETENTION_SECONDS,
    ShoppingSubmissionUnavailable,
    SubmissionClaim,
    SubmissionRecord,
    _interpret,
    _require_opaque_parts,
    epoch_ms,
    from_epoch_ms,
)

logger = get_logger(__name__)

_TABLE = ShoppingAssistantSubmissionModel.__table__
_MAX_ATTEMPTS = 8


class _Retry(Exception):
    """The competing writer committed first. Retry the claim."""


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


class SqlShoppingSubmissionStore:
    """Shared submission ledger. One row per scope and key hash."""

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

    def claim(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        now: datetime,
    ) -> SubmissionClaim:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint=fingerprint)
        now_ms = epoch_ms(now)
        last: Exception | None = None
        for _ in range(_MAX_ATTEMPTS):
            try:
                return self._claim_once(
                    scope=scope,
                    key_hash=key_hash,
                    fingerprint=fingerprint,
                    now_ms=now_ms,
                )
            except _Retry as exc:
                last = exc
                continue
            except ShoppingSubmissionUnavailable:
                raise
            except Exception as exc:
                if _retryable(exc):
                    last = exc
                    continue
                logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
                raise ShoppingSubmissionUnavailable(
                    "Shopping assistant submission store is unavailable."
                ) from exc
        logger.warning("shopping submission store unavailable: retries exhausted")
        raise ShoppingSubmissionUnavailable(
            "Shopping assistant submission store is unavailable."
        ) from last

    def _claim_once(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        now_ms: int,
    ) -> SubmissionClaim:
        horizon_ms = now_ms + PROCESSING_HORIZON_SECONDS * 1000
        with self._session() as session:
            self._seal(session, now_ms)
            self._purge(session, now_ms)
            try:
                with session.begin_nested():
                    session.execute(
                        insert(_TABLE).values(
                            scope=scope,
                            key_hash=key_hash,
                            fingerprint=fingerprint,
                            state="processing",
                            http_status=None,
                            response_body=None,
                            created_at_ms=now_ms,
                            updated_at_ms=now_ms,
                            expires_at_ms=horizon_ms,
                        )
                    )
            except IntegrityError:
                row = self._load(session, scope, key_hash)
                if row is None:
                    raise _Retry() from None
                if row["state"] != "processing" and int(row["expires_at_ms"]) <= now_ms:
                    raise _Retry() from None
                return _interpret(_to_record(row), fingerprint, from_epoch_ms(now_ms))
            return SubmissionClaim("execute")

    def complete(
        self,
        *,
        scope: str,
        key_hash: str,
        fingerprint: str,
        response_json: str,
        now: datetime,
    ) -> bool:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint=fingerprint)
        if len(response_json) > MAX_RESPONSE_CHARS:
            self.fail_closed(scope=scope, key_hash=key_hash, now=now)
            return False
        now_ms = epoch_ms(now)
        expires_ms = epoch_ms(
            from_epoch_ms(now_ms) + timedelta(seconds=SUBMISSION_RETENTION_SECONDS)
        )
        try:
            with self._session() as session:
                result = session.execute(
                    update(_TABLE)
                    .where(
                        _TABLE.c.scope == scope,
                        _TABLE.c.key_hash == key_hash,
                        _TABLE.c.fingerprint == fingerprint,
                        _TABLE.c.state == "processing",
                    )
                    .values(
                        state="completed",
                        http_status=200,
                        response_body=response_json,
                        updated_at_ms=now_ms,
                        expires_at_ms=expires_ms,
                    )
                )
                if int(result.rowcount or 0) == 1:
                    return True
                stored = self._load(session, scope, key_hash)
                return bool(
                    stored is not None
                    and stored["state"] == "completed"
                    and stored["fingerprint"] == fingerprint
                    and stored["response_body"] == response_json
                )
        except ShoppingSubmissionUnavailable:
            raise
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def fail_closed(self, *, scope: str, key_hash: str, now: datetime) -> None:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        now_ms = epoch_ms(now)
        expires_ms = epoch_ms(
            from_epoch_ms(now_ms) + timedelta(seconds=SUBMISSION_RETENTION_SECONDS)
        )
        try:
            with self._session() as session:
                session.execute(
                    update(_TABLE)
                    .where(
                        _TABLE.c.scope == scope,
                        _TABLE.c.key_hash == key_hash,
                        _TABLE.c.state == "processing",
                    )
                    .values(
                        state="indeterminate",
                        http_status=None,
                        response_body=None,
                        updated_at_ms=now_ms,
                        expires_at_ms=expires_ms,
                    )
                )
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def release_unentered(self, *, scope: str, key_hash: str) -> bool:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        try:
            with self._session() as session:
                result = session.execute(
                    delete(_TABLE).where(
                        _TABLE.c.scope == scope,
                        _TABLE.c.key_hash == key_hash,
                        _TABLE.c.state == "processing",
                    )
                )
                return int(result.rowcount or 0) == 1
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def cleanup(self, now: datetime) -> int:
        """Delete expired completed and indeterminate rows. Keep processing rows."""

        try:
            with self._session() as session:
                return self._purge(session, epoch_ms(now))
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def seal_stale_processing(self, now: datetime) -> int:
        """Seal an abandoned processing row without authorizing another execution."""

        try:
            with self._session() as session:
                return self._seal(session, epoch_ms(now))
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def read(self, *, scope: str, key_hash: str) -> SubmissionRecord | None:
        _require_opaque_parts(scope=scope, key_hash=key_hash, fingerprint="0" * 64)
        try:
            with self._session() as session:
                row = self._load(session, scope, key_hash)
                return None if row is None else _to_record(row)
        except Exception as exc:
            logger.warning("shopping submission store unavailable: %s", type(exc).__name__)
            raise ShoppingSubmissionUnavailable(
                "Shopping assistant submission store is unavailable."
            ) from exc

    def _seal(self, session: Session, now_ms: int) -> int:
        expires_ms = epoch_ms(
            from_epoch_ms(now_ms) + timedelta(seconds=SUBMISSION_RETENTION_SECONDS)
        )
        result = session.execute(
            update(_TABLE)
            .where(
                _TABLE.c.state == "processing",
                _TABLE.c.expires_at_ms <= now_ms,
            )
            .values(
                state="indeterminate",
                http_status=None,
                response_body=None,
                updated_at_ms=now_ms,
                expires_at_ms=expires_ms,
            )
        )
        return int(result.rowcount or 0)

    def _purge(self, session: Session, now_ms: int) -> int:
        result = session.execute(
            delete(_TABLE).where(
                _TABLE.c.state.in_(("completed", "indeterminate")),
                _TABLE.c.expires_at_ms <= now_ms,
            )
        )
        return int(result.rowcount or 0)

    def _load(self, session: Session, scope: str, key_hash: str):
        return (
            session.execute(
                select(_TABLE).where(
                    _TABLE.c.scope == scope,
                    _TABLE.c.key_hash == key_hash,
                )
            )
            .mappings()
            .first()
        )


def _to_record(row) -> SubmissionRecord:
    state = str(row["state"])
    if state not in {"processing", "completed", "indeterminate"}:
        raise ShoppingSubmissionUnavailable("Shopping assistant submission store is unavailable.")
    status = row["http_status"]
    return SubmissionRecord(
        scope=str(row["scope"]),
        key_hash=str(row["key_hash"]),
        fingerprint=str(row["fingerprint"]),
        state=state,  # type: ignore[arg-type]
        response_body=None if row["response_body"] is None else str(row["response_body"]),
        http_status=None if status is None else int(status),
        created_at=from_epoch_ms(int(row["created_at_ms"])),
        updated_at=from_epoch_ms(int(row["updated_at_ms"])),
        expires_at=from_epoch_ms(int(row["expires_at_ms"])),
    )
