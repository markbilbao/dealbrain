"""MarketplaceRateLimiter port — deterministic allow/reject decisions.

No real waiting or network throttling. Implementations calculate retry-after
information when a request is rejected.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Outcome of a rate-limit check."""

    allowed: bool
    marketplace: str
    retry_after_seconds: float | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "marketplace": self.marketplace,
            "retry_after_seconds": self.retry_after_seconds,
            "reason": self.reason,
        }


class MarketplaceRateLimiter(ABC):
    """Abstract rate limiter for marketplace collection requests."""

    @abstractmethod
    def allow(
        self,
        marketplace: str,
        *,
        now: datetime | None = None,
    ) -> RateLimitDecision:
        """Decide whether a request against ``marketplace`` is allowed."""

    def reject(
        self,
        marketplace: str,
        *,
        retry_after_seconds: float,
        reason: str = "rate_limited",
        now: datetime | None = None,
    ) -> RateLimitDecision:
        """Return an explicit rejection decision (no side effects by default)."""
        _ = now
        return RateLimitDecision(
            allowed=False,
            marketplace=marketplace.strip().lower(),
            retry_after_seconds=retry_after_seconds,
            reason=reason,
        )
