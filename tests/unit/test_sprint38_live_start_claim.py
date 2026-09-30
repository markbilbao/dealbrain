"""Sprint 38 safe live-start claim and HALF_OPEN single-probe lease.

No connector calls and no HTTP. A successful claim consumes the exact
authorization in the same transaction. Failed gates leave it pending.
"""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
    ResearchProviderStep,
    TrustedMarketContext,
)
from app.domain.entities.shopping_assistant import ConversationContext, DecisionContextReference
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.errors import PersistenceUnavailableError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import (
    RESEARCH_AUTHORIZED_EXECUTIONS,
    RESEARCH_PROVIDER_RELIABILITY,
    SHOPPING_CONVERSATIONS,
)
from app.market.support import production_certified_shopping_markets, shopping_markets_for_tests
from app.research.authorized_execution_repository import (
    DURABLE_LIVE_START_CLAIM_IMPLEMENTED,
    HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED,
    AuthorizedExecutionRevisionConflict,
    OperationalAuthorizedExecutionRepository,
)
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    make_research_provider_certification,
    production_research_provider_certification_catalog,
)
from app.research.live_start_claim import (
    AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM,
    EXECUTION_CLAIM_LEASE,
    HALF_OPEN_PROBE_LEASE,
    LiveStartClaimRequest,
    execution_claim_digest,
    in_memory_live_start_claims,
    operational_live_start_claims,
    validate_active_execution_claim,
    validate_active_half_open_probe,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import ResearchProviderRegistry, production_research_provider_registry
from app.research.reliability_repository import (
    InMemoryResearchReliabilityRepository,
    OperationalResearchReliabilityRepository,
    ResearchReliabilityGate,
)
from app.research.reliability_state import (
    BreakerPolicy,
    advance_recovery,
    build_research_provider_health,
)
from app.research.routing import (
    ResearchProviderRoutingPolicyCatalog,
    make_research_provider_routing_policy,
    production_research_provider_routing_policy_catalog,
)
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.shopify_global_catalog_certification_evidence import SHOPIFY_GLOBAL_CATALOG_SOURCE
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider
from app.research.sprint38_live_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
)
from app.services.research_execution_router import plan_authorized_research
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint31_research_execution_router import _authorization, _scope

_PROVIDER = "synthetic-claim-provider"
_MARKET = "PH"
_SOURCE = "synthetic-catalog"
_CAPABILITY = ResearchCapability.CURRENT_PRICING
_NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
_SUPPORTED = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("live-start claim tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'claims.db'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _token_factory() -> Callable[[], str]:
    counter = {"n": 0}

    def _next() -> str:
        counter["n"] += 1
        return f"opaque-claim-capability-{counter['n']:04d}"

    return _next


def _provider(
    *,
    provider_id: str = _PROVIDER,
    capabilities: tuple[ResearchCapability, ...] = _SUPPORTED,
    sources: tuple[str, ...] = (_SOURCE,),
    markets: tuple[str, ...] = (_MARKET,),
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    kill_switch: KillSwitch | None = None,
    test_fixture: bool = False,
) -> StaticResearchProvider:
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=provider_id,
            provider_type="test" if test_fixture else "merchant",
            supported_markets=markets,
            supported_capabilities=capabilities,
            supported_sources=sources,
            operational_status=operational_status,
            test_fixture=test_fixture,
            kill_switch=kill_switch or KillSwitch(),
            can_provide_pricing=ResearchCapability.CURRENT_PRICING in capabilities,
            can_provide_product_evidence=True,
            may_expand_evaluated_set=ResearchCapability.PRODUCT_DISCOVERY in capabilities,
        )
    )


