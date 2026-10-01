"""Explicit first-party analytics preference.

Silence is essential-only. Advertising stays off. This is not an external CMP
and does not change EXT-22. The preference cookie stores only the choice,
schema version, and selected time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from starlette.responses import Response

from app.analytics.identity import is_analytics_subject_id, new_analytics_subject_id
from app.analytics.retention import PRODUCT_ANALYTICS_ENGINEERING_TTL_SECONDS
from app.consumer.decision_owner import cookie_requires_secure, signing_secret

TrackingChoice = Literal["essential_only", "analytics_allowed"]

CONSENT_SCHEMA = "piqsavi.tracking_preference.v1"
CONSENT_VERSION = "1"
PREFERENCE_COOKIE = "piqsavi_tracking_preference"
ANALYTICS_SUBJECT_COOKIE = "piqsavi_analytics_subject"
_COOKIE_PREFIX = "p1"
_ALLOWED_CHOICES: frozenset[str] = frozenset({"essential_only", "analytics_allowed"})
_CLAIM_KEYS = frozenset({"choice", "schema", "version", "selected_at"})


@dataclass(frozen=True, slots=True)
class TrackingPreference:
    """Server-validated analytics choice. Advertising is always false."""

    choice: TrackingChoice
    analytics_allowed: bool
    advertising_allowed: bool
    consent_schema: str
    consent_version: str
    selected_at: str | None
    explicit: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "choice": self.choice,
            "analytics_allowed": self.analytics_allowed,
            "advertising_allowed": False,
            "consent_schema": self.consent_schema,
            "consent_version": self.consent_version,
            "selected_at": self.selected_at,
            "explicit": self.explicit,
        }


def default_tracking_preference() -> TrackingPreference:
    """No explicit choice. Analytics stays off."""

    return TrackingPreference(
        choice="essential_only",
        analytics_allowed=False,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version=CONSENT_VERSION,
        selected_at=None,
        explicit=False,
    )


def read_tracking_preference(raw: str | None) -> TrackingPreference:
    """Return the signed choice, or essential-only when the cookie is absent or bad."""

    claims = preference_cookie_claims(raw)
    if claims is None:
        return default_tracking_preference()
    choice = claims["choice"]
    if choice not in _ALLOWED_CHOICES:
        return default_tracking_preference()
    allowed = choice == "analytics_allowed"
    return TrackingPreference(
        choice=choice,  # type: ignore[arg-type]
        analytics_allowed=allowed,
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version=CONSENT_VERSION,
        selected_at=str(claims["selected_at"]),
        explicit=True,
    )


def preference_cookie_claims(raw: str | None) -> dict[str, str] | None:
    """Return the signed claim set, or None when the cookie is not intact."""

    if not raw:
        return None
    parts = raw.split(".")
    if len(parts) != 3 or parts[0] != _COOKIE_PREFIX:
        return None
    secret = signing_secret()
    if secret is None:
        return None
    prefix, encoded, signature = parts
    signing_input = f"{prefix}.{encoded}".encode("ascii")
    expected = _b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(encoded))
    except (json.JSONDecodeError, TypeError, ValueError, OSError):
        return None
    if not isinstance(payload, dict) or set(payload) != _CLAIM_KEYS:
        return None
    if payload.get("schema") != CONSENT_SCHEMA or payload.get("version") != CONSENT_VERSION:
        return None
    choice = payload.get("choice")
    selected_at = payload.get("selected_at")
    if choice not in _ALLOWED_CHOICES or not isinstance(selected_at, str):
        return None
    return {
        "choice": choice,
        "schema": CONSENT_SCHEMA,
        "version": CONSENT_VERSION,
        "selected_at": selected_at,
    }


def read_analytics_subject(raw: str | None) -> str | None:
    """Return the subject id only when it is an opaque 32-hex token."""

    if is_analytics_subject_id(raw):
        return raw
    return None


def apply_tracking_choice(
    response: Response,
    choice: TrackingChoice,
    *,
    existing_subject: str | None,
    now: datetime | None = None,
) -> tuple[TrackingPreference, str | None]:
    """Persist the choice and mint or clear the analytics subject cookie.

    Returns the public preference and the subject id when analytics is allowed.
    The subject id is not part of the public preference body.
    """

    if choice not in _ALLOWED_CHOICES:
        raise ValueError("tracking choice is not allowed")
    secret = signing_secret()
    if secret is None:
        raise RuntimeError("tracking preference cannot be signed")
    clock = now or datetime.now(UTC)
    selected_at = clock.isoformat()
    payload = {
        "choice": choice,
        "schema": CONSENT_SCHEMA,
        "version": CONSENT_VERSION,
        "selected_at": selected_at,
    }
    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{_COOKIE_PREFIX}.{encoded}".encode("ascii")
    signature = _b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    response.set_cookie(
        PREFERENCE_COOKIE,
        f"{_COOKIE_PREFIX}.{encoded}.{signature}",
        max_age=PRODUCT_ANALYTICS_ENGINEERING_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=cookie_requires_secure(),
        path="/",
    )
    subject: str | None = None
    if choice == "analytics_allowed":
        subject = existing_subject if is_analytics_subject_id(existing_subject) else None
        if subject is None:
            subject = new_analytics_subject_id()
        response.set_cookie(
            ANALYTICS_SUBJECT_COOKIE,
            subject,
            max_age=PRODUCT_ANALYTICS_ENGINEERING_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            secure=cookie_requires_secure(),
            path="/",
        )
    else:
        response.delete_cookie(ANALYTICS_SUBJECT_COOKIE, path="/")
    preference = TrackingPreference(
        choice=choice,
        analytics_allowed=choice == "analytics_allowed",
        advertising_allowed=False,
        consent_schema=CONSENT_SCHEMA,
        consent_version=CONSENT_VERSION,
        selected_at=selected_at,
        explicit=True,
    )
    return preference, subject


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)
