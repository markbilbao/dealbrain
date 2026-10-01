"""Sprint 38 B1 confirmed-research composition. Fake transport only."""

from __future__ import annotations

import json
import socket
import urllib.request
from dataclasses import replace
from datetime import datetime

import pytest
from app.domain.entities.connector_reliability import ConnectorOperationalStatus, KillSwitch
from app.domain.entities.marketplace_data import SourceMode
from app.domain.entities.research_execution import ResearchCapability
from app.infrastructure.persistence.errors import PersistenceError
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.market.support import production_certified_shopping_markets
from app.research.authorized_execution_repository import InMemoryAuthorizedExecutionRepository
from app.research.execution_evidence import InMemoryResearchExecutionEvidenceRepository
from app.research.live_start_claim import in_memory_live_start_claims
from app.research.reliability_repository import InMemoryResearchReliabilityRepository
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_execution import (
    REAL_SHOPIFY_CALLS,
    ShopifyExecutionResult,
    execute_production_shopify_catalog,
    in_memory_shopify_execution,
    production_shopify_execution_block_reasons,
)
from app.research.shopify_global_catalog_ph_probe import GLOBAL_CATALOG_ENDPOINT
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
)
from app.services.canonical_research_results import CanonicalResearchResultsService
from app.services.confirmed_research_execution import (
    ConfirmedResearchExecutionService,
    ConfirmedResearchRequest,
    InjectedResearchRuntimePolicy,
)
from app.services.research_execution import prepare_confirmed_research
from app.services.shopping_assistant_service import ShoppingAssistantService
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    DECISION_ID,
    SONY_ID,
    START,
    _owner,
    _presentation,
)
from tests.unit.test_sprint38_shopify_execution_adapter import (
    FakeCatalogTransport,
    _ok,
    _product,
    _token_factory,
    _world,
)

_SERVER_QUERY = "piq-savi-authorized-catalog-search"
_PRICE = "What's the price today?"
_CONFIRM = "Yes, check the current prices."


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("confirmed-research tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(urllib.request, "urlopen", _blocked)


def _clock() -> datetime:
    return START


class _BoomEvidence(InMemoryResearchExecutionEvidenceRepository):
    def save(self, record):  # noqa: ANN001
        raise PersistenceError("evidence persistence failed")


class _RecordingOrchestrator(ConfirmedResearchExecutionService):
    def continue_confirmed(self, request: ConfirmedResearchRequest):
        redirected = replace(
            request,
            caller_market="US",
            caller_capability=ResearchCapability.SHIPPING.value,
            caller_source="amazon",
            caller_provider_id="browser-provider",
            caller_execution_id="browser-execution",
            caller_catalog_query="browser-chosen-query",
        )
        return super().continue_confirmed(redirected)


def _stores():
    snapshots = InMemoryDecisionSnapshotRepository(clock=_clock)
    snapshot = _presentation()
    snapshots.add(snapshot)
    conversations = InMemoryConversationRepository(clock=_clock)
    executions = InMemoryAuthorizedExecutionRepository()
    reliability = InMemoryResearchReliabilityRepository()
    return snapshots, conversations, executions, reliability, snapshot


def _open_policy():
    _provider, registry, catalog, routing, markets = _world()
    return (
        InjectedResearchRuntimePolicy(
            mode="live",
            operational_status=ConnectorOperationalStatus.AVAILABLE,
            kill_switch=KillSwitch(),
            registry=registry,
            certifications=catalog,
            routing=routing,
            certified_markets=markets,
            reasons=(),
        ),
        registry,
        catalog,
        routing,
    )


def _assistant(
    *,
    policy,
    registry,
    catalog,
    routing,
    executions,
    reliability,
    conversations,
    snapshots,
    transport,
    evidence,
    integrator=None,
    orchestrator_type=ConfirmedResearchExecutionService,
    kill_switch: KillSwitch | None = None,
):
    claims, _executions, _reliability = in_memory_live_start_claims(
        executions,
        reliability,
        conversations,
        token_factory=_token_factory(),
    )
    adapter = in_memory_shopify_execution(
        executions,
        reliability,
        conversations,
        transport,
        clock=_clock,
    )
    if kill_switch is not None:
        policy = replace(policy, kill_switch=kill_switch)
    orchestrator = orchestrator_type(
        policy,
        claims=claims,
        adapter=adapter,
        evidence=evidence,
        executions=executions,
        integrator=integrator,
        clock=_clock,
    )
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=_clock,
        execution_ledger=executions,
        confirmed_execution=orchestrator,
        planning_registry=registry,
        planning_catalog=catalog,
        planning_routing=routing,
    )
    return assistant, orchestrator


