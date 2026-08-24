"""Session-scoped research proposal.

Authorization boundary only. Never executes research, mutates a canonical
decision, changes PiqScore, or expands the evaluated set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

ResearchReason = Literal[
    "outside_evaluated_set",
    "insufficient_evidence",
    "freshness_required",
    "requested_source",
    "reevaluation_required",
    "evaluated_set_expansion",
]

ResearchProposalStatus = Literal[
    "pending_confirmation",
    "cancelled",
    "replaced",
    "research_confirmation_received_but_execution_unavailable",
]

CONTRACT_PENDING_STATUS = "awaiting_explicit_confirmation"


@dataclass(frozen=True, slots=True)
class ResearchProposal:
    """Server-authored pending research request for one owned conversation."""

    proposal_id: str
    decision_id: str
    proposal_version: int
    reason: ResearchReason
    status: ResearchProposalStatus
    proposal_text: str
    scope_text: str
    evaluated_product_ids: tuple[str, ...]
    conversation_id: str | None = None
    requested_evidence_topics: tuple[str, ...] = ()
    outside_set_product_names: tuple[str, ...] = ()
    requested_sources: tuple[str, ...] = ()
    destination_label: str | None = None
    expansion_required: bool = False
    freshness_required: bool = False
    canonical_update_may_be_required: bool = False
    confirmation_required: bool = True
    session_best_piq_product_id: str | None = None
    original_best_piq_product_id: str | None = None
    canonical_context_version: int = 1
    replaced_proposal_id: str | None = None
    authorization_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.proposal_version < 1:
            raise ValueError("proposal_version must be at least 1")
        if self.canonical_context_version < 1:
            raise ValueError("canonical_context_version must be at least 1")
        if not self.proposal_text.strip():
            raise ValueError("proposal_text is required")
        if not self.scope_text.strip():
            raise ValueError("scope_text is required")
        if self.status == "pending_confirmation" and not self.confirmation_required:
            raise ValueError("a pending proposal always requires explicit confirmation")

    @property
    def is_pending(self) -> bool:
        return self.status == "pending_confirmation"

    @property
    def is_confirmation_recorded(self) -> bool:
        return self.status == "research_confirmation_received_but_execution_unavailable"

    def to_contract(self) -> dict[str, Any]:
        """Closed research_proposal object for the frozen conversation-action schema."""

        return {
            "proposal_id": self.proposal_id,
            "question": self.proposal_text,
            "requested_product_ids": list(self.evaluated_product_ids),
            "status": CONTRACT_PENDING_STATUS
            if self.status == "pending_confirmation"
            else self.status,
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Shopper-safe proposal payload. No connector class names or SKUs invented."""

        return {
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "decision_id": self.decision_id,
            "conversation_id": self.conversation_id,
            "reason": self.reason,
            "status": self.status,
            "proposal_text": self.proposal_text,
            "scope": self.scope_text,
            "requested_evidence_topics": list(self.requested_evidence_topics),
            "outside_set_product_names": list(self.outside_set_product_names),
            "requested_sources": list(self.requested_sources),
            "destination_label": self.destination_label,
            "expansion_required": self.expansion_required,
            "freshness_required": self.freshness_required,
            "canonical_update_may_be_required": self.canonical_update_may_be_required,
            "confirmation_required": self.confirmation_required,
            "evaluated_product_ids": list(self.evaluated_product_ids),
            "session_best_piq_product_id": self.session_best_piq_product_id,
            "original_best_piq_product_id": self.original_best_piq_product_id,
            "canonical_context_version": self.canonical_context_version,
            "replaced_proposal_id": self.replaced_proposal_id,
            "authorization_id": self.authorization_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "execution_started": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_public_dict()
