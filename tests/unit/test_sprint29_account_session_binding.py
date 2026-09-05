"""Account owner cookies require an active SessionRepository session."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.consumer.decision_owner import (
    OWNER_COOKIE,
    owner_cookie_payload,
    parse_owner_cookie,
)
from app.consumer.guest_continuity import account_owner_from_session
from app.consumer.owner_authorization import (
    authorize_conversation_owner,
    authorized_owner_from_cookie,
)
from app.core.dependencies import (
    get_db,
    get_shopping_conversation_repository,
    get_shopping_decision_snapshot_repository,
    get_user_platform_store,
)
from app.domain.entities.session_refinement import (
    SessionPriorities,
    SessionRecommendationRefinement,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.entities.user_platform import User, UserSession
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.main import create_app
from app.user.memory import InMemoryUserPlatformStore
from httpx import ASGITransport, AsyncClient

from tests.unit.test_canonical_uuid_consumer_presentation import (
    BOSE_ID,
    SONY_ID,
    _attrs,
    _economics_snapshot,
)
from tests.unit.test_canonical_uuid_consumer_presentation import (
    DECISION_ID as CANONICAL_UUID,
)
from tests.unit.test_canonical_uuid_consumer_presentation import (
    _owner as _guest_owner,
)

PASSWORD = "Password123"
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


def _session(
    *,
    session_id: str = "session-account-binding",
    user_id: str = "user-account-binding",
    revoked: bool = False,
    expires_at: datetime | None = None,
) -> UserSession:
    return UserSession(
        session_id=session_id,
        user_id=user_id,
        token_hash=f"hash-{session_id}",
        created_at=NOW,
        expires_at=expires_at or NOW + timedelta(hours=2),
        revoked=revoked,
    )


def _user(*, user_id: str = "user-account-binding", active: bool = True) -> User:
    return User(
        user_id=user_id,
        email=f"{user_id}@example.invalid",
        password_hash="hashed",
        display_name=user_id,
        is_active=active,
        created_at=NOW,
        updated_at=NOW,
    )


def _account_owner(
    *,
    user_id: str = "user-account-binding",
    session_id: str = "session-account-binding",
    expires_at: datetime | None = None,
) -> ConversationOwner:
    return account_owner_from_session(
        user_id=user_id,
        session_id=session_id,
        expires_at=expires_at or NOW + timedelta(days=1),
    )


def _store_with_session(
    session: UserSession,
    user: User | None = None,
) -> InMemoryUserPlatformStore:
    store = InMemoryUserPlatformStore()
    store.users.save(user or _user(user_id=session.user_id))
    store.sessions.save(session)
    return store


def test_guest_signed_cookie_does_not_need_a_session() -> None:
    guest = _guest_owner("guest-session-binding")
    store = InMemoryUserPlatformStore()
    authorized = authorize_conversation_owner(
        guest,
        sessions=store.sessions,
        users=store.users,
    )
    assert authorized is not None
    assert authorized.has_same_identity(guest)
    raw = owner_cookie_payload(guest)
    assert authorized_owner_from_cookie(raw, sessions=store.sessions) is not None


def test_account_cookie_without_session_authority_fails_closed() -> None:
    owner = _account_owner()
    assert parse_owner_cookie(owner_cookie_payload(owner)) is not None
    assert authorize_conversation_owner(owner, sessions=None, users=None) is None
    empty = InMemoryUserPlatformStore()
    assert authorize_conversation_owner(owner, sessions=empty.sessions, users=empty.users) is None


def test_account_cookie_requires_matching_active_session() -> None:
    owner = _account_owner()
    store = _store_with_session(_session())
    authorized = authorize_conversation_owner(
        owner,
        sessions=store.sessions,
        users=store.users,
    )
    assert authorized is not None


def test_revoked_session_rejects_still_valid_signature() -> None:
    owner = _account_owner()
    store = _store_with_session(_session(revoked=True))
    raw = owner_cookie_payload(owner)
    assert parse_owner_cookie(raw) is not None
    assert authorize_conversation_owner(owner, sessions=store.sessions, users=store.users) is None


def test_authoritative_session_expiry_beats_later_cookie_expiry() -> None:
    owner = _account_owner(expires_at=NOW + timedelta(days=7))
    store = _store_with_session(_session(expires_at=NOW - timedelta(minutes=1)))
    assert parse_owner_cookie(owner_cookie_payload(owner)) is not None
    assert (
        authorize_conversation_owner(
            owner,
            sessions=store.sessions,
            users=store.users,
            now=NOW,
        )
        is None
    )


def test_cookie_principal_must_match_session_user() -> None:
    owner = _account_owner(user_id="other-user")
    store = _store_with_session(_session())
    assert authorize_conversation_owner(owner, sessions=store.sessions, users=store.users) is None


def test_inactive_or_missing_account_fails_closed() -> None:
    owner = _account_owner()
    store = _store_with_session(_session(), user=_user(active=False))
    assert authorize_conversation_owner(owner, sessions=store.sessions, users=store.users) is None


async def _register(client: AsyncClient, email: str) -> dict:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "display_name": email.split("@", 1)[0],
            "terms_accepted": False,
            "privacy_acknowledged": False,
        },
    )
    assert registered.status_code == 201
    return registered.json()


def _owner_from_auth(body: dict) -> ConversationOwner:
    return account_owner_from_session(
        user_id=body["user"]["user_id"],
        session_id=body["session"]["session_id"],
        expires_at=datetime.fromisoformat(body["session"]["expires_at"]),
    )


@asynccontextmanager
async def _uuid_client(snapshots: InMemoryDecisionSnapshotRepository):
    app = create_app()

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shopping_decision_snapshot_repository] = lambda: snapshots
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _snapshots() -> InMemoryDecisionSnapshotRepository:
    return InMemoryDecisionSnapshotRepository(clock=lambda: datetime.now(UTC))


@pytest.mark.asyncio
async def test_active_account_session_resolves_owned_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-active@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(owner)},
        )
    assert page.status_code == 200
    assert _attrs(page.text, "unavailable") == "false"
    assert "Sony" in page.text


@pytest.mark.asyncio
async def test_revoked_session_stale_cookie_cannot_resolve_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-revoked@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        get_user_platform_store().sessions.revoke(body["session"]["session_id"])
        raw = owner_cookie_payload(owner)
        assert parse_owner_cookie(raw) is not None
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: raw},
        )
    assert _attrs(page.text, "unavailable") == "true"
    assert "18,990" not in page.text


@pytest.mark.asyncio
async def test_logout_without_clearing_cookie_cannot_resolve_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-logout@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        logged_out = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert logged_out.status_code == 204
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(owner)},
        )
    assert _attrs(page.text, "unavailable") == "true"
    assert "Sony" not in page.text or _attrs(page.text, "unavailable") == "true"
    assert "18,990" not in page.text


@pytest.mark.asyncio
async def test_deleted_account_stale_cookie_cannot_resolve_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-deleted@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        deleted = await client.post(
            "/api/v1/auth/account/delete",
            headers={"Authorization": f"Bearer {body['access_token']}"},
            json={"confirmation": "DELETE", "password": PASSWORD},
        )
        assert deleted.status_code == 200
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(owner)},
        )
    assert _attrs(page.text, "unavailable") == "true"
    assert "18,990" not in page.text


@pytest.mark.asyncio
async def test_expired_authoritative_session_cannot_resolve_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-expired@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        store = get_user_platform_store()
        live = store.sessions.get_by_id(body["session"]["session_id"])
        assert live is not None
        store.sessions.save(replace(live, expires_at=datetime.now(UTC) - timedelta(minutes=1)))
        later_cookie = account_owner_from_session(
            user_id=owner.principal_id,
            session_id=owner.session_id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(later_cookie)},
        )
    assert parse_owner_cookie(owner_cookie_payload(later_cookie)) is not None
    assert _attrs(page.text, "unavailable") == "true"


@pytest.mark.asyncio
async def test_mismatched_cookie_principal_cannot_resolve_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-mismatch@example.invalid")
        owner = _owner_from_auth(body)
        snapshots.add(_economics_snapshot(owner=owner))
        spoofed = account_owner_from_session(
            user_id="someone-else",
            session_id=owner.session_id,
            expires_at=owner.expires_at,
        )
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(spoofed)},
        )
    assert _attrs(page.text, "unavailable") == "true"


@pytest.mark.asyncio
async def test_other_account_session_cannot_open_foreign_uuid() -> None:
    snapshots = _snapshots()
    async with _uuid_client(snapshots) as client:
        owner_b = _owner_from_auth(await _register(client, "sprint29-session-b@example.invalid"))
        owner_a = _owner_from_auth(await _register(client, "sprint29-session-a@example.invalid"))
        snapshots.add(_economics_snapshot(owner=owner_b))
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(owner_a)},
        )
    assert _attrs(page.text, "unavailable") == "true"
    assert "18,990" not in page.text


@pytest.mark.asyncio
async def test_guest_signed_cookie_still_resolves_owned_uuid() -> None:
    snapshots = _snapshots()
    guest = _guest_owner("guest-binding-still-works")
    snapshots.add(_economics_snapshot(owner=guest))
    async with _uuid_client(snapshots) as client:
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(guest)},
        )
    assert _attrs(page.text, "unavailable") == "false"
    assert "Sony" in page.text


@pytest.mark.asyncio
async def test_canonical_uuid_owner_stays_immutable_after_account_claim() -> None:
    snapshots = _snapshots()
    guest = _guest_owner("guest-binding-immutable")
    snapshot = _economics_snapshot(owner=guest)
    snapshots.add(snapshot)
    conversations = get_shopping_conversation_repository()
    created = conversations.create(owner=guest, decision_context=snapshot.to_reference())
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-immutable@example.invalid")
        claim = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id, "decision_id": CANONICAL_UUID},
            headers={"Authorization": f"Bearer {body['access_token']}"},
            cookies={OWNER_COOKIE: owner_cookie_payload(guest)},
        )
        assert claim.json()["claimed"] is False
        assert claim.json()["reason"] == "immutable_snapshot_owner"
        page = await client.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(guest)},
        )
    assert conversations.get_for_owner(created.conversation_id, guest) is not None
    assert _attrs(page.text, "unavailable") == "false"


@pytest.mark.asyncio
async def test_session_overlay_is_not_applied_after_revocation() -> None:
    snapshots = _snapshots()
    conversations = get_shopping_conversation_repository()
    async with _uuid_client(snapshots) as client:
        body = await _register(client, "sprint29-session-overlay@example.invalid")
        owner = _owner_from_auth(body)
        snapshot = _economics_snapshot(owner=owner)
        snapshots.add(snapshot)
        created = conversations.create(owner=owner, decision_context=snapshot.to_reference())
        overlay = SessionRecommendationRefinement(
            decision_id=CANONICAL_UUID,
            canonical_context_version=1,
            refinement_version=1,
            original_best_piq_product_id=SONY_ID,
            session_best_piq_product_id=BOSE_ID,
            priorities=SessionPriorities(top_priority="battery life"),
            recommendation_changed=True,
            status="recommendation_changed",
            reasons=("Battery life is the current session priority.",),
        )
        conversations.save(replace(created, session_refinement=overlay))
        raw = owner_cookie_payload(owner)
        live = await client.get(f"/results/{CANONICAL_UUID}", cookies={OWNER_COOKIE: raw})
        assert "current session Recommendation" in live.text
        get_user_platform_store().sessions.revoke(body["session"]["session_id"])
        revoked = await client.get(f"/results/{CANONICAL_UUID}", cookies={OWNER_COOKIE: raw})
    assert _attrs(revoked.text, "unavailable") == "true"
    assert "current session Recommendation" not in revoked.text
    assert "18,990" not in revoked.text


@pytest.mark.asyncio
async def test_clear_device_still_removes_owner_cookie() -> None:
    async with _uuid_client(_snapshots()) as client:
        cleared = await client.post("/account/clear-device")
    assert cleared.status_code == 200
    header = cleared.headers.get("set-cookie", "")
    assert OWNER_COOKIE in header
    assert "Max-Age=0" in header or "max-age=0" in header.lower()
