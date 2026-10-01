"""Create feedback reports and, only with analytics consent, a sanitized event."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.analytics.identity import decision_hash as hash_decision
from app.analytics.schema import OUTCOMES
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.domain.entities.shopping_assistant import ConversationOwner
from app.feedback.decisions import BoundDecision
from app.feedback.repository import FirstPartyFeedbackRepository
from app.feedback.schema import (
    ANALYTICS_EVENT_FOR_CATEGORY,
    REPORT_STATUS_RECEIVED,
    FeedbackCommand,
    FeedbackRejected,
    FeedbackReport,
    feedback_content_digest,
)
from app.services.research_authorization import owner_binding_digest

DecisionResolver = Callable[[str, ConversationOwner | None], BoundDecision | None]


@dataclass(frozen=True, slots=True)
class FeedbackSubmission:
    report: FeedbackReport
    created: bool
    analytics_status: str


class FeedbackReportService:
    """Feedback works with analytics consent off. Report text stays in this domain."""

    def __init__(
        self,
        repository: FirstPartyFeedbackRepository | None = None,
        analytics: ProductAnalyticsService | None = None,
    ) -> None:
        self._repository = repository or FirstPartyFeedbackRepository()
        self._analytics = analytics or ProductAnalyticsService()

    def submit(
        self,
        command: FeedbackCommand,
        context: AnalyticsServerContext,
        *,
        owner: ConversationOwner | None,
        resolve_decision: DecisionResolver,
    ) -> FeedbackSubmission:
        bound: BoundDecision | None = None
        if command.decision_id:
            bound = resolve_decision(command.decision_id, owner)
            if bound is None:
                raise FeedbackRejected("decision_not_found")
        product_id = command.product_id
        if product_id and (bound is None or product_id not in bound.product_ids):
            raise FeedbackRejected("product_not_in_decision")
        context_version = bound.context_version if bound is not None else None
        report_id = str(uuid4())
        owner_digest = owner_binding_digest(owner) if owner is not None else None
        report = FeedbackReport(
            report_id=report_id,
            category=command.category,
            created_at=datetime.now(UTC),
            owner_digest=owner_digest,
            decision_id=bound.decision_id if bound is not None else None,
            product_id=product_id,
            context_version=context_version,
            message=command.message,
            status=REPORT_STATUS_RECEIVED,
            source_surface=command.source_surface,
            client_submission_id=command.client_submission_id,
            content_digest="",
        )
        digest = feedback_content_digest(report)
        report = FeedbackReport(
            report_id=report.report_id,
            category=report.category,
            created_at=report.created_at,
            owner_digest=report.owner_digest,
            decision_id=report.decision_id,
            product_id=report.product_id,
            context_version=report.context_version,
            message=report.message,
            status=report.status,
            source_surface=report.source_surface,
            client_submission_id=report.client_submission_id,
            content_digest=digest,
        )
        stored, created = self._repository.insert(report)
        analytics_status = "not_applicable"
        if created:
            analytics_status = self._emit_sanitized_analytics(stored, context)
        elif context.preference.analytics_allowed:
            analytics_status = "duplicate"
        else:
            analytics_status = "suppressed_no_consent"
        return FeedbackSubmission(
            report=stored,
            created=created,
            analytics_status=analytics_status,
        )

    def _emit_sanitized_analytics(
        self,
        report: FeedbackReport,
        context: AnalyticsServerContext,
    ) -> str:
        event_name = ANALYTICS_EVENT_FOR_CATEGORY.get(report.category)
        if event_name is None:
            return "not_applicable"
        outcome = report.category if report.category in OUTCOMES else "reported"
        action = (
            "report" if event_name in {"incorrect_information_report", "bug_report"} else "submit"
        )
        hashed_decision = hash_decision(report.decision_id) if report.decision_id else None
        analytics_context = AnalyticsServerContext(
            preference=context.preference,
            subject_id=context.subject_id,
            identity_kind=context.identity_kind,
            decision_hash=hashed_decision,
            context_version=report.context_version,
            selected_market=context.selected_market,
        )
        result = self._analytics.record_server_event(
            analytics_context,
            event_name=event_name,
            surface=report.source_surface,
            action_type=action,
            outcome=outcome,
            event_id=str(uuid4()),
        )
        return result.status
