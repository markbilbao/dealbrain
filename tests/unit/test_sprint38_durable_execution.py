"""Sprint 38 durable authorized-execution preparation. No connector calls."""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.core.dependencies import get_shopping_decision_snapshot_repository
from app.domain.entities.connector_reliability import ConnectorOperationalStatus
from app.domain.exceptions import ShoppingAssistantNotFoundError
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.persistence.errors import PersistenceUnavailableError
from app.infrastructure.persistence.operational_store import OperationalStore
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import RESEARCH_AUTHORIZED_EXECUTIONS
from app.main import create_app
from app.market.support import production_certified_shopping_markets
from app.research.authorized_execution_repository import (
    DURABLE_LIVE_START_CLAIM_IMPLEMENTED,
    EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION,
    FUTURE_LIVE_START_CLAIM,
    FUTURE_LIVE_START_PHASES,
    HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED,
    AuthorizedExecutionRevisionConflict,
    DurableAuthorizedExecution,
    InMemoryAuthorizedExecutionRepository,
    OperationalAuthorizedExecutionRepository,
    production_authorized_execution_repository,
)
from app.research.providers import StaticResearchProvider
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import SPRINT_41_STATUS
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider
from app.research.sprint38_live_execution import (
    DESTINATION_REEVALUATION_IMPLEMENTED,
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SHOPPING_RESEARCH_EXECUTION_MODE,
)
from app.services.research_authorization import mark_research_authorization_consumed
from app.services.research_execution import (
    AuthorizedExecutionLedger,
    authorized_execution_id,
    execute_research_plan,
)
from app.services.shopping_assistant_service import ShoppingAssistantService
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    SONY_ID,
    START,
    _owner,
    _presentation,
)
from tests.unit.test_sprint31_research_execution_router import (
    _authorization,
    _plan,
    _provider,
    _registry,
)

_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("durable execution tests must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture()
def sqlite_factory(tmp_path):
    reset_sync_engine()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'executions.db'}",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _repo(factory) -> OperationalAuthorizedExecutionRepository:
    return OperationalAuthorizedExecutionRepository(session_factory=factory)


def _prepared(auth=None, *, registry=None):
    authorization = auth or _authorization()
    kwargs = {} if registry is None else {"registry": registry}
    planned = _plan(authorization, **kwargs)
    assert planned.plan is not None
    return authorization, planned.plan


def _execute(plan, auth, repo, **extra):
    payload = {
        "authorization": auth,
        "owner": extra.pop("owner", _owner()),
        "conversation_id": extra.pop("conversation_id", auth.conversation_id),
        "decision_id": extra.pop("decision_id", auth.decision_id),
        "canonical_context_version": extra.pop(
            "canonical_context_version", auth.canonical_context_version
        ),
        "ledger": repo,
        "now": extra.pop("now", _NOW),
    }
    payload.update(extra)
    return execute_research_plan(plan, **payload)


def _bind(repo, auth, plan, *, now=_NOW):
    return repo.bind(
        authorization_idempotency_key=auth.idempotency_key,
        authorization_id=auth.authorization_id,
        authorization_version=auth.authorization_version,
        decision_id=auth.decision_id,
        plan_id=plan.plan_id,
        now=now,
    )