def _world(
    provider: StaticResearchProvider | None = None,
    *,
    routing: bool = True,
    certify: bool = True,
    markets: tuple[str, ...] = (_MARKET,),
    cert_capability: ResearchCapability | None = None,
    cert_source: str | None = None,
    cert_fixture: bool = False,
    routing_fixture: bool = False,
    capabilities: tuple[ResearchCapability, ...] | None = None,
):
    chosen = provider or _provider()
    certified_capabilities = capabilities or chosen.descriptor.supported_capabilities
    records = []
    if certify:
        for capability in certified_capabilities:
            records.append(
                make_research_provider_certification(
                    provider_id=chosen.provider_id,
                    capability=cert_capability or capability,
                    market=chosen.descriptor.supported_markets[0],
                    source=cert_source or chosen.descriptor.supported_sources[0],
                    certification_version="claim-v1",
                    test_fixture=cert_fixture or chosen.descriptor.test_fixture,
                )
            )
    registry = ResearchProviderRegistry((chosen,), allow_test_providers=True)
    catalog = ResearchProviderCertificationCatalog(records, allow_test_certifications=True)
    policies = []
    if routing:
        policies.append(
            make_research_provider_routing_policy(
                provider_id=chosen.provider_id,
                routing_priority=1,
                test_fixture=routing_fixture or chosen.descriptor.test_fixture,
            )
        )
    routing_catalog = ResearchProviderRoutingPolicyCatalog(policies, allow_test_policies=True)
    return chosen, registry, catalog, routing_catalog, shopping_markets_for_tests(markets)


def _plan_for(auth_overrides: dict[str, object] | None, registry, catalog, routing):
    auth = _authorization(
        _scope(requested_sources=(_SOURCE,)),
        **(auth_overrides or {}),
    )
    planned = plan_authorized_research(
        auth,
        owner=_owner(),
        conversation_id=auth.conversation_id,
        decision_id=auth.decision_id,
        canonical_context_version=auth.canonical_context_version,
        registry=registry,
        catalog=catalog,
        routing_policy=routing,
        trusted_market=TrustedMarketContext(country_code=_MARKET),
    )
    assert planned.plan is not None
    assert any(step.capability is _CAPABILITY for step in planned.plan.eligible_steps)
    return auth, planned.plan


def _bind(repo, auth, plan, *, now: datetime = _NOW):
    return repo.bind(
        authorization_idempotency_key=auth.idempotency_key,
        authorization_id=auth.authorization_id,
        authorization_version=auth.authorization_version,
        decision_id=auth.decision_id,
        plan_id=plan.plan_id,
        now=now,
    )


def _request(
    auth,
    plan,
    registry,
    catalog,
    routing,
    markets,
    *,
    now: datetime = _NOW,
    provider_id: str = _PROVIDER,
    market: str = _MARKET,
    capability: ResearchCapability = _CAPABILITY,
    source: str = _SOURCE,
    operational_status: ConnectorOperationalStatus = ConnectorOperationalStatus.AVAILABLE,
    kill_switch: KillSwitch | None = None,
    mode: str = "live",
) -> LiveStartClaimRequest:
    return LiveStartClaimRequest(
        authorization=auth,
        owner=_owner(),
        plan=plan,
        provider_id=provider_id,
        market=market,
        capability=capability,
        source=source,
        now=now,
        operational_status=operational_status,
        kill_switch=kill_switch or KillSwitch(),
        registry=registry,
        certifications=catalog,
        routing=routing,
        certified_markets=markets,
        mode=mode,
    )


def _memory_service():
    return in_memory_live_start_claims(token_factory=_token_factory())


def _seed_conversation(conversations, *authorizations, owner=None):
    if not authorizations:
        raise AssertionError("at least one authorization is required")
    auth = authorizations[0]
    if any(item.conversation_id != auth.conversation_id for item in authorizations):
        raise AssertionError("one seed call stores one conversation")
    context = ConversationContext(
        conversation_id=auth.conversation_id,
        turns=(),
        expires_at=datetime(2030, 6, 1, tzinfo=UTC),
        owner=owner or _owner(),
        decision_context=DecisionContextReference(
            decision_id=auth.decision_id,
            context_version=auth.canonical_context_version,
            evaluated_product_ids=auth.evaluated_product_ids,
            canonical_piqscore_snapshot_sha256="ab" * 32,
            recommendation_snapshot_sha256="cd" * 32,
        ),
        research_authorizations=tuple(authorizations),
    )
    return conversations.save(context)


