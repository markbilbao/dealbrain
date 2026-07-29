"""Community Intelligence Platform API endpoints.

Provider-neutral evidence-first community aggregation. Live connectors and
external AI are disabled by default.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.community_intelligence import (
    to_dashboard_response,
    to_evidence_response,
    to_product_response,
    to_timeline_response,
    to_topics_response,
)
from app.core.dependencies import get_community_intelligence_service
from app.domain.exceptions import (
    CommunityIntelligenceNotFoundError,
    CommunityIntelligenceValidationError,
)
from app.schemas.community_intelligence import (
    CommunityDashboardResponse,
    CommunityEvidenceResponse,
    CommunityMetaResponse,
    CommunityProductResponse,
    CommunityTimelineResponse,
    CommunityTopicsResponse,
)
from app.services.community_intelligence_service import CommunityIntelligenceService

router = APIRouter(prefix="/community")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CommunityIntelligenceValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, CommunityIntelligenceNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Community intelligence failed to process the request.",
    )


@router.get(
    "/demo",
    response_model=CommunityDashboardResponse,
    summary="Community Intelligence demo dashboard",
)
async def community_demo(
    mode: str | None = Query(default=None, description="Optional analysis mode"),
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityDashboardResponse:
    try:
        dashboard = service.demo(mode=mode)
    except (CommunityIntelligenceValidationError, CommunityIntelligenceNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_dashboard_response(dashboard)


@router.get(
    "/meta",
    response_model=CommunityMetaResponse,
    summary="Community Intelligence metadata and connector status",
)
async def community_meta(
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityMetaResponse:
    meta = service.meta()
    return CommunityMetaResponse(**meta)


@router.get(
    "/product/{product_id}",
    response_model=CommunityProductResponse,
    summary="Community intelligence for a product",
)
async def community_product(
    product_id: str,
    mode: str | None = Query(default=None),
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityProductResponse:
    try:
        product = service.get_product(product_id, mode=mode)
    except (CommunityIntelligenceValidationError, CommunityIntelligenceNotFoundError) as exc:
        raise _map_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_product_response(product)


@router.get(
    "/evidence/{evidence_id}",
    response_model=CommunityEvidenceResponse,
    summary="Fetch a single community evidence item",
)
async def community_evidence(
    evidence_id: str,
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityEvidenceResponse:
    try:
        evidence = service.get_evidence(evidence_id)
    except (CommunityIntelligenceValidationError, CommunityIntelligenceNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_evidence_response(evidence)


@router.get(
    "/topics/{product_id}",
    response_model=CommunityTopicsResponse,
    summary="Community topics for a product",
)
async def community_topics(
    product_id: str,
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityTopicsResponse:
    try:
        topics = service.get_topics(product_id)
    except (CommunityIntelligenceValidationError, CommunityIntelligenceNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_topics_response(product_id, topics)


@router.get(
    "/timeline/{product_id}",
    response_model=CommunityTimelineResponse,
    summary="Community timeline for a product",
)
async def community_timeline(
    product_id: str,
    service: CommunityIntelligenceService = Depends(get_community_intelligence_service),
) -> CommunityTimelineResponse:
    try:
        timeline = service.get_timeline(product_id)
    except (CommunityIntelligenceValidationError, CommunityIntelligenceNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_timeline_response(product_id, timeline)