def test_same_authorization_and_plan_creates_one_durable_execution(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    first = _execute(plan, auth, repo)
    second = _execute(plan, auth, repo)
    assert first.outcome == "prepared_but_live_unavailable"
    assert first.execution_id == authorized_execution_id(auth.idempotency_key)
    assert second.execution_id == first.execution_id
    assert first.plan_id == plan.plan_id
    assert repo.row_count() == 1
    stored = repo.get(first.execution_id or "")
    assert stored is not None
    assert stored.state == "prepared_unavailable"
    assert stored.revision == 1
    assert stored.authorization_id == auth.authorization_id
    assert stored.authorization_version == auth.authorization_version
    assert stored.decision_id == auth.decision_id
    assert auth.status == "authorized_pending_execution"


def test_new_repository_and_session_load_the_same_execution(sqlite_factory) -> None:
    auth, plan = _prepared()
    first_repo = _repo(sqlite_factory)
    prepared = _execute(plan, auth, first_repo)
    assert prepared.execution_id is not None
    reloaded = _execute(plan, auth, _repo(sqlite_factory))
    assert reloaded.execution_id == prepared.execution_id
    with sqlite_factory() as session:
        session.commit()
        reopened = OperationalAuthorizedExecutionRepository(session=session)
        loaded = reopened.get(prepared.execution_id)
    assert loaded is not None
    assert loaded.execution_id == prepared.execution_id
    assert loaded.plan_id == plan.plan_id
    assert _repo(sqlite_factory).row_count() == 1


def test_same_authorization_and_different_plan_conflicts_without_rewrite(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    prepared = _execute(plan, auth, repo)
    other = _plan(auth, registry=_registry(_provider("plan-pin-other"))).plan
    assert other is not None
    assert other.plan_id != plan.plan_id
    conflict = _execute(other, auth, repo)
    assert conflict.reason == "authorization_plan_conflict"
    assert conflict.execution_id is None
    assert conflict.connectors_invoked is False
    stored = repo.get(prepared.execution_id or "")
    assert stored is not None
    assert stored.plan_id == plan.plan_id
    assert stored.revision == 1
    assert repo.row_count() == 1
    assert auth.status == "authorized_pending_execution"


def test_different_authorization_gets_a_different_execution_id(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    first_auth, first_plan = _prepared()
    second_auth, second_plan = _prepared(
        _authorization(proposal_id="proposal-other", authorization_id="authorization-other")
    )
    first = _execute(first_plan, first_auth, repo)
    second = _execute(second_plan, second_auth, repo)
    assert first.execution_id != second.execution_id
    assert repo.row_count() == 2


def test_duplicate_first_insert_reloads_one_record(sqlite_factory, monkeypatch) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    original = _bind(repo, auth, plan)
    calls = {"n": 0}
    real_load = __import__(
        "app.research.authorized_execution_repository",
        fromlist=["_load"],
    )._load

    def _miss_once(ops, execution_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real_load(ops, execution_id)

    monkeypatch.setattr("app.research.authorized_execution_repository._load", _miss_once)
    raced = _bind(repo, auth, plan)
    assert raced.execution_id == original.execution_id
    assert raced.plan_id == original.plan_id
    assert repo.row_count() == 1


def test_concurrent_binds_create_one_row(sqlite_factory) -> None:
    auth, plan = _prepared()
    barrier = threading.Barrier(2)
    found: list[str] = []
    errors: list[BaseException] = []

    def _worker() -> None:
        try:
            barrier.wait(timeout=5)
            record = _bind(_repo(sqlite_factory), auth, plan)
            found.append(record.execution_id)
        except BaseException as exc:  # noqa: BLE001 — collect worker failures
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert errors == []
    assert found == [found[0], found[0]]
    assert _repo(sqlite_factory).row_count() == 1


def test_stale_revision_does_not_overwrite(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    stored = _bind(repo, auth, plan)
    newer = repo.save(stored, expected_revision=1)
    assert newer.revision == 2
    later = DurableAuthorizedExecution(
        execution_id=stored.execution_id,
        authorization_id=stored.authorization_id,
        authorization_version=stored.authorization_version,
        decision_id=stored.decision_id,
        plan_id=stored.plan_id,
        created_at=stored.created_at,
        updated_at=_NOW + timedelta(seconds=5),
        revision=1,
    )
    with pytest.raises(AuthorizedExecutionRevisionConflict):
        repo.save(later, expected_revision=1)
    reloaded = repo.get(stored.execution_id)
    assert reloaded is not None
    assert reloaded.revision == 2
    assert reloaded.updated_at == newer.updated_at
    assert reloaded.plan_id == stored.plan_id


def test_persistence_failure_does_not_fall_back_or_execute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed: list[str] = []
    execute_calls: list[object] = []

    def _ledger_init(self) -> None:
        constructed.append("ledger")
        raise AssertionError("production preparation fell back to the in-memory ledger")

    def _provider_execute(self, step: object) -> None:
        execute_calls.append(step)
        raise AssertionError("connector execute")

    def _consumed(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("authorization consumed")

    monkeypatch.setattr(AuthorizedExecutionLedger, "__init__", _ledger_init)
    monkeypatch.setattr(StaticResearchProvider, "execute", _provider_execute)
    monkeypatch.setattr(
        "app.services.research_authorization.mark_research_authorization_consumed",
        _consumed,
    )

    class _Down:
        def bind(self, **_kwargs: object) -> None:
            raise PersistenceUnavailableError("operational store unavailable")

    auth, plan = _prepared()
    refused = _execute(plan, auth, _Down())
    assert refused.outcome == "blocked_persistence"
    assert refused.reason == "execution_persistence_unavailable"
    assert refused.execution_id is None
    assert refused.execution_started is False
    assert refused.source_checked is False
    assert refused.attempted is False
    assert refused.live is False
    assert refused.connectors_invoked is False
    assert refused.shopify_execute_invoked is False
    assert refused.shopify_live_call_count == 0
    assert refused.prior_decision_preserved is True
    assert refused.prior_decision_id == auth.decision_id
    assert auth.status == "authorized_pending_execution"
    assert execute_calls == []
    assert constructed == []

    def _factory() -> None:
        raise PersistenceUnavailableError("factory unavailable")

    monkeypatch.setattr(
        "app.services.research_execution.production_authorized_execution_repository",
        _factory,
    )
    closed = _execute(plan, auth, None)
    assert closed.outcome == "blocked_persistence"
    assert closed.execution_id is None
    assert execute_calls == []
    assert constructed == []


def test_successful_preparation_keeps_authorization_pending_and_trace_empty(
    sqlite_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumed: list[object] = []

    def _consumed(*args: object, **_kwargs: object) -> None:
        consumed.append(args)

    monkeypatch.setattr(
        "app.services.research_authorization.mark_research_authorization_consumed",
        _consumed,
    )
    monkeypatch.setattr(
        StaticResearchProvider,
        "execute",
        lambda self, step: (_ for _ in ()).throw(AssertionError("connector execute")),
    )
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    prepared = _execute(plan, auth, repo)
    assert prepared.authorization_status == "authorized_pending_execution"
    assert auth.status == "authorized_pending_execution"
    assert consumed == []
    assert prepared.trace.steps == ()
    assert prepared.trace.attempted_sources == ()
    assert prepared.trace.succeeded_sources == ()
    assert prepared.attempted is False
    assert prepared.source_checked is False
    assert prepared.connectors_invoked is False
    assert prepared.live is False
    assert prepared.execution_started is False
    assert prepared.shopify_live_call_count == 0


def test_closed_authorization_states_do_not_create_a_row(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    with pytest.raises(ShoppingAssistantNotFoundError):
        _execute(plan, auth, repo, owner=_owner("other-shopper"))
    stale = _execute(
        plan,
        auth,
        repo,
        canonical_context_version=auth.canonical_context_version + 1,
    )
    assert stale.reason == "stale_context_version"
    cancelled = _execute(plan, replace(auth, status="cancelled"), repo)
    assert cancelled.reason == "cancelled"
    invalidated = _execute(plan, replace(auth, status="invalidated"), repo)
    assert invalidated.reason == "invalidated"
    consumed_auth = mark_research_authorization_consumed(auth, now=START)
    consumed = _execute(plan, consumed_auth, repo)
    assert consumed.reason == "consumed"
    assert consumed.execution_id is None
    assert consumed.execution_started is False
    again = _execute(plan, consumed_auth, repo)
    assert again.reason == "consumed"
    assert repo.row_count() == 0
    assert auth.status == "authorized_pending_execution"


def test_browser_overrides_are_rejected_before_a_durable_write(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    market = _execute(plan, auth, repo, caller_market="US")
    capability = _execute(plan, auth, repo, caller_capability="shipping")
    source = _execute(plan, auth, repo, caller_source="shopee")
    provider = _execute(plan, auth, repo, caller_provider_id="browser-provider")
    assert market.reason == "caller_market_rejected"
    assert capability.reason == "caller_capability_rejected"
    assert source.reason == "caller_source_rejected"
    assert provider.reason == "caller_provider_rejected"
    assert repo.row_count() == 0
    for refused in (market, capability, source, provider):
        assert refused.execution_id is None
        assert refused.connectors_invoked is False
        assert refused.assessed_targets == ()


def test_stored_record_omits_sensitive_authority_material(sqlite_factory) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    prepared = _execute(plan, auth, repo)
    assert prepared.execution_id is not None
    with sqlite_factory() as session:
        row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == RESEARCH_AUTHORIZED_EXECUTIONS,
                OperationalEntityModel.entity_id == prepared.execution_id,
            )
        )
    assert row is not None
    assert row.owner_id is None
    payload = json.dumps(row.payload)
    owner = _owner()
    assert owner.principal_id not in payload
    assert owner.session_id not in payload
    assert auth.idempotency_key not in payload
    assert auth.owner_binding not in payload
    assert "shopify" not in payload.lower()
    assert "secret" not in payload.lower()
    assert "token" not in payload.lower()
    assert "credential" not in payload.lower()
    fields = row.payload["fields"]
    assert set(fields) == {
        "execution_id",
        "authorization_id",
        "authorization_version",
        "decision_id",
        "plan_id",
        "created_at",
        "updated_at",
        "revision",
        "state",
        "claimed_at",
        "claim_expires_at",
        "claim_digest",
    }
    assert fields["state"] == "prepared_unavailable"
    assert fields["claimed_at"] is None
    assert fields["claim_expires_at"] is None
    assert fields["claim_digest"] is None


def test_production_composition_uses_the_durable_repository() -> None:
    import app.services.research_execution as execution

    assert not hasattr(execution, "_PRODUCTION_LEDGER")
    assert not hasattr(execution, "production_authorized_execution_ledger")
    repo = production_authorized_execution_repository()
    assert isinstance(repo, OperationalAuthorizedExecutionRepository)
    assert repo.persists_across_process_restart is True
    assert not isinstance(repo, AuthorizedExecutionLedger)
    service = ShoppingAssistantService()
    held = service._research_proposals._execution_ledger
    assert isinstance(held, OperationalAuthorizedExecutionRepository)
    assert held.persists_across_process_restart is True
    memory = InMemoryAuthorizedExecutionRepository()
    assert memory.persists_across_process_restart is False


def test_service_recreation_reuses_one_execution(sqlite_factory) -> None:
    auth, plan = _prepared()
    first_service = ShoppingAssistantService(execution_ledger=_repo(sqlite_factory))
    prepared = _execute(plan, auth, first_service._research_proposals._execution_ledger)
    second_service = ShoppingAssistantService(execution_ledger=_repo(sqlite_factory))
    again = _execute(plan, auth, second_service._research_proposals._execution_ledger)
    assert prepared.execution_id == again.execution_id
    assert _repo(sqlite_factory).row_count() == 1


def _database_down(*_args: object, **_kwargs: object) -> None:
    raise OperationalError("SELECT 1", {}, Exception("database unavailable"))


def _sample_record() -> DurableAuthorizedExecution:
    return DurableAuthorizedExecution(
        execution_id="research-exec:" + ("ab" * 16),
        authorization_id="authorization-outage",
        authorization_version=1,
        decision_id="decision-outage",
        plan_id="plan-outage",
        created_at=_NOW,
        updated_at=_NOW,
        revision=1,
    )


def test_sqlalchemy_operational_error_becomes_persistence_unavailable(
    sqlite_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(sqlite_factory)
    auth, plan = _prepared()
    inserted: list[object] = []
    execute_calls: list[object] = []
    consumed: list[object] = []

    def _insert(*args: object, **_kwargs: object) -> None:
        inserted.append(args)
        raise AssertionError("durable insert during a database outage")

    def _provider_execute(self: StaticResearchProvider, step: object) -> None:
        execute_calls.append(step)
        raise AssertionError("connector execute")

    monkeypatch.setattr(OperationalStore, "get_versioned", _database_down)
    monkeypatch.setattr(OperationalStore, "insert_versioned", _insert)
    monkeypatch.setattr(OperationalStore, "compare_and_swap", _database_down)
    monkeypatch.setattr(StaticResearchProvider, "execute", _provider_execute)
    monkeypatch.setattr(
        "app.services.research_authorization.mark_research_authorization_consumed",
        lambda *args, **_kwargs: consumed.append(args),
    )

    with pytest.raises(PersistenceUnavailableError):
        repo.get(_sample_record().execution_id)
    with pytest.raises(PersistenceUnavailableError):
        _bind(repo, auth, plan)
    with pytest.raises(PersistenceUnavailableError):
        repo.save(_sample_record(), expected_revision=1)
    assert inserted == []

    refused = _execute(plan, auth, repo)
    assert refused.outcome == "blocked_persistence"
    assert refused.reason == "execution_persistence_unavailable"
    assert refused.execution_id is None
    assert refused.attempted is False
    assert refused.source_checked is False
    assert refused.live is False
    assert refused.connectors_invoked is False
    assert refused.execution_started is False
    assert refused.authorization_consumed is False
    assert refused.prior_decision_preserved is True
    assert refused.prior_decision_id == auth.decision_id
    assert auth.status == "authorized_pending_execution"
    assert execute_calls == []
    assert consumed == []

    monkeypatch.setattr("app.infrastructure.persistence.session.sync_session", _database_down)
    with pytest.raises(PersistenceUnavailableError):
        repo.row_count()


def test_in_memory_repository_does_not_survive_a_new_instance() -> None:
    auth, plan = _prepared()
    first = InMemoryAuthorizedExecutionRepository()
    _bind(first, auth, plan)
    assert InMemoryAuthorizedExecutionRepository().row_count() == 0


def test_status_flags_and_shopify_stay_closed() -> None:
    provider = shopify_global_catalog_ph_provider()
    assert provider.descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    with pytest.raises(NotImplementedError):
        provider.execute(None)  # type: ignore[arg-type]
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()
    assert SHOPPING_RESEARCH_EXECUTION_MODE == "disabled"
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False
    assert DESTINATION_REEVALUATION_IMPLEMENTED is False
    assert SPRINT_41_STATUS == "UNSTARTED"
    assert HALF_OPEN_SINGLE_PROBE_LEASE_IMPLEMENTED is True
    assert DURABLE_LIVE_START_CLAIM_IMPLEMENTED is True
    assert EXTERNAL_CONNECTOR_ATTEMPT_INSIDE_DATABASE_TRANSACTION is False
    assert FUTURE_LIVE_START_PHASES == (
        "transactional_live_start_claim",
        "external_connector_attempt",
        "transactional_outcome_recording",
    )
    assert "persist_live_start_claim" in FUTURE_LIVE_START_CLAIM
    assert "connector_invocation" not in FUTURE_LIVE_START_CLAIM


_OUTAGE_DECISION_ID = "00000000-0000-4000-8000-00000000038a"


@pytest.mark.asyncio
async def test_http_confirmation_fails_closed_when_execution_store_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = replace(_presentation(), decision_id=_OUTAGE_DECISION_ID)
    get_shopping_decision_snapshot_repository().add(snapshot)
    execute_calls: list[object] = []

    def _provider_execute(self: StaticResearchProvider, step: object) -> None:
        execute_calls.append(step)
        raise AssertionError("connector execute")

    monkeypatch.setattr(StaticResearchProvider, "execute", _provider_execute)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(OWNER_COOKIE, owner_cookie_payload(_owner()))
        ask = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "What about AirPods Max?",
                "decision_id": _OUTAGE_DECISION_ID,
                "surface": "results",
            },
        )
        assert ask.status_code == 200, ask.text
        body = ask.json()
        monkeypatch.setattr(
            "app.infrastructure.persistence.session.sync_session",
            _database_down,
        )
        confirm = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Yes, research that",
                "decision_id": _OUTAGE_DECISION_ID,
                "conversation_id": body["conversation_id"],
                "surface": "results",
                "proposal_id": body["research_proposal"]["proposal_id"],
                "proposal_version": body["research_proposal"]["proposal_version"],
            },
        )
        assert confirm.status_code == 200, confirm.text
        payload = confirm.json()
        assert payload["execution_available"] is False
        assert payload["research_handoff_status"] == "authorized_pending_execution"
        assert payload["research_handoff_created"] is True
        assert payload["processing"]["execution_started"] is False
        assert payload["processing"]["source_checked"] is False
        assert payload["processing"]["attempted"] is False
        outcome = payload["processing"]["research_preparation_outcome"]
        assert outcome == "blocked_persistence"
        assert payload["processing"]["authorization_status"] == "authorized_pending_execution"
        assert "Researching" not in payload["answer"]
        assert execute_calls == []
        monkeypatch.undo()
        results = await client.get(f"/results/{_OUTAGE_DECISION_ID}")
        assert results.status_code == 200
        assert 'data-best-piq="' + SONY_ID in results.text