def _confirm(assistant: ShoppingAssistantService, **extra: object):
    first = assistant.query(
        {"query": _PRICE, "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert first.processing["action"] == "propose_research"
    payload = {
        "query": _CONFIRM,
        "decision_id": DECISION_ID,
        "conversation_id": first.conversation_id,
        "proposal_id": first.processing["proposal_id"],
        "proposal_version": first.processing["proposal_version"],
    }
    payload.update(extra)
    confirmed = assistant.query(payload, owner=_owner())
    return first, confirmed


def test_current_production_confirmation_stops_before_claim() -> None:
    snapshots, conversations, executions, _reliability, snapshot = _stores()
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=_clock,
        execution_ledger=executions,
    )
    _first, confirmed = _confirm(assistant)
    public = confirmed.processing["confirmed_research"]
    assert public["claim_invoked"] is False
    assert public["adapter_invoked"] is False
    assert public["transport_invoked"] is False
    assert public["authorization_consumed"] is False
    assert public["source_checked"] is False
    assert public["attempted"] is False
    assert public["shopper_results_updated"] is False
    assert public["live_research_completed"] is False
    assert confirmed.processing["execution_started"] is False
    assert confirmed.processing["source_checked"] is False
    assert confirmed.processing["attempted"] is False
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert "not available" in confirmed.answer.lower()
    assert "Research completed" not in confirmed.answer
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded == snapshot
    assert snapshots.get(DECISION_ID, 2) is None
    stored = next(iter(executions._rows.values()))  # noqa: SLF001
    assert stored.state == "prepared_unavailable"
    assert stored.claimed_at is None
    context = conversations.get(confirmed.conversation_id)
    assert context is not None
    assert context.research_authorization is not None
    assert context.research_authorization.status == "authorized_pending_execution"
    assert context.decision_context is not None
    assert context.decision_context.context_version == 1


def test_production_provider_routing_and_markets_stay_closed() -> None:
    provider = shopify_global_catalog_ph_provider()
    assert provider.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert REAL_SHOPIFY_CALLS == 0
    reasons = production_shopify_execution_block_reasons()
    assert reasons
    assert "production_execution_not_wired" not in reasons


def test_closed_gates_do_not_call_open_continuation() -> None:
    transport = FakeCatalogTransport(_ok(_product()))
    called = False

    def _continuation(received):  # noqa: ANN001
        nonlocal called
        called = True
        del received
        raise AssertionError("closed production gates must not call the continuation")

    result = execute_production_shopify_catalog(transport, continuation=_continuation)
    assert called is False
    assert transport.calls == []
    assert result.transport_invoked is False
    assert result.block_reason == production_shopify_execution_block_reasons()[0]


def test_open_gates_can_continue_without_calling_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.research.shopify_global_catalog_execution.production_shopify_execution_block_reasons",
        lambda: (),
    )
    transport = FakeCatalogTransport(_ok(_product()))
    seen: dict[str, object] = {}

    def _continuation(received):  # noqa: ANN001
        seen["transport"] = received
        return ShopifyExecutionResult(
            attempted=False,
            transport_invoked=False,
            persisted=False,
            state=None,
            block_reason="test_continuation_stopped",
        )

    result = execute_production_shopify_catalog(transport, continuation=_continuation)
    assert seen["transport"] is transport
    assert transport.calls == []
    assert result.block_reason == "test_continuation_stopped"
    assert REAL_SHOPIFY_CALLS == 0
    missing = execute_production_shopify_catalog(transport)
    assert missing.block_reason == "production_composition_context_required"
    assert transport.calls == []


def test_synthetic_confirmation_traverses_claim_and_stays_fixture() -> None:
    snapshots, conversations, executions, reliability, snapshot = _stores()
    policy, registry, catalog, routing = _open_policy()
    transport = FakeCatalogTransport(_ok(_product()))
    evidence = InMemoryResearchExecutionEvidenceRepository()
    integrator = CanonicalResearchResultsService(
        executions,
        evidence,
        snapshots,
        conversations,
        clock=_clock,
    )
    assistant, _orchestrator = _assistant(
        policy=policy,
        registry=registry,
        catalog=catalog,
        routing=routing,
        executions=executions,
        reliability=reliability,
        conversations=conversations,
        snapshots=snapshots,
        transport=transport,
        evidence=evidence,
        integrator=integrator,
        orchestrator_type=_RecordingOrchestrator,
    )
    _first, confirmed = _confirm(assistant)
    public = confirmed.processing["confirmed_research"]
    assert public["claim_invoked"] is True
    assert public["adapter_invoked"] is True
    assert public["transport_invoked"] is True
    assert public["authorization_consumed"] is True
    assert public["source_checked"] is False
    assert public["attempted"] is False
    assert public["shopper_results_updated"] is False
    assert public["synthetic"] is True
    assert public["test_fixture"] is True
    assert public["live_research_completed"] is False
    assert public["integration_outcome"] == "synthetic_evidence_only"
    assert confirmed.processing["authorization_status"] == "consumed"
    assert "not available" in confirmed.answer.lower()
    assert "Research completed" not in confirmed.answer
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["endpoint"] == GLOBAL_CATALOG_ENDPOINT
    encoded = json.dumps(call["payload"])
    assert _SERVER_QUERY in encoded
    assert "browser-chosen-query" not in encoded
    assert "browser-provider" not in encoded
    assert "browser-execution" not in encoded
    catalog_args = call["payload"]["params"]["arguments"]["catalog"]
    assert catalog_args["context"]["address_country"] == "PH"
    assert catalog_args["filters"]["ships_to"] == {"country": "PH"}
    stored = executions.get(public["execution_id"])
    assert stored is not None
    assert stored.state == "completed"
    assert stored.outcome == "succeeded"
    assert stored.observation_kind == "synthetic"
    assert stored.plan_id
    assert stored.attempted_provider_id == shopify_global_catalog_ph_provider().provider_id
    assert stored.attempted_market == "PH"
    assert stored.attempted_capability == ResearchCapability.CURRENT_PRICING.value
    assert stored.raw_response_persisted is False
    assert stored.evidence_ids == tuple(public["evidence_ids"])
    assert stored.evidence_ids
    assert stored.normalized_offer_digests
    assert set(stored.normalized_offer_digests).isdisjoint(stored.evidence_ids)
    for evidence_id in stored.evidence_ids:
        record = evidence.get(evidence_id)
        assert record is not None
        assert record.evidence_id == evidence_id
        assert record.test_fixture is True
        assert record.observation_kind == "synthetic"
        assert record.source_mode is SourceMode.FIXTURE
        assert record.raw_response_persisted is False
        assert record.product_id == "gid://shopify/Product/earbuds-1"
        assert record.variant_id == "variant-north-1"
        assert record.seller_identity == "North Audio"
        assert record.amount_minor == 79900
        assert record.currency == "USD"
        assert record.availability == "in_stock"
        assert record.launch_evidence is False
        assert record.activates_public_market is False
    assert stored.trace is not None
    assert stored.trace.plan_id == stored.plan_id
    assert snapshots.get(DECISION_ID, 1) == snapshot
    assert snapshots.get(DECISION_ID, 2) is None
    context = conversations.get(confirmed.conversation_id)
    assert context is not None
    assert context.decision_context is not None
    assert context.decision_context.context_version == 1
    assert context.research_proposal is not None
    assert context.research_authorization is not None
    assert context.research_authorization.status == "consumed"
    assert production_certified_shopping_markets().to_tuple() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert REAL_SHOPIFY_CALLS == 0


