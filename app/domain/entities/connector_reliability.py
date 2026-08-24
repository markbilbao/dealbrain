"""Sprint 31 minimum connector reliability contracts.

Exported so Sprints 32–36 can validate real paths against shared types.
Sprint 38 owns production hardening and honest degradation — not the first
appearance of these result types. This module does not perform HTTP, retries,
or circuit breaking.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ConnectorFailureKind(StrEnum):
    """Typed failure categories for certified connector paths."""

    TIMEOUT = "timeout"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"
    CREDENTIAL = "credential"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    KILL_SWITCH = "kill_switch"
    CIRCUIT_OPEN = "circuit_open"
    UNKNOWN = "unknown"


class CircuitBreakerState(StrEnum):
    """Minimum circuit-breaker states. Sprint 38 hardens cross-connector behavior."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ConnectorOperationalStatus(StrEnum):
    """Trusted operational availability. Distinct from certification."""

    AVAILABLE = "available"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    """Timeout interface for a future certified connector call."""

    timeout_ms: int = 5_000

    def __post_init__(self) -> None:
        if self.timeout_ms < 1:
            raise ValueError("timeout_ms must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {"timeout_ms": self.timeout_ms}


@dataclass(frozen=True, slots=True)
class BoundedRetryPolicy:
    """Bounded retry interface. Does not itself retry."""

    max_attempts: int = 1
    retry_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {"max_attempts": self.max_attempts, "retry_on": list(self.retry_on)}


@dataclass(frozen=True, slots=True)
class ExponentialBackoffPolicy:
    """Exponential-backoff policy contract. Not an executor."""

    initial_delay_ms: int = 100
    multiplier: float = 2.0
    max_delay_ms: int = 2_000

    def __post_init__(self) -> None:
        if self.initial_delay_ms < 1:
            raise ValueError("initial_delay_ms must be at least 1")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least 1")
        if self.max_delay_ms < self.initial_delay_ms:
            raise ValueError("max_delay_ms must be >= initial_delay_ms")

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_delay_ms": self.initial_delay_ms,
            "multiplier": self.multiplier,
            "max_delay_ms": self.max_delay_ms,
        }


@dataclass(frozen=True, slots=True)
class QuotaFailure:
    """Quota / rate-limit result type."""

    kind: ConnectorFailureKind = ConnectorFailureKind.QUOTA
    retryable: bool = True
    retry_after_ms: int | None = None
    message: str = "quota exceeded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "retryable": self.retryable,
            "retry_after_ms": self.retry_after_ms,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CredentialFailure:
    """Credential-failure result type. Must not include secret values."""

    kind: ConnectorFailureKind = ConnectorFailureKind.CREDENTIAL
    retryable: bool = False
    message: str = "credential rejected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "retryable": self.retryable,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PartialFailure:
    """Partial-failure result type for incomplete certified responses."""

    kind: ConnectorFailureKind = ConnectorFailureKind.PARTIAL
    retryable: bool = False
    completed_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    message: str = "partial connector result"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "retryable": self.retryable,
            "completed_capabilities": list(self.completed_capabilities),
            "missing_capabilities": list(self.missing_capabilities),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class KillSwitch:
    """Kill-switch / feature-flag hook. Engaged means the path is not executable."""

    engaged: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"engaged": self.engaged, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class CircuitBreakerSnapshot:
    """Minimum circuit-breaker baseline. Sprint 38 owns production breakers."""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    reason: str | None = None

    @property
    def allows_execution(self) -> bool:
        return self.state != CircuitBreakerState.OPEN

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "reason": self.reason}
