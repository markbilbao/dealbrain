"""Opaque rate-limit identity keys.

Storage keys are HMAC digests. They do not contain raw bearer tokens, session
tokens, owner cookies, passwords, or email addresses. Unverified credentials
fall back to the client IP and are not keyed by a token prefix.

Public traffic uses the trusted-proxy client address. Behind the ALB that is
the shopper address the load balancer appended, not the ALB or bridge address.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

from starlette.requests import Request

from app.launch.client_ip import client_host_for_rate_limit
from app.launch.rate_limit_backend import RateLimitUnavailable

_PURPOSE = b"dealbrain-rate-limit-v1"


class _SessionView(Protocol):
    user_id: str
    revoked: bool
    expires_at: datetime


def rate_limit_identity_secret() -> bytes:
    """Shared HMAC key. Staging and production refuse the development constant."""

    from app.consumer.decision_owner import signing_secret

    secret = signing_secret()
    if secret is None:
        raise RateLimitUnavailable("rate limit identity secret is not configured")
    return secret


def opaque_subject_key(action: str, material: str, *, secret: bytes | None = None) -> str:
    """Return ``action:<hex>`` for a sensitive subject.

    ``material`` may be an email or account id. It is not copied into the key.
    """

    key = secret if secret is not None else rate_limit_identity_secret()
    digest = hmac.new(
        key,
        _PURPOSE + b"\x00" + action.encode("utf-8") + b"\x00" + material.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{action}:{digest}"


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def _session_is_active(session: _SessionView, now: datetime) -> bool:
    if session.revoked or not session.user_id:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now


def _default_session_lookup(token_hash: str) -> _SessionView | None:
    from app.core.dependencies import get_user_platform_store

    return get_user_platform_store().sessions.get_by_token_hash(token_hash)


def _default_owner(request: Request):
    from app.consumer.owner_authorization import authorized_owner_from_request

    return authorized_owner_from_request(request)


def client_rate_limit_identity(
    request: Request,
    *,
    session_lookup=None,
    owner_resolver=None,
    secret: bytes | None = None,
    now: datetime | None = None,
    trusted_proxy_cidrs: Sequence[str] | None = None,
) -> str:
    """Per-IP for public traffic. Account HMAC when a session is verified.

    An unverified bearer token or owner cookie does not create its own bucket.
    The IP is the trusted client address, not an untrusted forwarding header.
    """

    clock = now or datetime.now(UTC)
    account_id = _verified_account_id(
        request,
        session_lookup=session_lookup,
        owner_resolver=owner_resolver,
        now=clock,
    )
    if account_id:
        return opaque_subject_key("acct", account_id, secret=secret)
    networks = (
        list(trusted_proxy_cidrs)
        if trusted_proxy_cidrs is not None
        else _configured_trusted_proxy_cidrs()
    )
    host = client_host_for_rate_limit(
        peer=request.client.host if request.client else None,
        forwarded_for=_forwarded_for_header(request),
        trusted_proxy_cidrs=networks,
    )
    return f"ip:{host}"


def _configured_trusted_proxy_cidrs() -> list[str]:
    from app.core.config import settings

    return list(settings.trusted_proxy_cidrs)


def _forwarded_for_header(request: Request) -> str:
    values = [
        value.decode("latin-1")
        for name, value in request.scope.get("headers", [])
        if name == b"x-forwarded-for"
    ]
    return ", ".join(values)


def _verified_account_id(
    request: Request,
    *,
    session_lookup,
    owner_resolver,
    now: datetime,
) -> str | None:
    from app.auth.service import AuthService

    token = _bearer_token(request)
    if token:
        lookup = session_lookup or _default_session_lookup
        try:
            session = lookup(AuthService.hash_token(token))
        except Exception:
            session = None
        if session is not None and _session_is_active(session, now):
            return str(session.user_id)
    resolver = owner_resolver or _default_owner
    try:
        owner = resolver(request)
    except Exception:
        return None
    if owner is None or getattr(owner, "principal_type", None) != "account":
        return None
    principal_id = str(getattr(owner, "principal_id", "") or "")
    return principal_id or None
