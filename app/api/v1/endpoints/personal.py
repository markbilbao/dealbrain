"""Personal AI Shopping Agent API endpoints.

Fixture-backed customer profiles. No authentication, payment, or external DB.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.personal_agent import (
    to_advice_payload,
    to_deals_response,
    to_demo_response,
    to_profile_payload,
    to_recommendation_payload,
)
from app.core.dependencies import get_personal_agent_service
from app.domain.exceptions import PersonalAgentNotFoundError, PersonalAgentValidationError
from app.schemas.personal_agent import (
    BuyingAdvicePayload,
    CustomerProfilePayload,
    PersonalDealsResponse,
    PersonalDemoResponse,
    PersonalMetaResponse,
    PersonalRecommendationPayload,
    ProfileSwitchRequest,
)
from app.services.personal_agent_service import PersonalAgentService

router = APIRouter(prefix="/personal")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PersonalAgentValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, PersonalAgentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Personal shopping agent failed to process the request.",
    )


@router.get(
    "/demo",
    response_model=PersonalDemoResponse,
    summary="Personal AI Shopping Agent demo with active profile deals",
)
async def personal_demo(
    profile_id: str | None = Query(default=None),
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> PersonalDemoResponse:
    try:
        payload = service.demo(profile_id=profile_id)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_demo_response(payload)


@router.get(
    "/meta",
    response_model=PersonalMetaResponse,
    summary="Personal agent metadata and available demo profiles",
)
async def personal_meta(
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> PersonalMetaResponse:
    return PersonalMetaResponse(**service.meta())


@router.get(
    "/profile",
    response_model=CustomerProfilePayload,
    summary="Get active or specified demo customer profile",
)
async def personal_profile(
    profile_id: str | None = Query(default=None),
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> CustomerProfilePayload:
    try:
        profile = service.get_profile(profile_id)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_profile_payload(profile)


@router.post(
    "/profile/switch",
    response_model=CustomerProfilePayload,
    summary="Switch the active demo customer profile",
)
async def switch_personal_profile(
    body: ProfileSwitchRequest,
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> CustomerProfilePayload:
    try:
        profile = service.set_active_profile(body.profile_id)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_profile_payload(profile)


@router.get(
    "/recommendation/{product_id}",
    response_model=PersonalRecommendationPayload,
    summary="Personalized recommendation for a product",
)
async def personal_recommendation(
    product_id: str,
    profile_id: str | None = Query(default=None),
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> PersonalRecommendationPayload:
    try:
        rec = service.recommendation(product_id, profile_id=profile_id)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_recommendation_payload(rec)


@router.get(
    "/deals",
    response_model=PersonalDealsResponse,
    summary="Ranked personalized deals for a demo profile",
)
async def personal_deals(
    profile_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> PersonalDealsResponse:
    try:
        result = service.deals(profile_id=profile_id, limit=limit)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_deals_response(result)


@router.get(
    "/advice/{product_id}",
    response_model=BuyingAdvicePayload,
    summary="Structured buying advice for a product and profile",
)
async def personal_advice(
    product_id: str,
    profile_id: str | None = Query(default=None),
    service: PersonalAgentService = Depends(get_personal_agent_service),
) -> BuyingAdvicePayload:
    try:
        advice = service.advice(product_id, profile_id=profile_id)
    except (PersonalAgentValidationError, PersonalAgentNotFoundError) as exc:
        raise _map_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_advice_payload(advice)
