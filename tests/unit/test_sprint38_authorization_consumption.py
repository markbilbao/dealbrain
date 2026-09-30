"""Atomic authorization consumption and recoverable live-start resume.

A successful claim consumes one exact authorization. A failed gate does not.
No connector and no Shopify HTTP run in this slice.
"""

from __future__ import annotations

import json
import socket
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
    TimeoutPolicy,
)
from app.domain.entities.research_execution import (
    ResearchProviderStep,
    empty_execution_trace,
)
from app.domain.exceptions import ConversationVersionConflictError
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.errors import PersistenceUnavailableError
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import (
    RESEARCH_AUTHORIZED_EXECUTIONS,
    RESEARCH_PROVIDER_RELIABILITY,
    SHOPPING_CONVERSATIONS,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.market.support import production_certified_shopping_markets
from app.research.authorized_execution_repository import OperationalAuthorizedExecutionRepository
from app.research.certification import production_research_provider_certification_catalog
from app.research.live_start_claim import (
    AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM,
    EXECUTION_CLAIM_LEASE,
    HALF_OPEN_PROBE_LEASE,
    LIVE_CONNECTOR_CLEANUP_MARGIN,
    MAX_LIVE_CONNECTOR_ATTEMPT_TIMEOUT,
    SHOPIFY_LIVE_HTTP_TIMEOUT,
    LiveStartClaimRequest,
    in_memory_live_start_claims,
    operational_live_start_claims,
    shopify_anonymous_request_contract,
    validate_active_execution_claim,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import production_research_provider_registry
from app.research.reliability_repository import OperationalResearchReliabilityRepository
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.shopify_global_catalog_certification_evidence import SHOPIFY_GLOBAL_CATALOG_SOURCE
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider
from app.research.shopify_global_catalog_reliability import (
    shopify_normalization_reliability_candidate,
)
from app.research.sprint38_live_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
)
from app.services.research_authorization import (
    cancel_research_authorization,
    invalidate_research_authorization,
    validate_consumed_authorization_for_execution_resume,
    validate_research_authorization_for_execution,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint38_live_start_claim import (
    _CAPABILITY,
    _MARKET,
    _NOW,
    _PROVIDER,
    _add_authorization,
    _bind,
    _open_then_half_open,
    _plan_for,
    _prepare_memory,
    _request,
    _save_half_open,
    _seed_conversation,
    _seed_sqlite_conversation,
    _token_factory,
    _world,
    request_execution_id,
)

_FAR = datetime(2030, 6, 1, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("authorization consumption tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'consumption.db'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _stored(service, auth):
    assert service.conversations is not None
    context = service.conversations.get(auth.conversation_id)
    assert context is not None
    found = next(
        item
        for item in context.research_authorizations
        if item.authorization_id == auth.authorization_id
    )
    return context, found


def test_successful_claim_consumes_the_exact_authorization() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    result = service.claim(request)
    context, consumed = _stored(service, auth)
    execution = executions.get(result.execution_id or "")
    assert result.claimed is True
    assert result.authorization_consumed is True
    assert result.state == "claimed_for_attempt"
    assert consumed.status == "consumed"
    assert consumed.authorization_id == auth.authorization_id
    assert consumed.authorization_version == auth.authorization_version
    assert consumed.scope_digest == auth.scope_digest
    assert consumed.idempotency_key == auth.idempotency_key
    assert context.persistence_version == 2
    assert execution is not None
    assert execution.state == "claimed_for_attempt"
    assert execution.plan_id == plan.plan_id
    assert AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM is True


def test_consumption_survives_repository_and_session_recreation(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    first = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = first.claim(_request(auth, plan, registry, catalog, routing, markets))
    reloaded_execution = OperationalAuthorizedExecutionRepository(
        session_factory=sqlite_factory
    ).get(result.execution_id or "")
    reloaded_conversation = SqlAlchemyConversationRepository(
        session_factory=sqlite_factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    ).get(auth.conversation_id)
    assert result.authorization_consumed is True
    assert reloaded_execution is not None
    assert reloaded_execution.state == "claimed_for_attempt"
    assert reloaded_conversation is not None
    assert reloaded_conversation.research_authorizations[0].status == "consumed"
    assert reloaded_conversation.persistence_version == 2


def test_closed_claim_consumes_authorization_and_writes_no_probe() -> None:
    service, executions, reliability, auth, _plan, request = _prepare_memory()
    closed = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    reliability.save(closed, expected_revision=0)
    result = service.claim(request)
    breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    _context, consumed = _stored(service, auth)
    execution = executions.get(result.execution_id or "")
    assert result.claimed is True
    assert result.half_open_probe_lease_acquired is False
    assert result.probe_capability is None
    assert consumed.status == "consumed"
    assert breaker.half_open_probe_claim_digest is None
    assert breaker.revision == 1
    assert execution is not None and execution.state == "claimed_for_attempt"


def test_half_open_claim_commits_execution_probe_and_consumption(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    _save_half_open(sqlite_factory, now=_NOW)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    with sqlite_factory() as session:
        session.commit()
        execution = OperationalAuthorizedExecutionRepository(session=session).get(
            result.execution_id or ""
        )
        breaker = OperationalResearchReliabilityRepository(session).load(
            _PROVIDER,
            _MARKET,
            now=_NOW,
        )
        conversation = SqlAlchemyConversationRepository(
            session=session,
            clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        ).get(auth.conversation_id)
    assert result.claimed is True
    assert result.authorization_consumed is True
    assert result.half_open_probe_lease_acquired is True
    assert execution is not None and execution.state == "claimed_for_attempt"
    assert breaker.half_open_probe_claim_digest
    assert conversation is not None
    assert conversation.research_authorizations[0].status == "consumed"


def test_racing_workers_consume_one_authorization() -> None:
    service, executions, _reliability, auth, _plan, request = _prepare_memory()
    first, second = service.claim_racing((request, request))
    winner = first if first.claimed else second
    loser = second if first.claimed else first
    context, consumed = _stored(service, auth)
    assert winner.authorization_consumed is True
    assert loser.claimed is False
    assert loser.block_reason == "execution_already_claimed"
    assert loser.authorization_consumed is False
    assert consumed.status == "consumed"
    assert consumed.authorization_version == auth.authorization_version
    assert context.persistence_version == 2
    assert executions.row_count() == 1


def test_active_claim_blocks_a_second_worker_after_consumption() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    first = service.claim(request)
    before = _stored(service, auth)[0].persistence_version
    second = service.claim(request)
    context, consumed = _stored(service, auth)
    assert first.authorization_consumed is True
    assert second.claimed is False
    assert second.block_reason == "execution_already_claimed"
    assert second.authorization_consumed is False
    assert consumed.status == "consumed"
    assert context.persistence_version == before


def test_expired_consumed_execution_can_be_reclaimed() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    first = service.claim(request)
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    reclaimed = service.claim(replace(request, now=expired_at))
    execution = executions.get(first.execution_id or "")
    _context, consumed = _stored(service, auth)
    assert first.claimed is True and first.authorization_consumed is True
    assert reclaimed.claimed is True
    assert reclaimed.authorization_consumed is False
    assert reclaimed.execution_id == first.execution_id
    assert execution is not None
    assert execution.execution_id == first.execution_id
    assert execution.plan_id == plan.plan_id
    assert execution.state == "claimed_for_attempt"
    assert consumed.status == "consumed"
    assert consumed.authorization_version == auth.authorization_version
    assert _context.persistence_version == 2


def test_reclaim_keeps_the_same_execution_id_and_does_not_consume_again() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    first = service.claim(request)
    version_after_claim = _stored(service, auth)[1].authorization_version
    persistence_after_claim = _stored(service, auth)[0].persistence_version
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    reclaimed = service.claim(replace(request, now=expired_at))
    context, consumed = _stored(service, auth)
    assert reclaimed.execution_id == first.execution_id
    assert reclaimed.authorization_consumed is False
    assert consumed.status == "consumed"
    assert consumed.authorization_version == version_after_claim
    assert context.persistence_version == persistence_after_claim


def test_old_claim_capability_is_invalid_after_reclaim() -> None:
    service, executions, _reliability, _auth, _plan, request = _prepare_memory()
    first = service.claim(request)
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    reclaimed = service.claim(replace(request, now=expired_at))
    current = executions.get(first.execution_id or "")
    assert current is not None
    old = validate_active_execution_claim(
        current,
        claim_capability=first.claim_capability or "",
        now=expired_at,
    )
    new = validate_active_execution_claim(
        current,
        claim_capability=reclaimed.claim_capability or "",
        now=expired_at,
    )
    assert old.valid is False
    assert new.valid is True


def test_different_plan_cannot_use_a_consumed_authorization() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    service.claim(request)
    other_plan = replace(plan, plan_id="plan-other")
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    refused = service.claim(replace(request, plan=other_plan, now=expired_at))
    execution = executions.get(request_execution_id(auth))
    _context, consumed = _stored(service, auth)
    assert refused.claimed is False
    assert refused.block_reason == "authorization_plan_conflict"
    assert refused.authorization_consumed is False
    assert consumed.status == "consumed"
    assert execution is not None and execution.plan_id == plan.plan_id
    assert _context.persistence_version == 2


def test_different_decision_cannot_use_a_consumed_authorization() -> None:
    service, _executions, _reliability, auth, plan, request = _prepare_memory()
    service.claim(request)
    other_plan = replace(plan, decision_id="decision-other")
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    refused = service.claim(replace(request, plan=other_plan, now=expired_at))
    _context, consumed = _stored(service, auth)
    assert refused.block_reason == "execution_pin_mismatch"
    assert consumed.status == "consumed"
    assert consumed.decision_id == auth.decision_id


def test_different_execution_cannot_use_a_consumed_authorization() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    service.claim(request)
    _context, consumed = _stored(service, auth)
    execution = executions.get(request_execution_id(auth))
    assert execution is not None
    normal = validate_research_authorization_for_execution(
        consumed,
        owner=request.owner,
        conversation_id=plan.conversation_id,
        decision_id=plan.decision_id,
        canonical_context_version=plan.canonical_context_version,
    )
    resume = validate_consumed_authorization_for_execution_resume(
        consumed,
        owner=request.owner,
        conversation_id=plan.conversation_id,
        decision_id=plan.decision_id,
        canonical_context_version=plan.canonical_context_version,
        proposal_id=plan.proposal_id,
        proposal_version=plan.proposal_version,
        scope_digest=plan.scope_digest,
        execution_id="research-exec:" + ("0" * 64),
        execution_plan_id=execution.plan_id,
        execution_authorization_id=execution.authorization_id,
        execution_authorization_version=execution.authorization_version,
        execution_decision_id=execution.decision_id,
        execution_state=execution.state,
        claim_active=False,
        requested_plan_id=plan.plan_id,
    )
    assert normal.valid is False and normal.reason == "consumed"
    assert resume.valid is False
    assert resume.reason == "consumed_authorization_execution_mismatch"


def test_different_owner_cannot_resume_a_consumed_execution() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    service.claim(request)
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    refused = service.claim(
        replace(request, owner=_owner("other-guest"), now=expired_at),
    )
    _context, consumed = _stored(service, auth)
    assert refused.claimed is False
    assert refused.block_reason == "wrong_owner"
    assert consumed.status == "consumed"
    assert _context.persistence_version == 2


def test_different_conversation_cannot_resume_a_consumed_execution() -> None:
    service, _executions, _reliability, auth, plan, request = _prepare_memory()
    service.claim(request)
    other_plan = replace(plan, conversation_id="conversation-other")
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    refused = service.claim(replace(request, plan=other_plan, now=expired_at))
    _context, consumed = _stored(service, auth)
    assert refused.claimed is False
    assert refused.block_reason == "wrong_conversation"
    assert consumed.conversation_id == auth.conversation_id
    assert _context.persistence_version == 2


def test_cancellation_does_not_resurrect_a_consumed_authorization() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    service.claim(request)
    _context, consumed = _stored(service, auth)
    cancelled = cancel_research_authorization(consumed, now=_NOW + timedelta(seconds=1))
    assert cancelled.status == "consumed"
    assert cancelled.authorization_version == consumed.authorization_version
    reloaded = _stored(service, auth)[1]
    assert reloaded.status == "consumed"


def test_invalidation_does_not_resurrect_a_consumed_authorization() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    service.claim(request)
    _context, consumed = _stored(service, auth)
    invalidated = invalidate_research_authorization(consumed, now=_NOW + timedelta(seconds=1))
    assert invalidated.status == "consumed"
    assert _stored(service, auth)[1].status == "consumed"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("mode", "disabled", "mode_not_live"),
        ("operational_status", ConnectorOperationalStatus.DISABLED, "provider_disabled"),
    ],
)
def test_failed_status_gates_leave_authorization_pending(
    field: str,
    value: object,
    reason: str,
) -> None:
    service, executions, _reliability, auth, _plan, request = _prepare_memory()
    refused = service.claim(replace(request, **{field: value}))
    execution = executions.get(request_execution_id(auth))
    context, stored = _stored(service, auth)
    assert refused.claimed is False
    assert refused.block_reason == reason
    assert refused.authorization_consumed is False
    assert stored.status == "authorized_pending_execution"
    assert context.persistence_version == 1
    assert execution is not None and execution.state == "prepared_unavailable"


def test_routing_absent_leaves_authorization_pending() -> None:
    from app.research.routing import ResearchProviderRoutingPolicyCatalog

    service, executions, _reliability, auth, _plan, request = _prepare_memory()
    refused = service.claim(
        replace(request, routing=ResearchProviderRoutingPolicyCatalog((), allow_test_policies=True))
    )
    context, stored = _stored(service, auth)
    execution = executions.get(request_execution_id(auth))
    assert refused.block_reason == "routing_absent"
    assert stored.status == "authorized_pending_execution"
    assert context.persistence_version == 1
    assert execution is not None and execution.state == "prepared_unavailable"


def test_kill_switch_leaves_authorization_pending() -> None:
    service, executions, _reliability, auth, _plan, request = _prepare_memory()
    refused = service.claim(replace(request, kill_switch=KillSwitch(engaged=True, reason="stop")))
    context, stored = _stored(service, auth)
    assert refused.block_reason == "kill_switch"
    assert stored.status == "authorized_pending_execution"
    assert context.persistence_version == 1
    assert executions.get(request_execution_id(auth)).state == "prepared_unavailable"  # type: ignore[union-attr]


def test_circuit_open_leaves_authorization_pending() -> None:
    from app.research.reliability_repository import ResearchReliabilityGate
    from app.research.reliability_state import BreakerPolicy

    service, executions, reliability, auth, _plan, request = _prepare_memory()
    gate = ResearchReliabilityGate(
        reliability,
        policy=BreakerPolicy(failure_threshold=1, recovery_window_ms=30_000),
    )
    gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=_NOW)
    refused = service.claim(replace(request, now=_NOW + timedelta(seconds=1)))
    context, stored = _stored(service, auth)
    breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    assert refused.block_reason == "circuit_open"
    assert stored.status == "authorized_pending_execution"
    assert context.persistence_version == 1
    assert breaker.half_open_probe_claim_digest is None
    assert executions.get(request_execution_id(auth)).state == "prepared_unavailable"  # type: ignore[union-attr]


def test_half_open_lease_conflict_leaves_the_loser_pending() -> None:
    service, executions, reliability, auth, _plan, request = _prepare_memory()
    other_auth, other_plan = _plan_for(
        {"proposal_id": "proposal-consume-b", "authorization_id": "authorization-consume-b"},
        request.registry,
        request.certifications,
        request.routing,
    )
    _bind(executions, other_auth, other_plan)
    assert service.conversations is not None
    _add_authorization(service.conversations, other_auth)
    _open_then_half_open(reliability, now=_NOW)
    other = _request(
        other_auth,
        other_plan,
        request.registry,
        request.certifications,
        request.routing,
        request.certified_markets,
    )
    first, second = service.claim_racing((request, other))
    assert first.claimed is True and first.authorization_consumed is True
    assert second.claimed is False
    assert second.block_reason == "half_open_probe_already_claimed"
    assert second.authorization_consumed is False
    winner = _stored(service, auth)[1]
    loser_context = service.conversations.get(other_auth.conversation_id)
    assert loser_context is not None
    loser = next(
        item
        for item in loser_context.research_authorizations
        if item.authorization_id == other_auth.authorization_id
    )
    assert winner.status == "consumed"
    assert loser.status == "authorized_pending_execution"
    assert executions.get(request_execution_id(other_auth)).state == "prepared_unavailable"  # type: ignore[union-attr]


def test_execution_claim_conflict_does_not_double_consume() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    first, second = service.claim_racing((request, replace(request)))
    assert sum(item.authorization_consumed for item in (first, second)) == 1
    assert _stored(service, auth)[1].status == "consumed"
    assert _stored(service, auth)[0].persistence_version == 2


def test_conversation_cas_conflict_rolls_back_execution_and_probe() -> None:
    class _Conflict(InMemoryConversationRepository):
        def consume_research_authorization(self, conversation_id: str, **kwargs: object):
            raise ConversationVersionConflictError(
                conversation_id,
                int(kwargs["expected_version"]),  # type: ignore[arg-type]
            )

    conversations = _Conflict()
    service, executions, reliability = in_memory_live_start_claims(
        conversations=conversations,
        token_factory=_token_factory(),
    )
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(executions, auth, plan)
    _seed_conversation(conversations, auth)
    _open_then_half_open(reliability, now=_NOW)
    before = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    execution = executions.get(request_execution_id(auth))
    breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    context = conversations.get(auth.conversation_id)
    assert result.claimed is False
    assert result.block_reason == "authorization_consumption_conflict"
    assert result.authorization_consumed is False
    assert result.half_open_probe_lease_acquired is False
    assert execution is not None and execution.state == "prepared_unavailable"
    assert execution.claim_digest is None
    assert breaker.half_open_probe_claim_digest is None
    assert breaker.revision == before.revision
    assert context is not None
    assert context.research_authorizations[0].status == "authorized_pending_execution"
    assert context.persistence_version == 1


def test_sqlite_conversation_cas_conflict_rolls_back_the_claim(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    before = _save_half_open(sqlite_factory, now=_NOW)

    def _conflict(self, conversation_id: str, **kwargs: object) -> None:
        del self
        raise ConversationVersionConflictError(conversation_id, int(kwargs["expected_version"]))  # type: ignore[arg-type]

    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        SqlAlchemyConversationRepository,
        "consume_research_authorization",
        _conflict,
    )
    try:
        result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    finally:
        monkeypatch.undo()
    execution = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        request_execution_id(auth)
    )
    conversation = SqlAlchemyConversationRepository(
        session_factory=sqlite_factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    ).get(auth.conversation_id)
    with sqlite_factory() as session:
        breaker = OperationalResearchReliabilityRepository(session).load(
            _PROVIDER,
            _MARKET,
            now=_NOW,
        )
    assert result.block_reason == "authorization_consumption_conflict"
    assert execution is not None and execution.state == "prepared_unavailable"
    assert execution.revision == 1
    assert breaker.revision == before.revision
    assert breaker.half_open_probe_claim_digest is None
    assert conversation is not None
    assert conversation.research_authorizations[0].status == "authorized_pending_execution"


def test_persistence_failure_rolls_back_consumption(sqlite_factory) -> None:
    from app.infrastructure.persistence.operational_store import OperationalStore

    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    before = _save_half_open(sqlite_factory, now=_NOW)
    real = OperationalStore.compare_and_swap

    def _fail_reliability(self, store: str, *args: object, **kwargs: object) -> bool:
        if store == RESEARCH_PROVIDER_RELIABILITY:
            raise PersistenceUnavailableError("reliability store unavailable")
        return real(self, store, *args, **kwargs)

    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(OperationalStore, "compare_and_swap", _fail_reliability)
    try:
        result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    finally:
        monkeypatch.undo()
    execution = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        request_execution_id(auth)
    )
    conversation = SqlAlchemyConversationRepository(
        session_factory=sqlite_factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    ).get(auth.conversation_id)
    with sqlite_factory() as session:
        breaker = OperationalResearchReliabilityRepository(session).load(
            _PROVIDER,
            _MARKET,
            now=_NOW,
        )
    assert result.block_reason == "claim_persistence_unavailable"
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert execution is not None and execution.state == "prepared_unavailable"
    assert breaker.revision == before.revision
    assert breaker.half_open_probe_claim_digest is None
    assert conversation is not None
    assert conversation.research_authorizations[0].status == "authorized_pending_execution"


def test_successful_claim_leaves_trace_and_attempt_flags_false() -> None:
    service, _executions, _reliability, auth, plan, request = _prepare_memory()
    result = service.claim(request)
    public = result.to_public_dict()
    trace = empty_execution_trace(plan.plan_id)
    assert trace.steps == ()
    assert trace.attempted_sources == ()
    assert trace.succeeded_sources == ()
    assert result.attempted is False
    assert result.source_checked is False
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert result.live_execution_started is False
    assert result.authorization_consumed is True
    assert public["attempted"] is False
    assert public["source_checked"] is False
    assert public["connector_invoked"] is False
    assert public["http_invoked"] is False
    assert public["live_execution_started"] is False
    assert public["authorization_consumed"] is True
    assert "claim_capability" not in public
    assert result.claim_capability not in json.dumps(public)
    context, consumed = _stored(service, auth)
    payload = json.dumps(context.to_dict())
    assert result.claim_capability not in payload
    assert consumed.status == "consumed"


def test_consumption_preserves_the_prior_decision_context() -> None:
    service, _executions, _reliability, auth, _plan, request = _prepare_memory()
    before = _stored(service, auth)[0]
    assert before.decision_context is not None
    score = before.decision_context.canonical_piqscore_snapshot_sha256
    recommendation = before.decision_context.recommendation_snapshot_sha256
    products = before.decision_context.evaluated_product_ids
    service.claim(request)
    after = _stored(service, auth)[0]
    assert after.decision_context is not None
    assert after.decision_context.decision_id == auth.decision_id
    assert after.decision_context.canonical_piqscore_snapshot_sha256 == score
    assert after.decision_context.recommendation_snapshot_sha256 == recommendation
    assert after.decision_context.evaluated_product_ids == products
    assert after.research_authorizations[0].evaluated_product_ids == auth.evaluated_product_ids


def test_connector_timeout_fits_under_both_leases() -> None:
    candidate = shopify_normalization_reliability_candidate()
    assert timedelta(milliseconds=TimeoutPolicy().timeout_ms) == SHOPIFY_LIVE_HTTP_TIMEOUT
    assert timedelta(milliseconds=candidate.timeout_policy.timeout_ms) == SHOPIFY_LIVE_HTTP_TIMEOUT
    assert MAX_LIVE_CONNECTOR_ATTEMPT_TIMEOUT == SHOPIFY_LIVE_HTTP_TIMEOUT
    assert timedelta(seconds=5) == SHOPIFY_LIVE_HTTP_TIMEOUT
    budget = SHOPIFY_LIVE_HTTP_TIMEOUT + LIVE_CONNECTOR_CLEANUP_MARGIN
    assert budget < EXECUTION_CLAIM_LEASE
    assert budget < HALF_OPEN_PROBE_LEASE
    assert timedelta(seconds=30) == EXECUTION_CLAIM_LEASE
    assert timedelta(seconds=30) == HALF_OPEN_PROBE_LEASE


def test_current_shopify_production_cannot_consume_authorization(sqlite_factory) -> None:
    provider = shopify_global_catalog_ph_provider()
    _synthetic, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    step = ResearchProviderStep(
        step_index=1,
        provider_id=provider.provider_id,
        provider_type=provider.descriptor.provider_type,
        capability=_CAPABILITY,
        source_identities=(SHOPIFY_GLOBAL_CATALOG_SOURCE,),
        market="PH",
        certification_id="production-observation",
        certification_version="current",
        selection_reason="current-production-gates",
    )
    production_plan = replace(plan, eligible_steps=(step,))
    _bind(
        OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory),
        auth,
        production_plan,
    )
    seeded = _seed_sqlite_conversation(sqlite_factory, auth)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = service.claim(
        LiveStartClaimRequest(
            authorization=auth,
            owner=_owner(),
            plan=production_plan,
            provider_id=provider.provider_id,
            market="PH",
            capability=_CAPABILITY,
            source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
            now=_NOW,
            operational_status=provider.descriptor.operational_status,
            kill_switch=provider.descriptor.kill_switch,
            registry=production_research_provider_registry(),
            certifications=production_research_provider_certification_catalog(),
            routing=production_research_provider_routing_policy_catalog(),
            certified_markets=production_certified_shopping_markets(),
            mode=SHOPPING_RESEARCH_EXECUTION_MODE,
        )
    )
    conversation = SqlAlchemyConversationRepository(
        session_factory=sqlite_factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    ).get(auth.conversation_id)
    execution = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        request_execution_id(auth)
    )
    with sqlite_factory() as session:
        reliability_row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_PROVIDER_RELIABILITY
            )
        )
        execution_row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS
            )
        )
    assert result.claimed is False
    assert result.block_reason == "mode_not_live"
    assert result.authorization_consumed is False
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert result.live_execution_started is False
    assert result.attempted is False
    assert result.source_checked is False
    assert conversation is not None
    assert conversation.research_authorizations[0].status == "authorized_pending_execution"
    assert conversation.persistence_version == seeded.persistence_version
    assert execution is not None and execution.state == "prepared_unavailable"
    assert reliability_row is None
    assert execution_row is not None
    assert "claimed_for_attempt" not in json.dumps(execution_row.payload)
    assert provider.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SPRINT_41_STATUS == "UNSTARTED"
    with pytest.raises(NotImplementedError):
        StaticResearchProvider.execute(provider, step)  # type: ignore[arg-type]


