"""Sprint 38 production reliability state. No connector calls and no network."""

from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerState,
    ConnectorFailureKind,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import RESEARCH_PROVIDER_RELIABILITY
from app.research.providers import StaticResearchProvider
from app.research.reliability_repository import (
    InMemoryResearchReliabilityRepository,
    OperationalResearchReliabilityRepository,
    ReliabilityRevisionConflict,
    ResearchReliabilityGate,
    production_reliability_repository,
)
from app.research.reliability_state import (
    BREAKER_AFFECTING_FAILURES,
    BREAKER_NEUTRAL_FAILURES,
    BreakerPolicy,
    ProviderReliabilityState,
    advance_recovery,
    aggregate_research_provider_health,
    build_research_provider_health,
    closed_reliability_state,
    failure_affects_breaker,
    production_research_provider_health,
    reliability_record_key,
)
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.shopify_global_catalog_provider import (
    SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
    shopify_global_catalog_ph_provider,
)
from app.research.sprint38_live_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    PRODUCTION_BREAKER_PERSISTED,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
    production_live_mode_assessment,
    shopify_retry_policy,
)
from app.services.launch_health_service import LaunchHealthService
from app.services.research_execution import AuthorizedExecutionLedger
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

_PROVIDER = "ph-reliability-fixture"
_MARKET = "PH"
_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


class _Clock:
    def __init__(self) -> None:
        self.now = _NOW

    def advance(self, milliseconds: int) -> datetime:
        self.now += timedelta(milliseconds=milliseconds)
        return self.now


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("reliability tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'reliability.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _gate(
    repository: InMemoryResearchReliabilityRepository | None = None,
    *,
    policy: BreakerPolicy | None = None,
) -> ResearchReliabilityGate:
    repo = repository or InMemoryResearchReliabilityRepository()
    return ResearchReliabilityGate(repo, policy=policy)


def _open(gate: ResearchReliabilityGate, clock: _Clock) -> ProviderReliabilityState:
    state = gate.load(_PROVIDER, _MARKET, now=clock.now)
    assert state.state is CircuitBreakerState.CLOSED
    for _ in range(gate.policy.failure_threshold):
        clock.advance(1)
        state = gate.record_failure(
            _PROVIDER,
            _MARKET,
            ConnectorFailureKind.TIMEOUT,
            now=clock.now,
        )
    return state


def _health_for(
    state: ProviderReliabilityState,
    *,
    status: ConnectorOperationalStatus = ConnectorOperationalStatus.DISABLED,
    kill_switch: bool = False,
    routing_present: bool = False,
    certification_present: bool = True,
    test_fixture: bool = False,
):
    return build_research_provider_health(
        provider_id=state.provider_id,
        market=state.market,
        operational_status=status,
        kill_switch_engaged=kill_switch,
        breaker=state,
        routing_present=routing_present,
        certification_present=certification_present,
        test_fixture=test_fixture,
    )


def test_breaker_is_closed_by_default() -> None:
    state = closed_reliability_state(_PROVIDER, _MARKET, now=_NOW)
    assert state.state is CircuitBreakerState.CLOSED
    assert state.consecutive_failure_count == 0
    assert state.revision == 0
    assert state.opened_at is None
    loaded = InMemoryResearchReliabilityRepository().load(_PROVIDER, _MARKET, now=_NOW)
    assert loaded.state is CircuitBreakerState.CLOSED
    assert loaded.revision == 0


def test_breaker_opens_at_configured_threshold() -> None:
    policy = BreakerPolicy()
    assert policy.failure_threshold == 3
    gate = _gate(policy=policy)
    clock = _Clock()
    below = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.UNAVAILABLE, now=clock.now)
    clock.advance(1)
    below = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.UNKNOWN, now=clock.now)
    assert below.state is CircuitBreakerState.CLOSED
    assert below.consecutive_failure_count == 2
    clock.advance(1)
    opened = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=clock.now)
    assert opened.state is CircuitBreakerState.OPEN
    assert opened.consecutive_failure_count == 3
    assert opened.opened_at == clock.now
    assert opened.reopen_at == clock.now + timedelta(milliseconds=policy.recovery_window_ms)
    assert opened.last_failure_category is ConnectorFailureKind.TIMEOUT


