"""Guest owner cookies and guest→account conversation claim."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response

from app.consumer.decision_owner import (
    OWNER_COOKIE,
    parse_owner_cookie,
    set_owner_cookie,
)
from app.consumer.uuid import is_canonical_uuid
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import ConversationOwnershipError
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository

GUEST_OWNER_TTL = timedelta(days=7)


def mint_guest_owner(*, now: datetime | None = None) -> ConversationOwner:
    clock = now or datetime.now(UTC)
    return ConversationOwner(
        principal_type="guest",
        principal_id=str(uuid4()),
        session_id=str(uuid4()),
        expires_at=clock + GUEST_OWNER_TTL,
    )


def account_owner_from_session(
    *,
    user_id: str,
    session_id: str,
    expires_at: datetime,
) -> ConversationOwner:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return ConversationOwner(
        principal_type="account",
        principal_id=user_id,
        session_id=session_id,
        expires_at=expires_at,
    )


def ensure_guest_owner_cookie(request: Request, response: Response) -> ConversationOwner:
    existing = parse_owner_cookie(request.cookies.get(OWNER_COOKIE))
    if existing is not None:
        return existing
    owner = mint_guest_owner()
    set_owner_cookie(response, owner)
    return owner


def clear_owner_cookie(response: Response) -> None:
    response.delete_cookie(OWNER_COOKIE, path="/")


def claim_guest_conversation(
    *,
    conversation_id: str,
    decision_id: str | None,
    guest_owner: ConversationOwner | None,
    account_owner: ConversationOwner,
    conversations: ConversationRepository,
    snapshots: DecisionSnapshotRepository | None = None,
) -> dict[str, Any]:
    """Transfer a guest conversation when snapshots stay immutable.

    Canonical UUID snapshots keep their original owner. Replacing the guest
    cookie would hide the decision, so those claims preserve the cookie and
    do not rebind.
    """

    if not conversation_id:
        return {
            "claimed": False,
            "reason": "missing_conversation",
            "decision_preserved": False,
        }
    if guest_owner is None:
        return {
            "claimed": False,
            "reason": "missing_guest_owner",
            "decision_preserved": False,
        }
    if guest_owner.principal_type != "guest":
        return {
            "claimed": False,
            "reason": "not_a_guest_owner",
            "decision_preserved": True,
        }
    bound = conversations.get_for_owner(conversation_id, guest_owner)
    if bound is None:
        return {
            "claimed": False,
            "reason": "conversation_not_found",
            "decision_preserved": False,
        }

    target_decision = decision_id or (
        bound.decision_context.decision_id if bound.decision_context is not None else ""
    )
    if target_decision and is_canonical_uuid(target_decision) and snapshots is not None:
        snapshot = snapshots.get_latest_for_owner(target_decision, guest_owner)
        if snapshot is not None:
            return {
                "claimed": False,
                "reason": "immutable_snapshot_owner",
                "decision_preserved": True,
                "conversation_id": conversation_id,
                "decision_id": target_decision,
            }

    try:
        rebound = conversations.rebind_owner(
            conversation_id,
            current_owner=guest_owner,
            new_owner=account_owner,
            expected_version=bound.persistence_version,
        )
    except ConversationOwnershipError:
        return {
            "claimed": False,
            "reason": "owner_mismatch",
            "decision_preserved": False,
        }
    return {
        "claimed": True,
        "reason": "conversation_rebound",
        "decision_preserved": True,
        "conversation_id": rebound.conversation_id,
        "decision_id": target_decision,
    }
