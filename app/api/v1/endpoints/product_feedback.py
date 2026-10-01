"""In-product feedback and incorrect-information reports.

Submitting a report does not send email and does not require analytics consent.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.analytics.identity import decision_hash
from app.analytics.request_context import analytics_context_for_request, authorized_owner
from app.analytics.service import AnalyticsServerContext
from app.core.dependencies import get_bound_decision_resolver, get_feedback_report_service
from app.feedback.schema import FeedbackConflict, FeedbackRejected, parse_feedback_command
from app.feedback.service import FeedbackReportService
from app.infrastructure.persistence.errors import PersistenceError
from app.schemas.product_feedback import FeedbackReportCreate, FeedbackReportResponse

router = APIRouter(prefix="/feedback")

_STATUS = {
    "decision_not_found": status.HTTP_404_NOT_FOUND,
    "product_not_in_decision": status.HTTP_400_BAD_REQUEST,
    "message_too_long": status.HTTP_400_BAD_REQUEST,
    "html_not_allowed": status.HTTP_400_BAD_REQUEST,
    "secret_not_allowed": status.HTTP_400_BAD_REQUEST,
    "message_required": status.HTTP_400_BAD_REQUEST,
    "invalid_category": status.HTTP_400_BAD_REQUEST,
    "invalid_message": status.HTTP_400_BAD_REQUEST,
    "unknown_field": status.HTTP_400_BAD_REQUEST,
    "invalid_decision_reference": status.HTTP_400_BAD_REQUEST,
    "invalid_product": status.HTTP_400_BAD_REQUEST,
    "invalid_surface": status.HTTP_400_BAD_REQUEST,
    "invalid_context_version": status.HTTP_400_BAD_REQUEST,
    "invalid_submission_id": status.HTTP_400_BAD_REQUEST,
    "payload_not_object": status.HTTP_400_BAD_REQUEST,
}


@router.post(
    "/reports",
    response_model=FeedbackReportResponse,
    summary="Submit a product feedback or incorrect-information report",
    description=(
        "Stores a received report. This does not send email and does not promise "
        "a correction. Report text is not copied into product analytics."
    ),
)
async def submit_feedback_report(
    body: FeedbackReportCreate,
    request: Request,
    response: Response,
    feedback: FeedbackReportService = Depends(get_feedback_report_service),
    resolve_decision: Any = Depends(get_bound_decision_resolver),
) -> FeedbackReportResponse:
    try:
        command = parse_feedback_command(body.client_payload())
    except FeedbackRejected as exc:
        raise HTTPException(
            status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail=exc.code,
        ) from exc
    owner = authorized_owner(request)
    context = analytics_context_for_request(request, response, mint_subject=True)
    if command.decision_id:
        bound = resolve_decision(command.decision_id, owner)
        if bound is not None:
            context = AnalyticsServerContext(
                preference=context.preference,
                subject_id=context.subject_id,
                identity_kind=context.identity_kind,
                decision_hash=decision_hash(bound.decision_id),
                context_version=bound.context_version,
                selected_market=context.selected_market,
            )
    try:
        submission = feedback.submit(
            command,
            context,
            owner=owner,
            resolve_decision=resolve_decision,
        )
    except FeedbackRejected as exc:
        raise HTTPException(
            status_code=_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail=exc.code,
        ) from exc
    except FeedbackConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="submission_conflict",
        ) from exc
    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feedback storage is unavailable.",
        ) from exc
    return FeedbackReportResponse(
        report_id=submission.report.report_id,
        status="received",
        category=submission.report.category,
        duplicate=not submission.created,
        analytics_status=submission.analytics_status,
    )
