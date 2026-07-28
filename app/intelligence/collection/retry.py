"""Deterministic retry policy for marketplace collection.

No sleeping — callers receive delay recommendations and decide whether to wait
(tests and domain logic never sleep).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Known retryable failure codes used by mock collectors and the service layer.
RETRYABLE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "rate_limited",
        "temporary_unavailable",
        "timeout",
        "collector_busy",
    }
)

NON_RETRYABLE_ERROR_CODES: frozenset[str] = frozenset(
    {
        "malformed_listing",
        "total_failure",
        "unsupported_marketplace",
        "validation_error",
        "not_found",
        "permanent_unavailable",
    }
)


class RetryableCollectionError(Exception):
    """Signal a retryable collection failure with a structured code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Outcome of evaluating whether another attempt should be made."""

    should_retry: bool
    attempt: int
    max_attempts: int
    delay_seconds: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_retry": self.should_retry,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "delay_seconds": self.delay_seconds,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CollectionRetryPolicy:
    """Exponential backoff policy without uncontrolled retry loops."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    retryable_codes: frozenset[str] = RETRYABLE_ERROR_CODES

    def is_retryable_code(self, code: str) -> bool:
        return code.strip().lower() in self.retryable_codes

    def delay_for_attempt(self, attempt: int) -> float:
        """Return exponential delay for the given 1-based attempt number.

        attempt=1 → base, attempt=2 → base*2, attempt=3 → base*4, …
        """
        if attempt < 1:
            return 0.0
        delay = self.base_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_delay_seconds)

    def decide(self, *, attempt: int, error_code: str) -> RetryDecision:
        """Decide whether another attempt is allowed after ``attempt`` failed.

        ``attempt`` is the number of attempts already performed (1-based).
        """
        code = error_code.strip().lower()
        if not self.is_retryable_code(code):
            return RetryDecision(
                should_retry=False,
                attempt=attempt,
                max_attempts=self.max_attempts,
                delay_seconds=0.0,
                reason=f"non_retryable:{code}",
            )
        if attempt >= self.max_attempts:
            return RetryDecision(
                should_retry=False,
                attempt=attempt,
                max_attempts=self.max_attempts,
                delay_seconds=0.0,
                reason="retry_exhausted",
            )
        delay = self.delay_for_attempt(attempt)
        return RetryDecision(
            should_retry=True,
            attempt=attempt,
            max_attempts=self.max_attempts,
            delay_seconds=delay,
            reason=f"retryable:{code}",
        )