def _seed_sqlite_conversation(factory, *authorizations, owner=None):
    repository = SqlAlchemyConversationRepository(
        session_factory=factory,
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    return _seed_conversation(repository, *authorizations, owner=owner)


def _add_authorization(conversations, auth):
    current = conversations.get(auth.conversation_id)
    if current is None:
        return _seed_conversation(conversations, auth)
    return conversations.save(
        replace(
            current,
            research_authorizations=(*current.research_authorizations, auth),
        ),
        expected_version=current.persistence_version,
    )


def _prepare_memory():
    provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    service, executions, reliability = _memory_service()
    _bind(executions, auth, plan)
    assert service.conversations is not None
    _seed_conversation(service.conversations, auth)
    request = _request(auth, plan, registry, catalog, routing, markets)
    return service, executions, reliability, auth, plan, request


def test_lease_durations_are_bounded() -> None:
    assert timedelta(seconds=30) == EXECUTION_CLAIM_LEASE
    assert timedelta(seconds=30) == HALF_OPEN_PROBE_LEASE
    assert DURABLE_LIVE_START_CLAIM_IMPLEMENTED is True
    assert HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED is True
    assert AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM is True


def test_prepared_execution_can_be_claimed_without_a_connector() -> None:
    service, executions, reliability, auth, plan, request = _prepare_memory()
    decision_id = auth.decision_id
    result = service.claim(request)
    stored = executions.get(result.execution_id or "")
    assert stored is not None
    assert result.claimed is True
    assert result.state == "claimed_for_attempt"
    assert result.block_reason is None
    assert result.claim_expires_at == _NOW + EXECUTION_CLAIM_LEASE
    assert result.half_open_probe_lease_acquired is False
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert result.live_execution_started is False
    assert result.attempted is False
    assert result.source_checked is False
    assert result.authorization_consumed is True
    assert stored.state == "claimed_for_attempt"
    assert stored.plan_id == plan.plan_id
    assert stored.decision_id == decision_id
    assert stored.authorization_id == auth.authorization_id
    assert stored.authorization_version == auth.authorization_version
    assert stored.claim_digest == execution_claim_digest(result.claim_capability or "")
    assert result.claim_capability not in (stored.claim_digest or "")
    assert auth.status == "authorized_pending_execution"
    assert service.conversations is not None
    persisted = service.conversations.get(auth.conversation_id)
    assert persisted is not None
    assert persisted.research_authorizations[0].status == "consumed"
    assert persisted.research_authorizations[0].authorization_version == auth.authorization_version
    assert persisted.persistence_version == 2
    assert persisted.decision_context is not None
    assert persisted.decision_context.decision_id == decision_id
    assert auth.decision_id == decision_id
    assert reliability.row_count(_PROVIDER, _MARKET) == 0
    public = result.to_public_dict()
    assert "claim_capability" not in public
    assert result.claim_capability not in json.dumps(public)
    assert public["state"] == "claimed_for_attempt"
    assert "live" not in public["state"]
    assert "running" not in public["state"]


def test_claim_survives_repository_service_and_session_recreation(sqlite_factory) -> None:
    provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    first = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = first.claim(_request(auth, plan, registry, catalog, routing, markets))
    assert result.claimed is True
    second = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    reloaded = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        result.execution_id or ""
    )
    with sqlite_factory() as session:
        session.commit()
        opened = OperationalAuthorizedExecutionRepository(session=session)
        from_session = opened.get(result.execution_id or "")
    assert reloaded is not None
    assert from_session is not None
    assert reloaded.state == "claimed_for_attempt"
    assert from_session.claim_digest == reloaded.claim_digest
    assert from_session.revision == 2
    assert validate_active_execution_claim(
        from_session,
        claim_capability=result.claim_capability or "",
        now=_NOW,
    ).valid
    del second


def test_two_workers_racing_one_execution_yield_one_claim() -> None:
    service, executions, _reliability, _auth, _plan, request = _prepare_memory()
    first, second = service.claim_racing((request, request))
    claimed = [item for item in (first, second) if item.claimed]
    refused = [item for item in (first, second) if not item.claimed]
    assert len(claimed) == 1
    assert len(refused) == 1
    assert refused[0].block_reason == "execution_already_claimed"
    assert executions.row_count() == 1
    stored = executions.get(claimed[0].execution_id or "")
    assert stored is not None
    assert stored.state == "claimed_for_attempt"
    assert stored.revision == 2
    assert stored.claim_digest == execution_claim_digest(claimed[0].claim_capability or "")


def test_sqlite_workers_cannot_both_claim(sqlite_factory) -> None:
    provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    request = _request(auth, plan, registry, catalog, routing, markets)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    first, second = service.claim_racing((request, request))
    assert sum(item.claimed for item in (first, second)) == 1
    loser = second if first.claimed else first
    assert loser.block_reason == "execution_already_claimed"
    stored = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        first.execution_id or second.execution_id or ""
    )
    assert stored is not None
    assert stored.state == "claimed_for_attempt"
    assert stored.revision == 2


