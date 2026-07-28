"""Product Intelligence API endpoints.

Routes delegate to :class:`ProductIntelligenceService` and map domain results
to HTTP schemas. No Product Identity business logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.mappers.intelligence import to_match_response, to_parse_response
from app.core.dependencies import get_product_intelligence_service
from app.domain.exceptions import UnsupportedProductError
from app.schemas.intelligence import (
    IntelligenceMatchRequest,
    IntelligenceMatchResponse,
    IntelligenceParseRequest,
    IntelligenceParseResponse,
)
from app.services.product_intelligence_service import ProductIntelligenceService

router = APIRouter(prefix="/intelligence")


@router.post(
    "/parse",
    response_model=IntelligenceParseResponse,
    summary="Parse a messy product listing into a canonical product",
)
async def parse_product_listing(
    payload: IntelligenceParseRequest,
    service: ProductIntelligenceService = Depends(get_product_intelligence_service),
) -> IntelligenceParseResponse:
    """Run Product Intelligence: parse → explain → resolve canonical identity."""
    try:
        result = await service.parse_listing(payload.title)
    except UnsupportedProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.reason,
        ) from exc
    return to_parse_response(result)


@router.post(
    "/match",
    response_model=IntelligenceMatchResponse,
    summary="Match two product listings to the same exact variant",
)
async def match_product_listings(
    payload: IntelligenceMatchRequest,
    service: ProductIntelligenceService = Depends(get_product_intelligence_service),
) -> IntelligenceMatchResponse:
    """Run Product Matching: parse both titles → compare canonical attributes."""
    try:
        result = service.match_listings(payload.title_a, payload.title_b)
    except UnsupportedProductError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.reason,
        ) from exc
    return to_match_response(result)