def test_browser_market_override_is_rejected_before_claim() -> None:
    snapshots, conversations, executions, reliability, _snapshot = _stores()
    policy, registry, catalog, routing = _open_policy()
    transport = FakeCatalogTransport(_ok(_product()))
    assistant, _orchestrator = _assistant(
        policy=policy,
        registry=registry,
        catalog=catalog,
        routing=routing,
        executions=executions,
        reliability=reliability,
        conversations=conversations,
        snapshots=snapshots,
        transport=transport,
        evidence=InMemoryResearchExecutionEvidenceRepository(),
    )
    _first, confirmed = _confirm(assistant, country_code="US", provider_id="browser-provider")
    public = confirmed.processing["confirmed_research"]
    assert public["claim_invoked"] is False
    assert public["adapter_invoked"] is False
    assert public["transport_invoked"] is False
    assert public["authorization_consumed"] is False
    assert transport.calls == []
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert confirmed.processing["research_preparation_outcome"] == "caller_target_rejected"
    assert executions.row_count() == 0


def test_kill_switch_failure_before_commit_leaves_authorization_pending() -> None:
    snapshots, conversations, executions, reliability, _snapshot = _stores()
    policy, registry, catalog, routing = _open_policy()
    transport = FakeCatalogTransport(_ok(_product()))
    assistant, _orchestrator = _assistant(
        policy=policy,
        registry=registry,
        catalog=catalog,
        routing=routing,
        executions=executions,
        reliability=reliability,
        conversations=conversations,
        snapshots=snapshots,
        transport=transport,
        evidence=InMemoryResearchExecutionEvidenceRepository(),
        kill_switch=KillSwitch(engaged=True, reason="stop"),
    )
    _first, confirmed = _confirm(assistant)
    public = confirmed.processing["confirmed_research"]
    assert public["claim_invoked"] is True
    assert public["adapter_invoked"] is False
    assert public["transport_invoked"] is False
    assert public["authorization_consumed"] is False
    assert public["source_checked"] is False
    assert public["attempted"] is False
    assert transport.calls == []
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    stored = next(iter(executions._rows.values()))  # noqa: SLF001
    assert stored.state == "prepared_unavailable"
    assert snapshots.get(DECISION_ID, 2) is None


def test_evidence_persistence_failure_preserves_results() -> None:
    snapshots, conversations, executions, reliability, snapshot = _stores()
    policy, registry, catalog, routing = _open_policy()
    transport = FakeCatalogTransport(_ok(_product()))
    assistant, _orchestrator = _assistant(
        policy=policy,
        registry=registry,
        catalog=catalog,
        routing=routing,
        executions=executions,
        reliability=reliability,
        conversations=conversations,
        snapshots=snapshots,
        transport=transport,
        evidence=_BoomEvidence(),
    )
    _first, confirmed = _confirm(assistant)
    public = confirmed.processing["confirmed_research"]
    assert public["block_reason"] == "evidence_persistence_failed"
    assert public["shopper_results_updated"] is False
    assert public["evidence_ids"] == []
    assert snapshots.get(DECISION_ID, 1) == snapshot
    assert snapshots.get(DECISION_ID, 2) is None


