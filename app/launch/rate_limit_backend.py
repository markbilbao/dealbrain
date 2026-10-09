"""Rate-limit backend selection and process-local store.

Staging and production use the shared PostgreSQL counter. Development and
tests may use this in-memory store only when that backend is explicit.
There is no silent fallback from the shared store to memory.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from app.core.config import Settings, settings

RateLimitBackendName = Literal["memory", "postgres"]
_SHARED_ENVIRONMENTS = frozenset({"staging", "production"})


class RateLimitUnavailable(Exception):
    """Shared rate-limit control could not be evaluated. Callers must deny."""


class RateLimitConfigurationError(Exception):
    """Staging or production was asked to use a non-shared limiter."""


@dataclass(frozen=True, slots=True)
class RateLimitConsumption:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    hits: int


class RateLimitStore(Protocol):
    def consume(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
        now: datetime,
    ) -> RateLimitConsumption: ...

    def reset(self, *, scope: str | None = None, identity: str | None = None) -> None: ...


def resolve_rate_limit_backend(cfg: Settings | None = None) -> RateLimitBackendName:
    """Return the only backend this environment is allowed to use.

    Unset in development means memory. Unset in staging or production means
    postgres. ``memory`` in staging or production is a configuration error.
    """

    cfg = cfg or settings
    requested = cfg.rate_limit_backend
    if cfg.app_env in _SHARED_ENVIRONMENTS:
        if requested == "memory":
            raise RateLimitConfigurationError(
                "RATE_LIMIT_BACKEND=memory is forbidden in staging and production"
            )
        return "postgres"
    if requested == "postgres":
        return "postgres"
    return "memory"


class InMemoryRateLimitStore:
    """Sliding-window store for an explicitly configured development process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)

    def consume(
        self,
        *,
        scope: str,
        identity: str,
        limit: int,
        window_seconds: int,
        now: datetime,
    ) -> RateLimitConsumption:
        window = timedelta(seconds=window_seconds)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        with self._lock:
            bucket = self._events[(scope, identity)]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if not bucket:
                # Drop empty windows so expired keys do not accumulate.
                self._events.pop((scope, identity), None)
                bucket = self._events[(scope, identity)]
            if len(bucket) >= limit:
                oldest = bucket[0]
                retry = max(1, int((oldest + window - now).total_seconds()) + 1)
                return RateLimitConsumption(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry,
                    hits=len(bucket),
                )
            bucket.append(now)
            hits = len(bucket)
            return RateLimitConsumption(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - hits),
                retry_after_seconds=0,
                hits=hits,
            )

    def reset(self, *, scope: str | None = None, identity: str | None = None) -> None:
        with self._lock:
            if scope is None and identity is None:
                self._events.clear()
                return
            if identity is None:
                for key in list(self._events):
                    if key[0] == scope:
                        del self._events[key]
                return
            if scope is None:
                for key in list(self._events):
                    if key[1] == identity:
                        del self._events[key]
                return
            self._events.pop((scope, identity), None)


_SHARED_STORE: RateLimitStore | None = None
_AUTH_LIMITER: object | None = None


def build_rate_limit_store(cfg: Settings | None = None) -> RateLimitStore:
    """Construct the backend selected for this environment. Never falls back."""

    cfg = cfg or settings
    backend = resolve_rate_limit_backend(cfg)
    if backend == "memory":
        return InMemoryRateLimitStore()
    from app.infrastructure.database.rate_limit_store import SqlRateLimitStore

    return SqlRateLimitStore()


def get_shared_rate_limit_store() -> RateLimitStore:
    """Process singleton for the environment-selected backend."""

    global _SHARED_STORE
    if _SHARED_STORE is None:
        _SHARED_STORE = build_rate_limit_store(settings)
    return _SHARED_STORE


def get_auth_rate_limiter():
    """Shared auth-abuse limiter. Development callers that want isolation construct their own."""

    global _AUTH_LIMITER
    if _AUTH_LIMITER is None:
        from app.auth.security import RateLimiterHook

        _AUTH_LIMITER = RateLimiterHook(
            max_attempts=20,
            window_seconds=60,
            store=get_shared_rate_limit_store(),
        )
    return _AUTH_LIMITER


def default_auth_rate_limiter():
    """AuthService default.

    Development keeps a private in-memory hook so tests stay isolated.
    Staging and production attach the shared PostgreSQL hook.
    """

    from app.auth.security import RateLimiterHook

    if resolve_rate_limit_backend(settings) == "memory":
        return RateLimiterHook(max_attempts=20, window_seconds=60)
    return get_auth_rate_limiter()


def reset_rate_limit_singletons_for_tests() -> None:
    """Clear cached backends. Tests only."""

    global _SHARED_STORE, _AUTH_LIMITER
    _SHARED_STORE = None
    _AUTH_LIMITER = None
