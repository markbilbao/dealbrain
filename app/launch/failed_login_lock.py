"""Durable failed-login memory for one opaque login identity.

The repository has no approved failed-login threshold or lock duration.
The conservative beta default is therefore:

- ``FAILED_LOGIN_LOCK_THRESHOLD`` = 20 consecutive failures
- ``FAILED_LOGIN_LOCK_DURATION_SECONDS`` = 900 (15 minutes)

The lock duration is measured from the attempt that reaches the threshold.
It is not a fixed window that starts on the first failure and can expire
immediately after the threshold is crossed. No approved retention duration
for an unlocked failure sequence was found. An unlocked sequence is
remembered for ``FAILED_LOGIN_FAILURE_RETENTION_SECONDS`` (15 minutes).
When that horizon has elapsed, the next failure starts again at count 1.
A successful login still deletes the row. An active lock is kept until
``locked_until`` and is not extended by later attempts. Expired locks and
unlocked rows older than the horizon are deleted during store writes.

The existing 20-attempt / 60-second auth limiter stays in place. This control
is an additional layer. Staging and production use PostgreSQL. Development
may use the in-memory store. There is no silent fallback from PostgreSQL to
memory. Store errors raise ``FailedLoginLockUnavailable`` so callers deny
the attempt.

Stored identities are opaque HMAC keys. This module rejects values that
could be a raw email. It does not accept passwords, bearer tokens, session
tokens, or owner cookies.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.core.config import Settings, settings
from app.launch.rate_limit_backend import resolve_rate_limit_backend

FAILED_LOGIN_LOCK_THRESHOLD = 20
FAILED_LOGIN_LOCK_DURATION_SECONDS = 15 * 60
FAILED_LOGIN_FAILURE_RETENTION_SECONDS = 15 * 60
LOGIN_ATTEMPT_LIMIT_MESSAGE = "Too many login attempts. Try again later."
_IDENTITY_MAX_LENGTH = 128


class FailedLoginLockUnavailable(Exception):
    """The durable login control could not be evaluated. Callers must deny."""


@dataclass(frozen=True, slots=True)
class FailedLoginLockState:
    """One opaque identity's failure memory. No raw credentials."""

    identity_key: str
    failure_count: int
    locked_until: datetime | None
    first_failure_at: datetime
    last_failure_at: datetime


class FailedLoginLockStore(Protocol):
    """Persistence for failed-login memory. Implementations must be atomic."""

    def get(self, identity: str) -> FailedLoginLockState | None: ...

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ) -> FailedLoginLockState: ...

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None: ...


def require_opaque_login_identity(identity: str) -> str:
    """Reject blank, overlong, or email-shaped identities before storage."""

    if not isinstance(identity, str):
        raise FailedLoginLockUnavailable("failed login lock store unavailable")
    if (
        not identity
        or len(identity) > _IDENTITY_MAX_LENGTH
        or "@" in identity
        or "\x00" in identity
        or any(character.isspace() for character in identity)
    ):
        raise FailedLoginLockUnavailable("failed login lock store unavailable")
    return identity


def aware_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def epoch_ms(now: datetime) -> int:
    return int(aware_utc(now).timestamp() * 1000)


def from_epoch_ms(millis: int) -> datetime:
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=millis)


class FailedLoginLock:
    """Policy over a failed-login store. The clock is supplied by the caller."""

    def __init__(
        self,
        store: FailedLoginLockStore,
        *,
        threshold: int = FAILED_LOGIN_LOCK_THRESHOLD,
        lock_duration_seconds: int = FAILED_LOGIN_LOCK_DURATION_SECONDS,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ) -> None:
        if threshold < 1 or lock_duration_seconds < 1 or failure_retention_seconds < 1:
            raise ValueError("failed login lock policy must be positive")
        self._store = store
        self._threshold = threshold
        self._lock_duration_seconds = lock_duration_seconds
        self._failure_retention_seconds = failure_retention_seconds

    @property
    def store(self) -> FailedLoginLockStore:
        return self._store

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def lock_duration_seconds(self) -> int:
        return self._lock_duration_seconds

    @property
    def failure_retention_seconds(self) -> int:
        return self._failure_retention_seconds

    def is_locked(self, identity: str, *, now: datetime) -> bool:
        state = self._store.get(identity)
        if state is None or state.locked_until is None:
            return False
        return epoch_ms(state.locked_until) > epoch_ms(now)

    def record_failure(self, identity: str, *, now: datetime) -> FailedLoginLockState:
        return self._store.record_failure(
            identity,
            now=now,
            threshold=self._threshold,
            lock_duration_seconds=self._lock_duration_seconds,
            failure_retention_seconds=self._failure_retention_seconds,
        )

    def clear(self, identity: str, *, now: datetime | None = None) -> None:
        self._store.clear(
            identity,
            now=now,
            failure_retention_seconds=self._failure_retention_seconds,
        )


