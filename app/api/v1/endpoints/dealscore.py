"""DealScore API endpoints.

Routes delegate to :class:`DealRecommendationService`. No DealScore business
logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.dealscore import to_dealscore_search_response
from app.core.dependencies import get_deal_recommendation_service
from app.domain.exceptions import DealScoreValidationError
from app.schemas.dealscore import DealScoreSearchResponse
from app.services.deal_recommendation_service import DealRecommendationService

router = APIRouter(prefix="/dealscore")


@router.get(
    "/search",
    response_model=DealScoreSearchResponse,
    summary="Search marketplaces and rank listings by DealScore",
)
def search_dealscore(
    q: str = Query(..., min_length=1, description="Search query"),
    service: DealRecommendationService = Depends(get_deal_recommendation_service),
) -> DealScoreSearchResponse:
    """Evaluate mocked marketplace listings and return ranked DealScores."""
    try:
        result = service.recommend(q)
    except DealScoreValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_dealscore_search_response(result)
