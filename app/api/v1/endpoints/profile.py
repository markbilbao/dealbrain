"""User Platform profile and preferences API endpoints.

All routes require an ``Authorization: Bearer <access_token>`` header issued
by ``POST /api/v1/auth/register`` or ``POST /api/v1/auth/login``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.api.v1.endpoints.auth import extract_bearer_token, map_user_platform_error
from app.api.v1.mappers.user_platform import to_preferences_payload, to_profile_response
from app.core.dependencies import get_user_platform_service
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformNotFoundError,
    UserPlatformValidationError,
)
from app.schemas.user_platform import (
    PreferencesPayload,
    PreferencesUpdateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/profile")

_ERRORS = (UserPlatformAuthError, UserPlatformValidationError, UserPlatformNotFoundError)


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Get the authenticated user's shopping profile",
)
async def get_profile(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> ProfileResponse:
    token = extract_bearer_token(authorization)
    try:
        profile = service.get_profile(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_profile_response(profile)


@router.put(
    "",
    response_model=ProfileResponse,
    summary="Update the authenticated user's shopping profile",
)
async def update_profile(
    body: ProfileUpdateRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> ProfileResponse:
    token = extract_bearer_token(authorization)
    updates = body.model_dump(exclude_unset=True)
    try:
        profile = service.update_profile(token, updates)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_profile_response(profile)


@router.get(
    "/preferences",
    response_model=PreferencesPayload,
    summary="Get the authenticated user's shopping preferences",
)
async def get_preferences(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> PreferencesPayload:
    token = extract_bearer_token(authorization)
    try:
        preferences = service.get_preferences(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_preferences_payload(preferences)


@router.put(
    "/preferences",
    response_model=PreferencesPayload,
    summary="Update the authenticated user's shopping preferences",
)
async def update_preferences(
    body: PreferencesUpdateRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> PreferencesPayload:
    token = extract_bearer_token(authorization)
    updates = body.model_dump(exclude_unset=True)
    try:
        preferences = service.update_preferences(token, updates)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_preferences_payload(preferences)
