"""User Dashboard API endpoint — Sprint 19.

Read-only aggregation of a user's watchlists, alert rules, and
notifications. Figures only ever summarize fixture/imported data — see
``UserDashboardResponse.limitations``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import extract_bearer_token
from app.api.v1.mappers.dashboard import to_dashboard_response
from app.core.config import settings
from app.core.dependencies import get_user_dashboard_service, get_user_platform_service
from app.domain.exceptions import DashboardValidationError, UserPlatformAuthError
from app.schemas.dashboard import UserDashboardResponse
from app.services.user_dashboard_service import UserDashboardService
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/dashboard")


def _resolve_actor(
    authorization: str | None,
    user_platform: UserPlatformService,
    *,
    fallback_user_id: str | None = None,
) -> str | None:
    token = extract_bearer_token(authorization)
    if token is None:
        if settings.watchlists_require_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
            )
        return fallback_user_id
    try:
        user = user_platform.require_user(token)
    except UserPlatformAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    return user.user_id


@router.get(
    "",
    response_model=UserDashboardResponse,
    summary="Get the authenticated user's dashboard",
)
async def get_dashboard(
    currency: str = Query("PHP", min_length=3, max_length=3),
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: UserDashboardService = Depends(get_user_dashboard_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> UserDashboardResponse:
    actor = _resolve_actor(authorization, user_platform, fallback_user_id=user_id)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    try:
        payload = await service.get_dashboard_dict(actor, currency=currency)
    except DashboardValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    return to_dashboard_response(payload)
