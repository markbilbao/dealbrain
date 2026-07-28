"""Price History API endpoints.

Routes delegate to :class:`PriceHistoryService`. No price-history business
logic lives here. No future price predictions are exposed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.price_history import (
    to_history_response,
    to_search_response,
    to_snapshot_payload,
)
from app.core.dependencies import get_price_history_service
from app.domain.exceptions import PriceHistoryValidationError
from app.schemas.price_history import (
    PriceHistoryResponse,
    PriceHistorySearchResponse,
    PriceSnapshotsCreateRequest,
    PriceSnapshotsCreateResponse,
)
from app.services.price_history_service import PriceHistoryService, snapshot_from_payload

router = APIRouter(prefix="/price-history")


@router.post(
    "/snapshots",
    response_model=PriceSnapshotsCreateResponse,
    summary="Record one or more normalized listing price snapshots",
)
async def create_snapshots(
    body: PriceSnapshotsCreateRequest,
    service: PriceHistoryService = Depends(get_price_history_service),
) -> PriceSnapshotsCreateResponse:
    """Persist timestamped marketplace observations with duplicate protection."""
    try:
        snapshots = []
        for item in body.snapshots:
            snapshot_id = UUID(item.snapshot_id) if item.snapshot_id else None
            snapshots.append(
                snapshot_from_payload(
                    canonical_product_id=item.canonical_product_id,
                    marketplace=item.marketplace,
                    listing_id=item.listing_id,
                    currency=item.currency,
                    item_price=item.item_price,
                    shipping_cost=item.shipping_cost,
                    availability=item.availability,
                    observed_at=item.observed_at,
                    seller_name=item.seller_name,
                    snapshot_id=snapshot_id,
                )
            )
        saved = await service.record_snapshots(snapshots)
    except (PriceHistoryValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return PriceSnapshotsCreateResponse(saved=[to_snapshot_payload(s) for s in saved])


@router.get(
    "/products/{canonical_product_id}",
    response_model=PriceHistoryResponse,
    summary="Return recorded price history for a canonical product",
)
async def get_product_price_history(
    canonical_product_id: str,
    service: PriceHistoryService = Depends(get_price_history_service),
) -> PriceHistoryResponse:
    """Return stored observations and statistics for one canonical product."""
    try:
        history = await service.get_product_history(canonical_product_id)
    except PriceHistoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_history_response(history)


@router.get(
    "/listings/{listing_id}",
    response_model=PriceHistoryResponse,
    summary="Return recorded price history for one marketplace listing",
)
async def get_listing_price_history(
    listing_id: str,
    service: PriceHistoryService = Depends(get_price_history_service),
) -> PriceHistoryResponse:
    """Return stored observations and statistics for one listing id."""
    try:
        history = await service.get_listing_history(listing_id)
    except PriceHistoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_history_response(history)


@router.get(
    "/search",
    response_model=PriceHistorySearchResponse,
    summary="Search marketplaces, record current prices, return history stats",
)
async def search_price_history(
    q: str = Query(..., min_length=1, description="Search query"),
    service: PriceHistoryService = Depends(get_price_history_service),
) -> PriceHistorySearchResponse:
    """Use the marketplace + product pipeline, record observations, return history."""
    try:
        result = await service.search_and_record(q)
    except PriceHistoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_search_response(result)


@router.get(
    "/products/{canonical_product_id}/range",
    response_model=PriceHistoryResponse,
    summary="Return product price history within an optional date range",
    include_in_schema=True,
)
async def get_product_price_history_range(
    canonical_product_id: str,
    start: datetime | None = Query(None, description="Inclusive start (ISO-8601)"),
    end: datetime | None = Query(None, description="Inclusive end (ISO-8601)"),
    service: PriceHistoryService = Depends(get_price_history_service),
) -> PriceHistoryResponse:
    """Date-range filter over stored observations for a canonical product."""
    try:
        history = await service.get_history_in_range(
            canonical_product_id=canonical_product_id,
            start=start,
            end=end,
        )
    except PriceHistoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_history_response(history)