def test_direct_continuation_uses_trusted_plan_not_caller_execution_id() -> None:
    snapshots, conversations, executions, reliability, _snapshot = _stores()
    policy, registry, catalog, routing = _open_policy()
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=_clock,
        execution_ledger=executions,
        planning_registry=registry,
        planning_catalog=catalog,
        planning_routing=routing,
    )
    first = assistant.query({"query": _PRICE, "decision_id": DECISION_ID}, owner=_owner())
    confirmed = assistant.query(
        {
            "query": _CONFIRM,
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
            "proposal_id": first.processing["proposal_id"],
            "proposal_version": first.processing["proposal_version"],
        },
        owner=_owner(),
    )
    context = conversations.get(confirmed.conversation_id)
    assert context is not None
    authorization = context.research_authorization
    assert authorization is not None
    assert authorization.is_pending_execution
    preparation = prepare_confirmed_research(
        authorization,
        owner=_owner(),
        conversation_id=context.conversation_id,
        decision_id=authorization.decision_id,
        canonical_context_version=authorization.canonical_context_version,
        proposal=context.research_proposal,
        ledger=executions,
        registry=registry,
        catalog=catalog,
        routing_policy=routing,
        now=START,
    )
    assert preparation.outcome == "prepared_but_live_unavailable"
    assert preparation.trusted_plan is not None
    transport = FakeCatalogTransport(_ok(_product()))
    claims, _executions, _reliability = in_memory_live_start_claims(
        executions,
        reliability,
        conversations,
        token_factory=_token_factory(),
    )
    adapter = in_memory_shopify_execution(
        executions,
        reliability,
        conversations,
        transport,
        clock=_clock,
    )
    orchestrator = ConfirmedResearchExecutionService(
        policy,
        claims=claims,
        adapter=adapter,
        evidence=InMemoryResearchExecutionEvidenceRepository(),
        executions=executions,
        clock=_clock,
    )
    result = orchestrator.continue_confirmed(
        ConfirmedResearchRequest(
            owner=_owner(),
            conversation_id=context.conversation_id,
            authorization=authorization,
            preparation=preparation,
            caller_execution_id="browser-execution",
            caller_catalog_query="browser-chosen-query",
        )
    )
    assert result.execution_id == preparation.execution_id
    assert result.execution_id != "browser-execution"
    assert "caller_execution_id" in result.ignored_caller_overrides
    assert result.synthetic is True
    assert result.test_fixture is True
    assert result.shopper_results_updated is False
    encoded = json.dumps(transport.calls[0]["payload"])
    assert _SERVER_QUERY in encoded
    assert "browser-chosen-query" not in encoded
    stored = executions.get(preparation.execution_id or "")
    assert stored is not None
    assert stored.plan_id == preparation.trusted_plan.plan_id


def test_production_composition_wires_continuation_and_stays_closed(monkeypatch) -> None:
    from app.research.authorized_execution_repository import (
        OperationalAuthorizedExecutionRepository,
    )
    from app.research.execution_evidence import OperationalResearchExecutionEvidenceRepository
    from app.research.live_start_claim import LiveStartClaimService
    from app.research.shopify_global_catalog_execution import (
        FAKE_TRANSPORT_PERMIT_CREATIONS,
        PRODUCTION_TRANSPORT_PERMIT_CREATIONS,
        ProductionShopifyTransportPermit,
    )
    from app.research.shopify_global_catalog_transport import UrllibJsonTransport
    from app.services.canonical_research_results import OperationalResultsIntegrationRepository
    from app.services.confirmed_research_execution import (
        ClosedProductionClaims,
        production_confirmed_research_execution,
    )

    sockets = {"socket": 0, "urlopen": 0}

    def _socket(*_args: object, **_kwargs: object) -> None:
        sockets["socket"] += 1
        raise AssertionError("production composition must not open a socket")

    def _urlopen(*_args: object, **_kwargs: object) -> None:
        sockets["urlopen"] += 1
        raise AssertionError("production composition must not call urlopen")

    monkeypatch.setattr(socket, "socket", _socket)
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen)
    before_fake = FAKE_TRANSPORT_PERMIT_CREATIONS
    before_production = PRODUCTION_TRANSPORT_PERMIT_CREATIONS
    service = production_confirmed_research_execution()
    assert isinstance(service.claims, LiveStartClaimService)
    assert not isinstance(service.claims, ClosedProductionClaims)
    assert service.production_composition is True
    assert service.adapter is not None
    assert isinstance(service.adapter._transport, UrllibJsonTransport)  # noqa: SLF001
    from app.research.shopify_global_catalog_transport import ProductionTransportAuthority

    authority = service.adapter._transport.production_transport_authority  # noqa: SLF001
    assert type(authority) is ProductionTransportAuthority
    assert authority.proves_production_transport()
    assert isinstance(service.evidence, OperationalResearchExecutionEvidenceRepository)
    assert isinstance(service.executions, OperationalAuthorizedExecutionRepository)
    assert service.integrator is not None
    assert isinstance(service.integrator._integrations, OperationalResultsIntegrationRepository)  # noqa: SLF001
    from app.services.confirmed_research_execution import ProductionResearchRuntimePolicy

    provider = shopify_global_catalog_ph_provider()
    policy = ProductionResearchRuntimePolicy()
    assert policy.operational_status is provider.descriptor.operational_status
    assert policy.operational_status is ConnectorOperationalStatus.DISABLED
    assert policy.kill_switch == provider.descriptor.kill_switch
    assert policy.kill_switch.engaged is False
    assert "live_flag_unexpectedly_enabled" not in production_shopify_execution_block_reasons()
    with pytest.raises(ValueError, match="every gate"):
        ProductionShopifyTransportPermit()
    snapshots, conversations, executions, _reliability, _snapshot = _stores()
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=_clock,
        execution_ledger=executions,
    )
    _first, confirmed = _confirm(assistant)
    public = confirmed.processing["confirmed_research"]
    assert public["claim_invoked"] is False
    assert public["adapter_invoked"] is False
    assert public["transport_invoked"] is False
    assert public["attempted"] is False
    assert public["source_checked"] is False
    assert public["research_executed"] is False
    assert public["live_research_completed"] is False
    assert public["shopper_results_updated"] is False
    assert confirmed.processing["execution_started"] is False
    assert confirmed.processing["research_executed"] is False
    assert before_fake == FAKE_TRANSPORT_PERMIT_CREATIONS
    assert before_production == PRODUCTION_TRANSPORT_PERMIT_CREATIONS
    assert sockets == {"socket": 0, "urlopen": 0}
    assert REAL_SHOPIFY_CALLS == 0


