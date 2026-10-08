"""Server observation of canonical Results recommendation and PiqScore UI.

A successful canonical Results response is a view when the completed HTML
contains the matching server-owned marker. This does not measure viewport
visibility, scroll depth, eye tracking, or time on screen.

``recommendation_viewed`` means the Best Piq recommendation hero was in the
response. ``piqscore_viewed`` means the hero PiqScore control was in the
response. The two checks are independent. ``results_viewed`` and
``updated_results_viewed`` stay separate measurements.

The browser cannot submit these names. Serving Results does not mint an
analytics subject. Analytics off, or analytics on without an existing opaque
subject, writes zero rows. Fixture, unavailable, compare, and why responses
are not this observer.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from app.analytics.request_context import analytics_context_for_request
from app.analytics.service import AnalyticsServerContext, ProductAnalyticsService
from app.consumer.canonical_resolve import resolve_canonical_snapshot
from app.consumer.owner_authorization import authorized_owner_from_request
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.feedback.decisions import BoundDecision

RECOMMENDATION_VIEW_MARKER = 'data-product-analytics-recommendation-view="true"'
PIQSCORE_VIEW_MARKER = 'data-product-analytics-piqscore-view="true"'

_VISIBILITY_EVENTS = (
    ("recommendation_viewed", RECOMMENDATION_VIEW_MARKER),
    ("piqscore_viewed", PIQSCORE_VIEW_MARKER),
)


def emit_canonical_results_visibility(
    request: Request,
    response: Response,
    *,
    decision_id: str,
    analytics: ProductAnalyticsService,
    snapshots: DecisionSnapshotRepository | None,
) -> None:
    """Record each rendered canonical Results element that this response contains.

    Canonical authority is the owner snapshot from the repository. The HTML
    markers are checked independently of ``presentation_mode``. ``context_version``
    1 is allowed. Each serve uses a new event id. Failures are swallowed.
    """

    try:
        html = _response_html(response)
        present = [name for name, marker in _VISIBILITY_EVENTS if marker in html]
        if not present:
            return
        owner = authorized_owner_from_request(request)
        snapshot = resolve_canonical_snapshot(decision_id, owner, snapshots)
        if snapshot is None:
            return
        bound = BoundDecision(
            decision_id=snapshot.decision_id,
            context_version=snapshot.context_version,
            product_ids=frozenset(snapshot.evaluated_product_ids),
        )
        context = analytics_context_for_request(
            request,
            response,
            bound_decision=bound,
            mint_subject=False,
        )
        for event_name in present:
            _record_visibility(analytics, context, event_name)
    except Exception:
        return


def _record_visibility(
    analytics: ProductAnalyticsService,
    context: AnalyticsServerContext,
    event_name: str,
) -> None:
    try:
        analytics.record_server_event(
            context,
            event_name=event_name,
            surface="results",
            action_type="view",
            outcome="viewed",
        )
    except Exception:
        return


def _response_html(response: Response) -> str:
    body = response.body
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)
