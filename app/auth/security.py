"""Security hooks for the User Platform.

Provides CSRF preparation, rate-limiting hooks, audit logging hooks,
security events, and extension points for future MFA / OAuth.
No secrets or hardcoded credentials live here.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.domain.entities.user_platform import SecurityEvent, SecurityEventType
from app.domain.interfaces.user_platform_repository import AuditLogRepository


class RateLimiterHook:
    """In-process sliding-window rate limiter hook (not a production WAF)."""

    def __init__(
        self,
        *,
        max_attempts: int = 10,
        window_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._max_attempts = max_attempts
        self._window = timedelta(seconds=window_seconds)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        """Return True if the action is allowed; False if rate-limited."""
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


class CsrfTokenService:
    """CSRF preparation — generate and validate double-submit style tokens."""

    def __init__(self, *, token_factory: Callable[[], str] | None = None) -> None:
        self._token_factory = token_factory or (lambda: secrets_token())

    def issue(self) -> str:
        return self._token_factory()

    def validate(self, expected: str | None, provided: str | None) -> bool:
        if not expected or not provided:
            return False
        import hmac

        return hmac.compare_digest(expected, provided)


def secrets_token(nbytes: int = 32) -> str:
    import secrets

    return secrets.token_urlsafe(nbytes)


class AuditLogger:
    """Audit logging hook that optionally persists SecurityEvent records."""

    def __init__(
        self,
        repository: AuditLogRepository | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._buffer: list[SecurityEvent] = []

    def record(
        self,
        event_type: SecurityEventType,
        *,
        user_id: str | None = None,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        event = SecurityEvent(
            event_id=self._id_factory(),
            event_type=event_type,
            user_id=user_id,
            detail=detail,
            created_at=self._clock(),
            metadata=dict(metadata or {}),
        )
        self._buffer.append(event)
        if self._repository is not None:
            return self._repository.append(event)
        return event

    def recent(self, *, user_id: str | None = None, limit: int = 100) -> list[SecurityEvent]:
        if self._repository is not None:
            return self._repository.list_events(user_id=user_id, limit=limit)
        items = [e for e in self._buffer if user_id is None or e.user_id == user_id]
        return items[-limit:]


class MfaExtensionPoint:
    """Future MFA extension point — not implemented in Sprint 17."""

    supported_methods: tuple[str, ...] = ()

    def is_enabled(self, user_id: str) -> bool:  # noqa: ARG002
        return False

    def challenge(self, user_id: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "mfa_required": False,
            "methods": list(self.supported_methods),
            "status": "not_implemented",
        }


class OAuthExtensionPoint:
    """Future OAuth / external IdP extension point — not implemented in Sprint 17."""

    supported_providers: tuple[str, ...] = ()

    def begin_link(self, provider: str, user_id: str) -> dict[str, Any]:
        return {
            "provider": provider,
            "user_id": user_id,
            "status": "not_implemented",
            "supported_providers": list(self.supported_providers),
        }