def test_synthetic_permit_cannot_use_production_transport() -> None:
    from app.domain.entities.research_execution import ResearchCapability
    from app.research.shopify_global_catalog_transport import UrllibJsonTransport

    from tests.unit.test_sprint38_shopify_execution_adapter import _attempt, _prepare

    prepared = _prepare(capability=ResearchCapability.CURRENT_PRICING)
    executions = prepared["executions"]
    synthetic = in_memory_shopify_execution(
        executions,
        prepared["reliability"],
        prepared["conversations"],
        UrllibJsonTransport(),
    )
    blocked = synthetic.execute(
        _attempt(
            prepared,
            capability=ResearchCapability.CURRENT_PRICING,
            operation="search_catalog",
        )
    )
    assert blocked.block_reason == "synthetic_permit_cannot_use_production_transport"
    assert blocked.transport_invoked is False
    assert REAL_SHOPIFY_CALLS == 0


def test_live_research_completed_is_a_real_field() -> None:
    from app.services.confirmed_research_execution import ConfirmedResearchResult

    closed = ConfirmedResearchResult(
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
    )
    assert closed.to_public_dict()["live_research_completed"] is False
    completed = ConfirmedResearchResult(
        claim_invoked=True,
        adapter_invoked=True,
        transport_invoked=True,
        authorization_consumed=True,
        source_checked=True,
        attempted=True,
        research_executed=True,
        live_research_completed=True,
        shopper_results_updated=True,
        synthetic=False,
        test_fixture=False,
        prior_decision_preserved=False,
        context_version=2,
    )
    assert completed.to_public_dict()["live_research_completed"] is True
    preserved = ConfirmedResearchResult(
        claim_invoked=True,
        adapter_invoked=True,
        transport_invoked=True,
        authorization_consumed=True,
        source_checked=True,
        attempted=True,
        research_executed=True,
        live_research_completed=True,
        shopper_results_updated=False,
        synthetic=False,
        test_fixture=False,
        prior_decision_preserved=True,
        integration_outcome="canonical_reevaluation_required",
    )
    assert preserved.to_public_dict()["shopper_results_updated"] is False
    assert preserved.to_public_dict()["attempted"] is True
    assert preserved.to_public_dict()["source_checked"] is True


def test_verified_production_result_keeps_execution_facts_independent() -> None:
    from types import SimpleNamespace

    from app.research.execution_evidence import (
        NormalizedOfferFact,
        VerifiedLiveOfferExecution,
    )
    from app.research.shopify_global_catalog_provider import SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
    from app.services.confirmed_research_execution import (
        ConfirmedResearchRequest,
        ProductionResearchRuntimePolicy,
        _after_unsuccessful_attempt,
    )
    from app.services.research_execution import authorized_execution_id

    from tests.unit.test_sprint38_execution_evidence_results import _AUTH_KEY, _SOURCE, _world

    execution_id = authorized_execution_id(_AUTH_KEY)
    world = _world(())
    fact = NormalizedOfferFact(
        product_id="outside-the-evaluated-set",
        variant_id=None,
        seller_identity="North Audio",
        amount_minor=79900,
        currency="USD",
        availability="in_stock",
        observed_at=START,
        normalized_offer_digest="ab" * 32,
        observation_kind="production",
        source_mode=SourceMode.LIVE.value,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        capability=ResearchCapability.CURRENT_PRICING.value,
        market="PH",
        source=_SOURCE,
    )
    from app.research.shopify_global_catalog_transport import issue_production_transport_authority

    verification = VerifiedLiveOfferExecution(
        execution_id=execution_id,
        decision_id=DECISION_ID,
        plan_id="plan-sprint38-b2",
        permit_marker="production_shopify_transport",
        transport_authority=issue_production_transport_authority(),
        facts=(fact,),
    )
    executed = ShopifyExecutionResult(
        attempted=True,
        transport_invoked=True,
        persisted=True,
        state="completed",
        block_reason=None,
        outcome="succeeded",
        observation_kind="production",
        evaluated_offer_count=1,
        normalized_offer_count=1,
        execution_authority="production",
        offer_facts=(fact,),
        verified_live_execution=verification,
    )
    service = ConfirmedResearchExecutionService(
        ProductionResearchRuntimePolicy(),
        evidence=world["evidence"],
        executions=world["executions"],
        integrator=world["service"],
    )
    result = service._record_production_evidence(  # noqa: SLF001
        ConfirmedResearchRequest(
            owner=_owner(),
            conversation_id=world["context"].conversation_id,
            authorization=SimpleNamespace(decision_id=DECISION_ID),  # type: ignore[arg-type]
            preparation=SimpleNamespace(execution_id=execution_id),  # type: ignore[arg-type]
        ),
        executed,
        ignored=(),
    )
    assert result.attempted is True
    assert result.source_checked is True
    assert result.research_executed is True
    assert result.live_research_completed is True
    assert result.shopper_results_updated is False
    assert result.integration_outcome == "canonical_reevaluation_required"
    assert result.prior_decision_preserved is True
    assert world["snapshots"].get(DECISION_ID, 2) is None
    timed_out = _after_unsuccessful_attempt(
        ShopifyExecutionResult(
            attempted=True,
            transport_invoked=True,
            persisted=True,
            state="failed",
            block_reason=None,
            outcome="timed_out",
            error_category="timeout",
            execution_authority="production",
        ),
        production=True,
        execution_id=execution_id,
        ignored=(),
    )
    assert timed_out.attempted is True
    assert timed_out.source_checked is False
    assert timed_out.research_executed is True
    assert timed_out.live_research_completed is False
    assert timed_out.shopper_results_updated is False


