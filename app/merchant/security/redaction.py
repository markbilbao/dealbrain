"""Secret redaction and rate-limit hooks for the Merchant Platform."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.domain.entities.merchant import MerchantAuditAction, MerchantAuditEvent

_SECRET_KEY_TOKENS = frozenset(
    {
        "password",
        "token",
        "api_key",
        "apikey",
        "secret",
        "access_token",
        "refresh_token",
        "authorization",
        "credential",
        "ssn",
        "passport",
        "national_id",
        "tax_id",
        "bank_account",
    }
)

_REDACTED = "***REDACTED***"


def redact_secrets(value: Any) -> Any:
    """Recursively redact secret-looking keys from mappings."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower().replace("-", "_")
            if any(token in lowered for token in _SECRET_KEY_TOKENS):
                out[str(key)] = _REDACTED
            else:
                out[str(key)] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


class RateLimiterHook:
    """In-process sliding-window rate limiter (not a production WAF)."""

    def __init__(
        self,
        *,
        max_attempts: int = 60,
        window_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._max_attempts = max_attempts
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = self._clock()
        bucket = self._attempts[key]
        while bucket and now - bucket[0] > self._window:
            bucket.popleft()
        if len(bucket) >= self._max_attempts:
            return False
        bucket.append(now)
        return True

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


class MerchantAuditHook:
    """Buffer-only audit hook; services also persist via repository."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self.entries: list[MerchantAuditEvent] = []

    def record(
        self,
        *,
        actor_account_id: str,
        organization_id: str | None,
        action: MerchantAuditAction,
        target_type: str,
        target_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> MerchantAuditEvent:
        event = MerchantAuditEvent(
            event_id=f"audit-{self._id_factory()}",
            actor_account_id=actor_account_id,
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            timestamp=self._clock(),
            metadata=redact_secrets(metadata or {}),
        )
        self.entries.append(event)
        return event
