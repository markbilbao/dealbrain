"""Observe existing server transitions. Does not cause them.

Research and refinement events are recorded only from fields the shopping
services already set after a successful transition. Decision start/completion
are intentionally absent: see ``decision_events``.
"""

from __future__ import annotations

import re
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from app.analytics.event_identity import deterministic_event_id
from app.analytics.request_context import analytics_context_for_request
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.consumer.canonical_resolve import resolve_canonical_snapshot
from app.consumer.owner_authorization import authorized_owner_from_request
from app.feedback.decisions import BoundDecision

_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_RESEARCH_PARTIAL_REASON = "no_authoritative_partial_transition"


def emit_research_observations(
    context: AnalyticsServerContext,
    processing: dict[str, Any],
    analytics: ProductAnalyticsService,
) -> None:
    """Map proposal and execution fields that the research services already set."""

    lifecycle = processing.get("research_lifecycle")
    proposal_id = _text(processing.get("proposal_id"))
    if (
        lifecycle in {"propose", "replace"}
        and processing.get("proposal_status") == "pending_confirmation"
    ):
        _safe_server_event(
            analytics,
            context,
            event_name="research_proposed",
            surface="ask",
            action_type="submit",
            outcome="proposed",
            identity_parts=_parts(proposal_id),
        )
    if lifecycle in {"confirm", "reconfirm"} and processing.get("authorization_created") is True:
        _safe_server_event(
            analytics,
            context,
            event_name="research_confirmed",
            surface="ask",
            action_type="submit",
            outcome="confirmed",
            identity_parts=_parts(_text(processing.get("research_authorization_id"))),
        )
    if lifecycle == "cancel" and processing.get("answer_status") == "cancelled":
        _safe_server_event(
            analytics,
            context,
            event_name="research_declined",
            surface="ask",
            action_type="submit",
            outcome="declined",
            identity_parts=_parts(proposal_id),
        )
    continuation = processing.get("confirmed_research")
    if not isinstance(continuation, dict):
        return
    execution_id = _text(continuation.get("execution_id"))
    started = bool(continuation.get("attempted") or continuation.get("research_executed"))
    if not started or not execution_id:
        return
    _safe_server_event(
        analytics,
        context,
        event_name="research_started",
        surface="ask",
        action_type="start",
        outcome="started",
        identity_parts=(execution_id,),
    )
    if continuation.get("live_research_completed") is True:
        _safe_server_event(
            analytics,
            context,
            event_name="research_completed",
            surface="ask",
            action_type="complete",
            outcome="completed",
            identity_parts=(execution_id,),
        )
        return
    _safe_server_event(
        analytics,
        context,
        event_name="research_failed",
        surface="ask",
        action_type="submit",
        outcome="failed",
        error_code=_bounded_error_code(continuation.get("block_reason")),
        identity_parts=(execution_id, "failed"),
    )


def emit_refinement_observations(
    context: AnalyticsServerContext,
    processing: dict[str, Any],
    analytics: ProductAnalyticsService,
) -> None:
    """Attempted and applied are the refinement service's own flags."""

    if processing.get("action") != "refine_session_recommendation":
        return
    status = _text(processing.get("answer_status")) or "unknown"
    version = processing.get("session_refinement_version")
    version_part = (
        str(version) if isinstance(version, int) and not isinstance(version, bool) else ""
    )
    decision_part = context.decision_hash or ""
    context_part = str(context.context_version) if context.context_version is not None else ""
    _safe_server_event(
        analytics,
        context,
        event_name="recommendation_refinement_attempted",
        surface=_surface(processing),
        action_type="submit",
        outcome="attempted",
        identity_parts=_parts(decision_part, context_part, version_part, status, "attempted"),
    )
    if processing.get("recommendation_applied") is True:
        _safe_server_event(
            analytics,
            context,
            event_name="recommendation_refinement_applied",
            surface=_surface(processing),
            action_type="submit",
            outcome="applied",
            identity_parts=_parts(decision_part, context_part, version_part, "applied"),
        )


def emit_updated_results_viewed(
    request: Request,
    response: Response,
    *,
    decision_id: str,
    analytics: ProductAnalyticsService,
    snapshots: Any,
) -> None:
    """Emit when the server resolves an owner snapshot newer than version 1.

    The browser's ``data-context-version`` is not consulted.
    """

    try:
        owner = authorized_owner_from_request(request)
        snapshot = resolve_canonical_snapshot(decision_id, owner, snapshots)
        if snapshot is None or snapshot.context_version < 2:
            return
        bound = BoundDecision(
            decision_id=snapshot.decision_id,
            context_version=snapshot.context_version,
            product_ids=frozenset(snapshot.evaluated_product_ids),
        )
        context = analytics_context_for_request(request, response, bound_decision=bound)
        _safe_server_event(
            analytics,
            context,
            event_name="updated_results_viewed",
            surface="results",
            action_type="view",
            outcome="viewed",
            identity_parts=None,
        )
    except Exception:
        return


def research_partial_reason() -> str:
    return _RESEARCH_PARTIAL_REASON


def _safe_server_event(
    analytics: ProductAnalyticsService,
    context: AnalyticsServerContext,
    *,
    event_name: str,
    surface: str,
    action_type: str,
    outcome: str,
    identity_parts: tuple[str, ...] | None,
    error_code: str | None = None,
) -> None:
    try:
        event_id = None
        if identity_parts:
            subject = context.subject_id or ""
            event_id = deterministic_event_id(event_name, subject, *identity_parts)
        analytics.record_server_event(
            context,
            event_name=event_name,
            surface=surface,
            action_type=action_type,
            outcome=outcome,
            error_code=error_code,
            event_id=event_id,
        )
    except Exception:
        return


def _parts(*values: str | None) -> tuple[str, ...] | None:
    if any(not value for value in values):
        return None
    return tuple(value for value in values if value)


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _surface(processing: dict[str, Any]) -> str:
    surface = processing.get("surface")
    if surface in {"results", "compare", "why", "ask"}:
        return str(surface)
    return "results"


def _bounded_error_code(value: object) -> str:
    if isinstance(value, str) and _ERROR_CODE_RE.match(value):
        return value
    return "research_unsuccessful"
