"""Guest owner cookies and guest→account conversation claim."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.consumer.canonical_resolve import resolve_canonical_snapshot
from app.consumer.decision_owner import (
    OWNER_COOKIE,
    owner_cookie_payload,
    owner_identity_payload,
    parse_owner_cookie,
    set_owner_cookie,
)
from app.consumer.guest_continuity import account_owner_from_session, claim_guest_conversation
from app.core.dependencies import (
    get_db,
    get_shopping_conversation_repository,
    get_shopping_decision_snapshot_repository,
)
from app.domain.entities.shopping_assistant import ConversationOwner, DecisionContextReference
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from starlette.responses import Response

from tests.unit.test_canonical_uuid_consumer_presentation import (
    DECISION_ID as CANONICAL_UUID,
)
from tests.unit.test_canonical_uuid_consumer_presentation import (
    START as CANONICAL_START,
)
from tests.unit.test_canonical_uuid_consumer_presentation import (
    _economics_snapshot,
    _owner as _uuid_owner,
)

DECISION_ID = "headphones-standard"
START = datetime(2030, 1, 1, 15, 0, tzinfo=UTC)


def _guest(*, principal_id: str = "guest-sprint29-claim") -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=START + timedelta(hours=1),
    )


def _account(*, user_id: str = "account-sprint29-claim") -> ConversationOwner:
    return account_owner_from_session(
        user_id=user_id,
        session_id=f"session-{user_id}",
        expires_at=START + timedelta(hours=2),
    )


def _decision_ref(decision_id: str) -> DecisionContextReference:
    return DecisionContextReference(
        decision_id=decision_id,
        context_version=1,
        evaluated_product_ids=("sony-wh-1000xm5-canonical",),
        canonical_piqscore_snapshot_sha256="a" * 64,
        recommendation_snapshot_sha256="b" * 64,
    )


async def _register(client: AsyncClient, email: str) -> dict:
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123",
            "display_name": email.split("@", 1)[0],
            "terms_accepted": False,
            "privacy_acknowledged": False,
        },
    )
    assert registered.status_code == 201
    return registered.json()


@pytest.mark.asyncio
async def test_results_mint_guest_owner_cookie(client: AsyncClient) -> None:
    response = await client.get("/results/headphones-standard")
    assert response.status_code == 200
    assert OWNER_COOKIE in response.cookies
    minted = parse_owner_cookie(response.cookies[OWNER_COOKIE])
    assert minted is not None
    assert minted.principal_type == "guest"


def test_claim_rebinds_guest_conversation_for_fixture_decision() -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest()
    created = conversations.create(owner=guest)
    result = claim_guest_conversation(
        conversation_id=created.conversation_id,
        decision_id=DECISION_ID,
        guest_owner=guest,
        account_owner=_account(),
        conversations=conversations,
    )
    assert result["claimed"] is True
    assert result["reason"] == "conversation_rebound"
    assert conversations.get_for_owner(created.conversation_id, guest) is None
    assert conversations.get_for_owner(created.conversation_id, _account()) is not None


def test_claim_rejects_foreign_guest_owner() -> None:
    conversations = get_shopping_conversation_repository()
    owner = _guest()
    created = conversations.create(owner=owner)
    stranger = _guest(principal_id="other-guest")
    result = claim_guest_conversation(
        conversation_id=created.conversation_id,
        decision_id=DECISION_ID,
        guest_owner=stranger,
        account_owner=_account(),
        conversations=conversations,
    )
    assert result["claimed"] is False
    assert conversations.get_for_owner(created.conversation_id, owner) is not None


def test_claim_rejects_changed_principal_type() -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-type-swap")
    created = conversations.create(owner=guest)
    swapped = ConversationOwner(
        principal_type="account",
        principal_id=guest.principal_id,
        session_id=guest.session_id,
        expires_at=guest.expires_at,
    )
    result = claim_guest_conversation(
        conversation_id=created.conversation_id,
        decision_id=DECISION_ID,
        guest_owner=swapped,
        account_owner=_account(),
        conversations=conversations,
    )
    assert result["claimed"] is False
    assert result["reason"] == "not_a_guest_owner"
    assert conversations.get_for_owner(created.conversation_id, guest) is not None


def test_claim_preserves_canonical_uuid_owner_immutability() -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-uuid-immutable")
    created = conversations.create(
        owner=guest,
        decision_context=_decision_ref(CANONICAL_UUID),
    )

    class _Snapshots:
        def get_latest_for_owner(self, decision_id: str, owner: ConversationOwner):
            if decision_id == CANONICAL_UUID and owner.has_same_identity(guest):
                return object()
            return None

    result = claim_guest_conversation(
        conversation_id=created.conversation_id,
        decision_id=CANONICAL_UUID,
        guest_owner=guest,
        account_owner=_account(),
        conversations=conversations,
        snapshots=_Snapshots(),  # type: ignore[arg-type]
    )
    assert result["claimed"] is False
    assert result["reason"] == "immutable_snapshot_owner"
    assert conversations.get_for_owner(created.conversation_id, guest) is not None
    assert conversations.get_for_owner(created.conversation_id, _account()) is None


@pytest.mark.asyncio
async def test_claim_endpoint_requires_auth(client: AsyncClient) -> None:
    response = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": "missing", "decision_id": DECISION_ID},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_endpoint_rebinds_after_register(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-sprint29-success")
    created = conversations.create(owner=guest)
    cookie_response = Response()
    set_owner_cookie(cookie_response, guest)
    raw_cookie = cookie_response.headers.get("set-cookie", "")
    assert OWNER_COOKIE in raw_cookie

    body = await _register(client, "sprint29-claim@example.invalid")
    token = body["access_token"]
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {token}"},
        cookies={OWNER_COOKIE: owner_cookie_payload(guest)},
    )
    assert claim.status_code == 200
    assert claim.json()["claimed"] is True
    account_owner = ConversationOwner(
        principal_type="account",
        principal_id=body["user"]["user_id"],
        session_id=body["session"]["session_id"],
        expires_at=datetime.fromisoformat(body["session"]["expires_at"]),
    )
    assert conversations.get_for_owner(created.conversation_id, account_owner) is not None
    rebound_cookie = parse_owner_cookie(claim.cookies.get(OWNER_COOKIE, ""))
    assert rebound_cookie is not None
    assert rebound_cookie.has_same_identity(account_owner)


@pytest.mark.asyncio
async def test_forged_guest_principal_cannot_claim(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-forged-principal")
    created = conversations.create(owner=guest)
    forged = _guest(principal_id="forged-other-guest")
    body = await _register(client, "sprint29-forged-principal@example.invalid")
    unsigned = json.dumps(owner_identity_payload(guest))
    for cookie in (unsigned, owner_cookie_payload(forged)):
        claim = await client.post(
            "/consumer/claim-decision",
            json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
            headers={"Authorization": f"Bearer {body['access_token']}"},
            cookies={OWNER_COOKIE: cookie},
        )
        assert claim.status_code == 200
        assert claim.json()["claimed"] is False
    assert conversations.get_for_owner(created.conversation_id, guest) is not None


@pytest.mark.asyncio
async def test_forged_session_id_cannot_claim(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-forged-session")
    created = conversations.create(owner=guest)
    forged = ConversationOwner(
        principal_type=guest.principal_type,
        principal_id=guest.principal_id,
        session_id="forged-session-id",
        expires_at=guest.expires_at,
    )
    body = await _register(client, "sprint29-forged-session@example.invalid")
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {body['access_token']}"},
        cookies={OWNER_COOKIE: owner_cookie_payload(forged)},
    )
    assert claim.json()["claimed"] is False
    assert conversations.get_for_owner(created.conversation_id, guest) is not None


@pytest.mark.asyncio
async def test_foreign_conversation_id_cannot_claim(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-own-conversation")
    foreign = _guest(principal_id="guest-foreign-conversation")
    conversations.create(owner=guest)
    other = conversations.create(owner=foreign)
    body = await _register(client, "sprint29-foreign-conversation@example.invalid")
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": other.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {body['access_token']}"},
        cookies={OWNER_COOKIE: owner_cookie_payload(guest)},
    )
    assert claim.json()["claimed"] is False
    assert conversations.get_for_owner(other.conversation_id, foreign) is not None


@pytest.mark.asyncio
async def test_expired_guest_owner_cannot_claim(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    live = _guest(principal_id="guest-expired-live")
    created = conversations.create(owner=live)
    expired = ConversationOwner(
        principal_type=live.principal_type,
        principal_id=live.principal_id,
        session_id=live.session_id,
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    body = await _register(client, "sprint29-expired-guest@example.invalid")
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {body['access_token']}"},
        cookies={OWNER_COOKIE: owner_cookie_payload(expired)},
    )
    assert parse_owner_cookie(owner_cookie_payload(expired)) is None
    assert claim.json()["claimed"] is False
    assert claim.json()["reason"] == "missing_guest_owner"


@pytest.mark.asyncio
async def test_account_a_cannot_claim_account_or_guest_b(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest_b = _guest(principal_id="guest-b-protected")
    guest_conversation = conversations.create(owner=guest_b)
    account_a = await _register(client, "sprint29-account-a@example.invalid")
    account_b = await _register(client, "sprint29-account-b@example.invalid")
    owner_b = account_owner_from_session(
        user_id=account_b["user"]["user_id"],
        session_id=account_b["session"]["session_id"],
        expires_at=datetime.fromisoformat(account_b["session"]["expires_at"]),
    )
    account_conversation = conversations.create(owner=owner_b)
    headers = {"Authorization": f"Bearer {account_a['access_token']}"}

    guest_claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": guest_conversation.conversation_id, "decision_id": DECISION_ID},
        headers=headers,
        cookies={OWNER_COOKIE: owner_cookie_payload(_guest(principal_id="guest-a-other"))},
    )
    account_claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": account_conversation.conversation_id, "decision_id": DECISION_ID},
        headers=headers,
        cookies={OWNER_COOKIE: owner_cookie_payload(owner_b)},
    )
    assert guest_claim.json()["claimed"] is False
    assert account_claim.json()["claimed"] is False
    assert conversations.get_for_owner(guest_conversation.conversation_id, guest_b) is not None
    assert conversations.get_for_owner(account_conversation.conversation_id, owner_b) is not None


@pytest.mark.asyncio
async def test_clear_device_removes_owner_cookie(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-shared-device")
    created = conversations.create(owner=guest)
    body = await _register(client, "sprint29-shared-device@example.invalid")
    cleared = await client.post("/account/clear-device")
    assert cleared.status_code == 200
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert claim.json()["claimed"] is False
    assert claim.json()["reason"] == "missing_guest_owner"


@pytest.mark.asyncio
async def test_client_supplied_ids_are_not_sole_authorization(client: AsyncClient) -> None:
    conversations = get_shopping_conversation_repository()
    guest = _guest(principal_id="guest-hint-only")
    created = conversations.create(owner=guest)
    body = await _register(client, "sprint29-client-id-hint@example.invalid")
    unsigned = json.dumps(owner_identity_payload(guest))
    claim = await client.post(
        "/consumer/claim-decision",
        json={"conversation_id": created.conversation_id, "decision_id": DECISION_ID},
        headers={"Authorization": f"Bearer {body['access_token']}"},
        cookies={OWNER_COOKIE: unsigned},
    )
    assert claim.json()["claimed"] is False
    assert conversations.get_for_owner(created.conversation_id, guest) is not None


@pytest.mark.asyncio
async def test_foreign_canonical_uuid_is_not_resolved_from_forged_cookie() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: CANONICAL_START)
    snapshot = _economics_snapshot()
    snapshots.add(snapshot)
    owner = snapshot.owner
    unsigned = json.dumps(owner_identity_payload(owner))
    forged = _uuid_owner("foreign-browser")
    assert parse_owner_cookie(unsigned) is None
    assert resolve_canonical_snapshot(CANONICAL_UUID, parse_owner_cookie(unsigned), snapshots) is None
    assert (
        resolve_canonical_snapshot(
            CANONICAL_UUID,
            parse_owner_cookie(owner_cookie_payload(forged)),
            snapshots,
        )
        is None
    )
    assert (
        resolve_canonical_snapshot(
            CANONICAL_UUID,
            parse_owner_cookie(owner_cookie_payload(owner)),
            snapshots,
        )
        is not None
    )

    app = create_app()

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shopping_decision_snapshot_repository] = lambda: snapshots
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        foreign = await http.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(forged)},
        )
        unsigned_page = await http.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: unsigned},
        )
        owned = await http.get(
            f"/results/{CANONICAL_UUID}",
            cookies={OWNER_COOKIE: owner_cookie_payload(owner)},
        )
    app.dependency_overrides.clear()
    assert foreign.status_code == 200
    assert unsigned_page.status_code == 200
    assert 'data-unavailable="true"' in foreign.text
    assert 'data-unavailable="true"' in unsigned_page.text
    assert 'data-unavailable="false"' in owned.text
