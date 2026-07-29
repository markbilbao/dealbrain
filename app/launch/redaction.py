"""Log and payload redaction — sensitive values must never be logged."""

from __future__ import annotations

from typing import Any

_SECRET_TOKENS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "authorization",
        "auth",
        "credential",
        "cookie",
        "set-cookie",
        "ssn",
        "credit_card",
        "card_number",
        "cvv",
        "bank_account",
        "private_key",
        "bearer",
    }
)

_REDACTED = "***REDACTED***"


def is_sensitive_key(key: str) -> bool:
    lowered = str(key).lower().replace("-", "_")
    return any(token in lowered for token in _SECRET_TOKENS)


def redact_value(value: Any) -> Any:
    """Recursively redact secret-looking keys from mappings."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                out[str(key)] = _REDACTED
            else:
                out[str(key)] = redact_value(item)
        return out
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_headers(headers: dict[str, str] | None) -> dict[str, str]:
    if not headers:
        return {}
    return {key: (_REDACTED if is_sensitive_key(key) else value) for key, value in headers.items()}


def safe_log_message(message: str, *, max_length: int = 500) -> str:
    """Truncate and scrub common secret patterns from free-form messages."""
    text = message.replace("\n", " ").strip()
    lowered = text.lower()
    for token in ("bearer ", "password=", "api_key=", "token="):
        idx = lowered.find(token)
        if idx >= 0:
            text = text[:idx] + token + _REDACTED
            lowered = text.lower()
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text