def test_open_breaker_blocks_execution() -> None:
    gate = _gate()
    clock = _Clock()
    _open(gate, clock)
    decision = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=clock.now,
    )
    assert decision.execution_permitted is False
    assert decision.block_reason == "circuit_open"
    assert decision.connector_invoked is False
    assert decision.http_invoked is False
    assert decision.live_execution_started is False
    assert decision.breaker.state is CircuitBreakerState.OPEN


def test_open_breaker_survives_service_and_repository_recreation(sqlite_factory) -> None:
    memory = InMemoryResearchReliabilityRepository()
    clock = _Clock()
    opened = _open(_gate(memory), clock)
    assert opened.state is CircuitBreakerState.OPEN
    recreated = ResearchReliabilityGate(memory).load(_PROVIDER, _MARKET, now=clock.now)
    assert recreated.state is CircuitBreakerState.OPEN
    assert recreated.revision == opened.revision

    session = sqlite_factory()
    repository = production_reliability_repository(session)
    persisted = _open(ResearchReliabilityGate(repository), clock)
    session.commit()
    session.close()

    reloaded = production_reliability_repository(sqlite_factory()).load(
        _PROVIDER,
        _MARKET,
        now=clock.now,
    )
    assert reloaded.state is CircuitBreakerState.OPEN
    assert reloaded.revision == persisted.revision
    assert reloaded.opened_at == persisted.opened_at

    engine = sqlite_factory.kw["bind"]
    engine.dispose()
    restarted = create_engine(engine.url, future=True)
    restarted_factory = sessionmaker(bind=restarted, autoflush=False, autocommit=False)
    try:
        survived = OperationalResearchReliabilityRepository(restarted_factory()).load(
            _PROVIDER,
            _MARKET,
            now=clock.now,
        )
    finally:
        restarted.dispose()
    assert survived.state is CircuitBreakerState.OPEN
    assert survived.consecutive_failure_count == persisted.consecutive_failure_count


def test_half_open_follows_recovery_rule() -> None:
    policy = BreakerPolicy()
    gate = _gate(policy=policy)
    clock = _Clock()
    opened = _open(gate, clock)
    assert opened.reopen_at is not None
    still_open = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=opened.reopen_at - timedelta(milliseconds=1),
    )
    assert still_open.block_reason == "circuit_open"
    assert still_open.breaker.state is CircuitBreakerState.OPEN
    probed = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=opened.reopen_at,
    )
    assert probed.breaker.state is CircuitBreakerState.HALF_OPEN
    assert probed.execution_permitted is True
    assert probed.connector_invoked is False
    assert probed.live_execution_started is False
    loaded = gate.load(_PROVIDER, _MARKET, now=opened.reopen_at)
    assert loaded.state is CircuitBreakerState.HALF_OPEN
    direct = advance_recovery(opened, now=opened.reopen_at)
    assert direct.state is CircuitBreakerState.HALF_OPEN


def test_half_open_success_closes_and_resets() -> None:
    gate = _gate()
    clock = _Clock()
    opened = _open(gate, clock)
    assert opened.reopen_at is not None
    gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=opened.reopen_at,
    )
    clock.now = opened.reopen_at + timedelta(milliseconds=5)
    closed = gate.record_success(_PROVIDER, _MARKET, now=clock.now)
    assert closed.state is CircuitBreakerState.CLOSED
    assert closed.consecutive_failure_count == 0
    assert closed.opened_at is None
    assert closed.reopen_at is None
    assert closed.last_success_at == clock.now
    assert (
        ResearchReliabilityGate(gate.repository)
        .load(
            _PROVIDER,
            _MARKET,
            now=clock.now,
        )
        .consecutive_failure_count
        == 0
    )


def test_half_open_failure_reopens() -> None:
    gate = _gate()
    clock = _Clock()
    opened = _open(gate, clock)
    assert opened.reopen_at is not None
    gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=opened.reopen_at,
    )
    clock.now = opened.reopen_at + timedelta(milliseconds=5)
    reopened = gate.record_failure(
        _PROVIDER,
        _MARKET,
        ConnectorFailureKind.UNAVAILABLE,
        now=clock.now,
    )
    assert reopened.state is CircuitBreakerState.OPEN
    assert reopened.consecutive_failure_count == opened.consecutive_failure_count + 1
    assert reopened.last_failure_category is ConnectorFailureKind.UNAVAILABLE
    decision = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=clock.now,
    )
    assert decision.block_reason == "circuit_open"
    assert decision.connector_invoked is False


