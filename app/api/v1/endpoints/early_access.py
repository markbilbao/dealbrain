"""Early Access interest-list API — not a user-account registration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.dependencies import get_early_access_service
from app.core.logging import get_logger, log_extra
from app.domain.exceptions import EarlyAccessValidationError
from app.schemas.early_access import (
    EarlyAccessEventRequest,
    EarlyAccessRegisterRequest,
    EarlyAccessRegisterResponse,
)
from app.services.early_access_service import EarlyAccessService

router = APIRouter(prefix="/early-access", tags=["early-access"])
logger = get_logger(__name__)

_SUCCESS_MESSAGE = "You're on the list."
_DUPLICATE_MESSAGE = "You're already on the Early Access list."

_ALLOWED_EVENTS = frozenset(
    {
        "early_access_cta_clicked",
        "early_access_form_started",
        "early_access_form_submitted",
        "how_it_works_viewed",
    }
)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id")


@router.post(
    "",
    response_model=EarlyAccessRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register interest in PiqSavi Early Access",
)
async def register_early_access(
    body: EarlyAccessRegisterRequest,
    request: Request,
    service: EarlyAccessService = Depends(get_early_access_service),
) -> EarlyAccessRegisterResponse:
    request_id = _request_id(request)
    try:
        result = service.register(
            full_name=body.full_name,
            email=body.email,
            country=body.country,
            shopping_interest=body.shopping_interest,
            source=body.source,
            utm_source=body.utm_source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
            utm_content=body.utm_content,
            utm_term=body.utm_term,
            referrer=body.referrer,
            request_id=request_id,
        )
    except EarlyAccessValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        logger.exception(
            "early_access_signup_error",
            extra={
                "structured": log_extra(
                    event="early_access_signup_error",
                    outcome="technical_error",
                    request_id=request_id,
                )
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from exc
    message = _SUCCESS_MESSAGE if result.outcome == "success" else _DUPLICATE_MESSAGE
    return EarlyAccessRegisterResponse(
        outcome=result.outcome,
        email_confirmation_status=result.email_confirmation_status,
        message=message,
    )


@router.post(
    "/events",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a first-party Early Access UI event",
    include_in_schema=True,
)
async def record_early_access_event(
    body: EarlyAccessEventRequest,
    request: Request,
) -> Response:
    if body.event not in _ALLOWED_EVENTS:
        raise EarlyAccessValidationError("Unknown event.")
    extra_fields: dict[str, object] = {
        "event": body.event,
        "request_id": _request_id(request),
    }
    if body.source is not None:
        extra_fields["source"] = body.source
    logger.info(
        body.event,
        extra={"structured": log_extra(**extra_fields)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
