"""Short-TTL in-process cache for launch performance (Sprint 22).

Used to reduce duplicate processing for identical read queries. Never caches
write paths and never alters ranking scores — only memoizes identical results.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    stores: int = 0
    evictions: int = 0
    size: int = 0


class TtlCache:
    """Thread-safe TTL cache with optional max entries."""

    def __init__(
        self,
        *,
        default_ttl_seconds: float = 30.0,
        max_entries: int = 512,
        enabled: bool = True,
    ) -> None:
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries
        self._enabled = enabled
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}
        self._stats = CacheStats()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def stats(self) -> CacheStats:
        with self._lock:
            self._stats.size = len(self._store)
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                stores=self._stats.stores,
                evictions=self._stats.evictions,
                size=self._stats.size,
            )

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._stats.misses += 1
                return None
            expires_at, value = entry
            if expires_at < now:
                del self._store[key]
                self._stats.evictions += 1
                self._stats.misses += 1
                return None
            self._stats.hits += 1
            return value

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        if not self._enabled:
            return
        ttl = self._default_ttl if ttl_seconds is None else ttl_seconds
        expires_at = time.monotonic() + max(0.0, ttl)
        with self._lock:
            if key not in self._store and len(self._store) >= self._max_entries:
                # Evict the soonest-expiring entry.
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
                self._stats.evictions += 1
            self._store[key] = (expires_at, value)
            self._stats.stores += 1

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        *,
        ttl_seconds: float | None = None,
    ) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]
        value = factory()
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


def cache_key(namespace: str, *parts: Any, **kwargs: Any) -> str:
    """Build a stable cache key from namespace + positional/keyword parts."""
    payload = {"parts": list(parts), "kwargs": kwargs}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return f"{namespace}:{digest}"