class InMemoryFailedLoginLockStore:
    """Process-local lock memory for development and unit tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[str, FailedLoginLockState] = {}

    def get(self, identity: str) -> FailedLoginLockState | None:
        identity = require_opaque_login_identity(identity)
        with self._lock:
            return self._rows.get(identity)

    def record_failure(
        self,
        identity: str,
        *,
        now: datetime,
        threshold: int,
        lock_duration_seconds: int,
        failure_retention_seconds: int = FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    ) -> FailedLoginLockState:
        identity = require_opaque_login_identity(identity)
        if threshold < 1 or lock_duration_seconds < 1 or failure_retention_seconds < 1:
            raise FailedLoginLockUnavailable("failed login lock store unavailable")
        current_time = aware_utc(now)
        with self._lock:
            _purge_memory_rows(
                self._rows,
                now=current_time,
                failure_retention_seconds=failure_retention_seconds,
            )
            current = self._rows.get(identity)
            state = _next_memory_state(
                identity,
                current,
                now=current_time,
                threshold=threshold,
                lock_duration_seconds=lock_duration_seconds,
                failure_retention_seconds=failure_retention_seconds,
            )
            self._rows[identity] = state
            return state

    def clear(
        self,
        identity: str,
        *,
        now: datetime | None = None,
        failure_retention_seconds: int | None = None,
    ) -> None:
        identity = require_opaque_login_identity(identity)
        with self._lock:
            self._rows.pop(identity, None)
            if now is None or failure_retention_seconds is None:
                return
            if failure_retention_seconds < 1:
                raise FailedLoginLockUnavailable("failed login lock store unavailable")
            _purge_memory_rows(
                self._rows,
                now=aware_utc(now),
                failure_retention_seconds=failure_retention_seconds,
            )


def _lock_deadline(now: datetime, lock_duration_seconds: int) -> datetime:
    return now + timedelta(seconds=lock_duration_seconds)


def _retention_cutoff_ms(now: datetime, failure_retention_seconds: int) -> int:
    return epoch_ms(now) - failure_retention_seconds * 1000


def _reapable(state: FailedLoginLockState, *, now_ms: int, cutoff_ms: int) -> bool:
    """Stale unlocked history and expired locks may be deleted.

    An active lock stays even when its last failure is older than the
    retention horizon. A recent unlocked sequence stays as well.
    """

    if state.locked_until is None:
        return epoch_ms(state.last_failure_at) <= cutoff_ms
    return epoch_ms(state.locked_until) <= now_ms


def _purge_memory_rows(
    rows: dict[str, FailedLoginLockState],
    *,
    now: datetime,
    failure_retention_seconds: int,
) -> None:
    now_ms = epoch_ms(now)
    cutoff_ms = _retention_cutoff_ms(now, failure_retention_seconds)
    stale = [
        key for key, state in rows.items() if _reapable(state, now_ms=now_ms, cutoff_ms=cutoff_ms)
    ]
    for key in stale:
        del rows[key]


def _unlocked_sequence_expired(
    state: FailedLoginLockState,
    now: datetime,
    failure_retention_seconds: int,
) -> bool:
    if state.locked_until is not None:
        return False
    return epoch_ms(state.last_failure_at) <= _retention_cutoff_ms(now, failure_retention_seconds)


def _next_memory_state(
    identity: str,
    current: FailedLoginLockState | None,
    *,
    now: datetime,
    threshold: int,
    lock_duration_seconds: int,
    failure_retention_seconds: int,
) -> FailedLoginLockState:
    if (
        current is None
        or _lock_expired(current, now)
        or _unlocked_sequence_expired(current, now, failure_retention_seconds)
    ):
        count = 1
        first_failure_at = now
        locked_until = _lock_deadline(now, lock_duration_seconds) if count >= threshold else None
        return FailedLoginLockState(
            identity_key=identity,
            failure_count=count,
            locked_until=locked_until,
            first_failure_at=first_failure_at,
            last_failure_at=now,
        )
    count = current.failure_count + 1
    if current.locked_until is not None and epoch_ms(current.locked_until) > epoch_ms(now):
        locked_until = current.locked_until
    elif count >= threshold:
        locked_until = _lock_deadline(now, lock_duration_seconds)
    else:
        locked_until = None
    return FailedLoginLockState(
        identity_key=identity,
        failure_count=count,
        locked_until=locked_until,
        first_failure_at=current.first_failure_at,
        last_failure_at=now,
    )


def _lock_expired(state: FailedLoginLockState, now: datetime) -> bool:
    if state.locked_until is None:
        return False
    return epoch_ms(state.locked_until) <= epoch_ms(now)


_SHARED_LOCK: FailedLoginLock | None = None


def build_failed_login_lock_store(cfg: Settings | None = None) -> FailedLoginLockStore:
    """Select the lock store the same way the shared rate limiter selects its store.

    ``memory`` in staging or production raises ``RateLimitConfigurationError``.
    A PostgreSQL failure is not replaced with this in-memory store.
    """

    cfg = cfg or settings
    backend = resolve_rate_limit_backend(cfg)
    if backend == "memory":
        return InMemoryFailedLoginLockStore()
    from app.infrastructure.database.failed_login_lock_store import SqlFailedLoginLockStore

    return SqlFailedLoginLockStore()


def get_failed_login_lock() -> FailedLoginLock:
    """Process singleton used by the application service in every environment."""

    global _SHARED_LOCK
    if _SHARED_LOCK is None:
        _SHARED_LOCK = FailedLoginLock(store=build_failed_login_lock_store(settings))
    return _SHARED_LOCK


def default_failed_login_lock() -> FailedLoginLock:
    """AuthService default.

    Development keeps a private in-memory lock so unit tests stay isolated.
    Staging and production attach the shared PostgreSQL lock.
    """

    if resolve_rate_limit_backend(settings) == "memory":
        return FailedLoginLock(store=InMemoryFailedLoginLockStore())
    return get_failed_login_lock()


def reset_failed_login_lock_singletons_for_tests() -> None:
    """Clear the cached lock. Tests only."""

    global _SHARED_LOCK
    _SHARED_LOCK = None