def test_shopify_anonymous_contract_is_recorded_without_http() -> None:
    contract = shopify_anonymous_request_contract()
    assert contract.endpoint == "https://catalog.shopify.com/api/ucp/mcp"
    assert contract.tools == ("search_catalog", "get_product")
    assert "lookup_catalog" in contract.forbidden_tools
    assert "pagination_beyond_first_page" in contract.forbidden_behaviors
    assert "bulk_ids" in contract.forbidden_behaviors
    assert "promoted_or_affiliate_fields" in contract.forbidden_behaviors
    assert "scraping" in contract.forbidden_behaviors
    assert contract.ships_to_country == "PH"
    assert contract.address_country == "PH"
    assert contract.requested_currency == "PHP"
    assert contract.preserve_returned_currency is True
    assert contract.offer_view == "offer"
    assert contract.content_type == "application/json"
    assert contract.accept == "application/json"
    assert contract.user_agent_required is True
    assert contract.authorization_header is False
    assert contract.signature is False
    assert contract.production_ucp_profile_deployed is False
    assert contract.http_implemented is False
    assert SHOPIFY_LIVE_CALL_PERMITTED is False


def test_consumed_authorization_cannot_start_a_prepared_execution() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    claimed = service.claim(request)
    _context, consumed = _stored(service, auth)
    execution = executions.get(claimed.execution_id or "")
    assert execution is not None
    refused = validate_consumed_authorization_for_execution_resume(
        consumed,
        owner=request.owner,
        conversation_id=plan.conversation_id,
        decision_id=plan.decision_id,
        canonical_context_version=plan.canonical_context_version,
        proposal_id=plan.proposal_id,
        proposal_version=plan.proposal_version,
        scope_digest=plan.scope_digest,
        execution_id=execution.execution_id,
        execution_plan_id=execution.plan_id,
        execution_authorization_id=execution.authorization_id,
        execution_authorization_version=execution.authorization_version,
        execution_decision_id=execution.decision_id,
        execution_state="prepared_unavailable",
        claim_active=False,
        requested_plan_id=plan.plan_id,
    )
    assert refused.valid is False
    assert refused.reason == "consumed_authorization_not_resumable"


def test_conversation_row_does_not_store_probe_capability(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    _save_half_open(sqlite_factory, now=_NOW)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    with sqlite_factory() as session:
        conversation = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == SHOPPING_CONVERSATIONS
            )
        )
        execution = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS
            )
        )
    assert result.probe_capability and result.claim_capability
    assert conversation is not None and execution is not None
    conversation_payload = json.dumps(conversation.payload)
    execution_payload = json.dumps(execution.payload)
    assert result.claim_capability not in conversation_payload
    assert result.probe_capability not in conversation_payload
    assert result.claim_capability not in execution_payload
    assert result.probe_capability not in execution_payload
    assert _FAR > _NOW