def test_live_research_completed_rejects_synthetic_completion() -> None:
    from app.services.confirmed_research_execution import ConfirmedResearchResult

    with pytest.raises(ValueError, match="synthetic execution cannot complete live research"):
        ConfirmedResearchResult(
            claim_invoked=True,
            adapter_invoked=True,
            transport_invoked=True,
            authorization_consumed=True,
            source_checked=False,
            attempted=False,
            research_executed=True,
            live_research_completed=True,
            shopper_results_updated=False,
            synthetic=True,
            test_fixture=True,
            prior_decision_preserved=True,
        )


def _harness_provider(*, kill_switch: KillSwitch | None = None):
    from app.research.providers import StaticResearchProvider

    base = shopify_global_catalog_ph_provider()
    descriptor = replace(
        base.descriptor,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=kill_switch or KillSwitch(),
    )
    return StaticResearchProvider(descriptor)


def _open_production_policy(*, kill_switch: KillSwitch | None = None):
    from app.research.registry import ResearchProviderRegistry
    from app.services.confirmed_research_execution import ProductionResearchRuntimePolicy

    _ignored, _registry, catalog, routing, markets = _world()
    provider = _harness_provider(kill_switch=kill_switch)
    registry = ResearchProviderRegistry((provider,), allow_test_providers=False)
    policy = ProductionResearchRuntimePolicy(
        registry=registry,
        certifications=catalog,
        routing=routing,
        certified_markets=markets,
        mode="live",
        live_call_permitted=True,
        profile_deployed=True,
    )
    return policy, registry, catalog, routing


def _sqlite_factory(tmp_path):  # noqa: ANN001
    from pathlib import Path

    from app.infrastructure.database.models.operational_entity import OperationalEntityModel
    from app.infrastructure.persistence.session import reset_sync_engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    reset_sync_engine()
    root = tmp_path if isinstance(tmp_path, Path) else Path(tmp_path)
    engine = create_engine(
        f"sqlite:///{root / 'future-open.db'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return engine, factory


def _matching_product() -> dict:
    product = _product()
    variant = dict(product["variants"][0])
    variant["id"] = "black"
    return {**product, "id": SONY_ID, "variants": [variant]}


def _future_open_stack(
    tmp_path,  # noqa: ANN001
    *,
    execution_kill_switch: KillSwitch | None = None,
    product: dict | None = None,
):
    import app.research.shopify_global_catalog_execution as shopify_execution
    from app.infrastructure.database.repositories.shopping_conversation_repository import (
        SqlAlchemyConversationRepository,
    )
    from app.research.authorized_execution_repository import (
        OperationalAuthorizedExecutionRepository,
    )
    from app.research.execution_evidence import OperationalResearchExecutionEvidenceRepository
    from app.research.live_start_claim import operational_live_start_claims
    from app.research.shopify_global_catalog_execution import operational_shopify_execution
    from app.services.canonical_research_results import OperationalResultsIntegrationRepository
    from app.services.confirmed_research_execution import ConfirmedResearchExecutionService

    engine, factory = _sqlite_factory(tmp_path)
    policy, planning_registry, catalog, routing = _open_production_policy()
    if execution_kill_switch is not None:
        policy, _execution_registry, catalog, routing = _open_production_policy(
            kill_switch=execution_kill_switch,
        )
    snapshots = InMemoryDecisionSnapshotRepository(clock=_clock)
    snapshots.add(_presentation())
    conversations = SqlAlchemyConversationRepository(session_factory=factory, clock=_clock)
    executions = OperationalAuthorizedExecutionRepository(session_factory=factory)
    evidence = OperationalResearchExecutionEvidenceRepository(session_factory=factory)
    integrations = OperationalResultsIntegrationRepository(session_factory=factory)
    integrator = CanonicalResearchResultsService(
        executions,
        evidence,
        snapshots,
        conversations,
        integrations,
        clock=_clock,
    )
    transport = FakeCatalogTransport(_ok(product or _product()))
    service = ConfirmedResearchExecutionService(
        policy,
        claims=operational_live_start_claims(factory, token_factory=_token_factory()),
        adapter=operational_shopify_execution(factory, transport, clock=_clock),
        evidence=evidence,
        executions=executions,
        integrator=integrator,
        clock=_clock,
        harness_composition=True,
    )
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=_clock,
        execution_ledger=executions,
        confirmed_execution=service,
        planning_registry=planning_registry,
        planning_catalog=catalog,
        planning_routing=routing,
    )
    return {
        "engine": engine,
        "policy": policy,
        "transport": transport,
        "assistant": assistant,
        "snapshots": snapshots,
        "evidence": evidence,
        "integrations": integrations,
        "executions": executions,
        "permits_before": shopify_execution.PRODUCTION_TRANSPORT_PERMIT_CREATIONS,
        "harness_before": shopify_execution.HARNESS_TRANSPORT_PERMIT_CREATIONS,
    }


def _close_stack(stack) -> None:  # noqa: ANN001
    from app.infrastructure.persistence.session import reset_sync_engine

    stack["engine"].dispose()
    reset_sync_engine()


