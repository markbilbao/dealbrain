"""Strict URL-safe Base64 for values this application signs.

The decoder accepts only the URL-safe alphabet. Standard Base64 characters
and trailing data after padding are rejected before the standard library
decoder runs. Callers that verify an HMAC must do that on the original text
before calling this decoder.
"""

from __future__ import annotations

import base64
import binascii

_ALPHABET = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")


def encode_urlsafe_b64(raw: bytes) -> str:
    """Encode bytes and strip padding, matching existing signed cookies."""

    if not isinstance(raw, bytes):
        raise TypeError("url-safe base64 encode requires bytes")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_urlsafe_b64(value: str) -> bytes:
    """Decode one URL-safe Base64 value, or raise ValueError."""

    if not isinstance(value, str) or value == "":
        raise ValueError("url-safe base64 is empty")
    try:
        raw = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("url-safe base64 is not ascii") from exc
    if b"+" in raw or b"/" in raw or any(byte not in _ALPHABET for byte in raw):
        raise ValueError("url-safe base64 contains a rejected character")
    if b"=" in raw:
        body = raw.rstrip(b"=")
        padding = len(raw) - len(body)
        if b"=" in body or padding > 2 or len(raw) % 4 != 0:
            raise ValueError("url-safe base64 padding is invalid")
        padded = raw
    else:
        remainder = len(raw) % 4
        if remainder == 1:
            raise ValueError("url-safe base64 padding is invalid")
        padded = raw + b"=" * ((4 - remainder) % 4)
    translated = padded.translate(bytes.maketrans(b"-_", b"+/"))
    try:
        return base64.b64decode(translated, validate=True)
    except binascii.Error as exc:
        raise ValueError("url-safe base64 did not validate") from exc