def test_threaded_sqlite_claim_has_one_winner(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    request = _request(auth, plan, registry, catalog, routing, markets)
    barrier = threading.Barrier(2)
    found: list[tuple[bool, str | None]] = []
    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            barrier.wait(timeout=5)
            service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
            result = service.claim(request)
            found.append((result.claimed, result.block_reason))
        except BaseException as exc:  # noqa: BLE001 — collect worker failures
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert errors == []
    assert sorted(found) == [(False, "execution_already_claimed"), (True, None)]


def test_active_lease_blocks_a_second_worker() -> None:
    service, executions, _reliability, _auth, _plan, request = _prepare_memory()
    first = service.claim(request)
    second = service.claim(request)
    assert first.claimed is True
    assert second.claimed is False
    assert second.block_reason == "execution_already_claimed"
    stored = executions.get(first.execution_id or "")
    assert stored is not None
    assert stored.revision == 2
    assert validate_active_execution_claim(
        stored,
        claim_capability=first.claim_capability or "",
        now=_NOW + EXECUTION_CLAIM_LEASE - timedelta(seconds=1),
    ).valid


def test_expired_claim_can_be_reclaimed_and_invalidates_the_old_worker() -> None:
    service, executions, _reliability, _auth, _plan, request = _prepare_memory()
    first = service.claim(request)
    assert first.claimed is True
    expired_at = _NOW + EXECUTION_CLAIM_LEASE
    held = executions.get(first.execution_id or "")
    assert held is not None
    expired = validate_active_execution_claim(
        held,
        claim_capability=first.claim_capability or "",
        now=expired_at,
    )
    assert expired.valid is False
    assert expired.reason == "execution_claim_expired"
    reclaimed = service.claim(replace(request, now=expired_at))
    assert reclaimed.claimed is True
    assert reclaimed.claim_capability != first.claim_capability
    current = executions.get(first.execution_id or "")
    assert current is not None
    assert current.revision == 3
    assert current.claimed_at == expired_at
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
    assert old.reason == "execution_claim_identity_mismatch"
    assert new.valid is True
    assert new.reason is None


def test_stale_revision_cannot_overwrite_the_active_claim() -> None:
    service, executions, _reliability, _auth, _plan, request = _prepare_memory()
    prepared = executions.get(service.claim(request).execution_id or "")
    assert prepared is not None
    winner = executions.get(prepared.execution_id)
    assert winner is not None
    stale = replace(winner, updated_at=_NOW + timedelta(seconds=1), revision=1)
    with pytest.raises(AuthorizedExecutionRevisionConflict):
        executions.cas_replace(stale, expected_revision=1)
    reloaded = executions.get(winner.execution_id)
    assert reloaded is not None
    assert reloaded.revision == winner.revision
    assert reloaded.claim_digest == winner.claim_digest
    assert reloaded.state == "claimed_for_attempt"


def test_different_plan_is_a_conflict_and_does_not_rewrite_the_pin() -> None:
    service, executions, _reliability, auth, plan, request = _prepare_memory()
    other_provider, registry, catalog, routing, markets = _world(
        _provider(provider_id="synthetic-other-provider")
    )
    _other_auth, other_plan = _plan_for(None, registry, catalog, routing)
    conflict = service.claim(
        _request(
            auth,
            other_plan,
            registry,
            catalog,
            routing,
            markets,
            provider_id=other_provider.provider_id,
        )
    )
    assert conflict.claimed is False
    assert conflict.block_reason == "authorization_plan_conflict"
    stored = executions.get(request_execution_id(auth))
    assert stored is not None
    assert stored.plan_id == plan.plan_id
    assert stored.state == "prepared_unavailable"
    assert stored.revision == 1
    del other_provider


def test_claim_consumption_preserves_the_prior_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import research_authorization as authorization_module

    consumed: list[str] = []
    real = authorization_module.mark_research_authorization_consumed

    def _consumed(authorization, *, now):  # noqa: ANN001
        consumed.append(authorization.authorization_id)
        return real(authorization, now=now)

    monkeypatch.setattr(authorization_module, "mark_research_authorization_consumed", _consumed)
    service, executions, _reliability, auth, _plan, request = _prepare_memory()
    decision_id = auth.decision_id
    assert service.conversations is not None
    before = service.conversations.get(auth.conversation_id)
    assert before is not None and before.decision_context is not None
    result = service.claim(request)
    stored = executions.get(result.execution_id or "")
    after = service.conversations.get(auth.conversation_id)
    assert result.authorization_consumed is True
    assert after is not None and after.decision_context == before.decision_context
    assert after.research_authorizations[0].status == "consumed"
    assert after.research_authorizations[0].evaluated_product_ids == auth.evaluated_product_ids
    assert auth.decision_id == decision_id
    assert stored is not None
    assert stored.decision_id == decision_id
    assert consumed == [auth.authorization_id]
    assert AUTHORIZATION_CONSUMPTION_ON_LIVE_START_CLAIM is True


def test_claim_does_not_create_trace_steps_or_attempt_flags() -> None:
    service, _executions, _reliability, _auth, _plan, request = _prepare_memory()
    result = service.claim(request)
    public = result.to_public_dict()
    assert result.attempted is False
    assert result.source_checked is False
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert result.live_execution_started is False
    assert public["attempted"] is False
    assert public["source_checked"] is False
    assert public["connector_invoked"] is False
    assert public["http_invoked"] is False
    assert public["live_execution_started"] is False


def test_open_breaker_before_reopen_blocks_the_probe_and_the_claim() -> None:
    service, executions, reliability, _auth, _plan, request = _prepare_memory()
    gate = ResearchReliabilityGate(
        reliability,
        policy=BreakerPolicy(failure_threshold=1, recovery_window_ms=30_000),
    )
    opened = gate.record_failure(
        _PROVIDER,
        _MARKET,
        ConnectorFailureKind.TIMEOUT,
        now=_NOW,
    )
    attempt_at = opened.last_attempt_at
    failure = opened.last_failure_category
    blocked = service.claim(replace(request, now=_NOW + timedelta(seconds=1)))
    assert blocked.claimed is False
    assert blocked.block_reason == "circuit_open"
    assert blocked.half_open_probe_lease_acquired is False
    stored = executions.get(request_execution_id(request.authorization))
    breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    assert stored is not None
    assert stored.state == "prepared_unavailable"
    assert breaker.half_open_probe_claim_digest is None
    assert breaker.last_attempt_at == attempt_at
    assert breaker.last_failure_category == failure
    assert breaker.last_success_at is None
    assert breaker.revision == opened.revision


def test_half_open_allows_one_probe_lease_and_blocks_the_next(sqlite_factory) -> None:
    _provider, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    other, other_plan = _plan_for(
        {"proposal_id": "proposal-probe-b", "authorization_id": "authorization-probe-b"},
        registry,
        catalog,
        routing,
    )
    executions = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory)
    _bind(executions, auth, plan)
    _bind(executions, other, other_plan)
    _seed_sqlite_conversation(sqlite_factory, auth, other)
    _save_half_open(sqlite_factory, now=_NOW)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    first_request = _request(auth, plan, registry, catalog, routing, markets)
    second_request = _request(other, other_plan, registry, catalog, routing, markets)
    first = service.claim(first_request)
    recreated = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    second = recreated.claim(second_request)
    assert first.claimed is True
    assert first.half_open_probe_lease_acquired is True
    assert second.claimed is False
    assert second.block_reason == "half_open_probe_already_claimed"
    with sqlite_factory() as session:
        session.commit()
        breaker = OperationalResearchReliabilityRepository(session).load(
            _PROVIDER,
            _MARKET,
            now=_NOW,
        )
        loser = OperationalAuthorizedExecutionRepository(session=session).get(
            request_execution_id(other)
        )
    assert breaker.state.value == "half_open"
    assert breaker.half_open_probe_claim_digest
    assert breaker.half_open_probe_expires_at == _NOW + HALF_OPEN_PROBE_LEASE
    assert validate_active_half_open_probe(
        breaker,
        claim_capability=first.probe_capability or "",
        now=_NOW,
    ).valid
    assert loser is not None
    assert loser.state == "prepared_unavailable"
    health = build_research_provider_health(
        provider_id=_PROVIDER,
        market=_MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch_engaged=False,
        breaker=breaker,
        routing_present=True,
        certification_present=True,
        test_fixture=False,
    )
    assert health.healthy is False
    assert health.live is False
    assert health.merchant_available is False
    assert breaker.last_success_at is None
    assert breaker.last_attempt_at == _NOW
    assert breaker.last_failure_category is ConnectorFailureKind.TIMEOUT


