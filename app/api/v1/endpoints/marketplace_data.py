"""Marketplace Data Synchronization API endpoints — Sprint 18.

Operational write endpoints require Bearer auth when user platform is enabled.
Secrets are never returned. Simulated live connectors are clearly labeled.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.v1.endpoints.auth import extract_bearer_token
from app.api.v1.mappers.marketplace_data import (
    to_conflict_payload,
    to_connector_payload,
    to_health_payload,
    to_import_error_payload,
    to_import_payload,
    to_offer_payload,
    to_source_payload,
    to_sync_payload,
)
from app.core.config import settings
from app.core.dependencies import get_marketplace_data_service, get_user_platform_service
from app.domain.entities.marketplace_data import SyncMode
from app.domain.exceptions import (
    MarketplaceDataAuthError,
    MarketplaceDataConflictError,
    MarketplaceDataNotFoundError,
    MarketplaceDataRateLimitError,
    MarketplaceDataValidationError,
    UserPlatformAuthError,
)
from app.schemas.marketplace_data import (
    ConnectorCapabilityPayload,
    ConnectorHealthPayload,
    ConnectorListResponse,
    ConnectorTestResponse,
    ImportBatchPayload,
    ImportCreateRequest,
    ImportErrorListResponse,
    InventoryHistoryListResponse,
    MarketplaceDataDemoResponse,
    MarketplaceOfferListResponse,
    MarketplaceOfferPayload,
    MarketplaceSourceListResponse,
    PriceHistoryListResponse,
    SyncConflictListResponse,
    SyncCreateRequest,
    SyncJobPayload,
)
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.user_platform_service import UserPlatformService

router = APIRouter(prefix="/marketplaces")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, MarketplaceDataValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, MarketplaceDataAuthError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    if isinstance(exc, MarketplaceDataNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, MarketplaceDataConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    if isinstance(exc, MarketplaceDataRateLimitError):
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Marketplace data request failed.",
    )


def _resolve_actor(
    authorization: str | None,
    user_platform: UserPlatformService,
    *,
    required: bool,
) -> str | None:
    token = extract_bearer_token(authorization)
    if token is None:
        if required and settings.user_platform_enabled:
            raise MarketplaceDataAuthError("Authentication required.")
        return None
    try:
        user = user_platform.require_user(token)
    except UserPlatformAuthError as exc:
        raise MarketplaceDataAuthError(exc.message) from exc
    return user.user_id


@router.get(
    "/sources", response_model=MarketplaceSourceListResponse, summary="List marketplace sources"
)
async def list_sources(
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> MarketplaceSourceListResponse:
    sources = [to_source_payload(item) for item in service.list_sources()]
    return MarketplaceSourceListResponse(sources=sources, count=len(sources))


@router.get(
    "/connectors",
    response_model=ConnectorListResponse,
    summary="List marketplace connectors",
)
async def list_connectors(
    include_stubs: bool = Query(True),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> ConnectorListResponse:
    connectors = [
        to_connector_payload(item) for item in service.list_connectors(include_stubs=include_stubs)
    ]
    return ConnectorListResponse(connectors=connectors, count=len(connectors))


@router.get(
    "/connectors/{connector_id}",
    response_model=ConnectorCapabilityPayload,
    summary="Get connector details (secrets redacted)",
)
async def get_connector(
    connector_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> ConnectorCapabilityPayload:
    try:
        payload = service.get_connector(connector_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return ConnectorCapabilityPayload(**payload)


@router.post(
    "/connectors/{connector_id}/test",
    response_model=ConnectorTestResponse,
    summary="Test connector configuration",
)
async def test_connector(
    connector_id: str,
    authorization: str | None = Header(default=None),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> ConnectorTestResponse:
    try:
        actor = _resolve_actor(authorization, user_platform, required=True)
        result = service.test_connector(connector_id, actor=actor)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return ConnectorTestResponse(**result)


@router.get(
    "/connectors/{connector_id}/health",
    response_model=ConnectorHealthPayload,
    summary="Get connector health",
)
async def get_connector_health(
    connector_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> ConnectorHealthPayload:
    try:
        health = service.get_connector_health(connector_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_health_payload(health)


@router.post(
    "/imports",
    response_model=ImportBatchPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Import marketplace products from CSV/JSON",
)
async def create_import(
    body: ImportCreateRequest,
    authorization: str | None = Header(default=None),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> ImportBatchPayload:
    try:
        actor = _resolve_actor(authorization, user_platform, required=True)
        batch = service.import_payload(
            filename=body.filename,
            payload=body.content,
            content_type=body.content_type,
            field_mapping=body.field_mapping or None,
            idempotency_key=body.idempotency_key,
            actor=actor,
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_import_payload(batch)


@router.get("/imports/{batch_id}", response_model=ImportBatchPayload, summary="Get import batch")
async def get_import(
    batch_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> ImportBatchPayload:
    try:
        batch = service.get_import(batch_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_import_payload(batch)


@router.get(
    "/imports/{batch_id}/errors",
    response_model=ImportErrorListResponse,
    summary="List import row errors",
)
async def get_import_errors(
    batch_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> ImportErrorListResponse:
    try:
        errors = [to_import_error_payload(item) for item in service.get_import_errors(batch_id)]
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return ImportErrorListResponse(batch_id=batch_id, errors=errors, count=len(errors))


@router.post(
    "/sync",
    response_model=SyncJobPayload,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger marketplace synchronization",
)
async def create_sync(
    body: SyncCreateRequest,
    authorization: str | None = Header(default=None),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> SyncJobPayload:
    try:
        actor = _resolve_actor(authorization, user_platform, required=True)
        mode = SyncMode.FULL if body.mode == "full" else SyncMode.INCREMENTAL
        job = service.trigger_sync(
            body.connector_id,
            mode=mode,
            idempotency_key=body.idempotency_key,
            actor=actor,
            query=body.query,
        )
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_sync_payload(job)


@router.get("/sync/{job_id}", response_model=SyncJobPayload, summary="Get sync job")
async def get_sync(
    job_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> SyncJobPayload:
    try:
        job = service.get_sync(job_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_sync_payload(job)


@router.get(
    "/sync/{job_id}/conflicts",
    response_model=SyncConflictListResponse,
    summary="List sync conflicts",
)
async def get_sync_conflicts(
    job_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> SyncConflictListResponse:
    try:
        conflicts = [to_conflict_payload(item) for item in service.get_sync_conflicts(job_id)]
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return SyncConflictListResponse(sync_job_id=job_id, conflicts=conflicts, count=len(conflicts))


@router.get(
    "/offers", response_model=MarketplaceOfferListResponse, summary="List normalized offers"
)
async def list_offers(
    source_mode: str | None = None,
    marketplace: str | None = None,
    product_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> MarketplaceOfferListResponse:
    offers = [
        to_offer_payload(item)
        for item in service.list_offers(
            source_mode=source_mode,
            marketplace=marketplace,
            product_id=product_id,
            limit=limit,
        )
    ]
    return MarketplaceOfferListResponse(offers=offers, count=len(offers))


@router.get("/offers/{offer_id}", response_model=MarketplaceOfferPayload, summary="Get offer")
async def get_offer(
    offer_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> MarketplaceOfferPayload:
    try:
        offer = service.get_offer(offer_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_offer_payload(offer)


@router.post(
    "/demo/seed",
    response_model=MarketplaceDataDemoResponse,
    summary="Seed deterministic fixture and simulated-live demos",
)
async def seed_demo(
    authorization: str | None = Header(default=None),
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
    user_platform: UserPlatformService = Depends(get_user_platform_service),
) -> MarketplaceDataDemoResponse:
    try:
        actor = _resolve_actor(authorization, user_platform, required=True)
        payload = service.seed_demo_data(actor=actor)
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return MarketplaceDataDemoResponse(**payload)


# Product-scoped history routes (also mounted under /products via products router extension)
history_router = APIRouter(prefix="/products")


@history_router.get(
    "/{product_id}/price-history",
    response_model=PriceHistoryListResponse,
    summary="Marketplace data price history for a product",
)
async def product_price_history(
    product_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> PriceHistoryListResponse:
    snapshots = [item.to_dict() for item in service.list_price_history(product_id)]
    return PriceHistoryListResponse(
        product_id=product_id, snapshots=snapshots, count=len(snapshots)
    )


@history_router.get(
    "/{product_id}/inventory-history",
    response_model=InventoryHistoryListResponse,
    summary="Marketplace data inventory history for a product",
)
async def product_inventory_history(
    product_id: str,
    service: MarketplaceDataService = Depends(get_marketplace_data_service),
) -> InventoryHistoryListResponse:
    snapshots = [item.to_dict() for item in service.list_inventory_history(product_id)]
    return InventoryHistoryListResponse(
        product_id=product_id, snapshots=snapshots, count=len(snapshots)
    )
