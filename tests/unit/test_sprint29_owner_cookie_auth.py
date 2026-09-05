"""Guest owner cookie is a server-signed credential, not a lookup hint."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

import pytest
from app.consumer.decision_owner import (
    OWNER_COOKIE,
    owner_cookie_payload,
    owner_from_mapping,
    owner_identity_payload,
    parse_owner_cookie,
    set_owner_cookie,
    signing_secret,
)
from app.core.config import settings
from app.domain.entities.shopping_assistant import ConversationOwner
from starlette.responses import Response

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


def _owner(**overrides: object) -> ConversationOwner:
    payload = {
        "principal_type": "guest",
        "principal_id": "guest-cookie-auth",
        "session_id": "guest-session-cookie-auth",
        "expires_at": NOW + timedelta(hours=1),
    }
    payload.update(overrides)
    expires_at = payload["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    return ConversationOwner(
        principal_type=str(payload["principal_type"]),
        principal_id=str(payload["principal_id"]),
        session_id=str(payload["session_id"]),
        expires_at=expires_at,  # type: ignore[arg-type]
    )


def test_signed_cookie_roundtrip() -> None:
    owner = _owner()
    raw = owner_cookie_payload(owner)
    assert raw.startswith("v1.")
    assert json.dumps(owner_identity_payload(owner)) not in raw
    parsed = parse_owner_cookie(raw)
    assert parsed is not None
    assert parsed.has_same_identity(owner)


def test_unsigned_json_cookie_is_rejected() -> None:
    owner = _owner()
    raw = json.dumps(owner_identity_payload(owner))
    assert parse_owner_cookie(raw) is None


def test_tampered_signature_is_rejected() -> None:
    raw = owner_cookie_payload(_owner())
    version, encoded, signature = raw.split(".")
    flipped = "A" if signature[0] != "A" else "B"
    assert parse_owner_cookie(f"{version}.{encoded}.{flipped}{signature[1:]}") is None


def test_forged_principal_payload_is_rejected() -> None:
    raw = owner_cookie_payload(_owner())
    version, _encoded, signature = raw.split(".")
    forged = _owner(principal_id="forged-guest")
    encoded = owner_cookie_payload(forged).split(".")[1]
    assert parse_owner_cookie(f"{version}.{encoded}.{signature}") is None


def test_changed_principal_type_requires_new_signature() -> None:
    guest = _owner()
    accountish = _owner(principal_type="account", principal_id=guest.principal_id)
    assert parse_owner_cookie(owner_cookie_payload(accountish)) is not None
    raw = owner_cookie_payload(guest)
    version, _encoded, signature = raw.split(".")
    swapped = owner_cookie_payload(accountish).split(".")[1]
    assert parse_owner_cookie(f"{version}.{swapped}.{signature}") is None


def test_expired_signed_cookie_is_rejected() -> None:
    expired = _owner(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    assert parse_owner_cookie(owner_cookie_payload(expired)) is None


def test_owner_from_mapping_is_not_a_cookie_authority() -> None:
    owner = _owner()
    mapped = owner_from_mapping(owner_identity_payload(owner))
    assert mapped is not None
    assert mapped.has_same_identity(owner)
    assert parse_owner_cookie(json.dumps(owner_identity_payload(owner))) is None


def test_set_owner_cookie_is_httponly_and_signed() -> None:
    response = Response()
    set_owner_cookie(response, _owner())
    header = response.headers.get("set-cookie", "")
    assert OWNER_COOKIE in header
    assert "HttpOnly" in header
    assert "v1." in header
    assert signing_secret() is not None


def test_staging_requires_secure_cookie_and_real_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "app_secret_key", "")
    assert signing_secret() is None
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        owner_cookie_payload(_owner())
    assert parse_owner_cookie("v1.not-a-real-payload.not-a-real-signature") is None
    response = Response()
    set_owner_cookie(response, _owner())
    assert OWNER_COOKIE not in response.headers.get("set-cookie", "")


def test_staging_signed_cookie_sets_secure_flag(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "app_secret_key", "staging-owner-cookie-secret-key")
    response = Response()
    set_owner_cookie(response, _owner())
    header = response.headers.get("set-cookie", "")
    assert "Secure" in header
    parsed_header = SimpleCookie()
    parsed_header.load(header)
    assert parse_owner_cookie(parsed_header[OWNER_COOKIE].value) is not None
