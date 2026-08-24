"""Research execution routing contracts — Sprint 31.

A validated ResearchAuthorization may be planned against certified providers.
Planning does not execute research, mutate a canonical decision, or claim that
a source was checked. Live execution remains unimplemented (Sprint 38).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from app.core.countries import is_valid_country_code, normalize_country_code
from app.domain.entities.connector_reliability import (
    CircuitBreakerSnapshot,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_authorization import FrozenResearchScope

PLAN_VERSION = 1
EXECUTION_REQUEST_VERSION = 1
DESTINATION_REEVALUATION_IMPLEMENTED = False

ResearchExecutionPlanStatus = Literal[
    "ready",
    "partially_supported",
    "unsupported",
    "blocked_missing_certified_provider",
    "blocked_market_context",
    "stale_authorization",
]

ProviderType = Literal["merchant", "manufacturer", "community", "test"]
ProviderCertificationStatus = Literal[
    "certified",
    "revoked",
    "disabled",
    "pending",
    "expired",
]
CapabilityPolicyState = Literal["allowed", "restricted", "prohibited", "unknown"]
CertificationSourceScope = Literal["exact", "source_agnostic"]
MarketContextSource = Literal["server_trusted"]
EXECUTABLE_CERTIFICATION_STATUS: ProviderCertificationStatus = "certified"


class ResearchCapability(StrEnum):
    """Bounded research capabilities mapped to PiqSavi research needs."""

    PRODUCT_DISCOVERY = "product_discovery"
    OFFER_DISCOVERY = "offer_discovery"
    CURRENT_PRICING = "current_pricing"
    AVAILABILITY = "availability"
    SHIPPING = "shipping"
    TAXES_IMPORT = "taxes_import"
    PROMOTION_EVIDENCE = "promotion_evidence"
    WARRANTY_EVIDENCE = "warranty_evidence"
    PRODUCT_SPECIFICATION = "product_specification"
    REVIEW_COMMUNITY_EVIDENCE = "review_community_evidence"


DESTINATION_SENSITIVE_CAPABILITIES = frozenset(
    {
        ResearchCapability.SHIPPING,
        ResearchCapability.TAXES_IMPORT,
    }
)

MARKET_SENSITIVE_CAPABILITIES = frozenset(
    {
        ResearchCapability.PRODUCT_DISCOVERY,
        ResearchCapability.OFFER_DISCOVERY,
        ResearchCapability.CURRENT_PRICING,
        ResearchCapability.AVAILABILITY,
        ResearchCapability.SHIPPING,
        ResearchCapability.TAXES_IMPORT,
        ResearchCapability.PROMOTION_EVIDENCE,
    }
)


@dataclass(frozen=True, slots=True)
class TrustedMarketContext:
    """Server-trusted market identity. Never accepted from browser input."""

    country_code: str
    source: MarketContextSource = "server_trusted"

    def __post_init__(self) -> None:
        code = normalize_country_code(self.country_code)
        if not code or not is_valid_country_code(code):
            raise ValueError("trusted market must be a valid ISO 3166-1 alpha-2 code")
        if code != self.country_code:
            object.__setattr__(self, "country_code", code)
        if self.source != "server_trusted":
            raise ValueError("market context must be server_trusted")

    def to_dict(self) -> dict[str, Any]:
        return {"country_code": self.country_code, "source": self.source}


@dataclass(frozen=True, slots=True)
class ResearchProviderCertification:
    """Trusted PiqSavi certification for one exact provider requirement.

    Distinct from technical provider capability. A provider must not author
    this record. No certification record means not certified.
    """

    provider_id: str
    capability: ResearchCapability
    market: str
    certification_version: str
    status: ProviderCertificationStatus
    policy: CapabilityPolicyState
    source: str | None = None
    source_scope: CertificationSourceScope = "exact"
    test_fixture: bool = False
    certification_id: str = ""

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError("provider_id is required")
        if not self.certification_version:
            raise ValueError("certification_version is required")
        code = normalize_country_code(self.market)
        if not code or not is_valid_country_code(code):
            raise ValueError("certification market must be a valid ISO country code")
        if code != self.market:
            object.__setattr__(self, "market", code)
        if self.status not in {
            "certified",
            "revoked",
            "disabled",
            "pending",
            "expired",
        }:
            raise ValueError("certification status is unknown and fails closed")
        if self.policy not in {"allowed", "restricted", "prohibited", "unknown"}:
            raise ValueError("certification policy is unknown and fails closed")
        if self.source_scope == "exact":
            if not self.source:
                raise ValueError("exact certification requires an explicit source identity")
        elif self.source_scope == "source_agnostic":
            if self.source is not None:
                raise ValueError("source-agnostic certification must not name a source")
        else:
            raise ValueError("source_scope must be exact or source_agnostic")

    @property
    def is_production_eligible(self) -> bool:
        return (
            self.status == EXECUTABLE_CERTIFICATION_STATUS
            and self.policy == "allowed"
            and not self.test_fixture
        )

    @property
    def is_executable(self) -> bool:
        return self.status == EXECUTABLE_CERTIFICATION_STATUS and self.policy == "allowed"

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
            "certification_id": self.certification_id,
            "provider_id": self.provider_id,
            "capability": self.capability.value,
            "market": self.market,
            "source": self.source,
            "source_scope": self.source_scope,
            "status": self.status,
            "policy": self.policy,
            "certification_version": self.certification_version,
            "test_fixture": self.test_fixture,
        }


@dataclass(frozen=True, slots=True)
class ResearchProviderRoutingPolicy:
    """Trusted server-owned routing preference. Does not certify a provider."""

    provider_id: str
    routing_priority: int
    test_fixture: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError("provider_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "routing_priority": self.routing_priority,
            "test_fixture": self.test_fixture,
        }


@dataclass(frozen=True, slots=True)
class ResearchProviderDescriptor:
    """Technical provider metadata. Does not grant certification or routing preference."""

    provider_id: str
    provider_type: ProviderType
    supported_markets: tuple[str, ...]
    supported_capabilities: tuple[ResearchCapability, ...]
    supported_sources: tuple[str, ...]
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE
    test_fixture: bool = False
    kill_switch: KillSwitch = KillSwitch()
    circuit_breaker: CircuitBreakerSnapshot = CircuitBreakerSnapshot()
    affiliate_commission_rate: float | None = None
    may_expand_evaluated_set: bool = False
    can_provide_pricing: bool = False
    can_provide_shipping_taxes: bool = False
    can_provide_product_evidence: bool = False
    can_provide_review_evidence: bool = False

    def __post_init__(self) -> None:
        if not self.provider_id:
            raise ValueError("provider_id is required")
        codes = tuple(normalize_country_code(code) or "" for code in self.supported_markets)
        if any(not code or not is_valid_country_code(code) for code in codes):
            raise ValueError("supported_markets must be valid ISO country codes")
        object.__setattr__(self, "supported_markets", codes)
        if self.test_fixture and self.provider_type != "test":
            raise ValueError("test fixtures must use provider_type='test'")
        if not self.test_fixture and self.provider_type == "test":
            raise ValueError("provider_type='test' requires test_fixture=True")

    @property
    def is_operationally_available(self) -> bool:
        return (
            self.operational_status == ConnectorOperationalStatus.AVAILABLE
            and not self.kill_switch.engaged
            and self.circuit_breaker.allows_execution
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "supported_markets": list(self.supported_markets),
            "supported_capabilities": [item.value for item in self.supported_capabilities],
            "supported_sources": list(self.supported_sources),
            "operational_status": self.operational_status.value,
            "test_fixture": self.test_fixture,
            "kill_switch": self.kill_switch.to_dict(),
            "circuit_breaker": self.circuit_breaker.to_dict(),
            "may_expand_evaluated_set": self.may_expand_evaluated_set,
            "can_provide_pricing": self.can_provide_pricing,
            "can_provide_shipping_taxes": self.can_provide_shipping_taxes,
            "can_provide_product_evidence": self.can_provide_product_evidence,
            "can_provide_review_evidence": self.can_provide_review_evidence,
        }


@dataclass(frozen=True, slots=True)
class ProviderEligibility:
    """Internal audit record for why a provider was selected or rejected."""

    provider_id: str
    eligible: bool
    reasons: tuple[str, ...]
    capability: ResearchCapability | None = None
    market: str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "capability": self.capability.value if self.capability else None,
            "market": self.market,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ResearchExecutionRequest:
    """Validated authorization ready to be planned. No owner identifiers."""

    execution_request_id: str
    execution_request_version: int
    authorization_id: str
    authorization_version: int
    decision_id: str
    canonical_context_version: int
    conversation_id: str
    proposal_id: str
    proposal_version: int
    scope: FrozenResearchScope
    scope_digest: str
    authorization_idempotency_key: str
    market: TrustedMarketContext | None = None

    def __post_init__(self) -> None:
        if not self.execution_request_id:
            raise ValueError("execution_request_id is required")
        if self.execution_request_version < 1:
            raise ValueError("execution_request_version must be at least 1")
        if not self.authorization_id:
            raise ValueError("authorization_id is required")
        if not self.scope_digest or len(self.scope_digest) != 64:
            raise ValueError("scope_digest must be a SHA-256 hex digest")
        if not self.authorization_idempotency_key:
            raise ValueError("authorization_idempotency_key is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_request_id": self.execution_request_id,
            "execution_request_version": self.execution_request_version,
            "authorization_id": self.authorization_id,
            "authorization_version": self.authorization_version,
            "decision_id": self.decision_id,
            "canonical_context_version": self.canonical_context_version,
            "conversation_id": self.conversation_id,
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "scope": self.scope.to_dict(),
            "scope_digest": self.scope_digest,
            "market": self.market.to_dict() if self.market else None,
        }


@dataclass(frozen=True, slots=True)
class ResearchProviderStep:
    """One certified capability assignment. Planned is not attempted."""

    step_index: int
    provider_id: str
    provider_type: ProviderType
    capability: ResearchCapability
    source_identities: tuple[str, ...]
    market: str | None
    certification_id: str
    certification_version: str
    selection_reason: str
    attempted: bool = False

    def __post_init__(self) -> None:
        if self.attempted:
            raise ValueError("Sprint 31 planning must not mark a provider as attempted")
        if self.step_index < 1:
            raise ValueError("step_index must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "provider_id": self.provider_id,
            "provider_type": self.provider_type,
            "capability": self.capability.value,
            "source_identities": list(self.source_identities),
            "market": self.market,
            "certification_id": self.certification_id,
            "certification_version": self.certification_version,
            "selection_reason": self.selection_reason,
            "attempted": False,
        }


@dataclass(frozen=True, slots=True)
class BlockedRequirement:
    """A required capability that cannot be executed truthfully."""

    capability: ResearchCapability
    reason: str
    detail: str
    unknown: bool = True
    material_to_final_cost: bool = False
    fabricated_value: None = None

    def __post_init__(self) -> None:
        if self.fabricated_value is not None:
            raise ValueError("unsupported capabilities must remain unknown, not fabricated")
        if not self.unknown:
            raise ValueError("blocked requirements remain unknown until certified execution")

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability.value,
            "reason": self.reason,
            "detail": self.detail,
            "unknown": True,
            "material_to_final_cost": self.material_to_final_cost,
            "fabricated_value": None,
        }


@dataclass(frozen=True, slots=True)
class ResearchExecutionPlan:
    """Bounded certified execution plan. Ready means plannable, not started."""

    plan_id: str
    plan_version: int
    authorization_id: str
    authorization_version: int
    decision_id: str
    canonical_context_version: int
    conversation_id: str
    proposal_id: str
    proposal_version: int
    scope_digest: str
    required_capabilities: tuple[ResearchCapability, ...]
    eligible_steps: tuple[ResearchProviderStep, ...]
    blocked_requirements: tuple[BlockedRequirement, ...]
    eligibility_audit: tuple[ProviderEligibility, ...]
    support_status: ResearchExecutionPlanStatus
    plan_digest: str
    outside_set_product_names: tuple[str, ...] = ()
    requested_sources: tuple[str, ...] = ()
    market: TrustedMarketContext | None = None
    execution_available: bool = False
    execution_implemented: bool = False
    plan_ready: bool = False
    source_checked: bool = False
    attempted: bool = False

    def __post_init__(self) -> None:
        if not self.plan_id:
            raise ValueError("plan_id is required")
        if self.plan_version < 1:
            raise ValueError("plan_version must be at least 1")
        if not self.plan_digest or len(self.plan_digest) != 64:
            raise ValueError("plan_digest must be a SHA-256 hex digest")
        if self.execution_available:
            raise ValueError("live research execution is not available")
        if self.execution_implemented:
            raise ValueError("certified provider execution is not implemented")
        if self.source_checked or self.attempted:
            raise ValueError("a planned provider is not an attempted or checked source")
        if self.plan_ready and self.support_status != "ready":
            raise ValueError("plan_ready requires support_status='ready'")
        if self.support_status == "ready" and not self.plan_ready:
            raise ValueError("ready plans must set plan_ready=True")
        if self.support_status == "ready" and self.blocked_requirements:
            raise ValueError("ready plans cannot carry blocked requirements")
        if self.support_status == "ready" and not self.eligible_steps:
            raise ValueError("ready plans require at least one certified step")

    def to_public_dict(self) -> dict[str, Any]:
        """Shopper-safe high-level state. No provider IDs, digests, or secrets."""

        return {
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "authorization_id": self.authorization_id,
            "authorization_version": self.authorization_version,
            "decision_id": self.decision_id,
            "canonical_context_version": self.canonical_context_version,
            "support_status": self.support_status,
            "plan_ready": self.plan_ready,
            "execution_available": False,
            "execution_implemented": False,
            "execution_started": False,
            "source_checked": False,
            "blocked_capability_count": len(self.blocked_requirements),
            "required_capability_count": len(self.required_capabilities),
            "outside_set_product_names": list(self.outside_set_product_names),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_public_dict(),
            "conversation_id": self.conversation_id,
            "proposal_id": self.proposal_id,
            "proposal_version": self.proposal_version,
            "scope_digest": self.scope_digest,
            "plan_digest": self.plan_digest,
            "required_capabilities": [item.value for item in self.required_capabilities],
            "eligible_steps": [step.to_dict() for step in self.eligible_steps],
            "blocked_requirements": [item.to_dict() for item in self.blocked_requirements],
            "eligibility_audit": [item.to_dict() for item in self.eligibility_audit],
            "requested_sources": list(self.requested_sources),
            "market": self.market.to_dict() if self.market else None,
        }


@dataclass(frozen=True, slots=True)
class ResearchPlanningResult:
    """Router output. Stale authorizations produce no plan."""

    planned: bool
    reason: str
    plan: ResearchExecutionPlan | None = None
    execution_available: bool = False
    execution_implemented: bool = False

    def __post_init__(self) -> None:
        if self.execution_available or self.execution_implemented:
            raise ValueError("live research execution is not available")
        if self.planned and self.plan is None:
            raise ValueError("planned results require a ResearchExecutionPlan")
        if not self.planned and self.plan is not None:
            raise ValueError("rejected planning must not return a plan")

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "planned": self.planned,
            "reason": self.reason,
            "support_status": self.plan.support_status if self.plan else None,
            "plan_ready": self.plan.plan_ready if self.plan else False,
            "execution_available": False,
            "execution_implemented": False,
            "execution_started": False,
            "plan": self.plan.to_public_dict() if self.plan else None,
        }


@dataclass(frozen=True, slots=True)
class ResearchExecutionTraceStep:
    """Sprint 38 skeleton. Sprint 31 must not fabricate attempts."""

    plan_id: str
    provider_id: str
    requested_capability: ResearchCapability
    market: str | None = None
    attempted: bool = False
    attempt_status: Literal["not_attempted"] = "not_attempted"
    evidence_ids: tuple[str, ...] = ()
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_category: str | None = None
    freshness_checked_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.attempted or self.attempt_status != "not_attempted":
            raise ValueError("Sprint 31 must not fabricate provider attempts")
        if self.evidence_ids:
            raise ValueError("planned providers do not produce evidence")
        if self.started_at is not None or self.finished_at is not None:
            raise ValueError("unattempted steps cannot have execution timestamps")
        if self.freshness_checked_at is not None:
            raise ValueError("unattempted steps cannot claim freshness checks")


@dataclass(frozen=True, slots=True)
class ResearchExecutionTrace:
    """Empty until Sprint 38 actually executes a certified plan."""

    plan_id: str
    steps: tuple[ResearchExecutionTraceStep, ...] = ()
    attempted_sources: tuple[str, ...] = ()
    succeeded_sources: tuple[str, ...] = ()
    failed_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.steps or self.attempted_sources or self.succeeded_sources or self.failed_sources:
            raise ValueError("Sprint 31 planning must not populate an execution trace")

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "steps": [],
            "attempted_sources": [],
            "succeeded_sources": [],
            "failed_sources": [],
            "attempted": False,
        }


def empty_execution_trace(plan_id: str) -> ResearchExecutionTrace:
    """Trace skeleton for a plan that has not been attempted."""

    return ResearchExecutionTrace(plan_id=plan_id)
