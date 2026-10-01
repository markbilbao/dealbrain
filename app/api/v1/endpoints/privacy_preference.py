"""First-party tracking preference. Not an external CMP and not advertising consent."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    PREFERENCE_COOKIE,
    apply_tracking_choice,
    read_analytics_subject,
    read_tracking_preference,
)
from app.schemas.tracking_preference import TrackingPreferenceResponse, TrackingPreferenceUpdate

router = APIRouter(prefix="/privacy")


@router.get(
    "/tracking-preference",
    response_model=TrackingPreferenceResponse,
    summary="Read the first-party analytics preference",
    description=(
        "Returns essential_only when the shopper has not made an explicit choice. "
        "Advertising is always false. This is not an external consent-management platform."
    ),
)
async def get_tracking_preference(request: Request) -> TrackingPreferenceResponse:
    preference = read_tracking_preference(request.cookies.get(PREFERENCE_COOKIE))
    return TrackingPreferenceResponse.model_validate(preference.to_public_dict())


@router.post(
    "/tracking-preference",
    response_model=TrackingPreferenceResponse,
    summary="Set the first-party analytics preference",
    description=(
        "Accepts essential_only or analytics_allowed. Opt-out deletes the analytics "
        "subject cookie. Opt-in may create an opaque subject id. Advertising cannot be enabled."
    ),
)
async def set_tracking_preference(
    body: TrackingPreferenceUpdate,
    request: Request,
    response: Response,
) -> TrackingPreferenceResponse:
    try:
        preference, _subject = apply_tracking_choice(
            response,
            body.choice,
            existing_subject=read_analytics_subject(request.cookies.get(ANALYTICS_SUBJECT_COOKIE)),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracking preference storage is unavailable.",
        ) from exc
    return TrackingPreferenceResponse.model_validate(preference.to_public_dict())
