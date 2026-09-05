"""Owner/session cookie used to authorize canonical UUID document routes.

The cookie is a server-authenticated credential, not a browser-trusted lookup
hint. Unsigned or tampered values grant no conversation, snapshot, or claim
access. It carries the same identity tuple already stored on the snapshot.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any

from starlette.responses import Response

from app.core.config import settings
from app.domain.entities.shopping_assistant import ConversationOwner

OWNER_COOKIE = "piqsavi_decision_owner"
COOKIE_MAX_BYTES = 768
_COOKIE_VERSION = "v1"
_DEV_ONLY_SIGNING_KEY = b"dealbrain-dev-only-owner-cookie-hmac-key-do-not-use-in-prod"
_PLACEHOLDER_SECRETS = frozenset({"", "changeme", "secret", "dev", "test", "password"})


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def signing_secret() -> bytes | None:
    """Return the HMAC key, or None when staging/production cannot sign."""

    key = (settings.app_secret_key or "").strip()
    if key and key.lower() not in _PLACEHOLDER_SECRETS and len(key) >= 16:
        return key.encode("utf-8")
    if settings.is_production or settings.is_staging:
        return None
    return _DEV_ONLY_SIGNING_KEY


def cookie_requires_secure() -> bool:
    return settings.is_production or settings.is_staging


def _owner_from_fields(payload: dict[str, Any]) -> ConversationOwner | None:
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at") or ""))
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    try:
        return ConversationOwner(
            principal_type=str(payload.get("principal_type") or ""),
            principal_id=str(payload.get("principal_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            expires_at=expires_at,
        )
    except ValueError:
        return None


def owner_identity_payload(owner: ConversationOwner) -> dict[str, str]:
    return {
        "principal_type": owner.principal_type,
        "principal_id": owner.principal_id,
        "session_id": owner.session_id,
        "expires_at": owner.expires_at.isoformat(),
    }


def owner_cookie_payload(owner: ConversationOwner) -> str:
    """Return the signed cookie value for this owner identity."""

    secret = signing_secret()
    if secret is None:
        raise RuntimeError("owner cookie cannot be signed without APP_SECRET_KEY")
    encoded = _b64encode(
        json.dumps(owner_identity_payload(owner), separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )
    signing_input = f"{_COOKIE_VERSION}.{encoded}".encode("ascii")
    signature = _b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    return f"{_COOKIE_VERSION}.{encoded}.{signature}"


def parse_owner_cookie(raw: str | None) -> ConversationOwner | None:
    """Return an owner only when the cookie is signed, intact, and unexpired."""

    if not raw:
        return None
    parts = raw.split(".")
    if len(parts) != 3 or parts[0] != _COOKIE_VERSION:
        return None
    secret = signing_secret()
    if secret is None:
        return None
    version, encoded, signature = parts
    signing_input = f"{version}.{encoded}".encode("ascii")
    expected = _b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(encoded))
    except (json.JSONDecodeError, TypeError, ValueError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    owner = _owner_from_fields(payload)
    if owner is None:
        return None
    if owner.expires_at <= datetime.now(UTC):
        return None
    return owner


def set_owner_cookie(response: Response, owner: ConversationOwner) -> None:
    secret = signing_secret()
    if secret is None:
        return
    payload = owner_cookie_payload(owner)
    if len(payload.encode()) > COOKIE_MAX_BYTES:
        raise ValueError("owner cookie exceeds size limit")
    response.set_cookie(
        OWNER_COOKIE,
        payload,
        httponly=True,
        samesite="lax",
        secure=cookie_requires_secure(),
        path="/",
    )


def owner_from_mapping(payload: dict[str, Any]) -> ConversationOwner | None:
    """Parse identity fields from a trusted server mapping. Not a cookie."""

    if not isinstance(payload, dict):
        return None
    return _owner_from_fields(payload)
