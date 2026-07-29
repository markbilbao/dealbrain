"""User Platform saved-items API endpoints — products, comparisons, history, searches.

All routes require an ``Authorization: Bearer <access_token>`` header issued
by ``POST /api/v1/auth/register`` or ``POST /api/v1/auth/login``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from app.api.v1.endpoints.auth import extract_bearer_token, map_user_platform_error
from app.api.v1.mappers.user_platform import (
    to_history_payload,
    to_recently_viewed_payload,
    to_saved_comparison_payload,
    to_saved_product_payload,
    to_saved_search_payload,
)
from app.core.dependencies import get_user_platform_service
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformNotFoundError,
    UserPlatformValidationError,
)
from app.schemas.user_platform import (
    MarkViewedRequest,
    RecentlyViewedPayload,
    RecommendationHistoryPayload,
    SaveComparisonRequest,
    SavedComparisonPayload,
    SavedProductPayload,
    SavedSearchPayload,
    SaveProductRequest,
    SaveSearchRequest,
)
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/user")

_ERRORS = (UserPlatformAuthError, UserPlatformValidationError, UserPlatformNotFoundError)


@router.get(
    "/saved-products",
    response_model=list[SavedProductPayload],
    summary="List the authenticated user's saved products",
)
async def list_saved_products(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> list[SavedProductPayload]:
    token = extract_bearer_token(authorization)
    try:
        items = service.list_saved_products(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return [to_saved_product_payload(item) for item in items]


@router.post(
    "/saved-products",
    response_model=SavedProductPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Save a product to the authenticated user's list",
)
async def save_product(
    body: SaveProductRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> SavedProductPayload:
    token = extract_bearer_token(authorization)
    try:
        item = service.save_product(token, body.model_dump())
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_saved_product_payload(item)


@router.delete(
    "/saved-products/{saved_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a saved product",
)
async def delete_saved_product(
    saved_id: str,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> None:
    token = extract_bearer_token(authorization)
    try:
        service.delete_saved_product(token, saved_id)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc


@router.get(
    "/history",
    response_model=list[RecommendationHistoryPayload],
    summary="List the authenticated user's recommendation history",
)
async def list_history(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> list[RecommendationHistoryPayload]:
    token = extract_bearer_token(authorization)
    try:
        items = service.list_history(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return [to_history_payload(item) for item in items]


@router.get(
    "/comparisons",
    response_model=list[SavedComparisonPayload],
    summary="List the authenticated user's saved comparisons",
)
async def list_comparisons(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> list[SavedComparisonPayload]:
    token = extract_bearer_token(authorization)
    try:
        items = service.list_comparisons(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return [to_saved_comparison_payload(item) for item in items]


@router.post(
    "/comparisons",
    response_model=SavedComparisonPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Save a product comparison for the authenticated user",
)
async def save_comparison(
    body: SaveComparisonRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> SavedComparisonPayload:
    token = extract_bearer_token(authorization)
    try:
        item = service.save_comparison(token, body.model_dump())
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_saved_comparison_payload(item)


@router.get(
    "/searches",
    response_model=list[SavedSearchPayload],
    summary="List the authenticated user's saved searches",
)
async def list_searches(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> list[SavedSearchPayload]:
    token = extract_bearer_token(authorization)
    try:
        items = service.list_searches(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return [to_saved_search_payload(item) for item in items]


@router.post(
    "/searches",
    response_model=SavedSearchPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Save a search query for the authenticated user",
)
async def save_search(
    body: SaveSearchRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> SavedSearchPayload:
    token = extract_bearer_token(authorization)
    try:
        item = service.save_search(token, body.model_dump())
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_saved_search_payload(item)


@router.get(
    "/recently-viewed",
    response_model=RecentlyViewedPayload,
    summary="Get the authenticated user's recently viewed products",
)
async def get_recently_viewed(
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> RecentlyViewedPayload:
    token = extract_bearer_token(authorization)
    try:
        item = service.get_recently_viewed(token)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_recently_viewed_payload(item)


@router.post(
    "/recently-viewed",
    response_model=RecentlyViewedPayload,
    summary="Record a product as recently viewed for the authenticated user",
)
async def mark_viewed(
    body: MarkViewedRequest,
    authorization: str | None = Header(default=None),
    service: UserPlatformService = Depends(get_user_platform_service),
) -> RecentlyViewedPayload:
    token = extract_bearer_token(authorization)
    try:
        item = service.mark_viewed(token, body.product_id)
    except _ERRORS as exc:
        raise map_user_platform_error(exc) from exc
    return to_recently_viewed_payload(item)
