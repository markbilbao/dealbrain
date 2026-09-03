"""Destination-sensitive invalidation for Sprint 37.1.

A destination-key change marks shipping/tax/import economics stale and may
require re-evaluation. It does not rewrite a canonical decision, PiqScore, or
Recommendation, and it does not execute live merchant re-evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.research_execution import DESTINATION_REEVALUATION_IMPLEMENTED
from app.market.context import MarketContext

DESTINATION_SENSITIVE_COMPONENT_KINDS = frozenset({"shipping", "tax", "import"})


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

    def to_dict(self) -> dict[str, object]:
        return {
            "destination_changed": self.destination_changed,
            "previous_destination_key": self.previous_destination_key,
            "current_destination_key": self.current_destination_key,
            "previous_destination_state": self.previous_destination_state,
            "current_destination_state": self.current_destination_state,
            "destination_sensitive_economics_stale": self.destination_sensitive_economics_stale,
            "reevaluation_required": self.reevaluation_required,
            "canonical_snapshot_rewritten": self.canonical_snapshot_rewritten,
            "piqscore_rewritten": self.piqscore_rewritten,
            "recommendation_rewritten": self.recommendation_rewritten,
            "live_reevaluation_attempted": self.live_reevaluation_attempted,
        }


def assert_destination_reevaluation_not_implemented() -> None:
    """Sprint 37.1 keeps live destination re-evaluation unimplemented."""

    if DESTINATION_REEVALUATION_IMPLEMENTED:
        raise RuntimeError("DESTINATION_REEVALUATION_IMPLEMENTED must remain False in Sprint 37.1")


def invalidate_for_destination_change(
    previous: MarketContext,
    current: MarketContext,
) -> DestinationInvalidation:
    """Mark destination-sensitive economics stale when the destination changes.

    Product facts, canonical PiqScore, and Recommendation stay untouched.
    Live merchant re-evaluation is not attempted.
    """

    assert_destination_reevaluation_not_implemented()
    changed = (
        previous.destination_key != current.destination_key
        or previous.destination_state != current.destination_state
    )
    return DestinationInvalidation(
        destination_changed=changed,
        previous_destination_key=previous.destination_key,
        current_destination_key=current.destination_key,
        previous_destination_state=previous.destination_state,
        current_destination_state=current.destination_state,
        destination_sensitive_economics_stale=changed,
        reevaluation_required=changed,
        canonical_snapshot_rewritten=False,
        piqscore_rewritten=False,
        recommendation_rewritten=False,
        live_reevaluation_attempted=False,
    )
