"""Configurable HTTP rate limiting (Sprint 22, shared counters in Sprint 40.3).

Staging and production use the PostgreSQL counter. Development may use an
explicit in-memory window. This is not a WAF or CDN.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.launch.rate_limit_backend import (
    InMemoryRateLimitStore,
    RateLimitStore,
    RateLimitUnavailable,
)

RateLimitBucket = Literal[
    "default",
    "login",
    "registration",
    "auth_email",
    "affiliate",
    "merchant",
    "search",
    "recommendations",
    "early_access_events",
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
    unavailable: bool = False


class ConfigurableRateLimiter:
    """Multi-bucket rate limiter over a shared or explicit in-memory store."""

    def __init__(
        self,
        rules: dict[RateLimitBucket, RateLimitRule],
        *,
        enabled: bool = True,
        clock: Callable[[], datetime] | None = None,
        store: RateLimitStore | None = None,
    ) -> None:
        self._rules = rules
        self._enabled = enabled
        self._clock = clock or (lambda: datetime.now(UTC))
        self._store = store or InMemoryRateLimitStore()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def reset(self, key: str | None = None) -> None:
        if key is None:
            for bucket in self._rules:
                self._store.reset(scope=bucket)
            return
        scope, separator, identity = key.partition(":")
        if separator and scope in self._rules:
            self._store.reset(scope=scope, identity=identity)
            return
        self._store.reset(identity=key)

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
        try:
            consumed = self._store.consume(
                scope=bucket,
                identity=identity,
                limit=rule.max_requests,
                window_seconds=rule.window_seconds,
                now=self._clock(),
            )
        except RateLimitUnavailable:
            return RateLimitDecision(
                allowed=False,
                bucket=bucket,
                limit=rule.max_requests,
                remaining=0,
                retry_after_seconds=0,
                key=key,
                unavailable=True,
            )
        return RateLimitDecision(
            allowed=consumed.allowed,
            bucket=bucket,
            limit=consumed.limit,
            remaining=consumed.remaining,
            retry_after_seconds=consumed.retry_after_seconds,
            key=key,
            unavailable=False,
        )


def classify_path(method: str, path: str) -> RateLimitBucket:
    """Map an HTTP path to a rate-limit bucket."""
    normalized = path.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
    upper = method.upper()

    if normalized.endswith("/auth/login") and upper == "POST":
        return "login"
    if normalized.endswith("/auth/register") and upper == "POST":
        return "registration"
    if (
        normalized.endswith("/auth/password-reset")
        or normalized.endswith("/auth/password-reset/confirm")
        or normalized.endswith("/auth/verify-email")
        or normalized.endswith("/auth/verify-email/confirm")
        or normalized.endswith("/auth/email-change")
        or normalized.endswith("/auth/email-change/confirm")
    ) and upper == "POST":
        return "auth_email"
    # Tiny first-party landing-page event stream. 20/min/IP by default — not the
    # generic 120/min default bucket, and not the 5/min registration bucket.
    if normalized.endswith("/early-access/events") and upper == "POST":
        return "early_access_events"
    if normalized.endswith("/early-access") and upper == "POST":
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