def test_kill_switch_overrides_closed_breaker() -> None:
    gate = _gate()
    decision = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(engaged=True, reason="operator"),
        now=_NOW,
    )
    assert decision.execution_permitted is False
    assert decision.block_reason == "kill_switch"
    assert decision.breaker.state is CircuitBreakerState.CLOSED
    assert decision.connector_invoked is False
    both = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.DISABLED,
        kill_switch=KillSwitch(engaged=True),
        now=_NOW,
    )
    assert both.block_reason == "kill_switch"
    released = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.DISABLED,
        kill_switch=KillSwitch(engaged=False),
        now=_NOW,
    )
    assert released.block_reason == "provider_disabled"
    assert released.execution_permitted is False
    assert released.live_execution_started is False


def test_disabled_provider_overrides_closed_breaker() -> None:
    gate = _gate()
    decision = gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.DISABLED,
        kill_switch=KillSwitch(),
        now=_NOW,
    )
    assert decision.breaker.state is CircuitBreakerState.CLOSED
    assert decision.block_reason == "provider_disabled"
    assert decision.execution_permitted is False
    assert decision.connector_invoked is False
    health = _health_for(decision.breaker, status=ConnectorOperationalStatus.DISABLED)
    assert health.certified is True
    assert health.operationally_available is False
    assert health.healthy is False
    assert health.merchant_available is False
    assert health.live is False


def test_certification_does_not_imply_availability() -> None:
    state = closed_reliability_state(SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID, "PH", now=_NOW)
    health = _health_for(state, certification_present=True)
    assert health.certified is True
    assert health.certification_present is True
    assert health.operationally_available is False
    assert health.healthy is False
    assert health.merchant_available is False
    closed_only = _health_for(
        state,
        status=ConnectorOperationalStatus.DISABLED,
        certification_present=False,
    )
    assert closed_only.breaker_state == "closed"
    assert closed_only.merchant_available is False


def test_routing_absence_keeps_live_unavailable() -> None:
    report = production_research_provider_health(now=_NOW)
    assert report.rows[0].routing_present is False
    assert "routing_absent" in report.rows[0].live_block_reasons
    assert report.rows[0].live is False
    assert report.live is False
    available = _health_for(
        closed_reliability_state("future-provider", "PH", now=_NOW),
        status=ConnectorOperationalStatus.AVAILABLE,
        routing_present=False,
        certification_present=True,
    )
    assert available.merchant_available is True
    assert available.live is False
    assert "routing_absent" in available.live_block_reasons
    assert production_live_mode_assessment().enabled is False


def test_ready_stays_true_while_merchant_availability_is_false() -> None:
    ready = LaunchHealthService().ready()
    assert ready["ready"] is True
    assert "merchant" not in ready
    report = production_research_provider_health(now=_NOW)
    assert report.merchant_available is False
    assert report.live is False
    disabled = aggregate_research_provider_health(
        (
            _health_for(
                closed_reliability_state(_PROVIDER, _MARKET, now=_NOW),
                status=ConnectorOperationalStatus.DISABLED,
            ),
        )
    )
    assert disabled.merchant_available is False
    assert LaunchHealthService().ready()["ready"] is True


def test_failure_categories_are_mapped_from_sprint31() -> None:
    assert {
        ConnectorFailureKind.TIMEOUT,
        ConnectorFailureKind.UNAVAILABLE,
        ConnectorFailureKind.UNKNOWN,
    } == BREAKER_AFFECTING_FAILURES
    assert {
        ConnectorFailureKind.RATE_LIMIT,
        ConnectorFailureKind.QUOTA,
        ConnectorFailureKind.CREDENTIAL,
        ConnectorFailureKind.KILL_SWITCH,
        ConnectorFailureKind.CIRCUIT_OPEN,
        ConnectorFailureKind.PARTIAL,
    } == BREAKER_NEUTRAL_FAILURES
    assert set(ConnectorFailureKind) == BREAKER_AFFECTING_FAILURES | BREAKER_NEUTRAL_FAILURES
    for kind in ConnectorFailureKind:
        assert failure_affects_breaker(kind) is (kind in BREAKER_AFFECTING_FAILURES)


