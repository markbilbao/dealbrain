"""Origin policy for mutations authorized by the decision-owner cookie.

SameSite=Lax is not this control. Browser fetch and form POST send an Origin
header. This module accepts that header only when it is a bare http(s) origin
configured on the server.

Trusted origins come from ``PUBLIC_APP_BASE_URL`` and ``CORS_ORIGINS``. The
request Host, the request URL, and Referer are not trusted sources. A ``*``
CORS entry is not a trusted origin.

Missing Origin is fail-closed (``MISSING_ORIGIN_POLICY``) on the routes this
policy covers. A cookie-authorized browser mutation without Origin is rejected.
Requests that do not present the owner cookie, and that do not clear it, are
not covered. Bearer-only API calls stay unchanged.

Staging and production trust https origins only.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.consumer.decision_owner import OWNER_COOKIE
from app.core.config import settings
from app.core.errors import error_response

MISSING_ORIGIN_POLICY = "fail_closed"
ORIGIN_REJECTION_ERROR = "origin_rejected"
ORIGIN_REJECTION_MESSAGE = "Origin is not allowed for this request."
_MAX_ORIGIN_LENGTH = 200
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Unsafe routes whose authority includes the decision-owner cookie.
# Enforced only when that cookie is present.
COOKIE_AUTHORIZED_MUTATION_PATHS = frozenset(
    {
        "/api/v1/shopping-assistant/query",
        "/consumer/claim-decision",
        "/api/v1/feedback/reports",
        "/api/v1/analytics/events",
    }
)

# Unsafe routes that mutate the owner-cookie session even when the request
# does not send the cookie. Clear-device writes the deletion Set-Cookie.
COOKIE_SESSION_MUTATION_PATHS = frozenset({"/account/clear-device"})

# Preference and location writers. They are not owner-cookie authorization.
PREFERENCE_COOKIE_MUTATION_PATHS = frozenset(
    {
        "/consumer/location",
        "/consumer/shopping-market",
        "/api/v1/privacy/tracking-preference",
    }
)


@dataclass(frozen=True, slots=True)
class OriginVerdict:
    """Result of comparing one request Origin to the server-owned allow list."""

    allowed: bool
    reason: str


def cookie_origin_applies(method: str, path: str, *, owner_cookie_present: bool) -> bool:
    """Return True when this request must pass the owner-cookie origin policy."""

    if method.upper() not in _UNSAFE_METHODS:
        return False
    if path in COOKIE_SESSION_MUTATION_PATHS:
        return True
    return path in COOKIE_AUTHORIZED_MUTATION_PATHS and owner_cookie_present


def trusted_cookie_origins(
    *,
    public_app_base_url: str,
    cors_origins: Iterable[str],
    require_https: bool,
) -> frozenset[str]:
    """Return normalized origins the server is willing to treat as same-party.

    Invalid, credential-bearing, and wildcard entries are omitted. They do not
    widen the set. ``require_https`` drops http origins for staging/production.
    """

    trusted: set[str] = set()
    for raw in (public_app_base_url, *cors_origins):
        origin = _configured_origin(raw, require_https=require_https)
        if origin is not None:
            trusted.add(origin)
    return frozenset(trusted)


def evaluate_cookie_origin(raw_origin: str | None, *, trusted: frozenset[str]) -> OriginVerdict:
    """Classify a request Origin header. Host and Referer are not arguments."""

    parsed = _request_origin(raw_origin)
    if parsed.reason != "ok" or parsed.origin is None:
        return OriginVerdict(allowed=False, reason=parsed.reason)
    if parsed.origin not in trusted:
        return OriginVerdict(allowed=False, reason="foreign")
    return OriginVerdict(allowed=True, reason="ok")


def configured_trusted_origins() -> frozenset[str]:
    """Trusted origins from the current process settings. Never from Host."""

    return trusted_cookie_origins(
        public_app_base_url=settings.public_app_base_url,
        cors_origins=settings.cors_origins,
        require_https=settings.is_staging or settings.is_production,
    )


class OwnerCookieOriginMiddleware(BaseHTTPMiddleware):
    """Reject untrusted origins on owner-cookie mutations. Other routes pass."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cookie = request.cookies.get(OWNER_COOKIE)
        # Path comes from the ASGI scope. The URL host is not an authority
        # for this policy.
        path = request.scope.get("path") or ""
        if not cookie_origin_applies(
            request.method,
            path if isinstance(path, str) else "",
            owner_cookie_present=bool(cookie),
        ):
            return await call_next(request)
        verdict = evaluate_cookie_origin(
            request.headers.get("origin"),
            trusted=configured_trusted_origins(),
        )
        if not verdict.allowed:
            return error_response(
                status_code=403,
                error=ORIGIN_REJECTION_ERROR,
                message=ORIGIN_REJECTION_MESSAGE,
            )
        return await call_next(request)


@dataclass(frozen=True, slots=True)
class _ParsedOrigin:
    reason: str
    origin: str | None = None


def _configured_origin(raw: str, *, require_https: bool) -> str | None:
    """Origin of a server-owned base URL or CORS entry. Path is ignored."""

    value = (raw or "").strip()
    if not value or value == "*" or any(char.isspace() for char in value):
        return None
    if len(value) > _MAX_ORIGIN_LENGTH * 4:
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if require_https and parsed.scheme != "https":
        return None
    if parsed.query or parsed.fragment or "\\" in parsed.netloc or "@" in parsed.netloc:
        return None
    if "%" in parsed.netloc:
        return None
    return _format_origin(parsed.scheme, parsed.hostname, port)


def _request_origin(raw: str | None) -> _ParsedOrigin:
    """Parse a browser Origin header. A path, userinfo, or null is not trusted."""

    if raw is None:
        return _ParsedOrigin("missing")
    if "\n" in raw or "\r" in raw or "\x00" in raw:
        return _ParsedOrigin("malformed")
    value = raw.strip()
    if not value:
        return _ParsedOrigin("malformed")
    if value == "null":
        return _ParsedOrigin("null")
    if (
        len(value) > _MAX_ORIGIN_LENGTH
        or any(char.isspace() for char in value)
        or value.lower() == "null"
    ):
        return _ParsedOrigin("malformed")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return _ParsedOrigin("malformed")
    if parsed.username or parsed.password:
        return _ParsedOrigin("malformed")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return _ParsedOrigin("malformed")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return _ParsedOrigin("malformed")
    if "\\" in parsed.netloc or "@" in parsed.netloc or "%" in parsed.netloc:
        return _ParsedOrigin("malformed")
    return _ParsedOrigin("ok", _format_origin(parsed.scheme, parsed.hostname, port))


def _format_origin(scheme: str, hostname: str, port: int | None) -> str | None:
    host = hostname.rstrip(".").lower()
    if not host:
        return None
    # urlsplit().hostname strips IPv6 brackets.
    if ":" in host:
        host = f"[{host}]"
    if (scheme == "https" and port in {None, 443}) or (scheme == "http" and port in {None, 80}):
        return f"{scheme}://{host}"
    if port is None:
        return None
    return f"{scheme}://{host}:{port}"
