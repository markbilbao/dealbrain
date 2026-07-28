"""Unit tests for retry policy and rate limiter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.intelligence.collection.rate_limiter import InMemoryMarketplaceRateLimiter
from app.intelligence.collection.retry import CollectionRetryPolicy

FIXED_NOW = datetime(2026, 7, 28, 15, 0, tzinfo=UTC)


def test_retryable_versus_non_retryable() -> None:
    policy = CollectionRetryPolicy(max_attempts=3, base_delay_seconds=1.0)
    retryable = policy.decide(attempt=1, error_code="rate_limited")
    assert retryable.should_retry is True
    assert retryable.delay_seconds == 1.0

    non_retryable = policy.decide(attempt=1, error_code="malformed_listing")
    assert non_retryable.should_retry is False
    assert non_retryable.reason.startswith("non_retryable")


def test_exponential_delay_and_exhaustion() -> None:
    policy = CollectionRetryPolicy(max_attempts=3, base_delay_seconds=2.0, max_delay_seconds=10.0)
    assert policy.delay_for_attempt(1) == 2.0
    assert policy.delay_for_attempt(2) == 4.0
    assert policy.delay_for_attempt(3) == 8.0
    assert policy.delay_for_attempt(4) == 10.0  # capped

    exhausted = policy.decide(attempt=3, error_code="timeout")
    assert exhausted.should_retry is False
    assert exhausted.reason == "retry_exhausted"


def test_rate_limiter_allow_and_reject() -> None:
    clock_state = {"now": FIXED_NOW}

    def clock() -> datetime:
        return clock_state["now"]

    limiter = InMemoryMarketplaceRateLimiter(
        max_requests=2,
        window_seconds=30.0,
        clock=clock,
    )
    first = limiter.allow("shopee", now=FIXED_NOW)
    second = limiter.allow("shopee", now=FIXED_NOW)
    third = limiter.allow("shopee", now=FIXED_NOW)
    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds is not None
    assert third.retry_after_seconds > 0

    # Other marketplace is independent.
    other = limiter.allow("lazada", now=FIXED_NOW)
    assert other.allowed is True

    # After window advances, requests are allowed again.
    clock_state["now"] = FIXED_NOW + timedelta(seconds=31)
    later = limiter.allow("shopee", now=clock_state["now"])
    assert later.allowed is True


def test_explicit_reject_helper() -> None:
    limiter = InMemoryMarketplaceRateLimiter()
    decision = limiter.reject("shopee", retry_after_seconds=12.5, reason="manual")
    assert decision.allowed is False
    assert decision.retry_after_seconds == 12.5
    assert decision.reason == "manual"
