"""Server-only decision lifecycle analytics.

Audit result for Sprint 39.2
----------------------------
No production workflow both validates a shopper decision request and creates
the canonical decision snapshot required for Results.

These paths do **not** start or complete that decision:

- ``GET /results``, ``/compare``, and ``/why-best-piq`` render an existing page.
- ``GET /search`` redirects to a fixture catalog or ``/results/unavailable``.
- ``GET /shopping-assistant/demo`` and ``POST /shopping-assistant/query``
  without a persisted canonical snapshot are recommendation or follow-up
  flows. The query path does not insert ``CanonicalDecisionSnapshot``.
- ``CanonicalResearchResultsService`` appends ``context_version + 1`` onto a
  snapshot that already exists. That is research completion, not the original
  decision completion.

``record_decision_started`` and ``record_decision_completed`` are the only
emitters. Production code does not call them until a real creator exists.
They refuse to invent a decision hash.

Definitions, when a future caller is authorized:

- ``decision_started``: the server has already accepted a shopper decision
  request and has begun canonical decision generation. The caller passes the
  server-owned decision hash allocated for that workflow.
- ``decision_completed``: the canonical snapshot required for Results has been
  persisted and owner binding for that snapshot has succeeded. A failed or
  abandoned attempt must pass ``canonical_persisted=False``.

Both events use that same authorized decision hash. Completion rate in the
beta-learning read model is a distinct-decision ratio on that hash, not a
unique-user funnel.
"""

from __future__ import annotations

from app.analytics.event_identity import deterministic_event_id
from app.analytics.schema import AnalyticsWriteResult
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService


def record_decision_started(
    analytics: ProductAnalyticsService,
    context: AnalyticsServerContext,
    *,
    generation_started: bool,
) -> AnalyticsWriteResult | None:
    """Emit only after validation when generation has actually started."""

    if not generation_started:
        return None
    return _emit(
        analytics, context, event_name="decision_started", action_type="start", outcome="started"
    )


def record_decision_completed(
    analytics: ProductAnalyticsService,
    context: AnalyticsServerContext,
    *,
    canonical_persisted: bool,
) -> AnalyticsWriteResult | None:
    """Emit only after the canonical Results snapshot and owner bind succeed."""

    if not canonical_persisted:
        return None
    return _emit(
        analytics,
        context,
        event_name="decision_completed",
        action_type="complete",
        outcome="completed",
    )


def _emit(
    analytics: ProductAnalyticsService,
    context: AnalyticsServerContext,
    *,
    event_name: str,
    action_type: str,
    outcome: str,
) -> AnalyticsWriteResult | None:
    decision_hash = context.decision_hash
    if not decision_hash or context.context_version is None:
        return None
    subject = context.subject_id or ""
    event_id = deterministic_event_id(
        event_name,
        subject,
        decision_hash,
        str(context.context_version),
    )
    try:
        return analytics.record_server_event(
            context,
            event_name=event_name,
            action_type=action_type,
            outcome=outcome,
            event_id=event_id,
        )
    except Exception:
        return None
