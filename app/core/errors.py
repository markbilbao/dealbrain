"""Standardized API error responses (Sprint 22)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.domain.exceptions import (
    AffiliateNotFoundError,
    AffiliateValidationError,
    AlertRuleNotFoundError,
    AlertRuleValidationError,
    DashboardValidationError,
    EarlyAccessValidationError,
    LaunchAuthorizationError,
    LaunchNotFoundError,
    LaunchRateLimitError,
    LaunchValidationError,
    MarketplaceDataAuthError,
    MarketplaceDataNotFoundError,
    MarketplaceDataRateLimitError,
    MarketplaceDataValidationError,
    MerchantAuthorizationError,
    MerchantIsolationError,
    MerchantNotFoundError,
    MerchantValidationError,
    NotificationNotFoundError,
    NotificationValidationError,
    UserPlatformAuthError,
    UserPlatformConflictError,
    UserPlatformNotFoundError,
    UserPlatformRateLimitError,
    UserPlatformValidationError,
    WatchlistOwnershipError,
)
from app.launch.redaction import safe_log_message

logger = get_logger(__name__)


class ErrorBody(BaseModel):
    """Consistent JSON error envelope."""

    error: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    status_code: int = Field(description="HTTP status code")
    details: list[Any] | dict[str, Any] | None = Field(
        default=None,
        description="Optional structured details (validation issues, etc.)",
    )
    request_id: str | None = Field(default=None, description="Request correlation id")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "validation_error",
                "message": "Request validation failed",
                "status_code": 422,
                "details": [{"loc": ["body", "email"], "msg": "field required"}],
                "request_id": "req-abc123",
            }
        }
    }


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id")


def error_response(
    *,
    status_code: int,
    error: str,
    message: str,
    details: list[Any] | dict[str, Any] | None = None,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
    detail_override: Any | None = None,
) -> JSONResponse:
    """Build a consistent error payload.

    Includes legacy ``detail`` (FastAPI-compatible) alongside the Sprint 22
    envelope fields so prior-sprint clients and tests keep working.
    """
    safe_message = safe_log_message(message, max_length=1000)
    body: dict[str, Any] = {
        "error": error,
        "message": safe_message,
        "status_code": status_code,
        # Preserve FastAPI's conventional ``detail`` key for compatibility.
        "detail": detail_override if detail_override is not None else safe_message,
    }
    if details is not None:
        body["details"] = details
    if request_id is not None:
        body["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def map_domain_exception(exc: Exception) -> tuple[int, str, str] | None:
    """Map known domain exceptions to (status, code, message)."""
    if isinstance(
        exc,
        (
            UserPlatformValidationError,
            EarlyAccessValidationError,
            MerchantValidationError,
            AffiliateValidationError,
            MarketplaceDataValidationError,
            AlertRuleValidationError,
            NotificationValidationError,
            DashboardValidationError,
            LaunchValidationError,
        ),
    ):
        return (
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            getattr(exc, "message", str(exc)),
        )

    if isinstance(
        exc,
        (
            UserPlatformAuthError,
            MerchantAuthorizationError,
            MarketplaceDataAuthError,
            LaunchAuthorizationError,
            WatchlistOwnershipError,
            MerchantIsolationError,
        ),
    ):
        msg = getattr(exc, "message", str(exc))
        lowered = msg.lower()
        if "token" in lowered or "login" in lowered or "authenticated" in lowered:
            return status.HTTP_401_UNAUTHORIZED, "authentication_error", msg
        return status.HTTP_403_FORBIDDEN, "authorization_error", msg

    if isinstance(
        exc,
        (
            UserPlatformNotFoundError,
            MerchantNotFoundError,
            AffiliateNotFoundError,
            MarketplaceDataNotFoundError,
            AlertRuleNotFoundError,
            NotificationNotFoundError,
            LaunchNotFoundError,
        ),
    ):
        return status.HTTP_404_NOT_FOUND, "not_found", str(exc)

    if isinstance(exc, UserPlatformConflictError):
        return status.HTTP_409_CONFLICT, "conflict", getattr(exc, "message", str(exc))

    if isinstance(
        exc,
        (
            UserPlatformRateLimitError,
            MarketplaceDataRateLimitError,
            LaunchRateLimitError,
        ),
    ):
        return (
            status.HTTP_429_TOO_MANY_REQUESTS,
            "rate_limited",
            getattr(exc, "message", str(exc)),
        )

    return None


def _json_safe(value: Any) -> Any:
    """Make validation error payloads JSON-serializable."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, BaseException):
        return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


