"""Positive confirmed-research composition.

ProposeResearchService still owns need detection, the proposal, confirmation,
the ResearchAuthorization, and trusted preparation. This service continues a
prepared authorization only when the injected runtime policy says every gate
is open. It does not perform HTTP itself. The live-start claim service owns
certification, routing, market, mode, provider status, kill switch, breaker,
claim, and authorization consumption. The Shopify adapter owns transport.

Current production policy is closed. A shopper confirmation therefore stops
before a claim, before the adapter, and before transport. Provider status and
the kill switch come from the server registry descriptor. An injected open
policy can traverse the claim and a fake transport. The production-shaped
harness permit stays a fixture. Fake transport output cannot become
shopper-visible canonical live evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from app.domain.entities.connector_reliability import ConnectorOperationalStatus, KillSwitch
from app.domain.entities.research_authorization import ResearchAuthorization
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchExecutionPlan,
    ResearchProviderStep,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.infrastructure.persistence.errors import PersistenceError
from app.market.support import CertifiedShoppingMarketCatalog, production_certified_shopping_markets
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
)
from app.research.execution_evidence import (
    InMemoryResearchExecutionEvidenceRepository,
    NormalizedOfferFact,
    OperationalResearchExecutionEvidenceRepository,
    attach_execution_evidence_references,
    evidence_from_adapter_fact,
    evidence_from_verified_live_offer_fact,
)
from app.research.live_start_claim import LiveStartClaimRequest, LiveStartClaimService
from app.research.providers import StaticResearchProvider
from app.research.registry import ResearchProviderRegistry, production_research_provider_registry
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    production_research_provider_routing_policy_catalog,
)
from app.research.shopify_global_catalog_capability_policy import SHOPIFY_GLOBAL_CATALOG_MARKET
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
)
from app.research.shopify_global_catalog_execution import (
    BoundedFakeTransportPermit,
    CatalogTransportPermit,
    ProductionShapeHarnessPermit,
    ProductionShopifyTransportPermit,
    ShopifyCatalogAttempt,
    ShopifyCatalogExecutionService,
    ShopifyExecutionResult,
    issue_production_shopify_transport_permit,
    production_shopify_execution_block_reasons,
)
from app.research.shopify_global_catalog_ph_probe import PH_COUNTRY, SEARCH_TOOL
from app.research.shopify_global_catalog_provider import (
    SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
)
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    LiveResearchTarget,
    assess_live_research_mode,
)
from app.services.canonical_research_results import CanonicalResearchResultsService
from app.services.research_execution import ResearchExecutionPreparation
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

_SERVER_CATALOG_QUERY = "piq-savi-authorized-catalog-search"
_SUPPORTED = frozenset(SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES)


class ResearchRuntimePolicy(Protocol):
    """Server-owned gate inputs. A browser request cannot supply these."""

    def block_reasons(self) -> tuple[str, ...]: ...

    @property
    def mode(self) -> str: ...

    @property
    def operational_status(self) -> ConnectorOperationalStatus: ...

    @property
    def kill_switch(self) -> KillSwitch: ...

    @property
    def registry(self) -> ResearchProviderRegistry: ...

    @property
    def certifications(self) -> ResearchProviderCertificationCatalog: ...

    @property
    def routing(self) -> ResearchProviderRoutingPolicyCatalog: ...

    @property
    def certified_markets(self) -> CertifiedShoppingMarketCatalog: ...


@dataclass(frozen=True, slots=True)
class InjectedResearchRuntimePolicy:
    """Test or harness policy. It does not mutate production constants."""

    mode: str
    operational_status: ConnectorOperationalStatus
    kill_switch: KillSwitch
    registry: ResearchProviderRegistry
    certifications: ResearchProviderCertificationCatalog
    routing: ResearchProviderRoutingPolicyCatalog
    certified_markets: CertifiedShoppingMarketCatalog
    reasons: tuple[str, ...] = ()

    def block_reasons(self) -> tuple[str, ...]:
        return self.reasons


class ProductionResearchRuntimePolicy:
    """Server registry gates. Status and the kill switch are not browser input.

    Defaults read the production catalogs. A harness may supply server-owned
    catalogs without changing production constants. Operational status and the
    kill switch always come from ``ph-shopify-global-catalog``. A missing
    provider fails closed. The claim service remains the kill-switch authority.
    """

    def __init__(
        self,
        *,
        registry: ResearchProviderRegistry | None = None,
        certifications: ResearchProviderCertificationCatalog | None = None,
        routing: ResearchProviderRoutingPolicyCatalog | None = None,
        certified_markets: CertifiedShoppingMarketCatalog | None = None,
        mode: str | None = None,
        live_call_permitted: bool | None = None,
        profile_deployed: bool | None = None,
    ) -> None:
        self._registry = registry
        self._certifications = certifications
        self._routing = routing
        self._certified_markets = certified_markets
        self._mode = mode
        self._live_call_permitted = live_call_permitted
        self._profile_deployed = profile_deployed

    def block_reasons(self) -> tuple[str, ...]:
        if not self._uses_injected_catalogs():
            return production_shopify_execution_block_reasons()
        return self._catalog_block_reasons()

    @property
    def mode(self) -> str:
        if self._mode is None:
            return SHOPPING_RESEARCH_EXECUTION_MODE
        return self._mode

    @property
    def operational_status(self) -> ConnectorOperationalStatus:
        provider = self._shopify_provider()
        if provider is None:
            return ConnectorOperationalStatus.DISABLED
        return provider.descriptor.operational_status

    @property
    def kill_switch(self) -> KillSwitch:
        provider = self._shopify_provider()
        if provider is None:
            return KillSwitch(engaged=True, reason="provider_missing")
        return provider.descriptor.kill_switch

    @property
    def registry(self) -> ResearchProviderRegistry:
        if self._registry is None:
            return production_research_provider_registry()
        return self._registry

    @property
    def certifications(self) -> ResearchProviderCertificationCatalog:
        if self._certifications is None:
            return production_research_provider_certification_catalog()
        return self._certifications

    @property
    def routing(self) -> ResearchProviderRoutingPolicyCatalog:
        if self._routing is None:
            return production_research_provider_routing_policy_catalog()
        return self._routing

    @property
    def certified_markets(self) -> CertifiedShoppingMarketCatalog:
        if self._certified_markets is None:
            return production_certified_shopping_markets()
        return self._certified_markets

    def _uses_injected_catalogs(self) -> bool:
        return any(
            value is not None
            for value in (
                self._registry,
                self._certifications,
                self._routing,
                self._certified_markets,
                self._mode,
                self._live_call_permitted,
                self._profile_deployed,
            )
        )

    def _shopify_provider(self) -> StaticResearchProvider | None:
        return self.registry.get(SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID)

    def _call_permitted(self) -> bool:
        if self._live_call_permitted is None:
            return SHOPIFY_LIVE_CALL_PERMITTED
        return self._live_call_permitted

    def _profile_is_deployed(self) -> bool:
        if self._profile_deployed is None:
            return PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED
        return self._profile_deployed

    def _catalog_block_reasons(self) -> tuple[str, ...]:
        """Same gates as production, read from this policy's server catalogs.

        Kill-switch engagement is left to the live-start claim. Folding it
        into these reasons would skip the claim that already owns that check.
        """

        assessment = assess_live_research_mode(
            mode=self.mode,
            requested=LiveResearchTarget(
                market=SHOPIFY_GLOBAL_CATALOG_MARKET,
                capability=ResearchCapability.CURRENT_PRICING,
                source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
            ),
            registry=self.registry,
            certifications=self.certifications,
            routing=self.routing,
            certified_markets=self.certified_markets,
            trace_handling_present=True,
        )
        reasons = [
            reason
            for reason in assessment.reasons
            if reason != "provider_not_operationally_eligible"
        ]
        if self.operational_status is not ConnectorOperationalStatus.AVAILABLE:
            reasons.append("provider_not_operationally_eligible")
        if self.mode != "live" and "mode_not_live" not in reasons:
            reasons.append("mode_not_live")
        if not self._call_permitted():
            reasons.append("shopify_live_call_not_permitted")
        if not self._profile_is_deployed():
            reasons.append("production_ucp_profile_undeployed")
        return tuple(dict.fromkeys(reasons))


class ClosedProductionClaims:
    """Backstop. Production composition returns before this is called."""

    def claim(self, request: LiveStartClaimRequest) -> None:
        del request
        raise RuntimeError("production composition must not claim while a gate is closed")


@dataclass(frozen=True, slots=True)
class ConfirmedResearchRequest:
    """Server-owned continuation. Caller target fields are override attempts."""

    owner: ConversationOwner
    conversation_id: str
    authorization: ResearchAuthorization
    preparation: ResearchExecutionPreparation
    caller_market: str | None = None
    caller_capability: str | None = None
    caller_source: str | None = None
    caller_provider_id: str | None = None
    caller_execution_id: str | None = None
    caller_catalog_query: str | None = None


@dataclass(frozen=True, slots=True)
class ConfirmedResearchResult:
    """Shopper-visible live completion is separate from a synthetic traversal."""

    claim_invoked: bool
    adapter_invoked: bool
    transport_invoked: bool
    authorization_consumed: bool
    source_checked: bool
    attempted: bool
    research_executed: bool
    live_research_completed: bool
    shopper_results_updated: bool
    synthetic: bool
    test_fixture: bool
    prior_decision_preserved: bool
    block_reason: str | None = None
    blocking_reasons: tuple[str, ...] = ()
    execution_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    context_version: int | None = None
    integration_outcome: str | None = None
    ignored_caller_overrides: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.live_research_completed and (self.synthetic or self.test_fixture):
            raise ValueError("synthetic execution cannot complete live research")
        if self.shopper_results_updated and not self.live_research_completed:
            raise ValueError("shopper Results update requires completed live research")
        if self.shopper_results_updated and (self.synthetic or self.test_fixture):
            raise ValueError("synthetic evidence cannot update shopper-visible Results")
        if self.live_research_completed and not self.research_executed:
            raise ValueError("completed live research is an execution")
        if self.synthetic and not self.test_fixture:
            raise ValueError("synthetic execution evidence must stay a test fixture")
        if not self.shopper_results_updated and self.context_version is not None:
            raise ValueError("a preserved decision does not publish a new context version")

    def to_public_dict(self) -> dict[str, object]:
        """No claim capability, probe capability, or raw transport body."""

        return {
            "claim_invoked": self.claim_invoked,
            "adapter_invoked": self.adapter_invoked,
            "transport_invoked": self.transport_invoked,
            "authorization_consumed": self.authorization_consumed,
            "source_checked": self.source_checked,
            "attempted": self.attempted,
            "research_executed": self.research_executed,
            "shopper_results_updated": self.shopper_results_updated,
            "synthetic": self.synthetic,
            "test_fixture": self.test_fixture,
            "prior_decision_preserved": self.prior_decision_preserved,
            "block_reason": self.block_reason,
            "live_research_completed": self.live_research_completed,
            "execution_id": self.execution_id,
            "evidence_ids": list(self.evidence_ids),
            "context_version": self.context_version,
            "integration_outcome": self.integration_outcome,
        }


class ConfirmedResearchExecutionService:
    """Claim and adapter orchestration after trusted preparation."""

    def __init__(
        self,
        policy: ResearchRuntimePolicy,
        *,
        claims: LiveStartClaimService | ClosedProductionClaims | None = None,
        adapter: ShopifyCatalogExecutionService | None = None,
        evidence: InMemoryResearchExecutionEvidenceRepository
        | OperationalResearchExecutionEvidenceRepository
        | None = None,
        executions: object | None = None,
        integrator: CanonicalResearchResultsService | None = None,
        clock: Callable[[], datetime] | None = None,
        production_composition: bool = False,
        harness_composition: bool = False,
    ) -> None:
        if production_composition and harness_composition:
            raise ValueError("production composition cannot use the harness permit")
        self._policy = policy
        self._claims = claims
        self._adapter = adapter
        self._evidence = evidence
        self._executions = executions
        self._integrator = integrator
        self._clock = clock or (lambda: datetime.now(UTC))
        self._production_composition = production_composition
        self._harness_composition = harness_composition

    @property
    def claims(self) -> LiveStartClaimService | ClosedProductionClaims | None:
        return self._claims

    @property
    def adapter(self) -> ShopifyCatalogExecutionService | None:
        return self._adapter

    @property
    def evidence(
        self,
    ) -> (
        InMemoryResearchExecutionEvidenceRepository
        | OperationalResearchExecutionEvidenceRepository
        | None
    ):
        return self._evidence

    @property
    def executions(self) -> object | None:
        return self._executions

    @property
    def integrator(self) -> CanonicalResearchResultsService | None:
        return self._integrator

    @property
    def production_composition(self) -> bool:
        return self._production_composition

    def _issue_permit(self) -> CatalogTransportPermit:
        """Issue a permit only after the runtime policy reports every gate open."""

        reasons = self._policy.block_reasons()
        if reasons:
            raise RuntimeError("a transport permit cannot be issued while a gate is closed")
        if self._production_composition:
            return issue_production_shopify_transport_permit(
                authoritative_block_reasons=reasons,
            )
        if self._harness_composition:
            return ProductionShapeHarnessPermit()
        return BoundedFakeTransportPermit()

    def continue_confirmed(self, request: ConfirmedResearchRequest) -> ConfirmedResearchResult:
        """Stop before a claim while any production gate is closed."""

        ignored = _ignored_overrides(request)
        preparation = request.preparation
        if preparation.outcome != "prepared_but_live_unavailable" or not preparation.execution_id:
            return _stopped(ignored, block_reason=preparation.reason or preparation.outcome)
        if not request.authorization.is_pending_execution:
            return _stopped(ignored, block_reason="authorization_not_pending")
        reasons = self._policy.block_reasons()
        if reasons:
            return _stopped(
                ignored,
                block_reason=reasons[0],
                blocking_reasons=reasons,
                execution_id=preparation.execution_id,
            )
        if self._claims is None or self._adapter is None:
            return _stopped(
                ignored,
                block_reason="production_composition_context_required",
                execution_id=preparation.execution_id,
            )
        plan = preparation.trusted_plan
        if plan is None or not _plan_matches(plan, request):
            return _stopped(
                ignored,
                block_reason="trusted_plan_required",
                execution_id=preparation.execution_id,
            )
        step = _server_step(plan)
        if step is None or not step.market or not step.source_identities:
            return _stopped(
                ignored,
                block_reason="plan_target_mismatch",
                execution_id=preparation.execution_id,
            )
        source = step.source_identities[0]
        now = self._clock()
        claim = self._claims.claim(
            LiveStartClaimRequest(
                authorization=request.authorization,
                owner=request.owner,
                plan=plan,
                provider_id=step.provider_id,
                market=step.market,
                capability=step.capability,
                source=source,
                now=now,
                operational_status=self._policy.operational_status,
                kill_switch=self._policy.kill_switch,
                registry=self._policy.registry,
                certifications=self._policy.certifications,
                routing=self._policy.routing,
                certified_markets=self._policy.certified_markets,
                mode=self._policy.mode,
            )
        )
        if not claim.claimed or not claim.claim_capability:
            return ConfirmedResearchResult(
                claim_invoked=True,
                adapter_invoked=False,
                transport_invoked=False,
                authorization_consumed=claim.authorization_consumed,
                source_checked=False,
                attempted=False,
                research_executed=False,
                live_research_completed=False,
                shopper_results_updated=False,
                synthetic=False,
                test_fixture=False,
                prior_decision_preserved=True,
                block_reason=claim.block_reason,
                execution_id=preparation.execution_id,
                ignored_caller_overrides=ignored,
            )
        permit = self._issue_permit()
        attempt = ShopifyCatalogAttempt(
            permit=permit,
            authorization=request.authorization,
            owner=request.owner,
            plan=plan,
            step=step,
            source=source,
            operation=SEARCH_TOOL,
            claim_capability=claim.claim_capability,
            harness_operational_status=self._policy.operational_status,
            catalog_query=_SERVER_CATALOG_QUERY,
            probe_capability=claim.probe_capability,
            kill_switch=self._policy.kill_switch,
        )
        if request.caller_catalog_query and request.caller_catalog_query != _SERVER_CATALOG_QUERY:
            ignored = (*ignored, "caller_catalog_query")
        executed = self._adapter.execute(attempt)
        production = isinstance(permit, ProductionShopifyTransportPermit)
        if not executed.durable_success:
            return _after_unsuccessful_attempt(
                executed,
                production=production,
                execution_id=preparation.execution_id,
                ignored=ignored,
            )
        if production:
            return self._record_production_evidence(
                request,
                executed,
                ignored=ignored,
            )
        return self._record_synthetic_evidence(
            request,
            executed.offer_facts,
            ignored=ignored,
            transport_invoked=executed.transport_invoked,
        )

    def _record_synthetic_evidence(
        self,
        request: ConfirmedResearchRequest,
        facts: tuple[NormalizedOfferFact, ...],
        *,
        ignored: tuple[str, ...],
        transport_invoked: bool,
    ) -> ConfirmedResearchResult:
        execution_id = request.preparation.execution_id or ""
        plan_id = request.preparation.plan_id or ""
        if self._evidence is None:
            return ConfirmedResearchResult(
                claim_invoked=True,
                adapter_invoked=True,
                transport_invoked=transport_invoked,
                authorization_consumed=True,
                source_checked=False,
                attempted=False,
                research_executed=False,
                live_research_completed=False,
                shopper_results_updated=False,
                synthetic=True,
                test_fixture=True,
                prior_decision_preserved=True,
                block_reason="evidence_repository_required",
                execution_id=execution_id,
                ignored_caller_overrides=ignored,
            )
        try:
            saved = tuple(
                self._evidence.save(
                    evidence_from_adapter_fact(
                        fact,
                        execution_id=execution_id,
                        decision_id=request.authorization.decision_id,
                        plan_id=plan_id,
                        created_at=self._clock(),
                    )
                )
                for fact in facts
            )
        except PersistenceError:
            return ConfirmedResearchResult(
                claim_invoked=True,
                adapter_invoked=True,
                transport_invoked=transport_invoked,
                authorization_consumed=True,
                source_checked=False,
                attempted=False,
                research_executed=False,
                live_research_completed=False,
                shopper_results_updated=False,
                synthetic=True,
                test_fixture=True,
                prior_decision_preserved=True,
                block_reason="evidence_persistence_failed",
                execution_id=execution_id,
                ignored_caller_overrides=ignored,
            )
        evidence_ids = tuple(record.evidence_id for record in saved)
        if self._executions is not None and evidence_ids:
            attach_execution_evidence_references(
                self._executions,  # type: ignore[arg-type]
                self._evidence,
                execution_id,
                evidence_ids,
            )
        production_records = saved and all(not record.test_fixture for record in saved)
        if production_records and self._integrator is not None:
            raise RuntimeError("adapter evidence cannot take the production canonical path")
        return ConfirmedResearchResult(
            claim_invoked=True,
            adapter_invoked=True,
            transport_invoked=transport_invoked,
            authorization_consumed=True,
            source_checked=False,
            attempted=False,
            research_executed=False,
            live_research_completed=False,
            shopper_results_updated=False,
            synthetic=True,
            test_fixture=True,
            prior_decision_preserved=True,
            execution_id=execution_id,
            evidence_ids=evidence_ids,
            ignored_caller_overrides=ignored,
            integration_outcome="synthetic_evidence_only",
        )

    def _record_production_evidence(
        self,
        request: ConfirmedResearchRequest,
        executed: ShopifyExecutionResult,
        *,
        ignored: tuple[str, ...],
    ) -> ConfirmedResearchResult:
        execution_id = request.preparation.execution_id or ""
        verification = executed.verified_live_execution
        if (
            executed.execution_authority != "production"
            or verification is None
            or self._evidence is None
            or self._integrator is None
            or self._executions is None
        ):
            return ConfirmedResearchResult(
                claim_invoked=True,
                adapter_invoked=True,
                transport_invoked=executed.transport_invoked,
                authorization_consumed=True,
                source_checked=True,
                attempted=True,
                research_executed=True,
                live_research_completed=True,
                shopper_results_updated=False,
                synthetic=False,
                test_fixture=False,
                prior_decision_preserved=True,
                block_reason="production_evidence_unverified",
                execution_id=execution_id,
                ignored_caller_overrides=ignored,
            )
        try:
            saved = tuple(
                self._evidence.save(
                    evidence_from_verified_live_offer_fact(
                        verification,
                        fact,
                        created_at=self._clock(),
                    )
                )
                for fact in verification.facts
            )
        except PersistenceError:
            return ConfirmedResearchResult(
                claim_invoked=True,
                adapter_invoked=True,
                transport_invoked=executed.transport_invoked,
                authorization_consumed=True,
                source_checked=True,
                attempted=True,
                research_executed=True,
                live_research_completed=True,
                shopper_results_updated=False,
                synthetic=False,
                test_fixture=False,
                prior_decision_preserved=True,
                block_reason="evidence_persistence_failed",
                execution_id=execution_id,
                ignored_caller_overrides=ignored,
            )
        evidence_ids = tuple(record.evidence_id for record in saved)
        if evidence_ids:
            attach_execution_evidence_references(
                self._executions,  # type: ignore[arg-type]
                self._evidence,
                execution_id,
                evidence_ids,
            )
        integrated = self._integrator.integrate(
            execution_id=execution_id,
            owner=request.owner,
            conversation_id=request.conversation_id,
            decision_id=request.authorization.decision_id,
        )
        updated = integrated.shopper_results_updated
        return ConfirmedResearchResult(
            claim_invoked=True,
            adapter_invoked=True,
            transport_invoked=executed.transport_invoked,
            authorization_consumed=True,
            source_checked=True,
            attempted=True,
            research_executed=True,
            live_research_completed=True,
            shopper_results_updated=updated,
            synthetic=False,
            test_fixture=False,
            prior_decision_preserved=not updated,
            execution_id=execution_id,
            evidence_ids=evidence_ids,
            context_version=integrated.context_version if updated else None,
            ignored_caller_overrides=ignored,
            integration_outcome=integrated.outcome,
        )


def production_confirmed_research_execution(
    *,
    snapshots: object | None = None,
    conversations: object | None = None,
) -> ConfirmedResearchExecutionService:
    """Shopper default. Durable continuation stays blocked by closed gates.

    The graph contains the live-start claim service, the Shopify adapter, the
    production transport object, durable execution and evidence repositories,
    and the canonical integrator. Current gates return before a permit, a
    claim, the adapter, and transport I/O. ``ClosedProductionClaims`` is not
    this factory's authority.
    """

    import secrets

    from sqlalchemy.orm import sessionmaker

    from app.infrastructure.database.repositories.shopping_conversation_repository import (
        SqlAlchemyConversationRepository,
    )
    from app.infrastructure.database.repositories.shopping_decision_snapshot_repository import (
        SqlAlchemyDecisionSnapshotRepository,
    )
    from app.infrastructure.persistence.session import get_sync_session_factory
    from app.research.authorized_execution_repository import (
        OperationalAuthorizedExecutionRepository,
    )
    from app.research.live_start_claim import operational_live_start_claims
    from app.research.shopify_global_catalog_execution import operational_shopify_execution
    from app.research.shopify_global_catalog_transport import (
        UrllibJsonTransport,
        issue_production_transport_authority,
    )
    from app.services.canonical_research_results import OperationalResultsIntegrationRepository

    factory = get_sync_session_factory()
    if not isinstance(factory, sessionmaker):
        raise TypeError("production composition requires the sync session factory")
    executions = OperationalAuthorizedExecutionRepository(session_factory=factory)
    evidence = OperationalResearchExecutionEvidenceRepository(session_factory=factory)
    integrations = OperationalResultsIntegrationRepository(session_factory=factory)
    snapshot_repo = snapshots or SqlAlchemyDecisionSnapshotRepository(session_factory=factory)
    conversation_repo = conversations or SqlAlchemyConversationRepository(session_factory=factory)
    integrator = CanonicalResearchResultsService(
        executions,
        evidence,
        snapshot_repo,  # type: ignore[arg-type]
        conversation_repo,  # type: ignore[arg-type]
        integrations,
    )
    claims = operational_live_start_claims(
        factory,
        token_factory=lambda: secrets.token_urlsafe(32),
    )
    adapter = operational_shopify_execution(
        factory,
        UrllibJsonTransport(authority=issue_production_transport_authority()),
    )
    return ConfirmedResearchExecutionService(
        ProductionResearchRuntimePolicy(),
        claims=claims,
        adapter=adapter,
        evidence=evidence,
        executions=executions,
        integrator=integrator,
        production_composition=True,
    )


def _after_unsuccessful_attempt(
    executed: ShopifyExecutionResult,
    *,
    production: bool,
    execution_id: str | None,
    ignored: tuple[str, ...],
) -> ConfirmedResearchResult:
    timed_out = executed.outcome == "timed_out" or executed.error_category == "timeout"
    if not production:
        return ConfirmedResearchResult(
            claim_invoked=True,
            adapter_invoked=True,
            transport_invoked=executed.transport_invoked,
            authorization_consumed=True,
            source_checked=False,
            attempted=False,
            research_executed=False,
            live_research_completed=False,
            shopper_results_updated=False,
            synthetic=executed.transport_invoked,
            test_fixture=executed.transport_invoked,
            prior_decision_preserved=True,
            block_reason=executed.block_reason or executed.outcome,
            execution_id=execution_id,
            ignored_caller_overrides=ignored,
            integration_outcome=executed.outcome,
        )
    reached = executed.transport_invoked or executed.attempted
    return ConfirmedResearchResult(
        claim_invoked=True,
        adapter_invoked=True,
        transport_invoked=executed.transport_invoked,
        authorization_consumed=True,
        source_checked=reached and not timed_out and not executed.transport_outcome_ambiguous,
        attempted=reached,
        research_executed=reached or executed.persisted,
        live_research_completed=False,
        shopper_results_updated=False,
        synthetic=False,
        test_fixture=False,
        prior_decision_preserved=True,
        block_reason=executed.block_reason or executed.outcome,
        execution_id=execution_id,
        ignored_caller_overrides=ignored,
        integration_outcome=executed.outcome,
    )


def _stopped(
    ignored: tuple[str, ...],
    *,
    block_reason: str,
    blocking_reasons: tuple[str, ...] = (),
    execution_id: str | None = None,
) -> ConfirmedResearchResult:
    return ConfirmedResearchResult(
        claim_invoked=False,
        adapter_invoked=False,
        transport_invoked=False,
        authorization_consumed=False,
        source_checked=False,
        attempted=False,
        research_executed=False,
        live_research_completed=False,
        shopper_results_updated=False,
        synthetic=False,
        test_fixture=False,
        prior_decision_preserved=True,
        block_reason=block_reason,
        blocking_reasons=blocking_reasons or (block_reason,),
        execution_id=execution_id,
        ignored_caller_overrides=ignored,
    )


def _ignored_overrides(request: ConfirmedResearchRequest) -> tuple[str, ...]:
    names = (
        ("caller_market", request.caller_market),
        ("caller_capability", request.caller_capability),
        ("caller_source", request.caller_source),
        ("caller_provider_id", request.caller_provider_id),
        ("caller_execution_id", request.caller_execution_id),
        ("caller_catalog_query", request.caller_catalog_query),
    )
    return tuple(name for name, value in names if value)


def _plan_matches(plan: ResearchExecutionPlan, request: ConfirmedResearchRequest) -> bool:
    authorization = request.authorization
    return (
        plan.authorization_id == authorization.authorization_id
        and plan.decision_id == authorization.decision_id
        and plan.conversation_id == request.conversation_id
        and plan.plan_id == request.preparation.plan_id
    )


def _server_step(plan: ResearchExecutionPlan) -> ResearchProviderStep | None:
    matches = [
        step
        for step in plan.eligible_steps
        if step.provider_id == SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
        and step.capability in _SUPPORTED
        and step.market == PH_COUNTRY
    ]
    pricing = [step for step in matches if step.capability is ResearchCapability.CURRENT_PRICING]
    if pricing:
        return pricing[0]
    if matches:
        return matches[0]
    return None
