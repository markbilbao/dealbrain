"""Sprint 37.4 destination-change / effective-cost re-evaluation readiness.

Server-authoritative assessment of whether a shopper destination change can
keep current decision economics, must invalidate destination-sensitive cost,
or requires re-evaluation that is not yet available.

This is not a live merchant executor, not a second price model, and not
Sprint 38. ``DESTINATION_REEVALUATION_IMPLEMENTED`` remains False.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.entities.offer_economics import CanonicalOfferEconomics
from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.market.context import MarketContext
from app.market.invalidation import (
    DESTINATION_SENSITIVE_COMPONENT_KINDS,
    DestinationInvalidation,
    assert_destination_reevaluation_not_implemented,
    destination_declaration_changed,
    invalidate_for_destination_change,
)

ReevaluationStatus = Literal["not_required", "required_unavailable"]

REEVALUATION_UNAVAILABLE_DISCLOSURE = (
    "Delivery costs need to be recalculated for this location. "
    "Updated pricing isn't available from this source yet."
)
HISTORICAL_COST_DISCLOSURE = (
    "The costs shown were evaluated for the original delivery location. "
    "They are historical and are not this location's current effective cost."
)
DESTINATION_INSENSITIVE_DISCLOSURE = (
    "Delivery area changed. These costs are not location-specific, "
    "so the evaluated amounts remain usable."
)


@dataclass(frozen=True, slots=True)
class DestinationReevaluationAssessment:
    """Readiness result. Never a live reprice and never a mutated decision."""

    invalidation: DestinationInvalidation
    reevaluation_status: ReevaluationStatus
    live_evidence_path_available: bool
    prior_canonical_decision_preserved: bool
    previous_destination_shipping_reused: bool
    manufactured_shipping: bool
    disclosure: str | None
    historical_cost_disclosure: str | None

    @property
    def destination_changed(self) -> bool:
        return self.invalidation.destination_changed

    @property
    def reevaluation_required(self) -> bool:
        return self.invalidation.reevaluation_required

    @property
    def destination_sensitive_economics_stale(self) -> bool:
        return self.invalidation.destination_sensitive_economics_stale

    @property
    def destination_insensitive_economics(self) -> bool:
        return self.invalidation.destination_insensitive_economics

    @property
    def live_reevaluation_attempted(self) -> bool:
        return self.invalidation.live_reevaluation_attempted

    def to_dict(self) -> dict[str, object]:
        payload = self.invalidation.to_dict()
        payload.update(
            {
                "reevaluation_status": self.reevaluation_status,
                "live_evidence_path_available": self.live_evidence_path_available,
                "prior_canonical_decision_preserved": self.prior_canonical_decision_preserved,
                "previous_destination_shipping_reused": self.previous_destination_shipping_reused,
                "manufactured_shipping": self.manufactured_shipping,
                "destination_reevaluation_implemented": DESTINATION_REEVALUATION_IMPLEMENTED,
                "disclosure": self.disclosure,
                "historical_cost_disclosure": self.historical_cost_disclosure,
            }
        )
        return payload


def live_destination_reevaluation_available() -> bool:
    """Operational live re-evaluation. Remains False until Sprint 38 evidence exists."""

    return DESTINATION_REEVALUATION_IMPLEMENTED


def economics_are_destination_insensitive(
    offer_economics: Sequence[CanonicalOfferEconomics] | None,
) -> bool:
    """True only when every destination-sensitive line is proven not applicable.

    Missing economics fail closed: they may be destination-sensitive.
    Verified shipping, including verified zero, is still destination-specific
    unless the line is explicitly ``not_applicable``.
    """

    if not offer_economics:
        return False
    for offer in offer_economics:
        lines = (offer.shipping, offer.taxes, offer.import_charges)
        for line in lines:
            if line is None:
                continue
            if line.kind not in DESTINATION_SENSITIVE_COMPONENT_KINDS:
                continue
            if line.status != "not_applicable":
                return False
    return True


def assess_destination_reevaluation(
    previous: MarketContext,
    current: MarketContext,
    *,
    offer_economics: Sequence[CanonicalOfferEconomics] | None = None,
) -> DestinationReevaluationAssessment:
    """Decide the destination-change state without executing merchants.

    Future certified evidence-backed re-evaluation must enter through this
    function. While ``DESTINATION_REEVALUATION_IMPLEMENTED`` is False, a
    required re-evaluation is always ``required_unavailable``.
    """

    assert_destination_reevaluation_not_implemented()
    invalidation = invalidate_for_destination_change(
        previous,
        current,
        offer_economics=offer_economics,
    )
    live_available = live_destination_reevaluation_available()
    if not invalidation.reevaluation_required:
        disclosure = (
            DESTINATION_INSENSITIVE_DISCLOSURE
            if invalidation.destination_changed and invalidation.destination_insensitive_economics
            else None
        )
        return DestinationReevaluationAssessment(
            invalidation=invalidation,
            reevaluation_status="not_required",
            live_evidence_path_available=False,
            prior_canonical_decision_preserved=True,
            previous_destination_shipping_reused=False,
            manufactured_shipping=False,
            disclosure=disclosure,
            historical_cost_disclosure=None,
        )
    if live_available:
        raise RuntimeError(
            "live destination re-evaluation must not run while Sprint 38 is not started"
        )
    return DestinationReevaluationAssessment(
        invalidation=invalidation,
        reevaluation_status="required_unavailable",
        live_evidence_path_available=False,
        prior_canonical_decision_preserved=True,
        previous_destination_shipping_reused=False,
        manufactured_shipping=False,
        disclosure=REEVALUATION_UNAVAILABLE_DISCLOSURE,
        historical_cost_disclosure=HISTORICAL_COST_DISCLOSURE,
    )


def attempt_certified_destination_reevaluation(
    previous: MarketContext,
    current: MarketContext,
    *,
    offer_economics: Sequence[CanonicalOfferEconomics] | None = None,
) -> DestinationReevaluationAssessment:
    """Sprint 38 handoff. Fail closed; do not manufacture shipping or mutate decisions."""

    return assess_destination_reevaluation(
        previous,
        current,
        offer_economics=offer_economics,
    )


__all__ = [
    "DESTINATION_INSENSITIVE_DISCLOSURE",
    "HISTORICAL_COST_DISCLOSURE",
    "REEVALUATION_UNAVAILABLE_DISCLOSURE",
    "DestinationReevaluationAssessment",
    "ReevaluationStatus",
    "assess_destination_reevaluation",
    "attempt_certified_destination_reevaluation",
    "destination_declaration_changed",
    "economics_are_destination_insensitive",
    "live_destination_reevaluation_available",
]