def test_concurrent_half_open_contenders_award_one_lease() -> None:
    service, executions, reliability, auth, plan, request = _prepare_memory()
    other_auth, other_plan = _plan_for(
        {"proposal_id": "proposal-race-b", "authorization_id": "authorization-race-b"},
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
    assert first.claimed is True
    assert first.half_open_probe_lease_acquired is True
    assert second.claimed is False
    assert second.block_reason == "half_open_probe_already_claimed"
    winner = executions.get(first.execution_id or "")
    loser = executions.get(request_execution_id(other_auth))
    breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    assert winner is not None and winner.state == "claimed_for_attempt"
    assert loser is not None and loser.state == "prepared_unavailable"
    assert breaker.half_open_probe_claim_digest
    assert validate_active_half_open_probe(
        breaker,
        claim_capability=first.probe_capability or "",
        now=_NOW,
    ).valid
    assert (
        validate_active_half_open_probe(
            breaker,
            claim_capability="opaque-not-the-winner",
            now=_NOW,
        ).valid
        is False
    )


def test_expired_half_open_lease_can_be_reclaimed() -> None:
    service, executions, reliability, auth, plan, request = _prepare_memory()
    other_auth, other_plan = _plan_for(
        {"proposal_id": "proposal-reclaim-b", "authorization_id": "authorization-reclaim-b"},
        request.registry,
        request.certifications,
        request.routing,
    )
    _bind(executions, other_auth, other_plan)
    assert service.conversations is not None
    _add_authorization(service.conversations, other_auth)
    _open_then_half_open(reliability, now=_NOW)
    first = service.claim(request)
    assert first.half_open_probe_lease_acquired is True
    expired_at = _NOW + HALF_OPEN_PROBE_LEASE
    held = reliability.load(_PROVIDER, _MARKET, now=expired_at)
    assert (
        validate_active_half_open_probe(
            held,
            claim_capability=first.probe_capability or "",
            now=expired_at,
        ).valid
        is False
    )
    second = service.claim(
        _request(
            other_auth,
            other_plan,
            request.registry,
            request.certifications,
            request.routing,
            request.certified_markets,
            now=expired_at,
        )
    )
    assert second.claimed is True
    assert second.half_open_probe_lease_acquired is True
    current = reliability.load(_PROVIDER, _MARKET, now=expired_at)
    old = validate_active_half_open_probe(
        current,
        claim_capability=first.probe_capability or "",
        now=expired_at,
    )
    new = validate_active_half_open_probe(
        current,
        claim_capability=second.probe_capability or "",
        now=expired_at,
    )
    assert old.valid is False
    assert new.valid is True
    loser = executions.get(request_execution_id(auth))
    winner = executions.get(request_execution_id(other_auth))
    assert loser is not None and loser.state == "claimed_for_attempt"
    assert winner is not None and winner.state == "claimed_for_attempt"
    assert loser.claim_digest != winner.claim_digest


def test_closed_breaker_does_not_require_a_probe_lease() -> None:
    service, executions, reliability, _auth, _plan, request = _prepare_memory()
    closed = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    reliability.save(closed, expected_revision=0)
    result = service.claim(request)
    stored_breaker = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    assert result.claimed is True
    assert result.half_open_probe_lease_acquired is False
    assert stored_breaker.state.value == "closed"
    assert stored_breaker.half_open_probe_claim_digest is None
    assert stored_breaker.revision == 1
    assert stored_breaker.last_success_at is None
    assert stored_breaker.last_attempt_at is None
    execution = executions.get(result.execution_id or "")
    assert execution is not None and execution.state == "claimed_for_attempt"


def test_kill_switch_disabled_routing_market_capability_and_source_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.research.reliability_state.record_success",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record_success")),
    )
    monkeypatch.setattr(
        "app.research.reliability_state.record_failure",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("record_failure")),
    )
    killed = _provider(kill_switch=KillSwitch(engaged=True, reason="stop"))
    assert _blocked_reason(killed, kill_switch=KillSwitch(engaged=True)) == "kill_switch"
    disabled = _provider(operational_status=ConnectorOperationalStatus.DISABLED)
    assert _blocked_reason(disabled, operational_status=ConnectorOperationalStatus.DISABLED) == (
        "provider_disabled"
    )
    assert _blocked_reason(_provider(), routing=False) == "routing_absent"
    assert _blocked_reason(_provider(), markets=()) == "market_not_eligible"
    narrow = _provider(capabilities=(ResearchCapability.PRODUCT_DISCOVERY,))
    _provider_obj, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    service, executions, _reliability = _memory_service()
    _bind(executions, auth, plan)
    capability = service.claim(
        _request(
            auth,
            plan,
            ResearchProviderRegistry((narrow,), allow_test_providers=True),
            catalog,
            routing,
            markets,
            provider_id=narrow.provider_id,
        )
    )
    assert capability.block_reason == "provider_capability_not_supported"
    sourced = _provider(sources=("other-source",))
    source = service.claim(
        _request(
            auth,
            plan,
            ResearchProviderRegistry((sourced,), allow_test_providers=True),
            catalog,
            routing,
            markets,
            provider_id=sourced.provider_id,
        )
    )
    assert source.block_reason == "source_not_supported"
    stored = executions.get(request_execution_id(auth))
    assert stored is not None
    assert stored.state == "prepared_unavailable"


