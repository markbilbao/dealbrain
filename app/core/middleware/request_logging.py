"""Request logging middleware with timing and redaction (Sprint 22)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import (
    get_logger,
    log_affiliate_event,
    log_auth_event,
    log_merchant_event,
    log_request,
)

logger = get_logger("dealbrain.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method/path/status/duration without sensitive payloads."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            status_code = response.status_code if response is not None else 500
            if response is not None:
                response.headers.setdefault("X-Request-ID", request_id)
                response.headers.setdefault("X-Response-Time-Ms", f"{duration_ms:.2f}")

            if settings.structured_logging_enabled:
                log_request(
                    logger,
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                    client=request.client.host if request.client else None,
                )
                path = request.url.path
                if "/auth/" in path:
                    log_auth_event(
                        logger,
                        action=f"{request.method} {path}",
                        status_code=status_code,
                        request_id=request_id,
                    )
                elif "/affiliate" in path:
                    log_affiliate_event(
                        logger,
                        action=f"{request.method} {path}",
                        status_code=status_code,
                        request_id=request_id,
                    )
                elif "/merchants" in path or path.startswith("/api/v1/admin"):
                    log_merchant_event(
                        logger,
                        action=f"{request.method} {path}",
                        status_code=status_code,
                        request_id=request_id,
                    )
