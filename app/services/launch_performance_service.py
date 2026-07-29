"""Performance cache helpers for repeated read queries (Sprint 22).

Wraps identical lookups to reduce duplicate processing. Does not change
DealScore, recommendation order, or affiliate ranking.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from app.core.config import settings
from app.launch.cache import TtlCache, cache_key

T = TypeVar("T")


class LaunchPerformanceService:
    """Namespace helpers for search / recommendations / dashboard caches."""

    def __init__(self, cache: TtlCache) -> None:
        self._cache = cache

    @property
    def cache(self) -> TtlCache:
        return self._cache

    def cached(
        self,
        namespace: str,
        factory: Callable[[], T],
        *parts: Any,
        **kwargs: Any,
    ) -> T:
        if not settings.performance_cache_enabled or not self._cache.enabled:
            return factory()
        key = cache_key(namespace, *parts, **kwargs)
        return self._cache.get_or_set(
            key,
            factory,
            ttl_seconds=settings.performance_cache_ttl_seconds,
        )

    def invalidate_namespace(self, namespace: str) -> int:
        """Best-effort clear of keys with a given namespace prefix."""
        stats_before = self._cache.stats().size
        # Full clear is acceptable for demo in-memory cache.
        if namespace == "*":
            self._cache.clear()
            return stats_before
        # Prefix scan
        cleared = 0
        with self._cache._lock:  # noqa: SLF001
            keys = [k for k in self._cache._store if k.startswith(f"{namespace}:")]  # noqa: SLF001
            for key in keys:
                del self._cache._store[key]  # noqa: SLF001
                cleared += 1
        return cleared

    def stats(self) -> dict[str, Any]:
        s = self._cache.stats()
        return {
            "enabled": self._cache.enabled and settings.performance_cache_enabled,
            "ttl_seconds": settings.performance_cache_ttl_seconds,
            "hits": s.hits,
            "misses": s.misses,
            "stores": s.stores,
            "evictions": s.evictions,
            "size": s.size,
            "namespaces": [
                "search",
                "recommendations",
                "watchlists",
                "dashboard",
                "merchant",
                "affiliate",
                "launch_metrics",
            ],
            "note": "Cache memoizes identical read results only; ranking logic is unchanged.",
        }
