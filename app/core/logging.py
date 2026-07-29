"""Structured logging configuration (Sprint 22)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.launch.redaction import redact_value, safe_log_message


class StructuredFormatter(logging.Formatter):
    """Emit JSON log lines when structured logging is enabled."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": safe_log_message(record.getMessage()),
        }
        extras = getattr(record, "structured", None)
        if isinstance(extras, dict):
            payload.update(redact_value(extras))
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure application-wide logging."""
    log_level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if settings.structured_logging_enabled:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root.addHandler(handler)
    root.setLevel(log_level)

    if not settings.app_debug:
        for logger_name in ("uvicorn.access", "sqlalchemy.engine"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for the given module."""
    return logging.getLogger(name)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """Helper for structured log context (secrets redacted)."""
    return redact_value(kwargs)  # type: ignore[return-value]


def _emit(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = redact_value({"event": event, **fields})
    logger.log(level, event, extra={"structured": payload})


def log_request(
    logger: logging.Logger,
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str | None = None,
    client: str | None = None,
) -> None:
    level = logging.WARNING if status_code >= 400 else logging.INFO
    _emit(
        logger,
        level,
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
        client=client,
    )


def log_auth_event(
    logger: logging.Logger,
    *,
    action: str,
    status_code: int,
    request_id: str | None = None,
) -> None:
    _emit(
        logger,
        logging.INFO if status_code < 400 else logging.WARNING,
        "auth_event",
        action=action,
        status_code=status_code,
        request_id=request_id,
    )


def log_affiliate_event(
    logger: logging.Logger,
    *,
    action: str,
    status_code: int,
    request_id: str | None = None,
) -> None:
    _emit(
        logger,
        logging.INFO,
        "affiliate_event",
        action=action,
        status_code=status_code,
        request_id=request_id,
    )


def log_merchant_event(
    logger: logging.Logger,
    *,
    action: str,
    status_code: int,
    request_id: str | None = None,
) -> None:
    _emit(
        logger,
        logging.INFO,
        "merchant_event",
        action=action,
        status_code=status_code,
        request_id=request_id,
    )
