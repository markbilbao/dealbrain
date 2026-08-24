"""Sprint 31 research execution router.

Validates a ResearchAuthorization, derives required capabilities, and builds
a fail-closed certified execution plan. Does not execute providers, mutate
canonical decisions, or claim that a source was checked.
"""

from __future__ import annotations

from app.domain.entities.research_authorization import (
    AuthorizedResearchHandoff,
    ResearchAuthorization,
)
from app.domain.entities.research_execution import (
    DESTINATION_SENSITIVE_CAPABILITIES,
    EXECUTION_REQUEST_VERSION,
    PLAN_VERSION,
    BlockedRequirement,
    ProviderEligibility,
    ResearchCapability,
    ResearchExecutionPlan,
    ResearchExecutionRequest,
    ResearchPlanningResult,
    ResearchProviderStep,
    TrustedMarketContext,
    empty_execution_trace,
)
from app.domain.entities.research_proposal import ResearchProposal
from app.domain.entities.shopping_assistant import ConversationOwner
from app.research.capabilities import derive_required_capabilities
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
)
from app.research.digest import stable_sha256
from app.research.eligibility import assign_capability_step, destination_sensitive_required
from app.research.registry import ResearchProviderRegistry
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    production_research_provider_routing_policy_catalog,
)
from app.services.research_authorization import (
    get_authorized_research_handoff,
    validate_research_authorization_for_execution,
)


def execution_request_from_handoff(
    handoff: AuthorizedResearchHandoff,
    *,
    trusted_market: TrustedMarketContext | None = None,
) -> ResearchExecutionRequest:
    """Build the trusted planning input from a validated authorization handoff."""

    request_id = "research-exec-req:" + stable_sha256(
        {
            "kind": "research_execution_request_v1",
            "authorization_id": handoff.authorization_id,
            "authorization_version": handoff.authorization_version,
            "scope_digest": handoff.scope_digest,
        }
    )
    return ResearchExecutionRequest(
        execution_request_id=request_id,
        execution_request_version=EXECUTION_REQUEST_VERSION,
        authorization_id=handoff.authorization_id,
        authorization_version=handoff.authorization_version,
        decision_id=handoff.decision_id,
        canonical_context_version=handoff.canonical_context_version,
        conversation_id=handoff.conversation_id,
        proposal_id=handoff.proposal_id,
        proposal_version=handoff.proposal_version,
        scope=handoff.scope,
        scope_digest=handoff.scope_digest,
        authorization_idempotency_key=handoff.idempotency_key,
        market=trusted_market,
    )


def plan_authorized_research(
    authorization: ResearchAuthorization | None,
    *,
    owner: ConversationOwner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    registry: ResearchProviderRegistry,
    catalog: ResearchProviderCertificationCatalog | None = None,
    routing_policy: ResearchProviderRoutingPolicyCatalog | None = None,
    trusted_market: TrustedMarketContext | None = None,
    proposal: ResearchProposal | None = None,
    expected_scope_digest: str | None = None,
    expected_proposal_id: str | None = None,
    expected_proposal_version: int | None = None,
) -> ResearchPlanningResult:
    """Plan certified research for a validated authorization, then stop.

    Input must be a server-held authorization. Client-selected providers,
    markets, sources, and product SKUs are ignored. This function never
    calls ``execute`` and never sets ``execution_available=True``.
    Technical provider support is not certification. Missing catalog records
    fail closed.
    """

    certification_catalog = catalog or production_research_provider_certification_catalog()
    routing = routing_policy or production_research_provider_routing_policy_catalog()
    validation = validate_research_authorization_for_execution(
        authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal=proposal,
        expected_scope_digest=expected_scope_digest,
        expected_proposal_id=expected_proposal_id,
        expected_proposal_version=expected_proposal_version,
    )
    if not validation.valid:
        return ResearchPlanningResult(planned=False, reason=validation.reason)
    handoff = get_authorized_research_handoff(
        authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal=proposal,
        expected_scope_digest=expected_scope_digest,
    )
    if handoff is None:
        return ResearchPlanningResult(planned=False, reason="stale_authorization")

    request = execution_request_from_handoff(handoff, trusted_market=trusted_market)
    plan = build_execution_plan(request, registry, certification_catalog, routing)
    return ResearchPlanningResult(
        planned=True,
        reason=plan.support_status,
        plan=plan,
    )


