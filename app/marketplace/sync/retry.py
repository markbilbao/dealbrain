"""Synchronization retry policy with exponential backoff abstraction (no sleeping)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncRetryDecision:
    should_retry: bool
    attempt: int
    delay_seconds: float
    reason: str = ""


class SyncRetryPolicy:
    """Advisory exponential backoff — callers must not sleep in unit tests."""

    def __init__(
        self,
        *,
        max_attempts: int = 3,
        base_delay_seconds: float = 0.5,
        max_delay_seconds: float = 30.0,
        retryable_codes: frozenset[str] | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.retryable_codes = retryable_codes or frozenset(
            {
                "rate_limited",
                "timeout",
                "transient",
                "simulated_transient_failure",
            }
        )

    def decide(self, *, attempt: int, error_code: str) -> SyncRetryDecision:
        if attempt >= self.max_attempts:
            return SyncRetryDecision(
                should_retry=False,
                attempt=attempt,
                delay_seconds=0.0,
                reason="max attempts reached",
            )
        if error_code not in self.retryable_codes:
            return SyncRetryDecision(
                should_retry=False,
                attempt=attempt,
                delay_seconds=0.0,
                reason=f"non-retryable error: {error_code}",
            )
        return SyncRetryDecision(
            should_retry=True,
            attempt=attempt,
            delay_seconds=self.delay_for_attempt(attempt),
            reason="retryable error",
        )

    def delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (2 ** max(0, attempt - 1))
        return min(delay, self.max_delay_seconds)
