"""Sprint 38 preparation entrypoint for a trusted research plan.

Ask PiqSavi confirmation already creates a ResearchAuthorization. This module
does not parse shopper confirmation text and does not accept a client token as
execution identity. It prepares or refuses the Sprint 31 plan that was built
from that authorization.

Live connectors are not called. ``mark_research_authorization_consumed`` is
not called. Consumption belongs only to the later boundary where one logical
live attempt actually starts. A closed live mode, a disabled provider, absent
routing, and a blocked plan leave the authorization
``authorized_pending_execution``.

One preparation binding pins one plan to the authorization. The same plan
reuses that binding. A different plan is ``authorization_plan_conflict`` and
does not replace the stored plan. The ledger is in-process only.

The authoritative production trace is
``app.domain.entities.research_execution.ResearchExecutionTrace``. It stays
empty. The scripted ``ExecutionTrace`` in ``sprint38_live_execution`` is
chaos-test accounting and is not a second production trace.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_execution import (
    DESTINATION_SENSITIVE_CAPABILITIES,
    ResearchExecutionPlan,
    ResearchExecutionTrace,
    TrustedMarketContext,
    empty_execution_trace,
)
from app.domain.entities.research_proposal import ResearchProposal
from app.domain.entities.shopping_assistant import ConversationOwner
from app.market.selection import SelectedShoppingMarket, intended_default_shopping_market
from app.market.support import production_certified_shopping_markets
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
)
from app.research.digest import stable_sha256
from app.research.registry import ResearchProviderRegistry, production_research_provider_registry
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    production_research_provider_routing_policy_catalog,
)
from app.research.shopify_global_catalog_provider import SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    ExecutionTrace,
    LiveResearchTarget,
    assess_live_research_mode,
    refuse_shopify_execution,
)
from app.services.research_authorization import validate_research_authorization_for_execution
from app.services.research_execution_router import plan_authorized_research

PreparationOutcome = Literal[
    "prepared_but_live_unavailable",
    "blocked_live_mode",
    "blocked_routing",
    "blocked_provider",
    "blocked_market",
    "blocked_capability",
    "blocked_authorization",
    "caller_target_rejected",
]

# Preparation is not the consumption boundary. ``mark_research_authorization_consumed``
# runs only when one logical live connector attempt starts.
AUTHORIZATION_CONSUMPTION_ON_PREPARATION = False
AUTHORITATIVE_TRACE_MODEL = "app.domain.entities.research_execution.ResearchExecutionTrace"


@dataclass(frozen=True, slots=True)
class ResearchExecutionPreparation:
    """Bounded refusal or non-live preparation. Never a completed live run."""

    outcome: PreparationOutcome
    reason: str
    decision_id: str
    execution_id: str | None
    authorization_status: str | None
    plan_id: str | None
    trace: ResearchExecutionTrace
    blocking_reasons: tuple[str, ...] = ()
    assessed_targets: tuple[tuple[str, str, str], ...] = ()
    authorization_consumed: bool = False
    execution_started: bool = False
    execution_completed: bool = False
    source_checked: bool = False
    attempted: bool = False
    live: bool = False
    connectors_invoked: bool = False
    shopify_live_call_count: int = 0
    shopify_execute_invoked: bool = False
    prior_decision_preserved: bool = True
    prior_decision_id: str = ""
    execution_available: bool = False
    execution_implemented: bool = False

    def __post_init__(self) -> None:
        if self.authorization_consumed or AUTHORIZATION_CONSUMPTION_ON_PREPARATION:
            raise ValueError("preparation must not consume an authorization")
        if self.execution_started or self.execution_completed:
            raise ValueError("preparation must not start or complete execution")
        if self.source_checked or self.attempted or self.live:
            raise ValueError("preparation must not claim a source was checked or live")
        if self.connectors_invoked or self.shopify_execute_invoked or self.shopify_live_call_count:
            raise ValueError("preparation must not call a connector or Shopify")
        if self.execution_available or self.execution_implemented:
            raise ValueError("live research execution is not available")
        if not self.prior_decision_preserved:
            raise ValueError("preparation must preserve the prior decision")
        if self.prior_decision_id and self.prior_decision_id != self.decision_id:
            raise ValueError("preparation must not replace the prior decision")
        if self.trace.steps or self.trace.attempted_sources or self.trace.succeeded_sources:
            raise ValueError("the authoritative trace stays empty until live execution")

    def to_public_dict(self) -> dict[str, object]:
        """Shopper-safe state. No principal id, session secret, or scope digest."""

        return {
            "outcome": self.outcome,
            "reason": self.reason,
            "execution_id": self.execution_id,
            "authorization_status": self.authorization_status,
            "authorization_consumed": False,
            "execution_started": False,
            "execution_completed": False,
            "source_checked": False,
            "attempted": False,
            "live": False,
            "connectors_invoked": False,
            "prior_decision_preserved": True,
            "plan_id": self.plan_id,
            "blocking_reasons": list(self.blocking_reasons),
        }


@dataclass(frozen=True, slots=True)
class AuthorizedExecutionBinding:
    """One logical execution for one server authorization key. No raw principal."""

    execution_id: str
    decision_id: str
    plan_id: str
    state: Literal["prepared_unavailable"] = "prepared_unavailable"

    def __post_init__(self) -> None:
        if self.state != "prepared_unavailable":
            raise ValueError("this slice cannot mark an execution running or completed")


class AuthorizationPlanConflict(Exception):
    """The authorization is already pinned to a different prepared plan."""

    def __init__(self, binding: AuthorizedExecutionBinding) -> None:
        self.binding = binding
        super().__init__("authorization_plan_conflict")


class AuthorizedExecutionLedger:
    """In-process preparation bindings keyed by the server authorization key.

    Not durable live-execution storage. One binding pins one plan. A different
    plan for the same authorization is rejected and the stored binding is left
    unchanged. Trusted replanning remains future Sprint 38 work.
    """

    def __init__(self) -> None:
        self._by_authorization_key: dict[str, AuthorizedExecutionBinding] = {}

    def bind(
        self,
        *,
        authorization_idempotency_key: str,
        decision_id: str,
        plan_id: str,
    ) -> AuthorizedExecutionBinding:
        existing = self._by_authorization_key.get(authorization_idempotency_key)
        if existing is not None:
            if existing.decision_id != decision_id:
                raise ValueError("authorization identity does not match the stored execution")
            if existing.plan_id != plan_id:
                raise AuthorizationPlanConflict(existing)
            return existing
        binding = AuthorizedExecutionBinding(
            execution_id=authorized_execution_id(authorization_idempotency_key),
            decision_id=decision_id,
            plan_id=plan_id,
        )
        self._by_authorization_key[authorization_idempotency_key] = binding
        return binding

    def get(self, authorization_idempotency_key: str) -> AuthorizedExecutionBinding | None:
        return self._by_authorization_key.get(authorization_idempotency_key)

    def __len__(self) -> int:
        return len(self._by_authorization_key)


_PRODUCTION_LEDGER = AuthorizedExecutionLedger()


def production_authorized_execution_ledger() -> AuthorizedExecutionLedger:
    return _PRODUCTION_LEDGER


def authorized_execution_id(authorization_idempotency_key: str) -> str:
    """Derive execution identity from the server authorization key only."""

    if not authorization_idempotency_key.startswith("research-auth:"):
        raise ValueError("execution identity requires a server research authorization key")
    digest = stable_sha256(
        {
            "kind": "sprint38_authorized_execution_v1",
            "authorization_idempotency_key": authorization_idempotency_key,
        }
    )
    return f"research-exec:{digest[:32]}"


def project_to_authoritative_trace(
    plan_id: str,
    scripted: ExecutionTrace | None = None,
) -> ResearchExecutionTrace:
    """One-way adapter. A scripted attempt cannot become an empty live claim."""

    if scripted is not None and (
        scripted.live or scripted.steps or scripted.attempted_sources or scripted.succeeded_sources
    ):
        raise ValueError(
            "A scripted execution trace is not production evidence and cannot "
            "disagree with the empty authoritative trace."
        )
    return empty_execution_trace(plan_id)


def prepare_confirmed_research(
    authorization: ResearchAuthorization,
    *,
    owner: ConversationOwner,
    conversation_id: str,
    decision_id: str,
    canonical_context_version: int,
    proposal: ResearchProposal | None = None,
    selected_market: SelectedShoppingMarket | None = None,
    ledger: AuthorizedExecutionLedger | None = None,
    caller_market: str | None = None,
    caller_capability: str | None = None,
    caller_source: str | None = None,
    caller_provider_id: str | None = None,
) -> ResearchExecutionPreparation:
    """Plan from the trusted authorization, then prepare or refuse execution.

    Browser market, capability, source, and provider arguments are override
    attempts. They are never the planning input.
    """

    market = selected_market if selected_market is not None else intended_default_shopping_market()
    trusted = TrustedMarketContext(country_code=market.country_code)
    planned = plan_authorized_research(
        authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        registry=production_research_provider_registry(),
        catalog=production_research_provider_certification_catalog(),
        routing_policy=production_research_provider_routing_policy_catalog(),
        trusted_market=trusted,
        proposal=proposal,
    )
    if not planned.planned or planned.plan is None:
        return _refusal(
            outcome="blocked_authorization",
            reason=planned.reason,
            decision_id=decision_id,
            authorization_status=authorization.status,
        )
    return execute_research_plan(
        planned.plan,
        authorization=authorization,
        owner=owner,
        conversation_id=conversation_id,
        decision_id=decision_id,
        canonical_context_version=canonical_context_version,
        proposal=proposal,
        ledger=ledger,
        caller_market=caller_market,
        caller_capability=caller_capability,
        caller_source=caller_source,
        caller_provider_id=caller_provider_id,
    )


def execute_research_plan(
    plan: ResearchExecutionPlan | None,
    *,
    authorization: ResearchAuthorization | None = None,
    owner: ConversationOwner | None = None,
    conversation_id: str | None = None,
    decision_id: str | None = None,
    canonical_context_version: int | None = None,
    proposal: ResearchProposal | None = None,
    expected_scope_digest: str | None = None,
    expected_proposal_id: str | None = None,
    expected_proposal_version: int | None = None,
    ledger: AuthorizedExecutionLedger | None = None,
    caller_market: str | None = None,
    caller_capability: str | None = None,
    caller_source: str | None = None,
    caller_provider_id: str | None = None,
    registry: ResearchProviderRegistry | None = None,
    catalog: ResearchProviderCertificationCatalog | None = None,
    routing_policy: ResearchProviderRoutingPolicyCatalog | None = None,
) -> ResearchExecutionPreparation:
    """Prepare or refuse a validated plan. Does not perform network I/O."""

    if plan is None:
        raise ValueError("A research execution plan is required")
    if LIVE_RESEARCH_EXECUTION_OPERATIONAL:
        raise RuntimeError("live research execution is not operational in this slice")

    decision = decision_id or plan.decision_id
    if authorization is None or owner is None:
        return _refusal(
            outcome="blocked_authorization",
            reason="not_found",
            decision_id=decision,
            plan_id=plan.plan_id,
        )

    validation = validate_research_authorization_for_execution(
        authorization,
        owner=owner,
        conversation_id=conversation_id or plan.conversation_id,
        decision_id=decision,
        canonical_context_version=(
            canonical_context_version
            if canonical_context_version is not None
            else plan.canonical_context_version
        ),
        proposal=proposal,
        expected_scope_digest=expected_scope_digest,
        expected_proposal_id=expected_proposal_id,
        expected_proposal_version=expected_proposal_version,
    )
    if not validation.valid or validation.authorization is None:
        return _refusal(
            outcome="blocked_authorization",
            reason=validation.reason,
            decision_id=decision,
            plan_id=plan.plan_id,
            authorization_status=authorization.status,
        )
    if not _plan_matches_authorization(plan, validation.authorization):
        return _refusal(
            outcome="blocked_authorization",
            reason="plan_authorization_mismatch",
            decision_id=decision,
            plan_id=plan.plan_id,
            authorization_status=authorization.status,
        )

    override = _caller_override_reason(
        plan,
        caller_market=caller_market,
        caller_capability=caller_capability,
        caller_source=caller_source,
        caller_provider_id=caller_provider_id,
    )
    if override is not None:
        return _refusal(
            outcome="caller_target_rejected",
            reason=override,
            decision_id=decision,
            plan_id=plan.plan_id,
            authorization_status=authorization.status,
        )

    store = ledger if ledger is not None else production_authorized_execution_ledger()
    try:
        binding = store.bind(
            authorization_idempotency_key=authorization.idempotency_key,
            decision_id=authorization.decision_id,
            plan_id=plan.plan_id,
        )
    except AuthorizationPlanConflict:
        return _refusal(
            outcome="blocked_authorization",
            reason="authorization_plan_conflict",
            decision_id=authorization.decision_id,
            authorization_status=authorization.status,
        )
    outcome, reasons, targets = _assess_plan(
        plan,
        registry=registry or production_research_provider_registry(),
        catalog=catalog or production_research_provider_certification_catalog(),
        routing=routing_policy or production_research_provider_routing_policy_catalog(),
    )
    _refuse_shopify_if_planned(plan)
    trace = project_to_authoritative_trace(plan.plan_id)
    return ResearchExecutionPreparation(
        outcome=outcome,
        reason=reasons[0] if reasons else outcome,
        decision_id=authorization.decision_id,
        execution_id=binding.execution_id,
        authorization_status=authorization.status,
        plan_id=binding.plan_id,
        trace=trace,
        blocking_reasons=reasons,
        assessed_targets=targets,
        prior_decision_id=authorization.decision_id,
    )


def _refuse_shopify_if_planned(plan: ResearchExecutionPlan) -> None:
    planned_shopify = any(
        step.provider_id == SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID for step in plan.eligible_steps
    )
    if not planned_shopify:
        return
    refusal = refuse_shopify_execution()
    if refusal.called_shopify or refusal.http_invoked or refusal.execute_invoked:
        raise RuntimeError("Shopify preparation must not perform a live call")


def _assess_plan(
    plan: ResearchExecutionPlan,
    *,
    registry: ResearchProviderRegistry,
    catalog: ResearchProviderCertificationCatalog,
    routing: ResearchProviderRoutingPolicyCatalog,
) -> tuple[PreparationOutcome, tuple[str, ...], tuple[tuple[str, str, str], ...]]:
    if not plan.eligible_steps:
        outcome, reasons = _blocked_plan_outcome(plan)
        return outcome, reasons, ()

    reasons: list[str] = []
    targets: list[tuple[str, str, str]] = []
    for step in plan.eligible_steps:
        if not step.market or not step.source_identities:
            reasons.append("plan_step_target_incomplete")
            continue
        for source in step.source_identities:
            target = LiveResearchTarget(
                market=step.market,
                capability=step.capability,
                source=source,
            )
            targets.append((target.market, target.capability.value, target.source))
            assessment = assess_live_research_mode(
                mode=SHOPPING_RESEARCH_EXECUTION_MODE,
                requested=target,
                registry=registry,
                certifications=catalog,
                routing=routing,
                certified_markets=production_certified_shopping_markets(),
                trace_handling_present=True,
            )
            reasons.extend(assessment.reasons)
            if assessment.enabled:
                reasons.append("live_execution_not_operational")
    unique = tuple(dict.fromkeys(reasons))
    if SHOPPING_RESEARCH_EXECUTION_MODE != "live" and "mode_not_live" not in unique:
        unique = ("mode_not_live", *unique)
    return "prepared_but_live_unavailable", unique, tuple(targets)


def _blocked_plan_outcome(
    plan: ResearchExecutionPlan,
) -> tuple[PreparationOutcome, tuple[str, ...]]:
    reasons = tuple(dict.fromkeys(item.reason for item in plan.blocked_requirements))
    destination_blocked = any(
        item.capability in DESTINATION_SENSITIVE_CAPABILITIES
        and item.reason == "destination_support_not_ready"
        for item in plan.blocked_requirements
    )
    if destination_blocked:
        return "blocked_capability", reasons or ("destination_support_not_ready",)
    if plan.support_status == "blocked_market_context" or "missing_market_context" in reasons:
        return "blocked_market", reasons or ("missing_market_context",)
    return "blocked_provider", reasons or ("blocked_missing_certified_provider",)


def _caller_override_reason(
    plan: ResearchExecutionPlan,
    *,
    caller_market: str | None,
    caller_capability: str | None,
    caller_source: str | None,
    caller_provider_id: str | None,
) -> str | None:
    if caller_market is not None:
        expected = plan.market.country_code if plan.market else None
        step_markets = {step.market for step in plan.eligible_steps if step.market}
        if caller_market != expected or (step_markets and caller_market not in step_markets):
            return "caller_market_rejected"
    if caller_capability is not None:
        allowed = {step.capability.value for step in plan.eligible_steps}
        allowed.update(item.value for item in plan.required_capabilities)
        if caller_capability not in allowed:
            return "caller_capability_rejected"
    if caller_source is not None:
        allowed_sources = set(plan.requested_sources)
        for step in plan.eligible_steps:
            allowed_sources.update(step.source_identities)
        if caller_source not in allowed_sources:
            return "caller_source_rejected"
    if caller_provider_id is not None:
        allowed_providers = {step.provider_id for step in plan.eligible_steps}
        if caller_provider_id not in allowed_providers:
            return "caller_provider_rejected"
    return None


def _plan_matches_authorization(
    plan: ResearchExecutionPlan,
    authorization: ResearchAuthorization,
) -> bool:
    return (
        plan.authorization_id == authorization.authorization_id
        and plan.authorization_version == authorization.authorization_version
        and plan.decision_id == authorization.decision_id
        and plan.canonical_context_version == authorization.canonical_context_version
        and plan.conversation_id == authorization.conversation_id
        and plan.proposal_id == authorization.proposal_id
        and plan.proposal_version == authorization.proposal_version
        and plan.scope_digest == authorization.scope_digest
    )


def _refusal(
    *,
    outcome: PreparationOutcome,
    reason: str,
    decision_id: str,
    plan_id: str | None = None,
    authorization_status: str | None = None,
    blocking_reasons: tuple[str, ...] = (),
) -> ResearchExecutionPreparation:
    trace = project_to_authoritative_trace(plan_id or "unplanned")
    return ResearchExecutionPreparation(
        outcome=outcome,
        reason=reason,
        decision_id=decision_id,
        execution_id=None,
        authorization_status=authorization_status,
        plan_id=plan_id,
        trace=trace,
        blocking_reasons=blocking_reasons or ((reason,) if reason else ()),
        prior_decision_id=decision_id,
    )
