"""Input validation helpers for merchant submissions."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.domain.exceptions import MerchantValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_URL_SCHEMES = frozenset({"http", "https"})
MAX_TEXT_LENGTH = 4_000
MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 8_000
MAX_IMAGE_URLS = 10


def validate_email(email: str) -> str:
    cleaned = (email or "").strip().lower()
    if not cleaned or not _EMAIL_RE.match(cleaned):
        raise MerchantValidationError("A valid email address is required.")
    if len(cleaned) > 254:
        raise MerchantValidationError("Email address is too long.")
    return cleaned


def validate_identifier(value: str, *, field: str = "id") -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise MerchantValidationError(f"{field} is required.")
    if not _SAFE_ID_RE.match(cleaned):
        raise MerchantValidationError(f"{field} contains invalid characters.")
    return cleaned


def validate_safe_url(url: str | None, *, required: bool = False) -> str | None:
    if url is None or not str(url).strip():
        if required:
            raise MerchantValidationError("URL is required.")
        return None
    cleaned = str(url).strip()
    if len(cleaned) > 2_048:
        raise MerchantValidationError("URL is too long.")
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in SAFE_URL_SCHEMES:
        raise MerchantValidationError(f"URL scheme not allowed: {parsed.scheme or '(missing)'}")
    if not parsed.netloc:
        raise MerchantValidationError("URL missing host.")
    # Block obvious credential leakage in URLs
    lowered = cleaned.lower()
    for token in ("password=", "api_key=", "secret=", "token="):
        if token in lowered:
            raise MerchantValidationError("URL must not contain credential parameters.")
    return cleaned


def validate_text_length(
    value: str | None,
    *,
    field: str,
    max_length: int = MAX_TEXT_LENGTH,
    required: bool = False,
) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise MerchantValidationError(f"{field} is required.")
    if len(text) > max_length:
        raise MerchantValidationError(f"{field} exceeds maximum length of {max_length}.")
    return text


def validate_image_urls(urls: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if not urls:
        return ()
    if len(urls) > MAX_IMAGE_URLS:
        raise MerchantValidationError(f"At most {MAX_IMAGE_URLS} image URLs are allowed.")
    cleaned: list[str] = []
    for url in urls:
        validated = validate_safe_url(url, required=True)
        assert validated is not None
        cleaned.append(validated)
    return tuple(cleaned)