def test_provider_status_and_kill_switch_come_from_the_registry() -> None:
    from app.research.registry import ResearchProviderRegistry
    from app.services.confirmed_research_execution import ProductionResearchRuntimePolicy

    current = ProductionResearchRuntimePolicy()
    descriptor = shopify_global_catalog_ph_provider().descriptor
    assert current.operational_status is descriptor.operational_status
    assert current.operational_status is ConnectorOperationalStatus.DISABLED
    assert current.kill_switch == descriptor.kill_switch
    assert current.kill_switch.engaged is False
    opened, _registry, _catalog, _routing = _open_production_policy()
    assert opened.operational_status is ConnectorOperationalStatus.AVAILABLE
    assert opened.kill_switch.engaged is False
    assert opened.block_reasons() == ()
    missing = ProductionResearchRuntimePolicy(
        registry=ResearchProviderRegistry((), allow_test_providers=False),
    )
    assert missing.operational_status is ConnectorOperationalStatus.DISABLED
    assert missing.kill_switch.engaged is True
    assert missing.kill_switch.reason == "provider_missing"
    assert "provider_not_operationally_eligible" in missing.block_reasons()
    assert shopify_global_catalog_ph_provider().descriptor.operational_status is (
        ConnectorOperationalStatus.DISABLED
    )


def test_live_operational_status_is_not_an_execution_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.research.shopify_global_catalog_execution.LIVE_RESEARCH_EXECUTION_OPERATIONAL",
        True,
    )
    reasons = production_shopify_execution_block_reasons()
    assert "live_flag_unexpectedly_enabled" not in reasons
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False


def test_production_result_can_represent_future_verified_live_operation() -> None:
    from app.research.execution_evidence import NormalizedOfferFact, VerifiedLiveOfferExecution
    from app.research.shopify_global_catalog_provider import SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID

    from tests.unit.test_sprint38_execution_evidence_results import _SOURCE

    fact = NormalizedOfferFact(
        product_id="outside-the-evaluated-set",
        variant_id=None,
        seller_identity="North Audio",
        amount_minor=79900,
        currency="USD",
        availability="in_stock",
        observed_at=START,
        normalized_offer_digest="ab" * 32,
        observation_kind="production",
        source_mode=SourceMode.LIVE.value,
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        capability=ResearchCapability.CURRENT_PRICING.value,
        market="PH",
        source=_SOURCE,
    )
    from app.research.shopify_global_catalog_transport import issue_production_transport_authority

    verification = VerifiedLiveOfferExecution(
        execution_id="research-exec:future-open",
        decision_id=DECISION_ID,
        plan_id="plan-sprint38-future",
        permit_marker="production_shopify_transport",
        transport_authority=issue_production_transport_authority(),
        facts=(fact,),
    )
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    represented = ShopifyExecutionResult(
        attempted=True,
        transport_invoked=True,
        persisted=True,
        state="completed",
        block_reason=None,
        outcome="succeeded",
        observation_kind="production",
        source_mode_live=True,
        live_research_execution_operational=True,
        real_shopify_call_count=1,
        evaluated_offer_count=1,
        normalized_offer_count=1,
        execution_authority="production",
        offer_facts=(fact,),
        verified_live_execution=verification,
    )
    assert represented.source_mode_live is True
    assert represented.live_research_execution_operational is True
    assert represented.real_shopify_call_count == 1
    assert REAL_SHOPIFY_CALLS == 0
    with pytest.raises(ValueError, match="synthetic execution cannot record live operation"):
        ShopifyExecutionResult(
            attempted=False,
            transport_invoked=False,
            persisted=False,
            state=None,
            block_reason="closed",
            source_mode_live=True,
        )
    with pytest.raises(ValueError, match="only a verified production success"):
        ShopifyExecutionResult(
            attempted=True,
            transport_invoked=True,
            persisted=True,
            state="failed",
            block_reason=None,
            outcome="timed_out",
            execution_authority="production",
            source_mode_live=True,
        )


def _assert_fixture_evidence(stack, public) -> None:  # noqa: ANN001
    import app.research.shopify_global_catalog_execution as shopify_execution

    assert public["claim_invoked"] is True
    assert public["adapter_invoked"] is True
    assert public["transport_invoked"] is True
    assert public["authorization_consumed"] is True
    assert public["synthetic"] is True
    assert public["test_fixture"] is True
    assert public["live_research_completed"] is False
    assert public["shopper_results_updated"] is False
    assert public["prior_decision_preserved"] is True
    assert public["integration_outcome"] == "synthetic_evidence_only"
    assert len(stack["transport"].calls) == 1
    assert stack["permits_before"] == shopify_execution.PRODUCTION_TRANSPORT_PERMIT_CREATIONS
    assert stack["harness_before"] + 1 == shopify_execution.HARNESS_TRANSPORT_PERMIT_CREATIONS
    assert public["evidence_ids"]
    for evidence_id in public["evidence_ids"]:
        record = stack["evidence"].get(evidence_id)
        assert record is not None
        assert record.observation_kind == "synthetic"
        assert record.source_mode is SourceMode.FIXTURE
        assert record.test_fixture is True
        assert record.launch_evidence is False
        assert record.activates_public_market is False
    assert stack["integrations"].get(public["execution_id"]) is None


