"""Owner/session cookie used to authorize canonical UUID document routes.

Does not weaken Phase 29.3 owner binding. The cookie only carries the same
identity tuple already stored on the snapshot.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from starlette.responses import Response

from app.domain.entities.shopping_assistant import ConversationOwner

OWNER_COOKIE = "piqsavi_decision_owner"
COOKIE_MAX_BYTES = 768


def parse_owner_cookie(raw: str | None) -> ConversationOwner | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        expires_at = datetime.fromisoformat(str(payload.get("expires_at") or ""))
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    try:
        owner = ConversationOwner(
            principal_type=str(payload.get("principal_type") or ""),
            principal_id=str(payload.get("principal_id") or ""),
            session_id=str(payload.get("session_id") or ""),
            expires_at=expires_at,
        )
    except ValueError:
        return None
    return owner


def owner_cookie_payload(owner: ConversationOwner) -> str:
    return json.dumps(
        {
            "principal_type": owner.principal_type,
            "principal_id": owner.principal_id,
            "session_id": owner.session_id,
            "expires_at": owner.expires_at.isoformat(),
        },
        separators=(",", ":"),
    )


def set_owner_cookie(response: Response, owner: ConversationOwner) -> None:
    payload = owner_cookie_payload(owner)
    if len(payload.encode()) > COOKIE_MAX_BYTES:
        raise ValueError("owner cookie exceeds size limit")
    response.set_cookie(
        OWNER_COOKIE,
        payload,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def owner_from_mapping(payload: dict[str, Any]) -> ConversationOwner | None:
    return parse_owner_cookie(json.dumps(payload))
