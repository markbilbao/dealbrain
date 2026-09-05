"""Guest owner cookies and guest→account conversation claim."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload, set_owner_cookie
from app.consumer.guest_continuity import account_owner_from_session, claim_guest_conversation
from app.core.dependencies import get_shopping_conversation_repository
from app.domain.entities.shopping_assistant import ConversationOwner
from httpx import AsyncClient
from starlette.responses import Response

DECISION_ID = "headphones-standard"
START = datetime(2026, 9, 5, 15, 0, tzinfo=UTC)


def _guest() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-sprint29-claim",
        session_id="guest-session-sprint29",
        expires_at=START + timedelta(hours=1),
    )


def _account() -> ConversationOwner:
    return account_owner_from_session(
        user_id="account-sprint29-claim",
        session_id="account-session-sprint29",
        expires_at=START + timedelta(hours=2),
    )


@pytest.mark.asyncio
async def test_results_mint_guest_owner_cookie(client: AsyncClient) -> None:
    response = await client.get("/results/headphones-standard")
    assert response.status_code == 200
    assert OWNER_COOKIE in response.cookies
    assert response.cookies[OWNER_COOKIE]


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
    stranger = ConversationOwner(
        principal_type="guest",
        principal_id="other-guest",
        session_id="other-session",
        expires_at=START + timedelta(hours=1),
    )
    result = claim_guest_conversation(
        conversation_id=created.conversation_id,
        decision_id=DECISION_ID,
        guest_owner=stranger,
        account_owner=_account(),
        conversations=conversations,
    )
    assert result["claimed"] is False
    assert conversations.get_for_owner(created.conversation_id, owner) is not None


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
    guest = _guest()
    created = conversations.create(owner=guest)
    cookie_response = Response()
    set_owner_cookie(cookie_response, guest)
    raw_cookie = cookie_response.headers.get("set-cookie", "")
    assert OWNER_COOKIE in raw_cookie

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sprint29-claim@example.invalid",
            "password": "Password123",
            "display_name": "Claim User",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert registered.status_code == 201
    token = registered.json()["access_token"]
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
        principal_id=registered.json()["user"]["user_id"],
        session_id=registered.json()["session"]["session_id"],
        expires_at=datetime.fromisoformat(registered.json()["session"]["expires_at"]),
    )
    assert conversations.get_for_owner(created.conversation_id, account_owner) is not None