def test_future_open_harness_stays_fixture_evidence(tmp_path) -> None:  # noqa: ANN001
    """Server-owned harness only. Not production evidence and not launch evidence."""

    stack = _future_open_stack(tmp_path)
    try:
        before = stack["snapshots"].get(DECISION_ID, 1)
        assert before is not None
        assert stack["policy"].block_reasons() == ()
        assert stack["policy"].operational_status is ConnectorOperationalStatus.AVAILABLE
        _first, confirmed = _confirm(stack["assistant"])
        public = confirmed.processing["confirmed_research"]
        _assert_fixture_evidence(stack, public)
        assert stack["snapshots"].get(DECISION_ID, 2) is None
        assert stack["snapshots"].get(DECISION_ID, 1) == before
    finally:
        _close_stack(stack)
    assert shopify_global_catalog_ph_provider().descriptor.operational_status is (
        ConnectorOperationalStatus.DISABLED
    )
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert REAL_SHOPIFY_CALLS == 0


def test_authoritative_kill_switch_blocks_before_transport(tmp_path) -> None:  # noqa: ANN001
    import app.research.shopify_global_catalog_execution as shopify_execution

    engaged = KillSwitch(engaged=True, reason="stop")
    stack = _future_open_stack(tmp_path, execution_kill_switch=engaged)
    try:
        before = stack["snapshots"].get(DECISION_ID, 1)
        assert before is not None
        assert stack["policy"].operational_status is ConnectorOperationalStatus.AVAILABLE
        assert stack["policy"].kill_switch.engaged is True
        assert stack["policy"].kill_switch.reason == "stop"
        assert stack["policy"].block_reasons() == ()
        provider = stack["policy"].registry.get("ph-shopify-global-catalog")
        assert provider is not None
        assert stack["policy"].kill_switch == provider.descriptor.kill_switch
        permits = shopify_execution.PRODUCTION_TRANSPORT_PERMIT_CREATIONS
        harness_permits = shopify_execution.HARNESS_TRANSPORT_PERMIT_CREATIONS
        _first, confirmed = _confirm(stack["assistant"])
        public = confirmed.processing["confirmed_research"]
        assert public["claim_invoked"] is True
        assert public["block_reason"] == "kill_switch"
        assert public["adapter_invoked"] is False
        assert public["transport_invoked"] is False
        assert public["authorization_consumed"] is False
        assert public["shopper_results_updated"] is False
        assert public["prior_decision_preserved"] is True
        assert stack["transport"].calls == []
        assert permits == shopify_execution.PRODUCTION_TRANSPORT_PERMIT_CREATIONS
        assert harness_permits == shopify_execution.HARNESS_TRANSPORT_PERMIT_CREATIONS
        assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
        assert stack["snapshots"].get(DECISION_ID, 2) is None
        assert stack["snapshots"].get(DECISION_ID, 1) == before
        execution = stack["executions"].get(public["execution_id"])
        assert execution is not None
        assert execution.state == "prepared_unavailable"
        assert execution.claimed_at is None
    finally:
        _close_stack(stack)


def test_fake_transport_exact_match_cannot_update_canonical_results(tmp_path) -> None:  # noqa: ANN001
    stack = _future_open_stack(tmp_path, product=_matching_product())
    try:
        before = stack["snapshots"].get(DECISION_ID, 1)
        assert before is not None
        _first, confirmed = _confirm(stack["assistant"])
        public = confirmed.processing["confirmed_research"]
        _assert_fixture_evidence(stack, public)
        assert public["evidence_ids"]
        matched = stack["evidence"].get(public["evidence_ids"][0])
        assert matched is not None
        assert matched.product_id == SONY_ID
        assert matched.variant_id == "black"
        assert stack["snapshots"].get(DECISION_ID, 2) is None
        preserved = stack["snapshots"].get(DECISION_ID, 1)
        assert preserved == before
        assert preserved is not None
        assert preserved.recommendation.best_piq_product_id == SONY_ID
        assert preserved.recommendation.decision == before.recommendation.decision
        assert preserved.canonical_piqscore_set_sha256 == before.canonical_piqscore_set_sha256
    finally:
        _close_stack(stack)


def test_production_permit_cannot_authorize_fake_transport() -> None:
    from app.domain.entities.research_execution import ResearchCapability
    from app.research.shopify_global_catalog_execution import (
        issue_production_shopify_transport_permit,
        production_live_evidence_authorized,
    )
    from app.research.shopify_global_catalog_transport import (
        ProductionTransportAuthority,
        UrllibJsonTransport,
        issue_production_transport_authority,
    )

    from tests.unit.test_sprint38_shopify_execution_adapter import _attempt, _prepare

    prepared = _prepare(capability=ResearchCapability.CURRENT_PRICING)
    permit = issue_production_shopify_transport_permit(authoritative_block_reasons=())
    fake = FakeCatalogTransport(_ok(_matching_product()))
    service = in_memory_shopify_execution(
        prepared["executions"],
        prepared["reliability"],
        prepared["conversations"],
        fake,
    )
    refused = service.execute(
        _attempt(
            prepared,
            capability=ResearchCapability.CURRENT_PRICING,
            operation="search_catalog",
            permit=permit,
        )
    )
    assert refused.block_reason == "production_transport_authority_required"
    assert refused.transport_invoked is False
    assert refused.verified_live_execution is None
    assert fake.calls == []
    assert production_live_evidence_authorized(permit, fake) is False
    bare = UrllibJsonTransport()
    assert production_live_evidence_authorized(permit, bare) is False
    authorized = UrllibJsonTransport(authority=issue_production_transport_authority())
    assert type(authorized.production_transport_authority) is ProductionTransportAuthority
    assert production_live_evidence_authorized(permit, authorized) is True
    assert REAL_SHOPIFY_CALLS == 0
