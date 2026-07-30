"""Notification Center & Preferences API endpoints — Sprint 19.

In-app notification inbox and per-user delivery preferences. All delivery
remains mock/simulated — no real email, SMS, or push transport exists
anywhere in this codebase.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import extract_bearer_token
from app.api.v1.mappers.notifications import to_notification_payload, to_preferences_payload
from app.core.config import settings
from app.core.dependencies import (
    get_notification_center_service,
    get_notification_preference_service,
    get_user_platform_service,
)
from app.domain.entities.notifications import NotificationSeverity, NotificationType
from app.domain.exceptions import (
    NotificationNotFoundError,
    NotificationValidationError,
    UserPlatformAuthError,
)
from app.schemas.api_common import (
    SORT_ALLOWLIST_NOTIFICATIONS,
    apply_sort,
    build_pagination_meta,
    parse_sort,
)
from app.schemas.notifications import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationPayload,
    NotificationPreferencesPayload,
    NotificationPreferencesUpdateRequest,
    UnreadCountResponse,
)
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/notifications")
preferences_router = APIRouter(prefix="/notification-preferences")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotificationValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, NotificationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _resolve_actor(
    authorization: str | None,
    user_platform: UserPlatformService,
    *,
    fallback_user_id: str | None = None,
) -> str | None:
    """Resolve the authenticated actor's user id (see ``endpoints.watchlists``)."""
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


def _require_actor(actor: str | None) -> str:
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return actor


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List the authenticated user's notifications",
    description=(
        "Primary collection key remains ``notifications``. Sprint 24 adds optional "
        "``items`` (alias) and ``pagination``. Optional presentation sort: "
        "created_at, severity."
    ),
)
async def list_notifications(
    type: str | None = None,  # noqa: A002 - matches query param naming
    severity: str | None = None,
    watchlist_id: str | None = None,
    unread: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(
        default=None,
        description="Optional presentation sort, e.g. sort=-created_at,severity",
    ),
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> NotificationListResponse:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    directives = parse_sort(sort, SORT_ALLOWLIST_NOTIFICATIONS)
    try:
        if directives:
            # Sort before pagination so allowlisted presentation order is stable.
            filtered = service.list_notifications(
                actor,
                type=NotificationType(type) if type else None,
                severity=NotificationSeverity(severity) if severity else None,
                watchlist_id=watchlist_id,
                unread=unread,
                limit=1_000_000,
                offset=0,
            )
            payloads = [to_notification_payload(n) for n in filtered]
            payloads = apply_sort(payloads, directives)
            total = len(payloads)
            page = payloads[offset : offset + limit]
        else:
            notifications = service.list_notifications(
                actor,
                type=NotificationType(type) if type else None,
                severity=NotificationSeverity(severity) if severity else None,
                watchlist_id=watchlist_id,
                unread=unread,
                limit=limit + 1,
                offset=offset,
            )
            has_more = len(notifications) > limit
            page_entities = notifications[:limit]
            page = [to_notification_payload(n) for n in page_entities]
            total = None
            pagination = build_pagination_meta(
                limit=limit, offset=offset, total=total, page_len=len(page), has_more=has_more
            )
            return NotificationListResponse(
                notifications=page,
                items=page,
                pagination=pagination,
            )
    except (ValueError, NotificationValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    pagination = build_pagination_meta(
        limit=limit, offset=offset, total=total, page_len=len(page)
    )
    return NotificationListResponse(notifications=page, items=page, pagination=pagination)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Count the authenticated user's unread notifications",
)
async def unread_count(
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> UnreadCountResponse:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    return UnreadCountResponse(unread_count=service.unread_count(actor))


@router.post(
    "/read-all",
    response_model=MarkAllReadResponse,
    summary="Mark all of the authenticated user's notifications as read",
)
async def mark_all_read(
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> MarkAllReadResponse:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    return MarkAllReadResponse(marked_read=service.mark_all_read(actor))


@router.post(
    "/{notification_id}/read",
    response_model=NotificationPayload,
    summary="Mark a notification as read",
)
async def mark_read(
    notification_id: str,
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> NotificationPayload:
    actor = _resolve_actor(authorization, user_platform)
    try:
        notification = service.mark_read(notification_id, user_id=actor)
    except NotificationNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_notification_payload(notification)


@router.post(
    "/{notification_id}/archive",
    response_model=NotificationPayload,
    summary="Archive a notification",
)
async def archive_notification(
    notification_id: str,
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> NotificationPayload:
    actor = _resolve_actor(authorization, user_platform)
    try:
        notification = service.archive(notification_id, user_id=actor)
    except NotificationNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_notification_payload(notification)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a notification",
)
async def delete_notification(
    notification_id: str,
    authorization: str | None = Header(default=None),
    service: NotificationCenterService = Depends(get_notification_center_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> None:
    actor = _resolve_actor(authorization, user_platform)
    try:
        service.delete(notification_id, user_id=actor)
    except NotificationNotFoundError as exc:
        raise _map_error(exc) from exc


@preferences_router.get(
    "",
    response_model=NotificationPreferencesPayload,
    summary="Get the authenticated user's notification preferences",
)
async def get_preferences(
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: NotificationPreferenceService = Depends(get_notification_preference_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> NotificationPreferencesPayload:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    return to_preferences_payload(service.get_preferences(actor))


@preferences_router.put(
    "",
    response_model=NotificationPreferencesPayload,
    summary="Update the authenticated user's notification preferences",
)
async def update_preferences(
    body: NotificationPreferencesUpdateRequest,
    user_id: str | None = Query(default=None, description="Demo-mode fallback user id"),
    authorization: str | None = Header(default=None),
    service: NotificationPreferenceService = Depends(get_notification_preference_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> NotificationPreferencesPayload:
    actor = _require_actor(_resolve_actor(authorization, user_platform, fallback_user_id=user_id))
    # ``NotificationPreferenceService.update_preferences`` distinguishes "not
    # supplied" from "explicitly cleared to None" for the quiet-hours fields
    # via its own module-private sentinel — only pass these kwargs at all
    # when the request actually wants to change them.
    quiet_hours_kwargs: dict[str, object] = {}
    if body.clear_quiet_hours_start:
        quiet_hours_kwargs["quiet_hours_start"] = None
    elif body.quiet_hours_start is not None:
        quiet_hours_kwargs["quiet_hours_start"] = body.quiet_hours_start
    if body.clear_quiet_hours_end:
        quiet_hours_kwargs["quiet_hours_end"] = None
    elif body.quiet_hours_end is not None:
        quiet_hours_kwargs["quiet_hours_end"] = body.quiet_hours_end

    try:
        preferences = service.update_preferences(
            actor,
            in_app_enabled=body.in_app_enabled,
            email_enabled=body.email_enabled,
            immediate_alerts=body.immediate_alerts,
            daily_digest=body.daily_digest,
            weekly_digest=body.weekly_digest,
            timezone=body.timezone,
            price_alerts=body.price_alerts,
            stock_alerts=body.stock_alerts,
            freshness_warnings=body.freshness_warnings,
            marketing_enabled=body.marketing_enabled,
            **quiet_hours_kwargs,
        )
    except NotificationValidationError as exc:
        raise _map_error(exc) from exc
    return to_preferences_payload(preferences)
