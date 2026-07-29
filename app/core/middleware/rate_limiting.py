"""HTTP rate limiting middleware (Sprint 22)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.dependencies import get_rate_limiter
from app.launch.rate_limit import classify_path
from app.launch.redaction import safe_log_message


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
        }:
            return await call_next(request)
        if path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json":
            return await call_next(request)

        identity = _client_identity(request)
        bucket = classify_path(request.method, path)
        limiter = get_rate_limiter()
        decision = limiter.check(bucket, identity)
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


def _client_identity(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        # Hash-ish truncation — never log full token; identity only.
        return f"tok:{token[:8]}" if token else "tok:empty"
    if request.client and request.client.host:
        return f"ip:{request.client.host}"
    return "ip:unknown"
