"""Build server analytics context from the current request.

The browser does not choose identity, consent, market, or decision hash.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from app.analytics.identity import decision_hash, identity_kind_for_owner
from app.analytics.preference import (
    ANALYTICS_SUBJECT_COOKIE,
    PREFERENCE_COOKIE,
    TrackingChoice,
    apply_tracking_choice,
    read_analytics_subject,
    read_tracking_preference,
)
from app.analytics.service import AnalyticsServerContext
from app.consumer.owner_authorization import authorized_owner_from_request
from app.consumer.shopping_market import SHOPPING_MARKET_COOKIE, parse_shopping_market_cookie
from app.domain.entities.shopping_assistant import ConversationOwner
from app.feedback.decisions import BoundDecision


def analytics_context_for_request(
    request: Request,
    response: Response | None = None,
    *,
    bound_decision: BoundDecision | None = None,
    mint_subject: bool = False,
) -> AnalyticsServerContext:
    """Read consent and opaque subject. Mint a subject only after an explicit opt-in."""

    preference = read_tracking_preference(request.cookies.get(PREFERENCE_COOKIE))
    subject = read_analytics_subject(request.cookies.get(ANALYTICS_SUBJECT_COOKIE))
    if (
        mint_subject
        and preference.analytics_allowed
        and subject is None
        and response is not None
        and preference.choice == "analytics_allowed"
    ):
        _stored, subject = apply_tracking_choice(
            response,
            preference.choice,
            existing_subject=None,
        )
    owner = authorized_owner_from_request(request)
    market = _explicit_market(request)
    return AnalyticsServerContext(
        preference=preference,
        subject_id=subject,
        identity_kind=identity_kind_for_owner(owner),
        decision_hash=decision_hash(bound_decision.decision_id) if bound_decision else None,
        context_version=bound_decision.context_version if bound_decision else None,
        selected_market=market,
    )


def authorized_owner(request: Request) -> ConversationOwner | None:
    return authorized_owner_from_request(request)


def explicit_choice(value: str) -> TrackingChoice:
    if value == "analytics_allowed":
        return "analytics_allowed"
    if value == "essential_only":
        return "essential_only"
    raise ValueError("tracking choice is not allowed")


def _explicit_market(request: Request) -> str | None:
    selected = parse_shopping_market_cookie(request.cookies.get(SHOPPING_MARKET_COOKIE))
    if selected is None or selected.origin != "explicit":
        return None
    code = selected.country_code
    if len(code) == 2 and code.isalpha() and code.isupper():
        return code
    return None
