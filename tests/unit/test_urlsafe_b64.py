"""Strict URL-safe Base64 keeps signed cookies and rejects malformed input."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from app.analytics.preference import (
    apply_tracking_choice,
    preference_cookie_claims,
    read_tracking_preference,
)
from app.consumer.decision_owner import (
    _COOKIE_VERSION,
    _b64encode,
    owner_cookie_payload,
    parse_owner_cookie,
    signing_secret,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.security.base64url import decode_urlsafe_b64, encode_urlsafe_b64
from starlette.responses import Response

NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


def _owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-b64",
        session_id="session-b64",
        expires_at=NOW + timedelta(hours=1),
    )


def test_valid_urlsafe_values_roundtrip() -> None:
    raw = b'{"choice":"essential_only","ok":true}'
    encoded = encode_urlsafe_b64(raw)
    assert "+" not in encoded
    assert "/" not in encoded
    assert "=" not in encoded
    assert decode_urlsafe_b64(encoded) == raw
    padded = base64.urlsafe_b64encode(raw).decode("ascii")
    assert decode_urlsafe_b64(padded) == raw


def test_standard_alphabet_and_trailing_data_are_rejected() -> None:
    token = encode_urlsafe_b64(b"a")
    assert token == "YQ"
    with_plus = token.replace("Y", "+") if "Y" in token else "+" + token
    assert decode_fails(with_plus)
    assert decode_fails(token[:-1] + "/")
    assert decode_fails("YQ==YQ==")
    assert decode_fails("YQ==YWI=")
    assert decode_fails("YQ=")
    assert decode_fails("Y")
    assert decode_fails("YQ@@")
    assert decode_fails("")


def decode_fails(value: str) -> bool:
    try:
        decode_urlsafe_b64(value)
    except ValueError:
        return True
    return False


def test_signed_owner_cookie_survives_and_tampering_fails(monkeypatch) -> None:
    raw = owner_cookie_payload(_owner())
    parsed = parse_owner_cookie(raw)
    assert parsed is not None
    assert parsed.principal_id == "guest-b64"
    version, encoded, signature = raw.split(".")
    flipped = "A" if signature[0] != "A" else "B"
    assert parse_owner_cookie(f"{version}.{encoded}.{flipped}{signature[1:]}") is None
    assert parse_owner_cookie(f"{version}.{encoded}+.{signature}") is None
    assert parse_owner_cookie(f"{version}.{encoded}/.{signature}") is None
    assert parse_owner_cookie(f"{version}.{encoded}YQ==.{signature}") is None

    calls: list[str] = []

    def refuse(value: str) -> bytes:
        calls.append(value)
        raise AssertionError("payload was decoded before the signature check")

    monkeypatch.setattr("app.consumer.decision_owner._b64decode", refuse)
    assert parse_owner_cookie(f"{version}.{encoded}.{flipped}{signature[1:]}") is None
    assert calls == []


def test_signature_over_rejected_base64_still_fails_closed(monkeypatch) -> None:
    secret = signing_secret()
    assert secret is not None
    encoded = "YQ+"
    signing_input = f"{_COOKIE_VERSION}.{encoded}".encode("ascii")
    signature = _b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    seen: list[str] = []
    real_decode = decode_urlsafe_b64

    def watch(value: str) -> bytes:
        seen.append(value)
        return real_decode(value)

    monkeypatch.setattr("app.consumer.decision_owner._b64decode", watch)
    assert parse_owner_cookie(f"{_COOKIE_VERSION}.{encoded}.{signature}") is None
    assert seen == [encoded]


def test_signed_preference_cookie_survives_and_malformed_payloads_fail(monkeypatch) -> None:
    response = Response()
    preference, _subject = apply_tracking_choice(
        response,
        "essential_only",
        existing_subject=None,
        now=NOW,
    )
    raw = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
    claims = preference_cookie_claims(raw)
    assert claims is not None
    assert claims["choice"] == "essential_only"
    stored = read_tracking_preference(raw)
    assert stored.choice == preference.choice
    prefix, encoded, signature = raw.split(".")
    flipped = "A" if signature[0] != "A" else "B"
    assert preference_cookie_claims(f"{prefix}.{encoded}.{flipped}{signature[1:]}") is None
    assert preference_cookie_claims(f"{prefix}.{encoded}+.{signature}") is None
    assert preference_cookie_claims(f"{prefix}.YQ==YQ==.{signature}") is None
    assert preference_cookie_claims(f"{prefix}.YQ=.{signature}") is None

    calls: list[str] = []

    def refuse(value: str) -> bytes:
        calls.append(value)
        raise AssertionError("payload was decoded before the signature check")

    monkeypatch.setattr("app.analytics.preference._b64decode", refuse)
    assert preference_cookie_claims(f"{prefix}.{encoded}.{flipped}{signature[1:]}") is None
    assert calls == []
