"""Sprint 40.4 origin policy for decision-owner cookie mutations.

Missing Origin is fail-closed on the covered routes. The finding stays
IMPLEMENTED-NOT-PROVEN until staging exercises the control.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.consumer.cookie_origin import (
    COOKIE_AUTHORIZED_MUTATION_PATHS,
    COOKIE_SESSION_MUTATION_PATHS,
    MISSING_ORIGIN_POLICY,
    ORIGIN_REJECTION_ERROR,
    ORIGIN_REJECTION_MESSAGE,
    PREFERENCE_COOKIE_MUTATION_PATHS,
    OwnerCookieOriginMiddleware,
    configured_trusted_origins,
    cookie_origin_applies,
    evaluate_cookie_origin,
    trusted_cookie_origins,
)
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.core.config import Settings, settings
from app.core.dependencies import get_shopping_conversation_repository
from app.domain.entities.shopping_assistant import ConversationOwner
from app.main import create_app
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "app" / "consumer" / "cookie_origin.py"
SAME_ORIGIN = "http://localhost:8000"
FRONTEND_ORIGIN = "http://localhost:3000"
CANONICAL = "https://piqsavi.com"
FOREIGN = "https://evil.example"
QUERY = "/api/v1/shopping-assistant/query"
CLAIM = "/consumer/claim-decision"
CLEAR = "/account/clear-device"
FEEDBACK = "/api/v1/feedback/reports"
ANALYTICS = "/api/v1/analytics/events"
MARKET = "/consumer/shopping-market"
LOCATION = "/consumer/location"
PREFERENCE = "/api/v1/privacy/tracking-preference"


def _guest(principal_id: str = "guest-sprint40-4") -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )


def _cookie(owner: ConversationOwner | None = None) -> dict[str, str]:
    return {OWNER_COOKIE: owner_cookie_payload(owner or _guest())}


def _assert_rejected(response, *, echoed: str = "") -> None:
    assert response.status_code == 403
    body = response.json()
    assert body["error"] == ORIGIN_REJECTION_ERROR
    assert body["message"] == ORIGIN_REJECTION_MESSAGE
    assert body["detail"] == ORIGIN_REJECTION_MESSAGE
    assert body["status_code"] == 403
    text = response.text.lower()
    assert "cookie" not in text
    assert "session" not in text
    assert "principal" not in text
    assert "signature" not in text
    assert OWNER_COOKIE not in response.text
    if echoed:
        assert echoed not in response.text


async def _register(client: AsyncClient, email: str) -> dict:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "display_name": "Sprint404",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert registered.status_code == 201
    return registered.json()


def test_missing_origin_policy_is_fail_closed() -> None:
    assert MISSING_ORIGIN_POLICY == "fail_closed"
    verdict = evaluate_cookie_origin(None, trusted=frozenset({SAME_ORIGIN}))
    assert verdict.allowed is False
    assert verdict.reason == "missing"


def test_trusted_origins_come_from_server_config_not_a_wildcard() -> None:
    trusted = trusted_cookie_origins(
        public_app_base_url="https://piqsavi.com/shop",
        cors_origins=["https://app.piqsavi.com", "*", "https://user:pass@piqsavi.com", ""],
        require_https=True,
    )
    assert trusted == frozenset({CANONICAL, "https://app.piqsavi.com"})
    http_dev = trusted_cookie_origins(
        public_app_base_url="",
        cors_origins=[SAME_ORIGIN, FRONTEND_ORIGIN, "*"],
        require_https=False,
    )
    assert http_dev == frozenset({SAME_ORIGIN, FRONTEND_ORIGIN})
    staging = trusted_cookie_origins(
        public_app_base_url=CANONICAL,
        cors_origins=[SAME_ORIGIN, CANONICAL],
        require_https=True,
    )
    assert staging == frozenset({CANONICAL})


def test_origin_classifier_rejects_null_malformed_and_foreign() -> None:
    trusted = frozenset({CANONICAL, SAME_ORIGIN})
    assert evaluate_cookie_origin("null", trusted=trusted).reason == "null"
    assert evaluate_cookie_origin("NULL", trusted=trusted).reason == "malformed"
    assert evaluate_cookie_origin("https://", trusted=trusted).reason == "malformed"
    assert evaluate_cookie_origin("https://user:pass@piqsavi.com", trusted=trusted).reason == (
        "malformed"
    )
    assert evaluate_cookie_origin("https://piqsavi.com/results", trusted=trusted).reason == (
        "malformed"
    )
    assert evaluate_cookie_origin("https://piqsavi.com.evil.example", trusted=trusted).reason == (
        "foreign"
    )
    assert evaluate_cookie_origin(FOREIGN, trusted=trusted).reason == "foreign"
    assert evaluate_cookie_origin("https://piqsavi.com:443", trusted=trusted).allowed is True
    assert evaluate_cookie_origin(SAME_ORIGIN, trusted=trusted).allowed is True


def test_policy_path_inventory_is_exact() -> None:
    assert frozenset({QUERY, CLAIM, FEEDBACK, ANALYTICS}) == COOKIE_AUTHORIZED_MUTATION_PATHS
    assert frozenset({CLEAR}) == COOKIE_SESSION_MUTATION_PATHS
    assert PREFERENCE_COOKIE_MUTATION_PATHS.isdisjoint(COOKIE_AUTHORIZED_MUTATION_PATHS)
    assert cookie_origin_applies("POST", QUERY, owner_cookie_present=False) is False
    assert cookie_origin_applies("POST", QUERY, owner_cookie_present=True) is True
    assert cookie_origin_applies("GET", QUERY, owner_cookie_present=True) is False
    assert cookie_origin_applies("POST", CLEAR, owner_cookie_present=False) is True
    assert cookie_origin_applies("POST", "/api/v1/auth/logout", owner_cookie_present=True) is False
    assert cookie_origin_applies("POST", MARKET, owner_cookie_present=True) is False
    source = POLICY.read_text(encoding="utf-8")
    assert "request.url" not in source
    assert 'headers.get("host")' not in source
    assert 'headers.get("referer")' not in source
    assert "Host" in source


def test_development_config_trusts_the_canonical_and_frontend_origins() -> None:
    trusted = configured_trusted_origins()
    assert SAME_ORIGIN in trusted
    assert FRONTEND_ORIGIN in trusted
    assert Settings.model_fields["cors_origins"].default == [FRONTEND_ORIGIN, SAME_ORIGIN]


def test_cors_allow_list_is_not_widened() -> None:
    app = create_app()
    cors = [layer for layer in app.user_middleware if layer.cls is CORSMiddleware]
    assert len(cors) == 1
    assert cors[0].kwargs["allow_origins"] == list(settings.cors_origins)
    assert cors[0].kwargs["allow_credentials"] is True
    assert "*" not in cors[0].kwargs["allow_origins"]
    classes = [layer.cls for layer in app.user_middleware]
    assert classes[0] is CORSMiddleware
    assert classes[1].__name__ == "RequestLoggingMiddleware"
    assert classes[2] is OwnerCookieOriginMiddleware
    assert classes[3].__name__ == "RateLimitMiddleware"
    assert StarletteCORSMiddleware is CORSMiddleware


@pytest.mark.asyncio
async def test_same_origin_and_configured_frontend_owner_queries_succeed(
    client: AsyncClient,
) -> None:
    cookies = _cookie()
    same = await client.post(
        QUERY,
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
        headers={"Origin": SAME_ORIGIN},
        cookies=cookies,
    )
    frontend = await client.post(
        QUERY,
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
        headers={"Origin": FRONTEND_ORIGIN},
        cookies=cookies,
    )
    assert same.status_code == 200, same.text
    assert frontend.status_code == 200, frontend.text
    assert same.json()["conversation_id"]
    assert "X-CSRF-Token" not in same.request.headers


@pytest.mark.asyncio
async def test_owner_cookie_query_rejects_foreign_null_malformed_and_missing_origin(
    client: AsyncClient,
) -> None:
    cookies = _cookie()
    body = {"query": "What is the best gaming laptop under 60000?", "mode": "economy"}
    foreign = await client.post(QUERY, json=body, headers={"Origin": FOREIGN}, cookies=cookies)
    opaque = await client.post(QUERY, json=body, headers={"Origin": "null"}, cookies=cookies)
    malformed = await client.post(
        QUERY,
        json=body,
        headers={"Origin": "https://user:pass@localhost:8000"},
        cookies=cookies,
    )
    missing = await client.post(QUERY, json=body, cookies=cookies)
    referred = await client.post(
        QUERY,
        json=body,
        headers={"Referer": f"{SAME_ORIGIN}/results/headphones-standard"},
        cookies=cookies,
    )
    for response in (foreign, opaque, malformed, missing, referred):
        _assert_rejected(response)
    _assert_rejected(foreign, echoed=FOREIGN)
    _assert_rejected(malformed, echoed="user:pass")


@pytest.mark.asyncio
async def test_forged_host_cannot_make_a_foreign_origin_trusted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_app_base_url", CANONICAL)
    monkeypatch.setattr(settings, "cors_origins", [CANONICAL])
    cookies = _cookie()
    body = {"query": "What is the best gaming laptop under 60000?", "mode": "economy"}
    forged = await client.post(
        QUERY,
        json=body,
        headers={"Host": "evil.example", "Origin": FOREIGN},
        cookies=cookies,
    )
    host_matches_victim = await client.post(
        QUERY,
        json=body,
        headers={"Host": "piqsavi.com", "Origin": FOREIGN},
        cookies=cookies,
    )
    trusted_origin_forged_host = await client.post(
        QUERY,
        json=body,
        headers={"Host": "evil.example", "Origin": CANONICAL},
        cookies=cookies,
    )
    _assert_rejected(forged, echoed="evil.example")
    _assert_rejected(host_matches_victim, echoed=FOREIGN)
    assert trusted_origin_forged_host.status_code == 200, trusted_origin_forged_host.text


@pytest.mark.asyncio
async def test_staging_trusts_https_config_only(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cookies = {OWNER_COOKIE: "present"}
    monkeypatch.setattr(settings, "app_env", "staging")
    monkeypatch.setattr(settings, "public_app_base_url", CANONICAL)
    monkeypatch.setattr(settings, "cors_origins", [CANONICAL, SAME_ORIGIN])
    body = {"query": "headphones", "mode": "economy"}
    http_origin = await client.post(
        QUERY,
        json=body,
        headers={"Origin": SAME_ORIGIN},
        cookies=cookies,
    )
    https_origin = await client.post(
        QUERY,
        json=body,
        headers={"Origin": CANONICAL},
        cookies=cookies,
    )
    _assert_rejected(http_origin)
    assert https_origin.status_code == 200, https_origin.text


@pytest.mark.asyncio
async def test_bearer_only_and_cookieless_posts_do_not_require_origin(
    client: AsyncClient,
) -> None:
    anonymous = await client.post(
        QUERY,
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
        headers={"Origin": FOREIGN},
    )
    assert anonymous.status_code == 200, anonymous.text
    registered = await _register(client, "sprint40-4-logout@example.invalid")
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
        cookies=_cookie(),
    )
    assert logout.status_code == 204
    assert logout.headers.get("content-type") != "application/json" or "origin_rejected" not in (
        logout.text
    )


@pytest.mark.asyncio
async def test_shopping_assistant_cookie_paths_are_protected(client: AsyncClient) -> None:
    cookies = _cookie()
    started = await client.post(
        QUERY,
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
        headers={"Origin": SAME_ORIGIN},
        cookies=cookies,
    )
    assert started.status_code == 200, started.text
    conversation_id = started.json()["conversation_id"]
    repository = get_shopping_conversation_repository()
    payloads = (
        {"query": "Show me a cheaper one", "conversation_id": conversation_id, "mode": "economy"},
        {
            "query": "Comfort matters more.",
            "decision_id": "headphones-standard",
            "surface": "results",
        },
        {
            "query": "Yes, research that",
            "decision_id": "headphones-standard",
            "conversation_id": conversation_id,
            "surface": "results",
            "proposal_id": "proposal-1",
            "proposal_version": 1,
        },
    )
    for payload in payloads:
        context = repository.get(conversation_id)
        assert context is not None
        turns = len(context.turns)
        rejected = await client.post(
            QUERY,
            json=payload,
            headers={"Origin": FOREIGN},
            cookies=cookies,
        )
        _assert_rejected(rejected, echoed=FOREIGN)
        unchanged = repository.get(conversation_id)
        assert unchanged is not None
        assert len(unchanged.turns) == turns
        allowed = await client.post(
            QUERY,
            json=payload,
            headers={"Origin": SAME_ORIGIN},
            cookies=cookies,
        )
        assert allowed.status_code != 403, allowed.text


@pytest.mark.asyncio
async def test_foreign_origin_does_not_continue_an_owned_conversation(
    client: AsyncClient,
) -> None:
    cookies = _cookie()
    started = await client.post(
        QUERY,
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
        headers={"Origin": SAME_ORIGIN},
        cookies=cookies,
    )
    conversation_id = started.json()["conversation_id"]
    repository = get_shopping_conversation_repository()
    context = repository.get(conversation_id)
    assert context is not None
    before = len(context.turns)
    rejected = await client.post(
        QUERY,
        json={
            "query": "What about a quieter keyboard?",
            "conversation_id": conversation_id,
            "mode": "economy",
        },
        headers={"Origin": FOREIGN},
        cookies=cookies,
    )
    _assert_rejected(rejected)
    unchanged = repository.get(conversation_id)
    assert unchanged is not None
    assert len(unchanged.turns) == before


@pytest.mark.asyncio
async def test_claim_origin_runs_before_signed_owner_authorization(client: AsyncClient) -> None:
    guest = _guest("guest-sprint40-4-claim")
    conversations = get_shopping_conversation_repository()
    created = conversations.create(owner=guest)
    registered = await _register(client, "sprint40-4-claim@example.invalid")
    token = registered["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    body = {"conversation_id": created.conversation_id, "decision_id": "headphones-standard"}
    foreign = await client.post(
        CLAIM,
        json=body,
        headers={**headers, "Origin": FOREIGN},
        cookies=_cookie(guest),
    )
    _assert_rejected(foreign, echoed=FOREIGN)
    assert conversations.get_for_owner(created.conversation_id, guest) is not None
    forged = owner_cookie_payload(guest)
    version, _encoded, signature = forged.split(".")
    tampered = f"{version}.aaaa.{signature}"
    authorized_reject = await client.post(
        CLAIM,
        json=body,
        headers={**headers, "Origin": SAME_ORIGIN},
        cookies={OWNER_COOKIE: tampered},
    )
    assert authorized_reject.status_code == 200
    assert authorized_reject.json()["claimed"] is False
    claimed = await client.post(
        CLAIM,
        json=body,
        headers={**headers, "Origin": SAME_ORIGIN},
        cookies=_cookie(guest),
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["claimed"] is True
    client.cookies.clear()
    no_cookie = await client.post(CLAIM, json=body, headers=headers)
    assert no_cookie.status_code == 200
    assert no_cookie.json()["claimed"] is False
    assert no_cookie.json()["reason"] == "missing_guest_owner"


@pytest.mark.asyncio
async def test_clear_device_requires_a_trusted_origin(client: AsyncClient) -> None:
    missing = await client.post(CLEAR)
    foreign = await client.post(CLEAR, headers={"Origin": FOREIGN}, cookies=_cookie())
    opaque = await client.post(CLEAR, headers={"Origin": "null"})
    for response in (missing, foreign, opaque):
        _assert_rejected(response)
        assert OWNER_COOKIE not in response.headers.get("set-cookie", "")
    cleared = await client.post(CLEAR, headers={"Origin": SAME_ORIGIN}, cookies=_cookie())
    assert cleared.status_code == 200, cleared.text
    header = cleared.headers.get("set-cookie", "")
    assert OWNER_COOKIE in header
    assert "max-age=0" in header.lower()


@pytest.mark.asyncio
async def test_feedback_and_analytics_cookie_posts_are_protected(client: AsyncClient) -> None:
    # Invalid bodies stop in route validation. Origin coverage must not open PostgreSQL.
    cookies = _cookie()
    cases = (
        (FEEDBACK, {"category": "not-a-category"}, "invalid_category"),
        (ANALYTICS, {"event_name": "not-a-real-event"}, "unknown_event"),
    )
    for path, body, detail in cases:
        rejected = await client.post(path, json=body, headers={"Origin": FOREIGN}, cookies=cookies)
        _assert_rejected(rejected, echoed=FOREIGN)
        allowed = await client.post(
            path,
            json=body,
            headers={"Origin": SAME_ORIGIN},
            cookies=cookies,
        )
        assert allowed.status_code == 400, allowed.text
        assert allowed.json()["detail"] == detail
        anonymous = await client.post(path, json=body, headers={"Origin": FOREIGN})
        assert anonymous.status_code == 400, anonymous.text
        assert anonymous.json()["detail"] == detail


@pytest.mark.asyncio
async def test_preference_routes_are_not_treated_as_owner_authorization(
    client: AsyncClient,
) -> None:
    cookies = _cookie()
    market = await client.post(
        MARKET,
        json={
            "country_code": "PH",
            "next": "/results/headphones-standard",
            "decision_id": "headphones-standard",
        },
        headers={"Origin": FOREIGN},
        cookies=cookies,
    )
    location = await client.post(
        LOCATION,
        json={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        headers={"Origin": FOREIGN},
        cookies=cookies,
    )
    preference = await client.post(
        PREFERENCE,
        json={"choice": "essential_only"},
        headers={"Origin": FOREIGN},
        cookies=cookies,
    )
    for response in (market, location, preference):
        assert response.status_code != 403, response.text
        if response.headers.get("content-type", "").startswith("application/json"):
            assert response.json().get("error") != ORIGIN_REJECTION_ERROR


@pytest.mark.asyncio
async def test_cors_preflight_does_not_reflect_a_foreign_origin(client: AsyncClient) -> None:
    foreign = await client.options(
        QUERY,
        headers={"Origin": FOREIGN, "Access-Control-Request-Method": "POST"},
    )
    allowed = await client.options(
        QUERY,
        headers={"Origin": SAME_ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert foreign.headers.get("access-control-allow-origin") not in {FOREIGN, "*"}
    assert allowed.headers.get("access-control-allow-origin") == SAME_ORIGIN


def test_sprint_40_4_record_does_not_close_the_sprint() -> None:
    evidence_path = ROOT / "docs/roadmap/evidence/SPRINT_40_4_COOKIE_ORIGIN_POLICY_2026-10-10.md"
    evidence = evidence_path.read_text(encoding="utf-8")
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    assert "**Status:** Planned" in sprint
    assert "06a2c9da40c2bc49bf361569e887e64b1dccb8a6" in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "Not ENGINEERING COMPLETE" in evidence
    assert "No Included requirement is PROVEN." in evidence
    assert "Fail-closed" in evidence
    assert "MISSING_ORIGIN_POLICY" in evidence
    assert "not closed and not PROVEN" in evidence
    assert "CSP `'unsafe-inline'`" in evidence
    assert "URL validation / SSRF" in evidence
    assert "R6 stays PARTIAL" in evidence
    assert "Class C count remains 19" in evidence
    assert "selected next engineering slice remains NONE" in evidence
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "Routing stays 0." in evidence
    assert "Sprint 40.4" in sprint
    assert "ENGINEERING COMPLETE" not in evidence.split("Not ENGINEERING COMPLETE")[0]
