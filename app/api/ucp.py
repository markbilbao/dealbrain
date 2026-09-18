"""Public unauthenticated UCP agent-profile route.

Serves the static PiqSavi-owned profile JSON from the existing FastAPI app.
No authentication, database, Redis, session, or outbound network.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.ucp.agent_profile import (
    PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL,
    PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE,
    PIQSAVI_UCP_AGENT_PROFILE_PATH,
    serialize_piqsavi_ucp_agent_profile,
)

router = APIRouter(include_in_schema=False)


@router.get(
    PIQSAVI_UCP_AGENT_PROFILE_PATH,
    include_in_schema=False,
    summary="PiqSavi UCP agent profile",
)
async def piqsavi_ucp_agent_profile(request: Request) -> Response:
    """Return the server-owned profile. Request input cannot change the body."""

    del request
    body = serialize_piqsavi_ucp_agent_profile()
    return Response(
        content=body,
        media_type=PIQSAVI_UCP_AGENT_PROFILE_CONTENT_TYPE,
        headers={
            "Cache-Control": PIQSAVI_UCP_AGENT_PROFILE_CACHE_CONTROL,
            "X-Content-Type-Options": "nosniff",
        },
    )
