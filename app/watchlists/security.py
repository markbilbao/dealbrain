"""Security hooks for Watchlists — Sprint 19.

Ownership checks, in-process rate-limiting / audit hooks (following the
``app/auth/security.py`` Sprint 17 pattern), and a secret-redaction helper for
notification bodies. No secrets or hardcoded credentials live here.
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.domain.entities.watchlist import Watchlist
from app.domain.exceptions import WatchlistOwnershipError

# Field names commonly present in notification/observation payloads that must
# never be echoed back verbatim (API keys, tokens, credentials, etc).
_DEFAULT_SECRET_KEYS = frozenset(
    {
        "password",
        "token",
        "api_key",
        "apikey",
        "secret",
        "access_token",
        "refresh_token",
        "authorization",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
    }
)

_REDACTED = "***REDACTED***"


def require_owner(watchlist: Watchlist, user_id: str | None) -> Watchlist:
    """Return ``watchlist`` if owned by ``user_id``, otherwise raise.

    A watchlist with ``owner_id is None`` is treated as unowned/shared and is
    accessible to any caller (mirrors Sprint 10 fixtures that never set an
    owner). Raises :class:`WatchlistOwnershipError` on mismatch.
    """
    if watchlist.owner_id is not None and watchlist.owner_id != user_id:
        raise WatchlistOwnershipError(watchlist.watchlist_id, user_id)
    return watchlist


class RateLimiterHook:
    """In-process sliding-window rate limiter hook (not a production WAF).

    Mirrors ``app.auth.security.RateLimiterHook``; kept as a separate,
    independently-instantiable stub for watchlist/alert-scoped actions
    (e.g. bulk item adds, manual evaluation triggers).
    """

    def __init__(
        self,
        *,
        max_attempts: int = 20,
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


class WatchlistAuditLogger:
    """Lightweight audit hook recording watchlist/alert-affecting actions.

    Buffer-only stub (no repository dependency) — callers may drain
    :attr:`entries` for persistence or forward each record elsewhere.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._entries: list[dict[str, Any]] = []

    def record(
        self,
        action: str,
        *,
        user_id: str | None = None,
        watchlist_id: str | None = None,
        detail: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "audit_id": self._id_factory(),
            "action": action,
            "user_id": user_id,
            "watchlist_id": watchlist_id,
            "detail": detail,
            "metadata": dict(metadata or {}),
            "created_at": self._clock(),
        }
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()


def redact_secrets(
    text: str,
    *,
    extra_keys: frozenset[str] | None = None,
) -> str:
    """Redact ``key=value``/``key: value``-shaped secrets within free text.

    Used to sanitize notification bodies built from observation payloads
    before they are rendered or logged. Conservative and text-based (no
    parsing of arbitrary structures) — case-insensitive match on known
    sensitive key names.
    """
    keys = _DEFAULT_SECRET_KEYS | (extra_keys or frozenset())
    result = text
    for key in keys:
        for sep in ("=", ":"):
            lowered = result.lower()
            needle = f"{key}{sep}"
            start = 0
            rebuilt: list[str] = []
            while True:
                idx = lowered.find(needle, start)
                if idx == -1:
                    rebuilt.append(result[start:])
                    break
                rebuilt.append(result[start:idx])
                rebuilt.append(needle)
                after = idx + len(needle)
                end = after
                while end < len(result) and result[end] not in (" ", ",", ";", "\n", "\t"):
                    end += 1
                rebuilt.append(_REDACTED)
                start = end
            result = "".join(rebuilt)
    return result


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of ``payload`` with sensitive keys redacted."""
    return {
        key: (_REDACTED if key.lower() in _DEFAULT_SECRET_KEYS else value)
        for key, value in payload.items()
    }
