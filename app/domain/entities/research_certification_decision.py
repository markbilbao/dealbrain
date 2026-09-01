"""Trusted certification-decision contracts — Sprint 32.2.

A decision reviews exact evidence and may write a certification record.
Evidence never self-promotes. Providers never self-certify. Routing is
unchanged. This is not a research-execution trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from app.core.countries import is_valid_country_code, normalize_country_code
from app.domain.entities.research_execution import (
    CapabilityPolicyState,
    CertificationSourceScope,
    ProviderCertificationStatus,
    ResearchCapability,
    ResearchProviderCertification,
)

CertificationDecisionReason = Literal[
    "approved",
    "revoked",
    "disabled",
    "expired",
    "denied",
    "evidence_missing",
    "evidence_incomplete",
    "identity_mismatch",
    "evidence_stale",
    "fixture_forbidden",
    "reviewer_missing",
    "restrictions_unresolved",
    "version_mismatch",
    "certification_missing",
]

_BLOCKING_STATUSES = frozenset({"revoked", "disabled", "expired"})


@dataclass(frozen=True, slots=True)
class CertificationDecisionRequest:
    """Explicit trusted review input. Does not infer policy from evidence."""

    provider_id: str
    capability: ResearchCapability
    market: str
    requested_status: ProviderCertificationStatus
    requested_policy: CapabilityPolicyState
    certification_version: str
    reviewer: str
    decided_at: date
    source: str | None = None
    source_scope: CertificationSourceScope = "exact"

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError("provider_id is required")
        if not self.certification_version.strip():
            raise ValueError("certification_version is required")
        if not self.reviewer.strip():
            raise ValueError("reviewer is required")
        if type(self.decided_at) is not date:
            raise ValueError("decided_at must be a calendar date")
        code = normalize_country_code(self.market)
        if not code or not is_valid_country_code(code):
            raise ValueError("decision market must be a valid ISO country code")
        if code != self.market:
            object.__setattr__(self, "market", code)
        if self.requested_status not in {
            "certified",
            "revoked",
            "disabled",
            "pending",
            "expired",
        }:
            raise ValueError("requested certification status is unknown and fails closed")
        if self.requested_policy not in {"allowed", "restricted", "prohibited", "unknown"}:
            raise ValueError("requested certification policy is unknown and fails closed")
        if self.source_scope == "exact":
            if not self.source:
                raise ValueError("exact decision requires an explicit source identity")
        elif self.source_scope == "source_agnostic":
            if self.source is not None:
                raise ValueError("source-agnostic decision must not name a source")
        else:
            raise ValueError("source_scope must be exact or source_agnostic")
        object.__setattr__(self, "reviewer", self.reviewer.strip())
        object.__setattr__(self, "certification_version", self.certification_version.strip())

    def lookup_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.provider_id,
            self.capability.value,
            self.market,
            self.source_scope,
            self.source or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "capability": self.capability.value,
            "market": self.market,
            "source": self.source,
            "source_scope": self.source_scope,
            "requested_status": self.requested_status,
            "requested_policy": self.requested_policy,
            "certification_version": self.certification_version,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class CertificationDecisionResult:
    """Auditable outcome of one trusted certification decision."""

    accepted: bool
    reason: CertificationDecisionReason
    provider_id: str
    capability: ResearchCapability
    market: str
    reviewer: str
    decided_at: date
    source: str | None = None
    source_scope: CertificationSourceScope = "exact"
    evidence_ids: tuple[str, ...] = ()
    certification: ResearchProviderCertification | None = None
    requested_status: ProviderCertificationStatus | None = None
    requested_policy: CapabilityPolicyState | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "provider_id": self.provider_id,
            "capability": self.capability.value,
            "market": self.market,
            "source": self.source,
            "source_scope": self.source_scope,
            "evidence_ids": list(self.evidence_ids),
            "certification_id": (
                self.certification.certification_id if self.certification else None
            ),
            "status": self.certification.status if self.certification else None,
            "policy": self.certification.policy if self.certification else None,
            "certification_version": (
                self.certification.certification_version if self.certification else None
            ),
            "requested_status": self.requested_status,
            "requested_policy": self.requested_policy,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at.isoformat(),
        }


def is_blocking_status(status: ProviderCertificationStatus) -> bool:
    return status in _BLOCKING_STATUSES
