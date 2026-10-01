"""Server-owned Ask analytics. The question and answer text are not parameters."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from app.analytics.funnel import emit_refinement_observations, emit_research_observations
from app.analytics.identity import identity_kind_for_owner
from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    PREFERENCE_COOKIE,
    apply_tracking_choice,
    read_analytics_subject,
    read_tracking_preference,
)
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.consumer.owner_authorization import authorized_owner_from_request
from app.domain.entities.shopping_assistant import ConversationOwner
from app.feedback.decisions import resolve_bound_decision


def emit_ask_product_events(
    request: Request,
    response: Response,
    *,
    surface: str | None,
    answer_status: str | None,
    evidence_count: int | None,
    decision_id: str | None,
    owner: ConversationOwner | None,
    analytics: ProductAnalyticsService,
    snapshots: Any,
    processing: dict[str, Any] | None = None,
) -> None:
    """Record Ask and related server transitions when consent allows.

    Failures are swallowed. Shopping answers must not depend on analytics.
    ``ask_evidence_answered`` is emitted only for status ``answered``.
    Question and answer text are not parameters.
    """

    try:
        preference = read_tracking_preference(request.cookies.get(PREFERENCE_COOKIE))
        if not preference.analytics_allowed:
            return
        subject = read_analytics_subject(request.cookies.get(ANALYTICS_SUBJECT_COOKIE))
        if subject is None and preference.choice == "analytics_allowed":
            _preference, subject = apply_tracking_choice(
                response,
                "analytics_allowed",
                existing_subject=None,
            )
        resolved_owner = owner if owner is not None else authorized_owner_from_request(request)
        decision_hash = None
        context_version = None
        if isinstance(decision_id, str) and decision_id:
            bound = resolve_bound_decision(decision_id, resolved_owner, snapshots)
            if bound is not None:
                from app.analytics.identity import decision_hash as hash_decision

                decision_hash = hash_decision(bound.decision_id)
                context_version = bound.context_version
        context = AnalyticsServerContext(
            preference=preference,
            subject_id=subject,
            identity_kind=identity_kind_for_owner(resolved_owner),
            decision_hash=decision_hash,
            context_version=context_version,
            selected_market=None,
        )
        safe_surface = surface if surface in {"results", "compare", "why", "ask"} else "ask"
        count = evidence_count if isinstance(evidence_count, int) and evidence_count >= 0 else None
        analytics.record_server_event(
            context,
            event_name="ask_question_submitted",
            surface=safe_surface,
            action_type="submit",
            evidence_count=count,
            outcome="submitted",
        )
        if answer_status == "insufficient_evidence":
            analytics.record_server_event(
                context,
                event_name="insufficient_evidence",
                surface=safe_surface,
                action_type="submit",
                evidence_count=count,
                outcome="insufficient_evidence",
            )
        elif answer_status == "answered":
            analytics.record_server_event(
                context,
                event_name="ask_evidence_answered",
                surface=safe_surface,
                action_type="submit",
                evidence_count=count,
                outcome="answered",
            )
        observed = processing if isinstance(processing, dict) else {}
        emit_research_observations(context, observed, analytics)
        emit_refinement_observations(context, observed, analytics)
    except Exception:
        return
