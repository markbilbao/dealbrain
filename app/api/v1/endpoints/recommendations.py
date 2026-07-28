"""Shopping recommendation API endpoints.

Routes delegate to :class:`ShoppingRecommendationService`. No recommendation
business logic lives here.
"""

from fastapi import APIRouter, Depends, Query

from app.api.v1.mappers.recommendation import to_shopping_recommendation_response
from app.core.dependencies import get_shopping_recommendation_service
from app.schemas.recommendation import ShoppingRecommendationSearchResponse
from app.services.shopping_recommendation_service import ShoppingRecommendationService

router = APIRouter(prefix="/recommendations")


@router.get(
    "/search",
    response_model=ShoppingRecommendationSearchResponse,
    summary="Search marketplaces and return explainable purchase recommendations",
)
def search_recommendations(
    q: str = Query(..., min_length=1, description="Search query"),
    service: ShoppingRecommendationService = Depends(get_shopping_recommendation_service),
) -> ShoppingRecommendationSearchResponse:
    """Rank mocked marketplace listings and explain a purchase decision."""
    result = service.recommend(q)
    return to_shopping_recommendation_response(result)
