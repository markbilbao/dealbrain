"""Session-level Recommendation refinement overlay.

Temporary conversational state. Never mutates a canonical decision snapshot,
PiqScore, economics, evaluated-set membership, or account preferences.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

RefinementStatus = Literal[
    "recommendation_changed",
    "recommendation_unchanged",
    "insufficient_evidence",
    "outside_evaluated_set",
    "unsupported_refinement",
    "ambiguous_request",
    "none_fit_constraint",
    "reset_to_original",
]


def _overlay_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SessionPriorities:
    """Structured preference change for one conversational session."""

    top_priority: str | None = None
    priorities: tuple[str, ...] = ()
    required_features: tuple[str, ...] = ()
    preferred_features: tuple[str, ...] = ()
    deprioritized: tuple[str, ...] = ()
    use_case: str | None = None
    budget_max: float | None = None
    budget_label: str | None = None
    reset_to_original: bool = False
    hard_constraint: bool = False

    def to_contract(self) -> dict[str, str | int | float | bool]:
        """Closed session_priorities object for the conversation-action schema."""

        payload: dict[str, str | int | float | bool] = {}
        if self.reset_to_original:
            payload["reset"] = True
        if self.top_priority:
            payload["top_priority"] = self.top_priority
        if self.priorities:
            payload["priority_order"] = ",".join(self.priorities)
        if self.required_features:
            payload["required_features"] = ",".join(self.required_features)
        if self.preferred_features:
            payload["preferred_features"] = ",".join(self.preferred_features)
        if self.deprioritized:
            payload["deprioritized"] = ",".join(self.deprioritized)
        if self.use_case:
            payload["use_case"] = self.use_case
        if self.budget_max is not None:
            payload["budget_max"] = self.budget_max
        if self.budget_label:
            payload["budget_label"] = self.budget_label
        if self.hard_constraint:
            payload["hard_constraint"] = True
        if not payload:
            payload["clarified"] = True
        return payload

    def merge(self, incoming: SessionPriorities) -> SessionPriorities:
        """Evolve session priorities without rewriting historical shopper context."""

        if incoming.reset_to_original:
            return incoming
        priorities = tuple(
            dict.fromkeys(
                (
                    *((incoming.top_priority,) if incoming.top_priority else ()),
                    *incoming.priorities,
                    *self.priorities,
                )
            )
        )
        if incoming.top_priority:
            priorities = tuple(
                dict.fromkeys((incoming.top_priority, *priorities))
            )
        return SessionPriorities(
            top_priority=incoming.top_priority or self.top_priority,
            priorities=priorities,
            required_features=tuple(
                dict.fromkeys((*self.required_features, *incoming.required_features))
            ),
            preferred_features=tuple(
                dict.fromkeys((*self.preferred_features, *incoming.preferred_features))
            ),
            deprioritized=tuple(
                dict.fromkeys((*self.deprioritized, *incoming.deprioritized))
            ),
            use_case=incoming.use_case or self.use_case,
            budget_max=incoming.budget_max
            if incoming.budget_max is not None
            else self.budget_max,
            budget_label=incoming.budget_label or self.budget_label,
            reset_to_original=False,
            hard_constraint=self.hard_constraint or incoming.hard_constraint,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "top_priority": self.top_priority,
            "priorities": list(self.priorities),
            "required_features": list(self.required_features),
            "preferred_features": list(self.preferred_features),
            "deprioritized": list(self.deprioritized),
            "use_case": self.use_case,
            "budget_max": self.budget_max,
            "budget_label": self.budget_label,
            "reset_to_original": self.reset_to_original,
            "hard_constraint": self.hard_constraint,
        }


@dataclass(frozen=True, slots=True)
class SessionRecommendationRefinement:
    """Authoritative server-side session overlay for one owned decision."""

    decision_id: str
    canonical_context_version: int
    refinement_version: int
    original_best_piq_product_id: str
    session_best_piq_product_id: str
    priorities: SessionPriorities
    recommendation_changed: bool
    status: RefinementStatus
    evidence_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    qualification_state: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    conversation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.canonical_context_version < 1:
            raise ValueError("canonical_context_version must be at least 1")
        if self.refinement_version < 1:
            raise ValueError("refinement_version must be at least 1")
        if not self.original_best_piq_product_id or not self.session_best_piq_product_id:
            raise ValueError("original and session Best Piq product IDs are required")

    @property
    def recommendation_snapshot_sha256(self) -> str:
        """Integrity digest of the session overlay, not a new canonical Recommendation."""

        return _overlay_sha256(
            {
                "decision_id": self.decision_id,
                "canonical_context_version": self.canonical_context_version,
                "refinement_version": self.refinement_version,
                "original_best_piq_product_id": self.original_best_piq_product_id,
                "session_best_piq_product_id": self.session_best_piq_product_id,
                "priorities": self.priorities.to_dict(),
                "recommendation_changed": self.recommendation_changed,
                "status": self.status,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "canonical_context_version": self.canonical_context_version,
            "refinement_version": self.refinement_version,
            "original_best_piq_product_id": self.original_best_piq_product_id,
            "session_best_piq_product_id": self.session_best_piq_product_id,
            "priorities": self.priorities.to_dict(),
            "recommendation_changed": self.recommendation_changed,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "reasons": list(self.reasons),
            "qualification_state": self.qualification_state,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "conversation_id": self.conversation_id,
            "recommendation_snapshot_sha256": self.recommendation_snapshot_sha256,
        }