def test_fixture_cannot_claim_a_live_start() -> None:
    fixture = _provider(test_fixture=True)
    reason = _blocked_reason(fixture, cert_fixture=True, mode="live")
    assert reason == "fixture_cannot_satisfy_live_gate"


def test_persistence_failure_rolls_back_the_execution_and_the_probe(sqlite_factory) -> None:
    _provider_obj, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    before = _save_half_open(sqlite_factory, now=_NOW)
    real = OperationalStore.compare_and_swap

    def _fail_reliability(self, store: str, *args: object, **kwargs: object) -> bool:
        if store == RESEARCH_PROVIDER_RELIABILITY:
            raise OperationalError("UPDATE", {}, Exception("database unavailable"))
        return real(self, store, *args, **kwargs)

    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(OperationalStore, "compare_and_swap", _fail_reliability)
    try:
        result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    finally:
        monkeypatch.undo()
    assert result.claimed is False
    assert result.block_reason == "claim_persistence_unavailable"
    assert result.half_open_probe_lease_acquired is False
    stored = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory).get(
        request_execution_id(auth)
    )
    with sqlite_factory() as session:
        breaker = OperationalResearchReliabilityRepository(session).load(
            _PROVIDER,
            _MARKET,
            now=_NOW,
        )
    assert stored is not None
    assert stored.state == "prepared_unavailable"
    assert stored.claim_digest is None
    assert stored.revision == 1
    assert breaker.revision == before.revision
    assert breaker.half_open_probe_claim_digest is None
    assert breaker.last_success_at is None


