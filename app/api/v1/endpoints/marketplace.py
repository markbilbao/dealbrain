"""Marketplace Intelligence API endpoints.

Routes delegate to :class:`MarketplaceIntelligenceService` and map domain
results to HTTP schemas. No marketplace business logic lives here.
"""

from fastapi import APIRouter, Depends, Query

from app.api.v1.mappers.marketplace import to_search_response
from app.core.dependencies import (
    get_launch_performance_service,
    get_marketplace_intelligence_service,
)
from app.schemas.marketplace import MarketplaceSearchResponse
from app.services.launch_performance_service import LaunchPerformanceService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService

router = APIRouter(prefix="/marketplace")


@router.get(
    "/search",
    response_model=MarketplaceSearchResponse,
    summary="Search mocked marketplace listings across connected marketplaces",
    description=(
        "Kind S search aggregate. Organic marketplace ordering is service-owned. "
        "Caller-controlled ``sort`` is not supported. Not paginated."
    ),
)
def search_marketplaces(
    q: str = Query(..., min_length=1, description="Search query"),
    service: MarketplaceIntelligenceService = Depends(get_marketplace_intelligence_service),
    performance: LaunchPerformanceService = Depends(get_launch_performance_service),
) -> MarketplaceSearchResponse:
    """Aggregate normalized listings from all registered marketplace connectors."""

    def _compute() -> MarketplaceSearchResponse:
        return to_search_response(service.search(q))

    return performance.cached("search", _compute, "marketplace", q)
