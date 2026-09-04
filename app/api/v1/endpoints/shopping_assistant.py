"""AI Shopping Assistant API endpoints.

Evidence-first shopping Q&A with deterministic fallback. External AI providers
are disabled by default and never receive client-supplied API keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.v1.mappers.shopping_assistant import to_assistant_response
from app.consumer.decision_owner import OWNER_COOKIE, parse_owner_cookie
from app.consumer.location import DELIVERY_COOKIE, parse_delivery_cookie
from app.consumer.shopping_market import (
    SHOPPING_MARKET_COOKIE,
    shopping_market_from_cookie,
)
from app.core.config import settings
from app.core.dependencies import get_shopping_assistant_service
from app.domain.exceptions import (
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
    ShoppingAssistantValidationError,
)
from app.intelligence.shopping_assistant.fixtures import DEMO_QUERIES
from app.schemas.shopping_assistant import (
    ShoppingAssistantDemoMeta,
    ShoppingAssistantQueryRequest,
    ShoppingAssistantResponse,
)
from app.services.shopping_assistant_service import ShoppingAssistantService

router = APIRouter(prefix="/shopping-assistant")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ShoppingAssistantValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, DecisionSnapshotIntegrityError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Decision evidence is not usable."
        )
    if isinstance(exc, (ShoppingAssistantNotFoundError, DecisionSnapshotOwnershipError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found.")
    # Never return provider stack traces or private errors.
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Shopping assistant failed to process the request.",
    )


@router.get(
    "/demo",
    response_model=ShoppingAssistantResponse,
    summary="Demo AI shopping assistant recommendation",
)
async def demo_shopping_assistant(
    mode: str | None = Query(
        default=None,
        description="Optional analysis mode (economy|balanced|maximum). "
        "Cannot exceed server AI_SHOPPING_MODE.",
    ),
    service: ShoppingAssistantService = Depends(get_shopping_assistant_service),
) -> ShoppingAssistantResponse:
    try:
        result = service.demo(mode=mode)
    except (ShoppingAssistantValidationError, ShoppingAssistantNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_assistant_response(result, allowed_modes=service.allowed_modes())


@router.get(
    "/meta",
    response_model=ShoppingAssistantDemoMeta,
    summary="Shopping assistant demo metadata and allowed modes",
)
async def shopping_assistant_meta(
    service: ShoppingAssistantService = Depends(get_shopping_assistant_service),
) -> ShoppingAssistantDemoMeta:
    return ShoppingAssistantDemoMeta(
        example_queries=list(DEMO_QUERIES),
        allowed_modes=service.allowed_modes(),
        data_status="mock",
        ai_enabled=settings.ai_shopping_enabled,
    )


@router.post(
    "/query",
    response_model=ShoppingAssistantResponse,
    summary="Ask the AI shopping assistant a product-shopping question",
    description=(
        "Organic Shopping Assistant ranking is service-owned. "
        "Caller-controlled sorting of organic results is not supported."
    ),
)
async def query_shopping_assistant(
    body: ShoppingAssistantQueryRequest,
    request: Request,
    service: ShoppingAssistantService = Depends(get_shopping_assistant_service),
) -> ShoppingAssistantResponse:
    location = parse_delivery_cookie(request.cookies.get(DELIVERY_COOKIE))
    owner = parse_owner_cookie(request.cookies.get(OWNER_COOKIE))
    selected_market = shopping_market_from_cookie(request.cookies.get(SHOPPING_MARKET_COOKIE))
    try:
        result = service.query(
            body.model_dump(),
            location=location,
            owner=owner,
            selected_market=selected_market,
        )
    except (
        ShoppingAssistantValidationError,
        ShoppingAssistantNotFoundError,
        DecisionSnapshotOwnershipError,
        DecisionSnapshotIntegrityError,
    ) as exc:
        raise _map_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_assistant_response(result, allowed_modes=service.allowed_modes())
