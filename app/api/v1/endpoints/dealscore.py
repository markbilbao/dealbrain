"""DealScore API endpoints.

Routes delegate to :class:`DealRecommendationService`. No DealScore business
logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.dealscore import to_dealscore_search_response
from app.core.dependencies import get_deal_recommendation_service, get_launch_performance_service
from app.domain.exceptions import DealScoreValidationError
from app.schemas.dealscore import DealScoreSearchResponse
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.launch_performance_service import LaunchPerformanceService

router = APIRouter(prefix="/dealscore")


@router.get(
    "/search",
    response_model=DealScoreSearchResponse,
    summary="Search marketplaces and rank listings by DealScore",
    description=(
        "Kind S search aggregate. Organic DealScore ordering is service-owned. "
        "Caller-controlled ``sort`` is not supported and must not influence ranking. "
        "Not paginated."
    ),
)
def search_dealscore(
    q: str = Query(..., min_length=1, description="Search query"),
    service: DealRecommendationService = Depends(get_deal_recommendation_service),
    performance: LaunchPerformanceService = Depends(get_launch_performance_service),
) -> DealScoreSearchResponse:
    """Evaluate mocked marketplace listings and return ranked DealScores."""

    def _compute() -> DealScoreSearchResponse:
        try:
            result = service.recommend(q)
        except DealScoreValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.message,
            ) from exc
        return to_dealscore_search_response(result)

    # Cache identical queries only — never alters DealScore ranking logic.
    return performance.cached("search", _compute, "dealscore", q)
