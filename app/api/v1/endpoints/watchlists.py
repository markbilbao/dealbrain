"""Watchlists & Price Alerts API endpoints.

CRUD for watchlists/items, alert listing, and manual alert evaluation.
Mock notifications only — no email, SMS, or push delivery.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.watchlists import (
    to_alert_payload,
    to_evaluation_response,
    to_item_payload,
    to_snapshot_payload,
    to_watchlist_payload,
)
from app.core.dependencies import get_alert_service, get_watchlist_service
from app.domain.exceptions import (
    AlertNotFoundError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
    WatchlistValidationError,
)
from app.schemas.watchlists import (
    AlertEvaluationResponse,
    AlertListResponse,
    AlertPayload,
    WatchlistCreateRequest,
    WatchlistItemCreateRequest,
    WatchlistItemListResponse,
    WatchlistItemPayload,
    WatchlistItemUpdateRequest,
    WatchlistListResponse,
    WatchlistPayload,
    WatchlistUpdateRequest,
)
from app.services.alert_service import AlertService
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/watchlists")
alerts_router = APIRouter(prefix="/alerts")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WatchlistValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(
        exc,
        (WatchlistNotFoundError, WatchlistItemNotFoundError, AlertNotFoundError),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "",
    response_model=WatchlistListResponse,
    summary="List watchlists",
)
async def list_watchlists(
    enabled: bool | None = None,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistListResponse:
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistPayload:
    try:
        watchlist = service.create_watchlist(
            name=body.name,
            owner_id=body.owner_id,
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistPayload:
    try:
        watchlist = service.get_watchlist(watchlist_id)
    except WatchlistNotFoundError as exc:
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistPayload:
    try:
        watchlist = service.update_watchlist(
            watchlist_id,
            name=body.name,
            owner_id=body.owner_id,
            description=body.description,
            enabled=body.enabled,
        )
    except (WatchlistValidationError, WatchlistNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_watchlist_payload(
        watchlist,
        item_count=len(service.list_items(watchlist_id)),
    )


@router.delete(
    "/{watchlist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a watchlist",
)
async def delete_watchlist(
    watchlist_id: str,
    service: WatchlistService = Depends(get_watchlist_service),
) -> None:
    try:
        service.delete_watchlist(watchlist_id)
    except WatchlistNotFoundError as exc:
        raise _map_error(exc) from exc


@router.get(
    "/{watchlist_id}/items",
    response_model=WatchlistItemListResponse,
    summary="List watchlist items (enriched)",
)
async def list_items(
    watchlist_id: str,
    enabled: bool | None = None,
    enrich: bool = Query(True),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemListResponse:
    try:
        if enrich:
            snapshots = await service.list_enriched_items(watchlist_id, enabled=enabled)
            return WatchlistItemListResponse(
                items=[to_snapshot_payload(s) for s in snapshots]
            )
        items = service.list_items(watchlist_id, enabled=enabled)
        return WatchlistItemListResponse(items=[to_item_payload(i) for i in items])
    except WatchlistNotFoundError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/{watchlist_id}/items",
    response_model=WatchlistItemPayload,
    summary="Add a product to a watchlist",
)
async def add_item(
    watchlist_id: str,
    body: WatchlistItemCreateRequest,
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemPayload:
    try:
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
        snapshot = await service.enrich_item(item)
    except (WatchlistValidationError, WatchlistNotFoundError) as exc:
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemPayload:
    try:
        service.get_watchlist(watchlist_id)
        item = service.get_item(item_id)
        if item.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        snapshot = await service.enrich_item(item)
    except (WatchlistNotFoundError, WatchlistItemNotFoundError) as exc:
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistItemPayload:
    try:
        service.get_watchlist(watchlist_id)
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
        snapshot = await service.enrich_item(item)
    except (
        WatchlistValidationError,
        WatchlistNotFoundError,
        WatchlistItemNotFoundError,
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
    service: WatchlistService = Depends(get_watchlist_service),
) -> None:
    try:
        service.get_watchlist(watchlist_id)
        existing = service.get_item(item_id)
        if existing.watchlist_id != watchlist_id:
            raise WatchlistItemNotFoundError(item_id)
        service.delete_item(item_id)
    except (WatchlistNotFoundError, WatchlistItemNotFoundError) as exc:
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
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertListResponse:
    try:
        alerts = alert_service.list_alerts(
            watchlist_id=watchlist_id,
            alert_type=alert_type,
            status=status_filter,
            limit=limit,
        )
    except (WatchlistNotFoundError, WatchlistValidationError) as exc:
        raise _map_error(exc) from exc
    return AlertListResponse(alerts=[to_alert_payload(a) for a in alerts])


@router.post(
    "/{watchlist_id}/check-alerts",
    response_model=AlertEvaluationResponse,
    summary="Evaluate alerts for one watchlist",
)
async def check_watchlist_alerts(
    watchlist_id: str,
    alert_service: AlertService = Depends(get_alert_service),
) -> AlertEvaluationResponse:
    try:
        result = await alert_service.evaluate_watchlist(watchlist_id)
    except WatchlistNotFoundError as exc:
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