def build_execution_plan(
    request: ResearchExecutionRequest,
    registry: ResearchProviderRegistry,
    catalog: ResearchProviderCertificationCatalog,
    routing: ResearchProviderRoutingPolicyCatalog,
) -> ResearchExecutionPlan:
    """Construct a fail-closed plan from a trusted execution request."""

    required = derive_required_capabilities(request.scope)
    destination_sensitive = destination_sensitive_required(bool(request.scope.destination_label))
    steps: list[ResearchProviderStep] = []
    blocked: list[BlockedRequirement] = []
    audits: list[ProviderEligibility] = []
    next_index = 1
    for capability in required:
        assigned, blocked_items, capability_audits = assign_capability_step(
            registry,
            catalog,
            routing,
            capability=capability,
            market=request.market,
            sources=request.scope.requested_sources,
            step_index=next_index,
            destination_sensitive=destination_sensitive
            or request.scope.reason == "reevaluation_required",
        )
        steps.extend(assigned)
        blocked.extend(blocked_items)
        audits.extend(capability_audits)
        next_index += max(len(assigned), 1)

    status = _support_status(
        required=required,
        steps=steps,
        blocked=blocked,
        destination_sensitive=destination_sensitive
        or request.scope.reason == "reevaluation_required",
        market=request.market,
        reason=request.scope.reason,
    )
    digest = research_plan_digest(
        request=request,
        required=required,
        steps=steps,
        blocked=blocked,
        status=status,
        registry_fingerprint=registry.fingerprint(),
        certification_fingerprint=catalog.fingerprint(),
        routing_policy_fingerprint=routing.fingerprint(),
    )
    plan = ResearchExecutionPlan(
        plan_id=f"research-plan:{digest}",
        plan_version=PLAN_VERSION,
        authorization_id=request.authorization_id,
        authorization_version=request.authorization_version,
        decision_id=request.decision_id,
        canonical_context_version=request.canonical_context_version,
        conversation_id=request.conversation_id,
        proposal_id=request.proposal_id,
        proposal_version=request.proposal_version,
        scope_digest=request.scope_digest,
        required_capabilities=required,
        eligible_steps=tuple(steps),
        blocked_requirements=tuple(blocked),
        eligibility_audit=tuple(audits),
        support_status=status,
        plan_digest=digest,
        outside_set_product_names=request.scope.outside_set_product_names,
        requested_sources=request.scope.requested_sources,
        market=request.market,
        execution_available=False,
        execution_implemented=False,
        plan_ready=status == "ready",
        source_checked=False,
        attempted=False,
    )
    empty_execution_trace(plan.plan_id)
    return plan


def research_plan_digest(
    *,
    request: ResearchExecutionRequest,
    required: tuple[ResearchCapability, ...],
    steps: list[ResearchProviderStep],
    blocked: list[BlockedRequirement],
    status: str,
    registry_fingerprint: str,
    certification_fingerprint: str,
    routing_policy_fingerprint: str,
) -> str:
    return stable_sha256(
        {
            "kind": "research_execution_plan_v1",
            "authorization_id": request.authorization_id,
            "authorization_version": request.authorization_version,
            "scope_digest": request.scope_digest,
            "market": request.market.country_code if request.market else None,
            "required_capabilities": [item.value for item in required],
            "provider_ids": [step.provider_id for step in steps],
            "capability_assignments": [
                {
                    "provider_id": step.provider_id,
                    "capability": step.capability.value,
                    "sources": list(step.source_identities),
                    "market": step.market,
                    "certification_id": step.certification_id,
                    "certification_version": step.certification_version,
                }
                for step in steps
            ],
            "blocked": [
                {"capability": item.capability.value, "reason": item.reason} for item in blocked
            ],
            "status": status,
            "registry_fingerprint": registry_fingerprint,
            "certification_fingerprint": certification_fingerprint,
            "routing_policy_fingerprint": routing_policy_fingerprint,
        }
    )


def _support_status(
    *,
    required: tuple[ResearchCapability, ...],
    steps: list[ResearchProviderStep],
    blocked: list[BlockedRequirement],
    destination_sensitive: bool,
    market: TrustedMarketContext | None,
    reason: str,
) -> str:
    if not required:
        return "unsupported"
    blocked_caps = {item.capability for item in blocked}
    covered = {step.capability for step in steps} - blocked_caps
    missing = [item for item in required if item not in covered]
    if not missing:
        return "ready"
    blocked_reasons = {item.reason for item in blocked}
    if not steps:
        if market is None or "missing_market_context" in blocked_reasons:
            return "blocked_market_context"
        if destination_sensitive and missing and set(missing) <= DESTINATION_SENSITIVE_CAPABILITIES:
            return "blocked_market_context"
        if reason == "reevaluation_required" and "destination_support_not_ready" in blocked_reasons:
            return "blocked_market_context"
        return "blocked_missing_certified_provider"
    if (
        destination_sensitive
        and reason == "reevaluation_required"
        and set(missing) <= DESTINATION_SENSITIVE_CAPABILITIES
    ):
        return "blocked_market_context"
    return "partially_supported"