def test_in_memory_persistence_failure_leaves_no_partial_claim() -> None:
    service, executions, reliability, auth, _plan, request = _prepare_memory()
    _open_then_half_open(reliability, now=_NOW)
    before = reliability.load(_PROVIDER, _MARKET, now=_NOW)

    def _down(state: object, *, expected_revision: int) -> None:
        del state, expected_revision
        raise PersistenceUnavailableError("reliability store unavailable")

    reliability.save = _down  # type: ignore[method-assign]
    result = service.claim(request)
    assert result.block_reason == "claim_persistence_unavailable"
    stored = executions.get(request_execution_id(auth))
    current = reliability.load(_PROVIDER, _MARKET, now=_NOW)
    assert stored is not None and stored.state == "prepared_unavailable"
    assert current.revision == before.revision
    assert current.half_open_probe_claim_digest is None


def test_current_shopify_production_state_cannot_claim(sqlite_factory) -> None:
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
    repo = OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory)
    _bind(repo, auth, production_plan)
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
    stored = repo.get(request_execution_id(auth))
    with sqlite_factory() as session:
        count = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_PROVIDER_RELIABILITY
            )
        )
        execution_row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS,
                OperationalEntityModel.entity_id == request_execution_id(auth),
            )
        )
    assert result.claimed is False
    assert result.block_reason == "mode_not_live"
    assert result.half_open_probe_lease_acquired is False
    assert result.connector_invoked is False
    assert result.http_invoked is False
    assert result.live_execution_started is False
    assert result.authorization_consumed is False
    assert auth.status == "authorized_pending_execution"
    assert stored is not None
    assert stored.state == "prepared_unavailable"
    assert count is None
    assert execution_row is not None
    payload = json.dumps(execution_row.payload)
    assert "claimed_for_attempt" not in payload
    assert provider.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    with pytest.raises(NotImplementedError):
        StaticResearchProvider.execute(provider, step)  # type: ignore[arg-type]
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SPRINT_41_STATUS == "UNSTARTED"


