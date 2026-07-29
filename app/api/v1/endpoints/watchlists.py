"""Watchlists & Price Alerts API endpoints.

CRUD for watchlists/items, alert listing, and manual alert evaluation.
Mock notifications only — no email, SMS, or push delivery.

Sprint 19 additions: owner-scoped auth/ownership enforcement (gated by
``settings.watchlists_require_auth``), default watchlists, pause/resume/
archive lifecycle, watchlist history, preferred seller/marketplace tagging,
item notes, and marketplace-offer tracking. Every Sprint 10 route keeps its
original path/behavior when authentication is not supplied and
``watchlists_require_auth`` is disabled (see ``tests/unit/test_watchlist_api.py``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import extract_bearer_token
from app.api.v1.mappers.watchlists import (
    to_alert_payload,
    to_evaluation_response,
    to_history_payload,
    to_item_payload,
    to_snapshot_payload,
    to_watchlist_payload,
)
from app.core.config import settings
from app.core.dependencies import (
    get_alert_service,
    get_user_platform_service,
    get_watchlist_service,
)
from app.domain.exceptions import (
    AlertNotFoundError,
    UserPlatformAuthError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
    WatchlistOwnershipError,
    WatchlistValidationError,
)
from app.schemas.watchlists import (
    AlertEvaluationResponse,
    AlertListResponse,
    AlertPayload,
    WatchlistCreateRequest,
    WatchlistHistoryListResponse,
    WatchlistItemCreateRequest,
    WatchlistItemListResponse,
    WatchlistItemPayload,
    WatchlistItemPreferredMarketplacesRequest,
    WatchlistItemPreferredSellersRequest,
    WatchlistItemUpdateRequest,
    WatchlistListResponse,
    WatchlistOfferCreateRequest,
    WatchlistPayload,
    WatchlistPreferredMarketplacesRequest,
    WatchlistPreferredSellersRequest,
    WatchlistUpdateRequest,
)
from app.services.alert_service import AlertService
from app.services.user_platform_service import UserPlatformService
from app.services.watchlist_service import WatchlistService
from app.watchlists.security import require_owner as require_watchlist_owner

router = APIRouter(prefix="/watchlists")
alerts_router = APIRouter(prefix="/alerts")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WatchlistValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, WatchlistOwnershipError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(
        exc,
        (WatchlistNotFoundError, WatchlistItemNotFoundError, AlertNotFoundError),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _resolve_actor(
    authorization: str | None,
    user_platform: UserPlatformService,
    *,
    required: bool,
) -> str | None:
    """Resolve the authenticated actor's user id, or ``None`` for anonymous access.

    When ``required`` is True and ``settings.watchlists_require_auth`` is
    True, a missing/invalid bearer token raises 401. When
    ``watchlists_require_auth`` is False (Sprint 10 backward-compat / test
    mode), anonymous access is always allowed and callers fall back to
    body/query-supplied identifiers (e.g. ``owner_id``).
    """
    token = extract_bearer_token(authorization)
    if token is None:
        if required and settings.watchlists_require_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
            )
        return None
    try:
        user = user_platform.require_user(token)
    except UserPlatformAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc
    return user.user_id


def _get_watchlist_checked(service: WatchlistService, watchlist_id: str, actor: str | None):
    """Fetch a watchlist and enforce ownership when an actor is known."""
    watchlist = service.get_watchlist(watchlist_id)
    if actor is not None:
        require_watchlist_owner(watchlist, actor)
    return watchlist


@router.get(
    "",
    response_model=WatchlistListResponse,
    summary="List watchlists",
)
async def list_watchlists(
    enabled: bool | None = None,
    status_filter: str | None = Query(None, alias="status"),
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistListResponse:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        watchlists = service.list_watchlists(owner_id=actor, enabled=enabled, status=status_filter)
    except TypeError:
        watchlists = service.list_watchlists(enabled=enabled)
    payloads = [
        to_watchlist_payload(
            wl,
            item_count=len(service.list_items(wl.watchlist_id)),
        )
        for wl in watchlists
    ]
    return WatchlistListResponse(watchlists=payloads)


@router.post(
    "",
    response_model=WatchlistPayload,
    summary="Create a watchlist",
)
async def create_watchlist(
    body: WatchlistCreateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    owner_id = actor if actor is not None else body.owner_id
    try:
        try:
            watchlist = service.create_watchlist(
                name=body.name,
                owner_id=owner_id,
                description=body.description,
                enabled=body.enabled,
                is_default=body.is_default,
            )
        except TypeError:
            watchlist = service.create_watchlist(
                name=body.name,
                owner_id=owner_id,
                description=body.description,
                enabled=body.enabled,
            )
    except WatchlistValidationError as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=0)


@router.post(
    "/check-alerts",
    response_model=AlertEvaluationResponse,
    summary="Evaluate alerts for all enabled watchlists",
)
async def check_all_alerts(
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertEvaluationResponse:
    result = await alert_service.evaluate_all()
    return to_evaluation_response(result)


@router.get(
    "/{watchlist_id}",
    response_model=WatchlistPayload,
    summary="Get a watchlist",
)
async def get_watchlist(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        watchlist = _get_watchlist_checked(service, watchlist_id, actor)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(
        watchlist,
        item_count=len(service.list_items(watchlist_id)),
    )


async def _update_watchlist_impl(
    watchlist_id: str,
    body: WatchlistUpdateRequest,
    authorization: str | None,
    service: WatchlistService,
    user_platform: UserPlatformService,
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        watchlist = service.update_watchlist(
            watchlist_id,
            name=body.name,
            owner_id=body.owner_id,
            description=body.description,
            enabled=body.enabled,
        )
    except (WatchlistValidationError, WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(
        watchlist,
        item_count=len(service.list_items(watchlist_id)),
    )


@router.patch(
    "/{watchlist_id}",
    response_model=WatchlistPayload,
    summary="Update a watchlist",
)
async def update_watchlist(
    watchlist_id: str,
    body: WatchlistUpdateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    return await _update_watchlist_impl(watchlist_id, body, authorization, service, user_platform)


@router.put(
    "/{watchlist_id}",
    response_model=WatchlistPayload,
    summary="Update a watchlist (alias of PATCH)",
)
async def replace_watchlist(
    watchlist_id: str,
    body: WatchlistUpdateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    return await _update_watchlist_impl(watchlist_id, body, authorization, service, user_platform)


@router.delete(
    "/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a watchlist",
)
async def delete_watchlist(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> None:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        service.delete_watchlist(watchlist_id)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{watchlist_id}/pause",
    response_model=WatchlistPayload,
    summary="Pause a watchlist (Sprint 19)",
)
async def pause_watchlist(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        pause = getattr(service, "pause_watchlist", None)
        if not callable(pause):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Pause is not supported by this watchlist service.",
            )
        watchlist = pause(watchlist_id, actor_id=actor)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=len(service.list_items(watchlist_id)))


@router.post(
    "/{watchlist_id}/resume",
    response_model=WatchlistPayload,
    summary="Resume a paused watchlist (Sprint 19)",
)
async def resume_watchlist(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        resume = getattr(service, "resume_watchlist", None)
        if not callable(resume):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Resume is not supported by this watchlist service.",
            )
        watchlist = resume(watchlist_id, actor_id=actor)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=len(service.list_items(watchlist_id)))


@router.post(
    "/{watchlist_id}/archive",
    response_model=WatchlistPayload,
    summary="Archive a watchlist (Sprint 19)",
)
async def archive_watchlist(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        archive = getattr(service, "archive_watchlist", None)
        if not callable(archive):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Archive is not supported by this watchlist service.",
            )
        watchlist = archive(watchlist_id, actor_id=actor)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=len(service.list_items(watchlist_id)))


@router.get(
    "/{watchlist_id}/history",
    response_model=WatchlistHistoryListResponse,
    summary="List watchlist history (Sprint 19)",
)
async def get_watchlist_history(
    watchlist_id: str,
    limit: int = Query(50, ge=1, le=200),
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistHistoryListResponse:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        get_history = getattr(service, "get_history", None)
        entries = get_history(watchlist_id, limit=limit) if callable(get_history) else []
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return WatchlistHistoryListResponse(history=[to_history_payload(e) for e in entries])


@router.put(
    "/{watchlist_id}/preferred-sellers",
    response_model=WatchlistPayload,
    summary="Set a watchlist's preferred sellers (Sprint 19)",
)
async def set_watchlist_preferred_sellers(
    watchlist_id: str,
    body: WatchlistPreferredSellersRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        setter = getattr(service, "set_watchlist_preferred_sellers", None)
        if not callable(setter):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferred sellers are not supported by this watchlist service.",
            )
        watchlist = setter(watchlist_id, sellers=body.sellers)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=len(service.list_items(watchlist_id)))


@router.put(
    "/{watchlist_id}/preferred-marketplaces",
    response_model=WatchlistPayload,
    summary="Set a watchlist's preferred marketplaces (Sprint 19)",
)
async def set_watchlist_preferred_marketplaces(
    watchlist_id: str,
    body: WatchlistPreferredMarketplacesRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        setter = getattr(service, "set_watchlist_preferred_marketplaces", None)
        if not callable(setter):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferred marketplaces are not supported by this watchlist service.",
            )
        watchlist = setter(watchlist_id, marketplaces=body.marketplaces)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(watchlist, item_count=len(service.list_items(watchlist_id)))


@router.get(
    "/{watchlist_id}/items",
    response_model=WatchlistItemListResponse,
    summary="List watchlist items (enriched)",
)
async def list_items(
    watchlist_id: str,
    enabled: bool | None = None,
    enrich: bool = Query(True),
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemListResponse:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        if enrich:
            snapshots = await service.list_enriched_items(watchlist_id, enabled=enabled)
            return WatchlistItemListResponse(items=[to_snapshot_payload(s) for s in snapshots])
        items = service.list_items(watchlist_id, enabled=enabled)
        return WatchlistItemListResponse(items=[to_item_payload(i) for i in items])
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemPayload,
    summary="Add a product to a watchlist",
)
async def add_item(
    watchlist_id: str,
    body: WatchlistItemCreateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        if body.marketplace_offer_id:
            add_offer_fn = getattr(service, "add_offer", None)
            if not callable(add_offer_fn):
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Offer tracking is not supported by this watchlist service.",
                )
            item = await add_offer_fn(
                watchlist_id,
                marketplace_offer_id=body.marketplace_offer_id,
                canonical_product_id=body.canonical_product_id,
                product_label=body.product_label,
                target_price=body.target_price,
                currency=body.currency,
                notes=body.notes,
            )
        else:
            item = await service.add_item(
                watchlist_id,
                canonical_product_id=body.canonical_product_id,
                product_label=body.product_label,
                target_price=body.target_price,
                currency=body.currency,
                search_query=body.search_query,
                enabled=body.enabled,
                last_known_price=body.last_known_price,
                last_known_dealscore=body.last_known_dealscore,
                last_historical_low=body.last_historical_low,
            )
            if body.notes is not None:
                set_notes = getattr(service, "set_item_notes", None)
                if callable(set_notes):
                    item = set_notes(item.item_id, notes=body.notes)
        snapshot = await service.enrich_item(item)
    except (WatchlistValidationError, WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.post(
    "/{watchlist_id}/offers",
    response_model=WatchlistItemPayload,
    summary="Track a marketplace offer on a watchlist (Sprint 19)",
)
async def add_offer(
    watchlist_id: str,
    body: WatchlistOfferCreateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        add_offer_fn = getattr(service, "add_offer", None)
        if not callable(add_offer_fn):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Offer tracking is not supported by this watchlist service.",
            )
        item = await add_offer_fn(
            watchlist_id,
            marketplace_offer_id=body.marketplace_offer_id,
            canonical_product_id=body.canonical_product_id,
            product_label=body.product_label,
            target_price=body.target_price,
            currency=body.currency,
            notes=body.notes,
        )
        snapshot = await service.enrich_item(item)
    except (WatchlistValidationError, WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.get(
    "/{watchlist_id}/items/{item_id}",
    response_model=WatchlistItemPayload,
    summary="Get a watchlist item",
)
async def get_item(
    watchlist_id: str,
    item_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        item = service.get_item(item_id)
        if item.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        snapshot = await service.enrich_item(item)
    except (
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.patch(
    "/{watchlist_id}/items/{item_id}",
    response_model=WatchlistItemPayload,
    summary="Update a watchlist item",
)
async def update_item(
    watchlist_id: str,
    item_id: str,
    body: WatchlistItemUpdateRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        existing = service.get_item(item_id)
        if existing.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        item = service.update_item(
            item_id,
            product_label=body.product_label,
            target_price=body.target_price,
            clear_target_price=body.clear_target_price,
            currency=body.currency,
            search_query=body.search_query,
            enabled=body.enabled,
        )
        if body.clear_notes or body.notes is not None:
            set_notes = getattr(service, "set_item_notes", None)
            if callable(set_notes):
                item = set_notes(item_id, notes=None if body.clear_notes else body.notes)
        snapshot = await service.enrich_item(item)
    except (
        WatchlistValidationError,
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.put(
    "/{watchlist_id}/items/{item_id}/preferred-sellers",
    response_model=WatchlistItemPayload,
    summary="Set an item's preferred sellers (Sprint 19)",
)
async def set_item_preferred_sellers(
    watchlist_id: str,
    item_id: str,
    body: WatchlistItemPreferredSellersRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        existing = service.get_item(item_id)
        if existing.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        setter = getattr(service, "set_item_preferred_sellers", None)
        if not callable(setter):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferred sellers are not supported by this watchlist service.",
            )
        item = setter(item_id, sellers=body.sellers)
        snapshot = await service.enrich_item(item)
    except (
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.put(
    "/{watchlist_id}/items/{item_id}/preferred-marketplaces",
    response_model=WatchlistItemPayload,
    summary="Set an item's preferred marketplaces (Sprint 19)",
)
async def set_item_preferred_marketplaces(
    watchlist_id: str,
    item_id: str,
    body: WatchlistItemPreferredMarketplacesRequest,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> WatchlistItemPayload:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        existing = service.get_item(item_id)
        if existing.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        setter = getattr(service, "set_item_preferred_marketplaces", None)
        if not callable(setter):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Preferred marketplaces are not supported by this watchlist service.",
            )
        item = setter(item_id, marketplaces=body.marketplaces)
        snapshot = await service.enrich_item(item)
    except (
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_snapshot_payload(snapshot)


@router.delete(
    "/{watchlist_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a product from a watchlist",
)
async def delete_item(
    watchlist_id: str,
    item_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> None:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        existing = service.get_item(item_id)
        if existing.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        service.delete_item(item_id)
    except (
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
        WatchlistOwnershipError,
    ) as exc:
        raise _map_error(exc) from exc


@router.get(
    "/{watchlist_id}/alerts",
    response_model=AlertListResponse,
    summary="List alerts for a watchlist",
)
async def list_watchlist_alerts(
    watchlist_id: str,
    alert_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertListResponse:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        alerts = alert_service.list_alerts(
            watchlist_id=watchlist_id,
            alert_type=alert_type,
            status=status_filter,
            limit=limit,
        )
    except (WatchlistNotFoundError, WatchlistValidationError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return AlertListResponse(alerts=[to_alert_payload(a) for a in alerts])


@router.post(
    "/{watchlist_id}/check-alerts",
    response_model=AlertEvaluationResponse,
    summary="Evaluate alerts for one watchlist",
)
async def check_watchlist_alerts(
    watchlist_id: str,
    authorization: str | None = Header(default=None),
    service: WatchlistService = Depends(get_watchlist_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertEvaluationResponse:
    actor = _resolve_actor(authorization, user_platform, required=True)
    try:
        _get_watchlist_checked(service, watchlist_id, actor)
        result = await alert_service.evaluate_watchlist(watchlist_id)
    except (WatchlistNotFoundError, WatchlistOwnershipError) as exc:
        raise _map_error(exc) from exc
    return to_evaluation_response(result)


@alerts_router.get(
    "",
    response_model=AlertListResponse,
    summary="List recent alerts",
)
async def list_alerts(
    watchlist_id: str | None = None,
    item_id: str | None = None,
    alert_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertListResponse:
    try:
        alerts = alert_service.list_alerts(
            watchlist_id=watchlist_id,
            item_id=item_id,
            alert_type=alert_type,
            status=status_filter,
            limit=limit,
        )
    except (WatchlistNotFoundError, WatchlistValidationError) as exc:
        raise _map_error(exc) from exc
    return AlertListResponse(alerts=[to_alert_payload(a) for a in alerts])


@alerts_router.get(
    "/{alert_id}",
    response_model=AlertPayload,
    summary="Get an alert",
)
async def get_alert(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertPayload:
    try:
        alert = alert_service.get_alert(alert_id)
    except AlertNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_alert_payload(alert)


@alerts_router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertPayload,
    summary="Acknowledge an alert",
)
async def acknowledge_alert(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertPayload:
    try:
        alert = alert_service.acknowledge_alert(alert_id)
    except AlertNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_alert_payload(alert)


@alerts_router.post(
    "/{alert_id}/dismiss",
    response_model=AlertPayload,
    summary="Dismiss an alert",
)
async def dismiss_alert(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertPayload:
    try:
        alert = alert_service.dismiss_alert(alert_id)
    except AlertNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_alert_payload(alert)
