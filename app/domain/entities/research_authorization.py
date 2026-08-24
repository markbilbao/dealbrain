"""Session-scoped research authorization.

Server-authored confirmation artifact for a future certified research
execution handoff. Never executes research, mutates a canonical decision,
changes PiqScore, or expands the evaluated set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.domain.entities.research_proposal import ResearchReason

ResearchAuthorizationStatus = Literal[
    "authorized_pending_execution",
    "consumed",
    "cancelled",
    "invalidated",
]

AUTHORIZATION_VERSION = 1
IDEMPOTENCY_KEY_AUTHORITY = "server_derived_owner_conversation_proposal_scope"

_TERMINAL_STATUSES = frozenset({"consumed", "cancelled", "invalidated"})


@dataclass(frozen=True, slots=True)
class FrozenResearchScope:
    """Exact shopper-approved research scope frozen at authorization time."""

    reason: ResearchReason
    evaluated_product_ids: tuple[str, ...]
    outside_set_product_names: tuple[str, ...] = ()
    requested_evidence_topics: tuple[str, ...] = ()
    requested_sources: tuple[str, ...] = ()
    destination_label: str | None = None
    expansion_required: bool = False
    freshness_required: bool = False
    canonical_update_may_be_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "evaluated_product_ids": list(self.evaluated_product_ids),
            "outside_set_product_names": list(self.outside_set_product_names),
            "requested_evidence_topics": list(self.requested_evidence_topics),
            "requested_sources": list(self.requested_sources),
            "destination_label": self.destination_label,
            "expansion_required": self.expansion_required,
            "freshness_required": self.freshness_required,
            "canonical_update_may_be_required": self.canonical_update_may_be_required,
        }

    def digest_payload(self) -> dict[str, Any]:
        """Stable server-authoritative values only. No presentation prose."""

        return {
            "reason": self.reason,
            "evaluated_product_ids": list(self.evaluated_product_ids),
            "outside_set_product_names": list(self.outside_set_product_names),
            "requested_evidence_topics": list(self.requested_evidence_topics),
            "requested_sources": list(self.requested_sources),
            "destination_label": self.destination_label,
            "expansion_required": self.expansion_required,
            "freshness_required": self.freshness_required,
            "canonical_update_may_be_required": self.canonical_update_may_be_required,
        }


@dataclass(frozen=True, slots=True)
class ResearchAuthorization:
    """Owner-bound, version-bound authorization for one logical research execution."""

    authorization_id: str
    authorization_version: int
    owner_binding: str
    conversation_id: str
    decision_id: str
    canonical_context_version: int
    proposal_id: str
    proposal_version: int
    scope: FrozenResearchScope
    scope_digest: str
    proposal_reason: ResearchReason
    evaluated_product_ids: tuple[str, ...]
    idempotency_key: str
    status: ResearchAuthorizationStatus
    created_at: datetime
    updated_at: datetime | None = None
    execution_available: bool = False

    def __post_init__(self) -> None:
        if not self.authorization_id:
            raise ValueError("authorization_id is required")
        if self.authorization_version < 1:
            raise ValueError("authorization_version must be at least 1")
        if not self.owner_binding:
            raise ValueError("owner_binding is required")
        if not self.conversation_id:
            raise ValueError("conversation_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if self.canonical_context_version < 1:
            raise ValueError("canonical_context_version must be at least 1")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if self.proposal_version < 1:
            raise ValueError("proposal_version must be at least 1")
        if not self.scope_digest or len(self.scope_digest) != 64:
            raise ValueError("scope_digest must be a SHA-256 hex digest")
        if not self.idempotency_key:
            raise ValueError("idempotency_key is required")
        if self.execution_available:
            raise ValueError("live research execution is not available")

    @property
    def is_pending_execution(self) -> bool:
        return self.status == "authorized_pending_execution"

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    def to_public_dict(self) -> dict[str, Any]:
        """Shopper-safe authorization payload. No owner identifiers or digests."""

        return {
            "authorization_id": self.authorization_id,
            "authorization_version": self.authorization_version,
            "conversation_id": self.conversation_id,
            "decision_id": self.decision_id,
            "canonical_context_version": self.canonical_context_version,
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "status": self.status,
            "execution_available": False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_public_dict(),
            "proposal_reason": self.proposal_reason,
            "evaluated_product_ids": list(self.evaluated_product_ids),
            "scope": self.scope.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ResearchAuthorizationValidation:
    """Fail-closed result for future execution to consult before doing anything."""

    valid: bool
    reason: str
    authorization: ResearchAuthorization | None = None
    execution_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "authorization_id": (
                self.authorization.authorization_id if self.authorization else None
            ),
            "status": self.authorization.status if self.authorization else None,
            "execution_available": False,
        }


@dataclass(frozen=True, slots=True)
class AuthorizedResearchHandoff:
    """Bounded packet for Sprints 31–38. Contains no connector or live data."""

    authorization_id: str
    authorization_version: int
    conversation_id: str
    decision_id: str
    canonical_context_version: int
    proposal_id: str
    proposal_version: int
    scope: FrozenResearchScope
    scope_digest: str
    idempotency_key: str
    status: ResearchAuthorizationStatus
    execution_available: bool = False

    def __post_init__(self) -> None:
        if self.execution_available:
            raise ValueError("live research execution is not available")
        if self.status != "authorized_pending_execution":
            raise ValueError("handoff requires authorized_pending_execution")

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "authorization_version": self.authorization_version,
            "conversation_id": self.conversation_id,
            "decision_id": self.decision_id,
            "canonical_context_version": self.canonical_context_version,
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "scope": self.scope.to_dict(),
            "scope_digest": self.scope_digest,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "execution_available": False,
            "idempotency_key_authority": IDEMPOTENCY_KEY_AUTHORITY,
            "single_logical_execution": True,
        }
