"""Trusted client IP for public rate limits behind the AWS ALB.

Proves an ALB-proxied shopper is keyed by the address the load balancer
appended, not by the ALB or a forged forwarding prefix. Sprint 40.3 stays
IMPLEMENTED-NOT-PROVEN. These tests are not staging proof.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from app.auth.service import AuthService
from app.core.config import Settings, settings
from app.core.dependencies import get_rate_limiter
from app.core.validation import validate_settings
from app.domain.entities.shopping_assistant import ConversationOwner
from app.launch.client_ip import TrustedProxyConfigurationError, parse_trusted_networks
from app.launch.rate_limit import RateLimitRule
from app.launch.rate_limit_backend import RateLimitUnavailable
from app.launch.rate_limit_keys import client_rate_limit_identity, opaque_subject_key
from app.main import create_app
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

ROOT = Path(__file__).resolve().parents[2]
_SECRET = b"sprint40-trusted-proxy-client-ip"
_STAGING = ("10.10.0.0/24", "10.10.1.0/24", "172.16.0.0/12")
_PRODUCTION = ("10.20.0.0/24", "10.20.1.0/24", "172.16.0.0/12")
_DOCKER_GATEWAY = "172.18.0.1"
_ALB_A = "10.10.0.20"
_ALB_B = "10.10.1.40"
_SHOPPER_A = "203.0.113.10"
_SHOPPER_B = "203.0.113.11"
_SHOPPER_V6 = "2001:db8::10"


def _request(
    *,
    host: str,
    forwarded: str | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
    port: int = 443,
) -> Request:
    raw = list(headers or [])
    if forwarded is not None:
        raw.append((b"x-forwarded-for", forwarded.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/marketplace/search",
            "raw_path": b"/api/v1/marketplace/search",
            "query_string": b"",
            "headers": raw,
            "client": (host, port),
            "server": ("test", 80),
        }
    )


def _identity(host: str, forwarded: str | None = None, **kwargs: object) -> str:
    return client_rate_limit_identity(
        _request(host=host, forwarded=forwarded),
        session_lookup=kwargs.get("session_lookup", lambda _token_hash: None),
        owner_resolver=kwargs.get("owner_resolver", lambda _request: None),
        secret=_SECRET,
        trusted_proxy_cidrs=kwargs.get("trusted_proxy_cidrs", _STAGING),
    )


def test_alb_proxied_request_uses_the_real_client_not_the_alb() -> None:
    assert _identity(_ALB_A, f"198.51.100.8, {_SHOPPER_A}") == f"ip:{_SHOPPER_A}"
    assert _identity(_DOCKER_GATEWAY, _SHOPPER_A) == f"ip:{_SHOPPER_A}"
    production = _identity("10.20.0.15", _SHOPPER_A, trusted_proxy_cidrs=_PRODUCTION)
    assert production == f"ip:{_SHOPPER_A}"


def test_two_client_ips_behind_one_alb_are_separate() -> None:
    left = _identity(_ALB_A, _SHOPPER_A)
    right = _identity(_ALB_A, _SHOPPER_B)
    assert left == f"ip:{_SHOPPER_A}"
    assert right == f"ip:{_SHOPPER_B}"
    assert left != right


def test_same_client_across_alb_connections_shares_one_key() -> None:
    first = _identity(_ALB_A, f"1.2.3.4, {_SHOPPER_A}")
    second = client_rate_limit_identity(
        _request(host=_ALB_B, forwarded=f"9.9.9.9, {_SHOPPER_A}", port=51000),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: None,
        secret=_SECRET,
        trusted_proxy_cidrs=_STAGING,
    )
    via_docker = _identity(_DOCKER_GATEWAY, _SHOPPER_A)
    assert first == second == via_docker == f"ip:{_SHOPPER_A}"


def test_untrusted_direct_caller_cannot_forge_forwarded_for() -> None:
    forged = _identity("198.51.100.9", "203.0.113.50")
    rotated = _identity("198.51.100.9", "203.0.113.51, 198.51.100.77")
    assert forged == rotated == "ip:198.51.100.9"
    other = _identity("198.51.100.10", "203.0.113.50")
    assert other == "ip:198.51.100.10"


def test_forged_forwarded_chain_does_not_become_the_client() -> None:
    forged_prefix = _identity(_ALB_A, f"203.0.113.50, 198.51.100.8, {_SHOPPER_A}")
    leftmost_trusted = _identity(_ALB_A, f"10.10.0.5, {_SHOPPER_A}")
    assert forged_prefix == leftmost_trusted == f"ip:{_SHOPPER_A}"
    all_trusted = _identity(_DOCKER_GATEWAY, "10.10.0.5, 10.10.1.8")
    assert all_trusted == f"ip:{_DOCKER_GATEWAY}"
    malformed_tail = _identity(_ALB_A, f"{_SHOPPER_A}, not-an-ip")
    assert malformed_tail == f"ip:{_ALB_A}"


def test_private_subnet_peer_is_not_a_trusted_proxy() -> None:
    """The API host subnet is not an ALB subnet and cannot supply the client."""

    identity = _identity("10.10.10.20", _SHOPPER_A)
    assert identity == "ip:10.10.10.20"


def test_ipv4_and_ipv6_clients_are_canonical() -> None:
    ipv4 = _identity(_ALB_A, _SHOPPER_A)
    mapped = _identity(_ALB_A, f"::ffff:{_SHOPPER_A}")
    expanded = _identity(_ALB_A, "2001:0db8:0000:0000:0000:0000:0000:0010")
    compressed = _identity(_ALB_A, _SHOPPER_V6)
    assert ipv4 == mapped == f"ip:{_SHOPPER_A}"
    assert expanded == compressed == f"ip:{_SHOPPER_V6}"
    direct_v6 = _identity("2001:db8::20", "203.0.113.50")
    assert direct_v6 == "ip:2001:db8::20"


def test_verified_account_ignores_proxy_and_client_ip() -> None:
    token = "verified-bearer-token-value"
    future = datetime.now(UTC) + timedelta(hours=1)
    session = SimpleNamespace(user_id="user-42", revoked=False, expires_at=future)
    identity = client_rate_limit_identity(
        _request(
            host=_ALB_A,
            forwarded=_SHOPPER_A,
            headers=[(b"authorization", f"Bearer {token}".encode())],
        ),
        session_lookup=lambda token_hash: (
            session if token_hash == AuthService.hash_token(token) else None
        ),
        owner_resolver=lambda _request: None,
        secret=_SECRET,
        trusted_proxy_cidrs=_STAGING,
    )
    assert identity == opaque_subject_key("acct", "user-42", secret=_SECRET)
    assert _SHOPPER_A not in identity
    assert token not in identity


def test_invalid_bearer_and_guest_cookie_fall_back_to_the_trusted_client_ip() -> None:
    token = "not-a-real-session-token"
    cookie = "v1.forged-owner-cookie.signature"
    invalid = client_rate_limit_identity(
        _request(
            host=_DOCKER_GATEWAY,
            forwarded=f"1.2.3.4, {_SHOPPER_B}",
            headers=[
                (b"authorization", f"Bearer {token}".encode()),
                (b"cookie", f"piqsavi_decision_owner={cookie}".encode()),
            ],
        ),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: None,
        secret=_SECRET,
        trusted_proxy_cidrs=_STAGING,
    )
    assert invalid == f"ip:{_SHOPPER_B}"
    assert token not in invalid
    guest = ConversationOwner(
        principal_type="guest",
        principal_id="guest-secret",
        session_id="guest-session",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    guest_identity = client_rate_limit_identity(
        _request(host=_ALB_A, forwarded=_SHOPPER_A),
        session_lookup=lambda _token_hash: None,
        owner_resolver=lambda _request: guest,
        secret=_SECRET,
        trusted_proxy_cidrs=_STAGING,
    )
    assert guest_identity == f"ip:{_SHOPPER_A}"
    assert "guest-secret" not in guest_identity


def test_wildcard_and_default_route_are_rejected() -> None:
    for value in ("*", "0.0.0.0/0", "::/0", "10.10.0.1/24", "not-a-cidr"):
        with pytest.raises(TrustedProxyConfigurationError):
            parse_trusted_networks([value])
    staging = validate_settings(
        Settings(_env_file=None, APP_ENV="staging", TRUSTED_PROXY_CIDRS="*")
    )
    assert any("TRUSTED_PROXY_CIDRS" in error for error in staging.errors)
    missing = validate_settings(Settings(_env_file=None, APP_ENV="production"))
    assert any("TRUSTED_PROXY_CIDRS" in error for error in missing.errors)
    development = validate_settings(
        Settings(
            _env_file=None,
            APP_ENV="development",
            DATABASE_URL="postgresql+asyncpg://dealbrain:dealbrain@localhost:5432/dealbrain",
            CORS_ORIGINS="http://localhost:8000",
        )
    )
    assert development.ok is True


async def _post(app, peer: str, forwarded: str | None, port: int) -> httpx.Response:
    headers = {}
    if forwarded is not None:
        headers["X-Forwarded-For"] = forwarded
    transport = httpx.ASGITransport(app=app, client=(peer, port))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/api/v1/auth/login",
            json={"email": "a@b.com", "password": "x"},
            headers=headers,
        )


async def test_http_limits_follow_the_real_client_and_keep_429(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", list(_STAGING))
    limiter = get_rate_limiter()
    original = limiter._rules["login"]
    previous_enabled = limiter.enabled
    limiter._rules["login"] = RateLimitRule("login", 1, 60)
    limiter.set_enabled(True)
    limiter.reset()
    app = create_app()
    try:
        first = await _post(app, _ALB_A, _SHOPPER_A, 41001)
        repeated = await _post(app, _ALB_B, f"198.51.100.8, {_SHOPPER_A}", 41002)
        other = await _post(app, _DOCKER_GATEWAY, _SHOPPER_B, 41003)
        assert first.status_code != 429
        assert repeated.status_code == 429
        body = repeated.json()
        assert body["error"] == "rate_limited"
        assert body["status_code"] == 429
        assert body["detail"] == "Rate limit exceeded for login"
        assert body["details"]["bucket"] == "login"
        assert body["details"]["limit"] == 1
        assert repeated.headers["Retry-After"] == str(body["details"]["retry_after_seconds"])
        assert repeated.headers["X-RateLimit-Limit"] == "1"
        assert repeated.headers["X-RateLimit-Remaining"] == "0"
        assert repeated.headers["X-RateLimit-Bucket"] == "login"
        assert other.status_code != 429
        forged = await _post(app, "198.51.100.9", "203.0.113.80", 41004)
        forged_again = await _post(app, "198.51.100.9", "203.0.113.81", 41005)
        assert forged.status_code != 429
        assert forged_again.status_code == 429
    finally:
        limiter._rules["login"] = original
        limiter.set_enabled(previous_enabled)
        limiter.reset()


async def test_http_store_failure_stays_503_for_a_proxied_client(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", list(_STAGING))

    class _Boom:
        def consume(self, **kwargs: object):
            raise RateLimitUnavailable("down")

        def reset(self, **kwargs: object) -> None:
            raise RateLimitUnavailable("down")

    limiter = get_rate_limiter()
    previous_store = limiter._store
    previous_enabled = limiter.enabled
    limiter.set_enabled(True)
    limiter._store = _Boom()
    app = create_app()
    try:
        blocked = await _post(app, _ALB_A, _SHOPPER_A, 42001)
        health = httpx.ASGITransport(app=app, client=(_ALB_A, 9))
        async with httpx.AsyncClient(transport=health, base_url="http://test") as client:
            live = await client.get("/live")
        assert live.status_code == 200
        assert blocked.status_code == 503
        body = blocked.json()
        assert body["error"] == "rate_limit_unavailable"
        assert body["status_code"] == 503
        assert body["details"]["bucket"] == "login"
        assert blocked.headers["Retry-After"] == "1"
        assert "X-RateLimit-Remaining" not in blocked.headers
    finally:
        limiter._store = previous_store
        limiter.set_enabled(previous_enabled)


def test_uvicorn_proxy_headers_and_the_app_agree() -> None:
    seen: dict[str, str] = {}

    async def inner(scope, receive, send) -> None:
        del receive, send
        seen["identity"] = client_rate_limit_identity(
            Request(scope),
            session_lookup=lambda _token_hash: None,
            owner_resolver=lambda _request: None,
            secret=_SECRET,
            trusted_proxy_cidrs=_STAGING,
        )

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message) -> None:
        return None

    wrapped = ProxyHeadersMiddleware(inner, trusted_hosts=list(_STAGING))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/marketplace/search",
        "raw_path": b"/api/v1/marketplace/search",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", f"1.2.3.4, {_SHOPPER_A}".encode())],
        "client": (_DOCKER_GATEWAY, 40000),
        "server": ("test", 80),
    }
    asyncio.run(wrapped(scope, receive, send))
    assert seen["identity"] == f"ip:{_SHOPPER_A}"


def _public_subnets(environment: str) -> list[str]:
    text = (ROOT / "infra" / "terraform" / "environments" / environment / "variables.tf").read_text(
        encoding="utf-8"
    )
    match = re.search(r'variable "public_subnet_cidrs".*?default\s*=\s*\[(.*?)\]', text, re.S)
    assert match is not None
    return re.findall(r'"([^"]+)"', match.group(1))


def _compose_proxy_lists(name: str) -> tuple[str, str]:
    text = (ROOT / "infra" / "compose" / name).read_text(encoding="utf-8")
    trusted = re.search(r'TRUSTED_PROXY_CIDRS:\s*"([^"]+)"', text)
    forwarded = re.search(r'FORWARDED_ALLOW_IPS:\s*"([^"]+)"', text)
    assert trusted is not None and forwarded is not None
    return trusted.group(1), forwarded.group(1)


def test_compose_trusts_the_alb_public_subnets_and_not_every_address() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FORWARDED_ALLOW_IPS=*" not in dockerfile
    assert "--forwarded-allow-ips=*" not in dockerfile
    alb = (ROOT / "infra" / "terraform" / "modules" / "alb" / "main.tf").read_text(encoding="utf-8")
    assert 'load_balancer_type = "application"' in alb
    assert "dualstack" not in alb
    groups = (ROOT / "infra" / "terraform" / "modules" / "security_groups" / "main.tf").read_text(
        encoding="utf-8"
    )
    assert "referenced_security_group_id = aws_security_group.alb.id" in groups
    assert "from_port                    = 8000" in groups
    for script in ("staging.sh", "production.sh"):
        user_data = (ROOT / "infra" / "ec2" / "user_data" / script).read_text(encoding="utf-8")
        assert "userland-proxy" not in user_data

    expected = {
        "docker-compose.staging.yml": _public_subnets("staging"),
        "docker-compose.production.yml": _public_subnets("production"),
    }
    for filename, subnets in expected.items():
        trusted, forwarded = _compose_proxy_lists(filename)
        assert trusted == forwarded
        assert "*" not in trusted
        assert "0.0.0.0/0" not in trusted
        networks = [item.strip() for item in trusted.split(",")]
        assert networks[:-1] == subnets
        assert networks[-1] == "172.16.0.0/12"
        whole_vpc = "10.10.0.0/16" if "staging" in filename else "10.20.0.0/16"
        assert whole_vpc not in networks
