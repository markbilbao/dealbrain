"""In-memory deterministic marketplace rate limiter."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.domain.interfaces.marketplace_rate_limiter import (
    MarketplaceRateLimiter,
    RateLimitDecision,
)


class InMemoryMarketplaceRateLimiter(MarketplaceRateLimiter):
    """Fixed-window request limiter with injected clock (no real waiting)."""

    def __init__(
        self,
        *,
        max_requests: int = 10,
        window_seconds: float = 60.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._windows: dict[str, list[datetime]] = defaultdict(list)

    def allow(
        self,
        marketplace: str,
        *,
        now: datetime | None = None,
    ) -> RateLimitDecision:
        market = marketplace.strip().lower()
        current = now or self._clock()
        window_start = current - timedelta(seconds=self._window_seconds)
        recent = [ts for ts in self._windows[market] if ts > window_start]
        self._windows[market] = recent

        if len(recent) >= self._max_requests:
            oldest = min(recent)
            retry_after = max(
                0.0,
                self._window_seconds - (current - oldest).total_seconds(),
            )
            return RateLimitDecision(
                allowed=False,
                marketplace=market,
                retry_after_seconds=round(retry_after, 3),
                reason="rate_limited",
            )

        recent.append(current)
        self._windows[market] = recent
        return RateLimitDecision(allowed=True, marketplace=market)

    def clear(self) -> None:
        """Reset all windows (tests)."""
        self._windows.clear()