def test_rate_limit_and_quota_follow_shopify_policy() -> None:
    policy = shopify_retry_policy()
    assert policy.max_attempts == 1
    assert policy.retry_on == ()
    assert ConnectorFailureKind.RATE_LIMIT.value not in policy.retry_on
    assert ConnectorFailureKind.QUOTA.value not in policy.retry_on
    assert ConnectorFailureKind.CREDENTIAL.value not in policy.retry_on
    assert ConnectorFailureKind.TIMEOUT.value not in policy.retry_on
    gate = _gate()
    clock = _Clock()
    for kind in (
        ConnectorFailureKind.RATE_LIMIT,
        ConnectorFailureKind.QUOTA,
        ConnectorFailureKind.CREDENTIAL,
    ):
        clock.advance(1)
        state = gate.record_failure(_PROVIDER, _MARKET, kind, now=clock.now)
        assert state.state is CircuitBreakerState.CLOSED
        assert state.consecutive_failure_count == 0
        assert state.last_failure_category is kind
    clock.advance(1)
    counted = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=clock.now)
    clock.advance(1)
    counted = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.TIMEOUT, now=clock.now)
    clock.advance(1)
    held = gate.record_failure(_PROVIDER, _MARKET, ConnectorFailureKind.RATE_LIMIT, now=clock.now)
    assert held.state is CircuitBreakerState.CLOSED
    assert held.consecutive_failure_count == counted.consecutive_failure_count == 2
    opened = _open_from(gate, clock, ConnectorFailureKind.TIMEOUT)
    assert opened.reopen_at is not None
    gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=KillSwitch(),
        now=opened.reopen_at,
    )
    neutral = gate.record_failure(
        _PROVIDER,
        _MARKET,
        ConnectorFailureKind.QUOTA,
        now=opened.reopen_at + timedelta(milliseconds=1),
    )
    assert neutral.state is CircuitBreakerState.HALF_OPEN
    assert neutral.consecutive_failure_count == opened.consecutive_failure_count


def _open_from(
    gate: ResearchReliabilityGate,
    clock: _Clock,
    kind: ConnectorFailureKind,
) -> ProviderReliabilityState:
    state = gate.load(_PROVIDER, _MARKET, now=clock.now)
    while state.consecutive_failure_count < gate.policy.failure_threshold:
        clock.advance(1)
        state = gate.record_failure(_PROVIDER, _MARKET, kind, now=clock.now)
    assert state.state is CircuitBreakerState.OPEN
    return state


def test_stale_revision_does_not_overwrite(sqlite_factory) -> None:
    repository = InMemoryResearchReliabilityRepository()
    clock = _Clock()
    first = repository.save(
        closed_reliability_state(_PROVIDER, _MARKET, now=clock.now),
        expected_revision=0,
    )
    winner = repository.save(first, expected_revision=first.revision)
    with pytest.raises(ReliabilityRevisionConflict):
        repository.save(first, expected_revision=first.revision)
    assert repository.load(_PROVIDER, _MARKET, now=clock.now) == winner
    assert repository.row_count(_PROVIDER, _MARKET) == 1

    session = sqlite_factory()
    durable = OperationalResearchReliabilityRepository(session)
    inserted = durable.save(
        closed_reliability_state(_PROVIDER, _MARKET, now=clock.now),
        expected_revision=0,
    )
    current = durable.save(inserted, expected_revision=inserted.revision)
    with pytest.raises(ReliabilityRevisionConflict):
        durable.save(inserted, expected_revision=inserted.revision)
    session.commit()
    assert durable.load(_PROVIDER, _MARKET, now=clock.now) == current
    key = reliability_record_key(_PROVIDER, _MARKET)
    count = session.scalar(
        select(func.count())
        .select_from(OperationalEntityModel)
        .where(
            OperationalEntityModel.store == RESEARCH_PROVIDER_RELIABILITY,
            OperationalEntityModel.entity_id == key,
        )
    )
    assert count == 1
    assert (
        session.scalar(
            select(OperationalEntityModel.owner_id).where(
                OperationalEntityModel.store == RESEARCH_PROVIDER_RELIABILITY,
                OperationalEntityModel.entity_id == key,
            )
        )
        is None
    )


def test_no_connector_or_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"execute": 0}

    def _execute(self: StaticResearchProvider, step: object) -> None:
        del self, step
        calls["execute"] += 1
        raise AssertionError("connector execute is forbidden")

    monkeypatch.setattr(StaticResearchProvider, "execute", _execute)
    gate = _gate()
    clock = _Clock()
    _open(gate, clock)
    gate.permission(
        _PROVIDER,
        _MARKET,
        operational_status=ConnectorOperationalStatus.DISABLED,
        kill_switch=KillSwitch(engaged=True),
        now=clock.now,
    )
    production_research_provider_health(now=clock.now)
    assert calls["execute"] == 0
    assert SHOPIFY_LIVE_CALL_PERMITTED is False


