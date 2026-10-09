"""HTTP rate limiting middleware (Sprint 22)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.dependencies import get_rate_limiter
from app.launch.rate_limit import classify_path
from app.launch.rate_limit_backend import RateLimitUnavailable
from app.launch.rate_limit_keys import client_rate_limit_identity
from app.launch.redaction import safe_log_message
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PATH


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply configurable per-bucket rate limits."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limiting_enabled:
            return await call_next(request)

        # Skip probes and docs to avoid false alarms from orchestrators.
        path = request.url.path
        if path in {
            "/health",
            "/ready",
            "/live",
            "/api/v1/health",
            "/api/v1/ready",
            "/api/v1/live",
            PIQSAVI_UCP_AGENT_PROFILE_PATH,
        }:
            return await call_next(request)
        if path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        bucket = classify_path(request.method, path)
        try:
            identity = client_rate_limit_identity(request)
        except RateLimitUnavailable:
            return _unavailable_response(bucket)
        limiter = get_rate_limiter()
        decision = limiter.check(bucket, identity)
        if decision.unavailable:
            return _unavailable_response(bucket)
        if not decision.allowed:
            body = {
                "error": "rate_limited",
                "message": safe_log_message(
                    f"Rate limit exceeded for {decision.bucket} ({decision.limit}/min)"
                ),
                "status_code": 429,
                "detail": f"Rate limit exceeded for {decision.bucket}",
                "details": {
                    "bucket": decision.bucket,
                    "limit": decision.limit,
                    "retry_after_seconds": decision.retry_after_seconds,
                },
            }
            return JSONResponse(
                status_code=429,
                content=body,
                headers={
                    "Retry-After": str(decision.retry_after_seconds),
                    "X-RateLimit-Limit": str(decision.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Bucket": decision.bucket,
                },
            )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(decision.limit))
        response.headers.setdefault("X-RateLimit-Remaining", str(decision.remaining))
        response.headers.setdefault("X-RateLimit-Bucket", decision.bucket)
        return response


def _unavailable_response(bucket: str) -> JSONResponse:
    """Shared-store failure. Deny the request. Do not serve it and do not use memory."""

    message = safe_log_message("Rate limit control is unavailable")
    body = {
        "error": "rate_limit_unavailable",
        "message": message,
        "status_code": 503,
        "detail": "Rate limit control is unavailable",
        "details": {"bucket": bucket},
    }
    return JSONResponse(
        status_code=503,
        content=body,
        headers={"Retry-After": "1"},
    )
