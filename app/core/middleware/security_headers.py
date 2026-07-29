"""Security response headers middleware (Sprint 22)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach CSP, HSTS, frame options, and related headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if not settings.security_headers_enabled:
            return response

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", settings.security_frame_options)
        response.headers.setdefault("Referrer-Policy", settings.security_referrer_policy)
        response.headers.setdefault("Permissions-Policy", settings.security_permissions_policy)
        response.headers.setdefault("Content-Security-Policy", settings.security_csp)
        response.headers.setdefault("X-XSS-Protection", "0")

        if settings.app_env in {"staging", "production"} and settings.security_hsts_max_age > 0:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={settings.security_hsts_max_age}; includeSubDomains",
            )
        return response