def test_fixture_state_is_not_production_persisted_evidence() -> None:
    assert PRODUCTION_BREAKER_PERSISTED is True
    assert InMemoryResearchReliabilityRepository.persists_across_process_restart is False
    assert OperationalResearchReliabilityRepository.persists_across_process_restart is True
    clock = _Clock()
    memory = InMemoryResearchReliabilityRepository()
    _open(_gate(memory), clock)
    assert (
        InMemoryResearchReliabilityRepository()
        .load(
            _PROVIDER,
            _MARKET,
            now=clock.now,
        )
        .state
        is CircuitBreakerState.CLOSED
    )
    names = {field.name for field in ProviderReliabilityState.__dataclass_fields__.values()}
    assert names.isdisjoint(
        {
            "secret",
            "token",
            "password",
            "principal_id",
            "credential",
            "browser_confirmation_token",
            "raw_response",
        }
    )


def test_shopify_production_status_stays_disabled() -> None:
    report = production_research_provider_health(now=_NOW)
    row = report.rows[0]
    assert row.provider_id == SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID
    assert row.operational_status == "disabled"
    assert row.certified is True
    assert row.operationally_available is False
    assert row.healthy is False
    assert row.merchant_available is False
    assert row.live is False
    assert row.breaker_state == "closed"
    assert row.breaker_revision == 0
    assert report.merchant_available is False
    with pytest.raises(NotImplementedError):
        shopify_global_catalog_ph_provider().execute(None)  # type: ignore[arg-type]
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SPRINT_41_STATUS == "UNSTARTED"


def test_one_connector_aggregate_stays_unavailable() -> None:
    report = production_research_provider_health(now=_NOW)
    assert len(report.rows) == 1
    assert report.merchant_available is False
    assert report.live_evidence is False
    opened = _open(_gate(), _Clock())
    killed = _health_for(
        closed_reliability_state("one-killed", "PH", now=_NOW),
        status=ConnectorOperationalStatus.AVAILABLE,
        kill_switch=True,
        routing_present=True,
        certification_present=True,
    )
    open_row = _health_for(
        opened,
        status=ConnectorOperationalStatus.AVAILABLE,
        routing_present=True,
        certification_present=True,
    )
    certified_only = _health_for(
        closed_reliability_state("one-certified", "PH", now=_NOW),
        status=ConnectorOperationalStatus.DISABLED,
        certification_present=True,
    )
    for row in (killed, open_row, certified_only):
        aggregate = aggregate_research_provider_health((row,))
        assert aggregate.merchant_available is False
        assert aggregate.live is False
        assert aggregate.live_evidence is False


def test_multi_provider_aggregation_is_not_live_evidence() -> None:
    available = _health_for(
        closed_reliability_state("future-a", "PH", now=_NOW),
        status=ConnectorOperationalStatus.AVAILABLE,
        routing_present=True,
        certification_present=True,
    )
    disabled = _health_for(
        closed_reliability_state("future-b", "PH", now=_NOW),
        status=ConnectorOperationalStatus.DISABLED,
        certification_present=True,
    )
    report = aggregate_research_provider_health((available, disabled))
    assert available.merchant_available is True
    assert available.healthy is True
    assert available.live is False
    assert report.merchant_available is True
    assert report.live is False
    assert report.live_evidence is False
    assert len(report.rows) == 2
    production = production_research_provider_health(now=_NOW)
    assert len(production.rows) == 1
    assert production.merchant_available is False
    assert production.live_evidence is False


def test_durable_authorized_execution_persistence_is_deferred() -> None:
    first = AuthorizedExecutionLedger()
    binding = first.bind(
        authorization_idempotency_key="research-auth:deferred",
        decision_id="decision-1",
        plan_id="plan-1",
    )
    assert binding.execution_id
    assert AuthorizedExecutionLedger().get("research-auth:deferred") is None
    assert getattr(first, "persists_across_process_restart", False) is False


def test_success_does_not_close_an_open_breaker() -> None:
    gate = _gate()
    clock = _Clock()
    opened = _open(gate, clock)
    clock.advance(1)
    unchanged = gate.record_success(_PROVIDER, _MARKET, now=clock.now)
    assert unchanged.state is CircuitBreakerState.OPEN
    assert unchanged.revision == opened.revision
    assert unchanged.last_success_at is None
