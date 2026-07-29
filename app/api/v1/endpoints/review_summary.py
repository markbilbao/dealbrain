"""AI Review Summary API endpoints.

Multi-model architecture with deterministic fallback. External AI providers
are disabled by default and never receive client-supplied API keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.review_summary import to_summary_response
from app.core.dependencies import get_review_summary_service
from app.domain.exceptions import (
    ReviewSummaryNotFoundError,
    ReviewSummaryValidationError,
)
from app.schemas.review_summary import ReviewSummaryResponse
from app.services.review_summary_service import ReviewSummaryService

router = APIRouter(prefix="/review-summary")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ReviewSummaryValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, ReviewSummaryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/demo",
    response_model=ReviewSummaryResponse,
    summary="Demo AI review summary for iPhone 17 Pro Max",
)
async def demo_review_summary(
    mode: str | None = Query(
        default=None,
        description="Optional analysis mode (economy|balanced|maximum). "
        "Cannot exceed server AI_REVIEW_MODE.",
    ),
    service: ReviewSummaryService = Depends(get_review_summary_service),
) -> ReviewSummaryResponse:
    try:
        summary = service.demo_summary(mode=mode)
    except (ReviewSummaryValidationError, ReviewSummaryNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_summary_response(summary)


@router.get(
    "/{product_id}",
    response_model=ReviewSummaryResponse,
    summary="AI review summary for a product",
)
async def get_review_summary(
    product_id: str,
    mode: str | None = Query(
        default=None,
        description="Optional analysis mode (economy|balanced|maximum). "
        "Cannot exceed server AI_REVIEW_MODE.",
    ),
    service: ReviewSummaryService = Depends(get_review_summary_service),
) -> ReviewSummaryResponse:
    try:
        summary = service.get_summary(product_id, mode=mode)
    except (ReviewSummaryValidationError, ReviewSummaryNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_summary_response(summary)
