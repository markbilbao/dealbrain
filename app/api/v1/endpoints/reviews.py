"""Review & Rating Intelligence API endpoints.

Mock collectors only — no live scraping, HTTP requests, or browser automation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.reviews import (
    to_collect_response,
    to_compare_response,
    to_history_response,
    to_latest_response,
)
from app.core.dependencies import get_review_service
from app.domain.exceptions import ReviewNotFoundError, ReviewValidationError
from app.intelligence.reviews.fixtures import resolve_product_label
from app.schemas.reviews import (
    ReviewCollectRequest,
    ReviewCollectResponse,
    ReviewCompareResponse,
    ReviewHistoryResponse,
    ReviewLatestResponse,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ReviewValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, ReviewNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/collect",
    response_model=ReviewCollectResponse,
    summary="Collect mock marketplace reviews for a product",
)
async def collect_reviews(
    body: ReviewCollectRequest,
    service: ReviewService = Depends(get_review_service),
) -> ReviewCollectResponse:
    try:
        result = service.collect_reviews(
            body.product_id,
            product_label=body.product_label,
            marketplaces=body.marketplaces,
        )
    except (ReviewValidationError, ReviewNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_collect_response(
        result,
        overall_rating=service.overall_rating(result.product_id),
        total_review_count=service.total_review_count(result.product_id),
    )


@router.get(
    "/history/{product_id}",
    response_model=ReviewHistoryResponse,
    summary="Review snapshot history for a product",
)
async def review_history(
    product_id: str,
    marketplace: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: ReviewService = Depends(get_review_service),
) -> ReviewHistoryResponse:
    try:
        history = service.review_history(
            product_id,
            marketplace=marketplace,
            limit=limit,
        )
    except (ReviewValidationError, ReviewNotFoundError) as exc:
        raise _map_error(exc) from exc
    label = resolve_product_label(product_id)
    for snap in history:
        if snap.product_label:
            label = snap.product_label
            break
    return to_history_response(product_id.strip(), label, history)


@router.get(
    "/compare/{product_id}",
    response_model=ReviewCompareResponse,
    summary="Compare marketplace ratings for a product",
)
async def compare_marketplaces(
    product_id: str,
    service: ReviewService = Depends(get_review_service),
) -> ReviewCompareResponse:
    try:
        comparison = service.compare_marketplaces(product_id)
    except (ReviewValidationError, ReviewNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_compare_response(comparison)


@router.get(
    "/{product_id}",
    response_model=ReviewLatestResponse,
    summary="Latest marketplace reviews for a product",
)
async def latest_reviews(
    product_id: str,
    service: ReviewService = Depends(get_review_service),
) -> ReviewLatestResponse:
    try:
        summaries = service.latest_reviews(product_id)
        comparison = service.compare_marketplaces(product_id)
    except (ReviewValidationError, ReviewNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_latest_response(
        comparison.product_id,
        comparison.product,
        summaries,
        overall_rating=comparison.overall_rating,
        total_review_count=comparison.total_review_count,
    )
