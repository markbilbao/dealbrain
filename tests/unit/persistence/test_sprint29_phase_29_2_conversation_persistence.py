"""Sprint 29 Phase 29.2 durable conversation persistence tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest
from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
)
from app.domain.exceptions import (
    ConversationOwnershipError,
    ConversationVersionConflictError,
)
from app.domain.interfaces.shopping_assistant_repository import ConversationRepository
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.persistence.stores import SHOPPING_CONVERSATIONS
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000029"


@pytest.fixture()
def sqlite_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'sprint29-phase-29-2.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def _guest_owner(*, expires_at: datetime | None = None) -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-contract-29",
        session_id="session-contract-29",
        expires_at=expires_at or START + timedelta(minutes=30),
    )


def _account_owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="account",
        principal_id="account-contract-29",
        session_id="account-session-contract-29",
        expires_at=START + timedelta(hours=1),
    )


def _decision_context() -> DecisionContextReference:
    return DecisionContextReference(
        decision_id=DECISION_ID,
        context_version=1,
        evaluated_product_ids=(
            "apple-iphone-17-pro-max",
            "samsung-galaxy-s25-ultra-512gb",
        ),
        canonical_piqscore_snapshot_sha256="a" * 64,
        recommendation_snapshot_sha256="b" * 64,
        evidence_ids=("fixture-battery-iphone", "fixture-battery-samsung"),
    )


def _turn(number: int) -> ConversationTurn:
    return ConversationTurn(
        role="user",
        intent="comparison",
        product_ids=(
            "apple-iphone-17-pro-max",
            "samsung-galaxy-s25-ultra-512gb",
        ),
        product_names=("iPhone 17 Pro Max", "Samsung Galaxy S25 Ultra 512GB"),
        query=f"Follow-up {number}",
        created_at=START,
        turn_id=f"00000000-0000-4000-8000-{number:012d}",
        decision_id=DECISION_ID,
        context_version=1,
        action="answer_from_evidence",
    )


def _repository(
    backend: str,
    sqlite_factory: sessionmaker[Session],
    clock_state: dict[str, datetime],
    *,
    ttl_seconds: int = 600,
    max_turns: int = 2,
    id_factory: Any = None,
) -> ConversationRepository:
    kwargs = {
        "ttl_seconds": ttl_seconds,
        "max_turns": max_turns,
        "clock": lambda: clock_state["now"],
        "id_factory": id_factory or (lambda: "conversation-contract-29"),
    }
    if backend == "memory":
        return InMemoryConversationRepository(**kwargs)
    return SqlAlchemyConversationRepository(session_factory=sqlite_factory, **kwargs)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_memory_sql_repository_contract_parity(
    backend: str, sqlite_factory: sessionmaker[Session]
) -> None:
    clock_state = {"now": START}
    repository = _repository(backend, sqlite_factory, clock_state)
    owner = _guest_owner()
    created = repository.create(owner=owner, decision_context=_decision_context())

    assert created.persistence_version == 1
    assert repository.get_for_owner(created.conversation_id, owner) == created

    updated = repository.append_turn(
        created.conversation_id,
        _turn(1),
        expected_version=created.persistence_version,
    )
    assert updated.persistence_version == 2
    assert updated.owner == owner
    assert updated.decision_context == _decision_context()

    with pytest.raises(ConversationVersionConflictError):
        repository.append_turn(
            created.conversation_id,
            _turn(2),
            expected_version=created.persistence_version,
        )


def test_sql_repository_survives_restart(sqlite_factory: sessionmaker[Session]) -> None:
    clock_state = {"now": START}
    first = _repository("sql", sqlite_factory, clock_state)
    created = first.create(owner=_guest_owner(), decision_context=_decision_context())
    updated = first.append_turn(created.conversation_id, _turn(1), expected_version=1)

    restarted = _repository("sql", sqlite_factory, clock_state)
    assert restarted.get(created.conversation_id) == updated


def test_sql_repository_is_shared_across_instances(
    sqlite_factory: sessionmaker[Session],
) -> None:
    clock_state = {"now": START}
    first = _repository("sql", sqlite_factory, clock_state)
    second = _repository("sql", sqlite_factory, clock_state)
    created = first.create(owner=_guest_owner(), decision_context=_decision_context())

    observed = second.get(created.conversation_id)
    assert observed == created
    second.append_turn(created.conversation_id, _turn(1), expected_version=1)
    assert first.get(created.conversation_id).persistence_version == 2  # type: ignore[union-attr]


def test_sql_concurrent_writers_use_compare_and_swap(
    sqlite_factory: sessionmaker[Session],
) -> None:
    clock_state = {"now": START}
    creator = _repository("sql", sqlite_factory, clock_state)
    created = creator.create(owner=_guest_owner(), decision_context=_decision_context())
    barrier = Barrier(2)

    def write(number: int) -> str:
        repository = _repository("sql", sqlite_factory, clock_state)
        loaded = repository.get(created.conversation_id)
        assert loaded is not None
        barrier.wait()
        try:
            repository.append_turn(
                loaded.conversation_id,
                _turn(number),
                expected_version=loaded.persistence_version,
            )
            return "updated"
        except ConversationVersionConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (1, 2)))

    assert sorted(results) == ["conflict", "updated"]
    final = creator.get(created.conversation_id)
    assert final is not None
    assert final.persistence_version == 2
    assert len(final.turns) == 1


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_expired_conversation_is_removed_on_read(
    backend: str, sqlite_factory: sessionmaker[Session]
) -> None:
    clock_state = {"now": START}
    repository = _repository(backend, sqlite_factory, clock_state, ttl_seconds=60)
    created = repository.create(owner=_guest_owner(), decision_context=_decision_context())

    clock_state["now"] = START + timedelta(seconds=61)
    assert repository.get(created.conversation_id) is None
    assert repository.cleanup_expired(limit=10) == 0


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_owner_expiry_ends_conversation_access(
    backend: str, sqlite_factory: sessionmaker[Session]
) -> None:
    clock_state = {"now": START}
    repository = _repository(backend, sqlite_factory, clock_state, ttl_seconds=600)
    owner = _guest_owner(expires_at=START + timedelta(seconds=30))
    created = repository.create(owner=owner, decision_context=_decision_context())

    clock_state["now"] = START + timedelta(seconds=31)
    assert repository.get_for_owner(created.conversation_id, owner) is None


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_cleanup_is_bounded(backend: str, sqlite_factory: sessionmaker[Session]) -> None:
    clock_state = {"now": START}
    identifiers = iter(("conversation-1", "conversation-2", "conversation-3"))
    repository = _repository(
        backend,
        sqlite_factory,
        clock_state,
        ttl_seconds=10,
        id_factory=lambda: next(identifiers),
    )
    for _ in range(3):
        repository.create(owner=_guest_owner(), decision_context=_decision_context())

    clock_state["now"] = START + timedelta(seconds=11)
    assert repository.cleanup_expired(limit=2) == 2
    assert repository.cleanup_expired(limit=2) == 1
    assert repository.cleanup_expired(limit=2) == 0


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_owner_rebind_is_explicit_and_versioned(
    backend: str, sqlite_factory: sessionmaker[Session]
) -> None:
    clock_state = {"now": START}
    repository = _repository(backend, sqlite_factory, clock_state)
    guest = _guest_owner()
    account = _account_owner()
    created = repository.create(owner=guest, decision_context=_decision_context())

    assert repository.get_for_owner(created.conversation_id, account) is None
    rebound = repository.rebind_owner(
        created.conversation_id,
        current_owner=guest,
        new_owner=account,
        expected_version=created.persistence_version,
    )
    assert rebound.owner == account
    assert rebound.persistence_version == 2
    assert repository.get_for_owner(created.conversation_id, guest) is None
    assert repository.get_for_owner(created.conversation_id, account) == rebound

    with pytest.raises(ConversationOwnershipError):
        repository.rebind_owner(
            created.conversation_id,
            current_owner=guest,
            new_owner=account,
            expected_version=rebound.persistence_version,
        )


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_bounded_turn_history_and_legacy_calls_remain_compatible(
    backend: str, sqlite_factory: sessionmaker[Session]
) -> None:
    clock_state = {"now": START}
    repository = _repository(backend, sqlite_factory, clock_state, max_turns=2)
    context = repository.create()
    for number in range(1, 4):
        context = repository.append_turn(context.conversation_id, _turn(number))

    assert context.persistence_version == 4
    assert [turn.query for turn in context.turns] == ["Follow-up 2", "Follow-up 3"]


def test_sql_repository_uses_existing_operational_entities_table_only(
    sqlite_factory: sessionmaker[Session],
) -> None:
    clock_state = {"now": START}
    repository = _repository("sql", sqlite_factory, clock_state)
    repository.create(owner=_guest_owner(), decision_context=_decision_context())
    engine = sqlite_factory.kw["bind"]

    assert inspect(engine).get_table_names() == ["operational_entities"]
    with sqlite_factory() as session:
        rows = session.scalar(
            select(func.count())
            .select_from(OperationalEntityModel)
            .where(OperationalEntityModel.store == SHOPPING_CONVERSATIONS)
        )
    assert rows == 1


def test_decision_bound_context_requires_owner_after_codec_roundtrip(
    sqlite_factory: sessionmaker[Session],
) -> None:
    clock_state = {"now": START}
    repository = _repository("sql", sqlite_factory, clock_state)
    created = repository.create(owner=_guest_owner(), decision_context=_decision_context())
    loaded = repository.get(created.conversation_id)

    assert isinstance(loaded, ConversationContext)
    assert loaded.owner == _guest_owner()
    assert loaded.decision_context == _decision_context()