# Constraint metadata that cannot contain submitted field values.
_SAFE_CONSTRAINT_CTX_KEYS = frozenset(
    {
        "min_length",
        "max_length",
        "expected",
        "gt",
        "ge",
        "lt",
        "le",
        "multiple_of",
    }
)


def _validation_error_log_projection(errors: list[Any]) -> list[dict[str, Any]]:
    """Project RequestValidationError details for logs without submitted values.

    Never includes ``input``, ``body``, request payloads, or unconstrained ``ctx`` /
    ``msg`` text that could echo rejected user data.
    """
    projected: list[dict[str, Any]] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        item: dict[str, Any] = {}
        error_type = error.get("type")
        if isinstance(error_type, str):
            item["type"] = error_type
        loc = error.get("loc")
        if loc is not None:
            item["loc"] = _json_safe(loc)
        ctx = error.get("ctx")
        if isinstance(ctx, dict):
            safe_ctx = {
                key: _json_safe(value)
                for key, value in ctx.items()
                if key in _SAFE_CONSTRAINT_CTX_KEYS
            }
            if safe_ctx:
                item["ctx"] = safe_ctx
        projected.append(item)
    return projected


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers with consistent JSON errors."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        safe_errors = _json_safe(exc.errors())
        log_errors = _validation_error_log_projection(exc.errors())
        logger.warning(
            "validation_error method=%s path=%s errors=%s request_id=%s",
            request.method,
            request.url.path,
            safe_log_message(str(log_errors)),
            _request_id(request),
        )
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="validation_error",
            message="Request validation failed",
            details=safe_errors,
            detail_override=safe_errors,
            request_id=_request_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed"
        details: list[Any] | dict[str, Any] | None = None
        if isinstance(detail, dict):
            message = str(detail.get("message") or detail.get("detail") or message)
            details = detail
        elif isinstance(detail, list):
            details = detail

        code_map = {
            400: "validation_error",
            401: "authentication_error",
            403: "authorization_error",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_error",
            503: "service_unavailable",
        }
        error = code_map.get(exc.status_code, "http_error")
        if exc.status_code >= 500:
            logger.error(
                "http_error status=%s path=%s message=%s request_id=%s",
                exc.status_code,
                request.url.path,
                safe_log_message(message),
                _request_id(request),
            )
        elif exc.status_code == 429:
            logger.warning(
                "rate_limited path=%s request_id=%s",
                request.url.path,
                _request_id(request),
            )
        return error_response(
            status_code=exc.status_code,
            error=error,
            message=message if isinstance(message, str) else "Request failed",
            details=details,
            detail_override=detail,
            request_id=_request_id(request),
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        mapped = map_domain_exception(exc)
        if mapped is not None:
            status_code, error, message = mapped
            headers: dict[str, str] | None = None
            if isinstance(exc, LaunchRateLimitError):
                headers = {"Retry-After": str(exc.retry_after_seconds)}
            if status_code >= 500:
                logger.error(
                    "domain_error code=%s path=%s message=%s",
                    error,
                    request.url.path,
                    safe_log_message(message),
                )
            else:
                logger.warning(
                    "domain_error code=%s path=%s message=%s",
                    error,
                    request.url.path,
                    safe_log_message(message),
                )
            return error_response(
                status_code=status_code,
                error=error,
                message=message,
                request_id=_request_id(request),
                headers=headers,
            )

        logger.exception(
            "internal_error path=%s request_id=%s",
            request.url.path,
            _request_id(request),
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="internal_error",
            message="An unexpected error occurred",
            request_id=_request_id(request),
        )