def test_sqlite_claim_stores_only_the_digest(sqlite_factory) -> None:
    _provider_obj, registry, catalog, routing, markets = _world()
    auth, plan = _plan_for(None, registry, catalog, routing)
    _bind(OperationalAuthorizedExecutionRepository(session_factory=sqlite_factory), auth, plan)
    _seed_sqlite_conversation(sqlite_factory, auth)
    service = operational_live_start_claims(sqlite_factory, token_factory=_token_factory())
    result = service.claim(_request(auth, plan, registry, catalog, routing, markets))
    with sqlite_factory() as session:
        row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS
            )
        )
    assert row is not None
    payload = json.dumps(row.payload)
    assert result.claim_capability
    assert result.claim_capability not in payload
    assert "token" not in payload.lower()
    assert row.payload["fields"]["claim_digest"] == execution_claim_digest(result.claim_capability)
    with sqlite_factory() as session:
        conversation = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == SHOPPING_CONVERSATIONS
            )
        )
    assert conversation is not None
    conversation_payload = json.dumps(conversation.payload)
    assert result.claim_capability not in conversation_payload
    assert "claim_capability" not in conversation_payload
    assert "probe_capability" not in conversation_payload


def _blocked_reason(
    provider: StaticResearchProvider,
    *,
    routing: bool = True,
    markets: tuple[str, ...] = (_MARKET,),
    cert_fixture: bool = False,
    mode: str = "live",
    operational_status: ConnectorOperationalStatus | None = None,
    kill_switch: KillSwitch | None = None,
) -> str:
    """Plan an eligible step, then claim under the altered gate inputs."""

    _eligible, registry, catalog, routing_catalog, _certified = _world()
    auth, plan = _plan_for(None, registry, catalog, routing_catalog)
    claim_registry = ResearchProviderRegistry((provider,), allow_test_providers=True)
    claim_catalog = catalog
    if cert_fixture or provider.descriptor.test_fixture:
        _fixture, claim_registry, claim_catalog, _routing, _markets = _world(
            provider,
            cert_fixture=True,
        )
    claim_routing = routing_catalog
    if not routing:
        claim_routing = ResearchProviderRoutingPolicyCatalog((), allow_test_policies=True)
    service, executions, _reliability = _memory_service()
    _bind(executions, auth, plan)
    result = service.claim(
        _request(
            auth,
            plan,
            claim_registry,
            claim_catalog,
            claim_routing,
            shopping_markets_for_tests(markets),
            provider_id=provider.provider_id,
            operational_status=operational_status or provider.descriptor.operational_status,
            kill_switch=kill_switch or provider.descriptor.kill_switch,
            mode=mode,
        )
    )
    assert result.block_reason
    stored = executions.get(request_execution_id(auth))
    assert stored is not None and stored.state == "prepared_unavailable"
    return result.block_reason


def _open_then_half_open(reliability: InMemoryResearchReliabilityRepository, *, now: datetime):
    gate = ResearchReliabilityGate(
        reliability,
        policy=BreakerPolicy(failure_threshold=1, recovery_window_ms=1_000),
    )
    opened = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=now)
    opened_at = now + timedelta(milliseconds=1_000)
    advanced = advance_recovery(opened, now=opened_at)
    return reliability.save(advanced, expected_revision=opened.revision)


def _save_half_open(factory, *, now: datetime):
    session = factory()
    repository = OperationalResearchReliabilityRepository(session)
    gate = ResearchReliabilityGate(
        repository,
        policy=BreakerPolicy(failure_threshold=1, recovery_window_ms=1_000),
    )
    opened = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=now)
    advanced = advance_recovery(opened, now=now + timedelta(milliseconds=1_000))
    stored = repository.save(advanced, expected_revision=opened.revision)
    session.commit()
    session.close()
    return stored


def request_execution_id(auth) -> str:
    from app.services.research_execution import authorized_execution_id

    return authorized_execution_id(auth.idempotency_key)
