"""Security helpers for marketplace data — secret redaction and CSV injection."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SECRET_KEY_TOKENS = ("secret", "password", "token", "apikey", "api_key", "auth", "credential")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
ALLOWED_IMPORT_CONTENT_TYPES = frozenset(
    {
        "text/csv",
        "application/csv",
        "application/json",
        "text/json",
        "application/vnd.ms-excel",
    }
)
ALLOWED_IMPORT_EXTENSIONS = frozenset({".csv", ".json"})
MAX_IMPORT_BYTES = 1_048_576  # 1 MiB
MAX_IMPORT_ROWS = 5_000
SAFE_URL_SCHEMES = frozenset({"http", "https"})


def redact_secrets(value: Any) -> Any:
    """Recursively redact secret-looking keys from mappings."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower().replace("-", "_")
            if any(token in lowered for token in SECRET_KEY_TOKENS):
                out[str(key)] = "***REDACTED***"
            else:
                out[str(key)] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


def sanitize_csv_cell(value: Any) -> str:
    """Neutralize formula injection in CSV cell values."""
    text = "" if value is None else str(value)
    if text and text[0] in FORMULA_PREFIXES:
        return "'" + text
    return text


def looks_like_secret(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in SECRET_KEY_TOKENS)


def validate_url(url: str | None) -> str | None:
    """Validate http(s) URLs; return cleaned URL or raise ValueError."""
    if url is None or not str(url).strip():
        return None
    cleaned = str(url).strip()
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in SAFE_URL_SCHEMES:
        raise ValueError(f"URL scheme not allowed: {parsed.scheme or '(missing)'}")
    if not parsed.netloc:
        raise ValueError("URL missing host")
    return cleaned


def validate_import_filename(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        raise ValueError("Import filename is required")
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError("Import filename must not contain path components")
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_IMPORT_EXTENSIONS):
        raise ValueError("Import file type must be .csv or .json")
    return name


def validate_import_size(payload: bytes | str, *, max_bytes: int = MAX_IMPORT_BYTES) -> None:
    size = len(payload.encode("utf-8") if isinstance(payload, str) else payload)
    if size <= 0:
        raise ValueError("Import payload is empty")
    if size > max_bytes:
        raise ValueError(f"Import payload exceeds {max_bytes} bytes")


_CONTENT_HASH_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return _CONTENT_HASH_SAFE.sub(" ", value.strip().lower()).strip()
