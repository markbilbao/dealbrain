"""Destination-sensitive invalidation for Sprint 37.

A declared destination-key change marks shipping/tax/import economics stale
when those costs may be destination-sensitive. It does not rewrite a canonical
decision, PiqScore, or Recommendation, and it does not execute live merchant
re-evaluation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.market.context import MarketContext

if TYPE_CHECKING:
    from app.domain.entities.offer_economics import CanonicalOfferEconomics

DESTINATION_SENSITIVE_COMPONENT_KINDS = frozenset({"shipping", "tax", "import"})
ReevaluationStatus = Literal["not_required", "required_unavailable"]


@dataclass(frozen=True, slots=True)
class DestinationInvalidation:
    """Deterministic invalidation result. Not a live reprice."""

    destination_changed: bool
    previous_destination_key: str
    current_destination_key: str
    previous_destination_state: str
    current_destination_state: str
    destination_sensitive_economics_stale: bool
    reevaluation_required: bool
    canonical_snapshot_rewritten: bool = False
    piqscore_rewritten: bool = False
    recommendation_rewritten: bool = False
    live_reevaluation_attempted: bool = False
    destination_insensitive_economics: bool = False
    reevaluation_status: ReevaluationStatus = "not_required"
    prior_decision_preserved: bool = True
    updated_delivery_cost_available: bool = False
    previous_shipping_reused: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "destination_changed": self.destination_changed,
            "previous_destination_key": self.previous_destination_key,
            "current_destination_key": self.current_destination_key,
            "previous_destination_state": self.previous_destination_state,
            "current_destination_state": self.current_destination_state,
            "destination_sensitive_economics_stale": self.destination_sensitive_economics_stale,
            "destination_insensitive_economics": self.destination_insensitive_economics,
            "reevaluation_required": self.reevaluation_required,
            "reevaluation_status": self.reevaluation_status,
            "canonical_snapshot_rewritten": self.canonical_snapshot_rewritten,
            "piqscore_rewritten": self.piqscore_rewritten,
            "recommendation_rewritten": self.recommendation_rewritten,
            "live_reevaluation_attempted": self.live_reevaluation_attempted,
            "prior_decision_preserved": self.prior_decision_preserved,
            "updated_delivery_cost_available": self.updated_delivery_cost_available,
            "previous_shipping_reused": self.previous_shipping_reused,
        }


def assert_destination_reevaluation_not_implemented() -> None:
    """Sprint 37 keeps live destination re-evaluation unimplemented."""

    if DESTINATION_REEVALUATION_IMPLEMENTED:
        raise RuntimeError("DESTINATION_REEVALUATION_IMPLEMENTED must remain False in Sprint 37")


def destination_declaration_changed(
    previous: MarketContext,
    current: MarketContext,
) -> bool:
    """True when the shopper declared a materially different destination.

    A missing session declaration (``absent``) is not a shopper change. The
    historical evaluated destination remains the current decision context.
    ``absent`` and ``skipped`` both normalize to destination key ``unknown``;
    moving between those two unknown states is not a material cost change.
    Known-city / postal / skip transitions compare ``destination_key``.
    """

    if current.destination_state == "absent":
        return False
    return previous.destination_key != current.destination_key


def _destination_insensitive(
    offer_economics: Sequence[CanonicalOfferEconomics] | None,
) -> bool:
    if not offer_economics:
        return False
    for offer in offer_economics:
        for line in (offer.shipping, offer.taxes, offer.import_charges):
            if line is None:
                continue
            if line.kind not in DESTINATION_SENSITIVE_COMPONENT_KINDS:
                continue
            if line.status != "not_applicable":
                return False
    return True


def invalidate_for_destination_change(
    previous: MarketContext,
    current: MarketContext,
    *,
    offer_economics: Sequence[CanonicalOfferEconomics] | None = None,
) -> DestinationInvalidation:
    """Mark destination-sensitive economics stale when the destination changes.

    Product facts, canonical PiqScore, and Recommendation stay untouched.
    Live merchant re-evaluation is not attempted. Destination-insensitive
    economics (every shipping/tax/import line ``not_applicable``) remain usable.
    Missing economics fail closed as potentially destination-sensitive.
    """

    assert_destination_reevaluation_not_implemented()
    changed = destination_declaration_changed(previous, current)
    insensitive = _destination_insensitive(offer_economics)
    stale = changed and not insensitive
    status: ReevaluationStatus = "required_unavailable" if stale else "not_required"
    return DestinationInvalidation(
        destination_changed=changed,
        previous_destination_key=previous.destination_key,
        current_destination_key=current.destination_key,
        previous_destination_state=previous.destination_state,
        current_destination_state=current.destination_state,
        destination_sensitive_economics_stale=stale,
        destination_insensitive_economics=insensitive and changed,
        reevaluation_required=stale,
        reevaluation_status=status,
        canonical_snapshot_rewritten=False,
        piqscore_rewritten=False,
        recommendation_rewritten=False,
        live_reevaluation_attempted=False,
        prior_decision_preserved=True,
        updated_delivery_cost_available=False,
        previous_shipping_reused=False,
    )
