"""Authorize a parsed owner cookie against trusted User Platform session state.

Guest credentials keep the bounded signed-cookie model. Account credentials
are not sufficient until SessionRepository confirms an active matching session.
"""

from __future__ import annotations

from datetime import UTC, datetime

from starlette.requests import Request

from app.consumer.decision_owner import OWNER_COOKIE, parse_owner_cookie
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.interfaces.user_platform_repository import SessionRepository, UserRepository


def authorize_conversation_owner(
    owner: ConversationOwner | None,
    *,
    sessions: SessionRepository | None = None,
    users: UserRepository | None = None,
    now: datetime | None = None,
) -> ConversationOwner | None:
    """Return an owner only when guest-signed or backed by an active account session."""

    if owner is None:
        return None
    if owner.principal_type == "guest":
        return owner
    if owner.principal_type != "account":
        return None
    if sessions is None:
        return None
    session = sessions.get_by_id(owner.session_id)
    if session is None:
        return None
    if session.session_id != owner.session_id:
        return None
    if session.user_id != owner.principal_id:
        return None
    if session.revoked:
        return None
    clock = now or datetime.now(UTC)
    if session.expires_at.tzinfo is None:
        expires_at = session.expires_at.replace(tzinfo=UTC)
    else:
        expires_at = session.expires_at
    if expires_at <= clock:
        return None
    if users is not None:
        user = users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            return None
    return owner


def authorized_owner_from_cookie(
    raw: str | None,
    *,
    sessions: SessionRepository | None = None,
    users: UserRepository | None = None,
    now: datetime | None = None,
) -> ConversationOwner | None:
    """Parse cookie integrity, then authorize account principals against sessions."""

    owner = parse_owner_cookie(raw)
    if owner is None:
        return None
    if owner.principal_type == "guest":
        return owner
    if sessions is None or users is None:
        from app.core.dependencies import get_user_platform_store

        store = get_user_platform_store()
        sessions = sessions or store.sessions
        users = users or store.users
    return authorize_conversation_owner(owner, sessions=sessions, users=users, now=now)


def authorized_owner_from_request(request: Request) -> ConversationOwner | None:
    return authorized_owner_from_cookie(request.cookies.get(OWNER_COOKIE))
