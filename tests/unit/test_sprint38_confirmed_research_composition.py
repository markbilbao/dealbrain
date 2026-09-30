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
    return InjectedResearchRuntimePolicy(
        mode="live",
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        registry=registry,
        certifications=catalog,
        routing=routing,
        certified_markets=markets,
        reasons=(),
    ), registry, catalog, routing


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
