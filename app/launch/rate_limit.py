"""Configurable HTTP rate limiting (Sprint 22).

In-process sliding windows — not a production WAF/CDN. Protects login,
registration, affiliate, merchant, search, and recommendation surfaces.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

RateLimitBucket = Literal[
    "default",
    "login",
    "registration",
    "affiliate",
    "merchant",
    "search",
    "recommendations",
]


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    bucket: RateLimitBucket
    max_requests: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    bucket: RateLimitBucket
    limit: int
    remaining: int
    retry_after_seconds: int
    key: str


class ConfigurableRateLimiter:
    """Multi-bucket sliding-window rate limiter."""

    def __init__(
        self,
        rules: dict[RateLimitBucket, RateLimitRule],
        *,
        enabled: bool = True,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._rules = rules
        self._enabled = enabled
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._attempts.clear()
            else:
                self._attempts.pop(key, None)

    def check(self, bucket: RateLimitBucket, identity: str) -> RateLimitDecision:
        rule = self._rules.get(bucket) or self._rules["default"]
        key = f"{bucket}:{identity}"
        if not self._enabled:
            return RateLimitDecision(
                allowed=True,
                bucket=bucket,
                limit=rule.max_requests,
                remaining=rule.max_requests,
                retry_after_seconds=0,
                key=key,
            )

        now = self._clock()
        window = timedelta(seconds=rule.window_seconds)
        with self._lock:
            bucket_q = self._attempts[key]
            while bucket_q and now - bucket_q[0] > window:
                bucket_q.popleft()
            if len(bucket_q) >= rule.max_requests:
                oldest = bucket_q[0]
                retry = max(1, int((oldest + window - now).total_seconds()) + 1)
                return RateLimitDecision(
                    allowed=False,
                    bucket=bucket,
                    limit=rule.max_requests,
                    remaining=0,
                    retry_after_seconds=retry,
                    key=key,
                )
            bucket_q.append(now)
            remaining = max(0, rule.max_requests - len(bucket_q))
            return RateLimitDecision(
                allowed=True,
                bucket=bucket,
                limit=rule.max_requests,
                remaining=remaining,
                retry_after_seconds=0,
                key=key,
            )


def classify_path(method: str, path: str) -> RateLimitBucket:
    """Map an HTTP path to a rate-limit bucket."""
    normalized = path.rstrip("/") or "/"
    upper = method.upper()

    if normalized.endswith("/auth/login") and upper == "POST":
        return "login"
    if normalized.endswith("/auth/register") and upper == "POST":
        return "registration"
    if "/affiliate" in normalized:
        return "affiliate"
    if "/merchants" in normalized or normalized.startswith("/api/v1/admin"):
        return "merchant"
    if "/recommendations" in normalized:
        return "recommendations"
    if (
        "/marketplace/search" in normalized
        or "/dealscore/search" in normalized
        or "/price-history/search" in normalized
        or normalized.endswith("/search")
    ):
        return "search"
    return "default"
