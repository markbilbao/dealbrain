"""Shopping recommendation API endpoints.

Routes delegate to :class:`ShoppingRecommendationService`. No recommendation
business logic lives here.
"""

from fastapi import APIRouter, Depends, Query

from app.api.v1.mappers.recommendation import to_shopping_recommendation_response
from app.core.dependencies import (
    get_launch_performance_service,
    get_shopping_recommendation_service,
)
from app.schemas.recommendation import ShoppingRecommendationSearchResponse
from app.services.launch_performance_service import LaunchPerformanceService
from app.services.shopping_recommendation_service import ShoppingRecommendationService

router = APIRouter(prefix="/recommendations")


@router.get(
    "/search",
    response_model=ShoppingRecommendationSearchResponse,
    summary="Search marketplaces and return explainable purchase recommendations",
    description=(
        "Kind S search aggregate. Buy/Wait/Consider/Avoid decisions are service-owned. "
        "Caller-controlled ``sort`` is not supported. Not paginated."
    ),
)
def search_recommendations(
    q: str = Query(..., min_length=1, description="Search query"),
    service: ShoppingRecommendationService = Depends(get_shopping_recommendation_service),
    performance: LaunchPerformanceService = Depends(get_launch_performance_service),
) -> ShoppingRecommendationSearchResponse:
    """Rank mocked marketplace listings and explain a purchase decision."""

    def _compute() -> ShoppingRecommendationSearchResponse:
        return to_shopping_recommendation_response(service.recommend(q))

    # Identical query → identical ranking; cache never reorders results.
    return performance.cached("recommendations", _compute, q)
