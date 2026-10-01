"""Consent-gated first-party analytics collection."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.analytics.request_context import analytics_context_for_request, authorized_owner
from app.analytics.service import ProductAnalyticsService
from app.core.dependencies import get_bound_decision_resolver, get_product_analytics_service
from app.feedback.decisions import BoundDecision
from app.infrastructure.persistence.errors import PersistenceError
from app.schemas.product_analytics import (
    ProductAnalyticsEventRequest,
    ProductAnalyticsEventResponse,
)

router = APIRouter(prefix="/analytics")

_CLOSED_RESULTS = {"schema_rejected": status.HTTP_400_BAD_REQUEST}


@router.post(
    "/events",
    response_model=ProductAnalyticsEventResponse,
    summary="Record one allow-listed product analytics event",
    description=(
        "Stores a first-party event only when analytics consent is on. "
        "Consent off returns suppressed_no_consent and writes no analytics row. "
        "The server derives identity, consent, and decision hash."
    ),
)
async def collect_product_event(
    body: ProductAnalyticsEventRequest,
    request: Request,
    response: Response,
    analytics: ProductAnalyticsService = Depends(get_product_analytics_service),
    resolve_decision: Any = Depends(get_bound_decision_resolver),
) -> ProductAnalyticsEventResponse:
    payload = body.client_payload()
    decision_id = payload.pop("decision_id", None)
    bound: BoundDecision | None = None
    if isinstance(decision_id, str) and decision_id:
        bound = resolve_decision(decision_id, authorized_owner(request))
    context = analytics_context_for_request(
        request,
        response,
        bound_decision=bound,
        mint_subject=True,
    )
    try:
        result = analytics.record_client_event(payload, context)
    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics storage is unavailable.",
        ) from exc
    if result.status == "schema_rejected":
        raise HTTPException(
            status_code=_CLOSED_RESULTS["schema_rejected"],
            detail=result.reason or "schema_rejected",
        )
    if result.status == "identity_conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="identity_conflict",
        )
    return ProductAnalyticsEventResponse(result=result.status, event_id=result.event_id)
