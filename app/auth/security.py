"""Security hooks for the User Platform.

Provides CSRF preparation, rate-limiting hooks, audit logging hooks,
security events, and extension points for future MFA / OAuth.
No secrets or hardcoded credentials live here.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.user_platform import SecurityEvent, SecurityEventType
from app.domain.interfaces.user_platform_repository import AuditLogRepository
from app.launch.rate_limit_backend import (
    InMemoryRateLimitStore,
    RateLimitStore,
    RateLimitUnavailable,
)

_AUTH_SCOPE = "auth"


class RateLimiterHook:
    """Auth abuse counter. Staging and production pass the shared store.

    A private in-memory store is used only when the caller does not pass one,
    which development and unit tests do explicitly via the default.
    Store failure denies the attempt. It does not fall back to another store.
    """

    def __init__(
        self,
        *,
        max_attempts: int = 10,
        window_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
        store: RateLimitStore | None = None,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._store = store or InMemoryRateLimitStore()

    def check(self, key: str) -> bool:
        """Return True if the action is allowed; False if rate-limited or unavailable."""
        try:
            consumed = self._store.consume(
                scope=_AUTH_SCOPE,
                identity=key,
                limit=self._max_attempts,
                window_seconds=self._window_seconds,
                now=self._clock(),
            )
        except RateLimitUnavailable:
            return False
        return consumed.allowed

    def reset(self, key: str) -> None:
        try:
            self._store.reset(scope=_AUTH_SCOPE, identity=key)
        except RateLimitUnavailable:
            return


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
