"""Sprint 29 Phase 29.3 canonical decision snapshot tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest
from app.domain.entities.decision_snapshot import (
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.shopping_assistant import (
    ConversationOwner,
    ConversationTurn,
    DecisionContextReference,
)
from app.domain.exceptions import (
    ConversationContextDriftError,
    DecisionSnapshotConflictError,
    DecisionSnapshotIntegrityError,
)
from app.domain.interfaces.decision_snapshot_repository import DecisionSnapshotRepository
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.shopping_conversation_repository import (
    SqlAlchemyConversationRepository,
)
from app.infrastructure.database.repositories.shopping_decision_snapshot_repository import (
    SqlAlchemyDecisionSnapshotRepository,
)
from app.infrastructure.persistence.stores import SHOPPING_DECISION_SNAPSHOTS
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.services.decision_snapshot_service import DecisionSnapshotBinder
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000029"
IPHONE_ID = "apple-iphone-17-pro-max"
SAMSUNG_ID = "samsung-galaxy-s25-ultra-512gb"
PIXEL_ID = "google-pixel-9-128gb"


@pytest.fixture()
def sqlite_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'sprint29-phase-29-3.db'}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def _owner(
    *,
    principal_id: str = "guest-contract-29",
    expires_at: datetime | None = None,
) -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=expires_at or START + timedelta(minutes=30),
    )


def _score(value: float, digest_character: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest_character * 64,
    )


def _product(
    product_id: str,
    name: str,
    variant: str,
    score: CanonicalPiqScoreSnapshot,
) -> EvaluatedProductSnapshot:
    return EvaluatedProductSnapshot(
        product_id=product_id,
        display_name=name,
        variant=variant,
        canonical_piqscore=score,
    )


def _snapshot(
    *,
    owner: ConversationOwner | None = None,
    context_version: int = 1,
) -> CanonicalDecisionSnapshot:
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=context_version,
        owner=owner or _owner(),
        evaluated_products=(
            _product(IPHONE_ID, "iPhone 17 Pro Max", "contract-fixture-variant", _score(87, "a")),
            _product(
                SAMSUNG_ID,
                "Samsung Galaxy S25 Ultra 512GB",
                "512GB contract-fixture-variant",
                _score(83, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=IPHONE_ID,
            alternative_product_ids=(SAMSUNG_ID,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-iphone",
                product_id=IPHONE_ID,
                topic="battery",
                fact="non-live fixture battery evidence A",
                source="contract-fixture://battery/a",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-samsung",
                product_id=SAMSUNG_ID,
                topic="battery",
                fact="non-live fixture battery evidence B",
                source="contract-fixture://battery/b",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
            ),
        ),
        unknowns=("live marketplace facts are intentionally absent",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
    )


def _snapshot_repository(
    sqlite_factory: sessionmaker[Session],
    *,
    now: datetime = START,
) -> DecisionSnapshotRepository:
    return SqlAlchemyDecisionSnapshotRepository(
        session_factory=sqlite_factory,
        clock=lambda: now,
    )


def _conversation_repository(
    backend: str,
    sqlite_factory: sessionmaker[Session],
) -> Any:
    kwargs = {
        "ttl_seconds": 600,
        "clock": lambda: START,
        "id_factory": lambda: f"conversation-{backend}-29-3",
    }
    if backend == "memory":
        return InMemoryConversationRepository(**kwargs)
    return SqlAlchemyConversationRepository(session_factory=sqlite_factory, **kwargs)


def _turn(*, product_ids: tuple[str, ...], decision_id: str = DECISION_ID) -> ConversationTurn:
    return ConversationTurn(
        role="user",
        intent="comparison",
        product_ids=product_ids,
        product_names=tuple(product_ids),
        query="Which one has better battery?",
        created_at=START,
        turn_id="00000000-0000-4000-8000-000000000293",
        decision_id=decision_id,
        context_version=1,
        action="answer_from_evidence",
    )


def test_canonical_snapshot_matches_frozen_contract_and_builds_reference() -> None:
    snapshot = _snapshot()
    reference = snapshot.to_reference()

    assert snapshot.evaluated_product_ids == (IPHONE_ID, SAMSUNG_ID)
    assert snapshot.evidence_ids == (
        "fixture-battery-iphone",
        "fixture-battery-samsung",
    )
    assert reference == DecisionContextReference(
        decision_id=DECISION_ID,
        context_version=1,
        evaluated_product_ids=(IPHONE_ID, SAMSUNG_ID),
        canonical_piqscore_snapshot_sha256=snapshot.canonical_piqscore_set_sha256,
        recommendation_snapshot_sha256="c" * 64,
        evidence_ids=("fixture-battery-iphone", "fixture-battery-samsung"),
    )
    assert snapshot.to_dict()["recommendation"]["authority"] == ("canonical-recommendation-engine")
    assert snapshot.to_dict()["unknowns"] == ["live marketplace facts are intentionally absent"]


def test_canonical_snapshot_serialization_validates_against_frozen_schema() -> None:
    root = Path(__file__).resolve().parents[3]
    schema = json.loads(
        (root / "schemas/sprint29-decision-context.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(_snapshot().to_dict())


def test_snapshot_value_objects_are_frozen() -> None:
    snapshot = _snapshot()

    with pytest.raises(FrozenInstanceError):
        snapshot.context_version = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.evaluated_products[0].display_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_products",
        "recommendation_outside_set",
        "evidence_outside_set",
        "affiliate_influence",
        "invalid_score_digest",
    ],
)
def test_snapshot_rejects_cross_field_or_integrity_contract_violations(change: str) -> None:
    snapshot = _snapshot()

    with pytest.raises(ValueError):
        if change == "duplicate_products":
            replace(snapshot, evaluated_products=(snapshot.evaluated_products[0],) * 2)
        elif change == "recommendation_outside_set":
            replace(
                snapshot,
                recommendation=replace(
                    snapshot.recommendation,
                    best_piq_product_id=PIXEL_ID,
                ),
            )
        elif change == "evidence_outside_set":
            replace(
                snapshot,
                evidence=(
                    replace(snapshot.evidence[0], product_id=PIXEL_ID),
                    snapshot.evidence[1],
                ),
            )
        elif change == "affiliate_influence":
            replace(
                snapshot,
                affiliate_neutrality=AffiliateNeutralitySnapshot(commission_influenced_scores=True),
            )
        else:
            replace(
                snapshot,
                evaluated_products=(
                    replace(
                        snapshot.evaluated_products[0],
                        canonical_piqscore=replace(
                            snapshot.evaluated_products[0].canonical_piqscore,
                            snapshot_sha256="invalid",
                        ),
                    ),
                    snapshot.evaluated_products[1],
                ),
            )


def test_snapshot_repository_is_owner_bound_and_survives_restart(
    sqlite_factory: sessionmaker[Session],
) -> None:
    first = _snapshot_repository(sqlite_factory)
    snapshot = first.add(_snapshot())

    restarted = _snapshot_repository(sqlite_factory)
    assert restarted.get_for_owner(DECISION_ID, 1, _owner()) == snapshot
    assert restarted.get_for_owner(DECISION_ID, 1, _owner(principal_id="other")) is None


def test_expired_snapshot_owner_cannot_resume_access(
    sqlite_factory: sessionmaker[Session],
) -> None:
    snapshot = _snapshot(owner=_owner(expires_at=START + timedelta(seconds=30)))
    _snapshot_repository(sqlite_factory).add(snapshot)

    after_expiry = _snapshot_repository(
        sqlite_factory,
        now=START + timedelta(seconds=31),
    )
    assert after_expiry.get_for_owner(DECISION_ID, 1, snapshot.owner) is None


def test_snapshot_identity_is_immutable_and_cannot_be_overwritten(
    sqlite_factory: sessionmaker[Session],
) -> None:
    repository = _snapshot_repository(sqlite_factory)
    original = repository.add(_snapshot())
    altered = replace(original, unknowns=("silently changed",))

    with pytest.raises(DecisionSnapshotConflictError):
        repository.add(altered)

    assert repository.get(DECISION_ID, 1) == original


def test_concurrent_snapshot_writers_cannot_overwrite_each_other(
    sqlite_factory: sessionmaker[Session],
) -> None:
    barrier = Barrier(2)

    def write(unknown: str) -> str:
        repository = _snapshot_repository(sqlite_factory)
        candidate = replace(_snapshot(), unknowns=(unknown,))
        barrier.wait()
        try:
            repository.add(candidate)
            return "created"
        except DecisionSnapshotConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ("unknown-a", "unknown-b")))

    assert sorted(results) == ["conflict", "created"]
    stored = _snapshot_repository(sqlite_factory).get(DECISION_ID, 1)
    assert stored is not None
    assert stored.unknowns in {("unknown-a",), ("unknown-b",)}


def test_persisted_snapshot_content_tampering_fails_integrity_check(
    sqlite_factory: sessionmaker[Session],
) -> None:
    repository = _snapshot_repository(sqlite_factory)
    repository.add(_snapshot())

    with sqlite_factory() as session:
        row = session.scalar(
            select(OperationalEntityModel).where(
                OperationalEntityModel.store == SHOPPING_DECISION_SNAPSHOTS
            )
        )
        assert row is not None
        payload = deepcopy(row.payload)
        product_items = payload["fields"]["snapshot"]["fields"]["evaluated_products"]["items"]
        product_items[0]["fields"]["display_name"] = "tampered product"
        row.payload = payload
        session.commit()

    with pytest.raises(DecisionSnapshotIntegrityError):
        repository.get(DECISION_ID, 1)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_binder_uses_persisted_snapshot_as_the_only_decision_reference(
    backend: str,
    sqlite_factory: sessionmaker[Session],
) -> None:
    snapshots = _snapshot_repository(sqlite_factory)
    snapshot = snapshots.add(_snapshot())
    conversations = _conversation_repository(backend, sqlite_factory)
    conversation = conversations.create(owner=snapshot.owner)
    binder = DecisionSnapshotBinder(snapshots, conversations)

    bound = binder.bind(
        conversation.conversation_id,
        decision_id=DECISION_ID,
        context_version=1,
        owner=snapshot.owner,
        expected_conversation_version=conversation.persistence_version,
    )

    assert bound.decision_context == snapshot.to_reference()
    assert bound.last_product_ids == snapshot.evaluated_product_ids


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_battery_follow_up_preserves_the_exact_evaluated_set(
    backend: str,
    sqlite_factory: sessionmaker[Session],
) -> None:
    snapshots = _snapshot_repository(sqlite_factory)
    snapshot = snapshots.add(_snapshot())
    conversations = _conversation_repository(backend, sqlite_factory)
    created = conversations.create(owner=snapshot.owner)
    bound = DecisionSnapshotBinder(snapshots, conversations).bind(
        created.conversation_id,
        decision_id=DECISION_ID,
        context_version=1,
        owner=snapshot.owner,
        expected_conversation_version=created.persistence_version,
    )

    updated = conversations.append_turn(
        bound.conversation_id,
        _turn(product_ids=(IPHONE_ID, SAMSUNG_ID)),
        expected_version=bound.persistence_version,
    )

    assert updated.decision_context == snapshot.to_reference()
    assert updated.decision_context.evaluated_product_ids == (IPHONE_ID, SAMSUNG_ID)


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_follow_up_cannot_introduce_the_forbidden_pixel(
    backend: str,
    sqlite_factory: sessionmaker[Session],
) -> None:
    snapshots = _snapshot_repository(sqlite_factory)
    snapshot = snapshots.add(_snapshot())
    conversations = _conversation_repository(backend, sqlite_factory)
    created = conversations.create(owner=snapshot.owner)
    bound = DecisionSnapshotBinder(snapshots, conversations).bind(
        created.conversation_id,
        decision_id=DECISION_ID,
        context_version=1,
        owner=snapshot.owner,
        expected_conversation_version=created.persistence_version,
    )

    with pytest.raises(ConversationContextDriftError):
        conversations.append_turn(
            bound.conversation_id,
            _turn(product_ids=(IPHONE_ID, PIXEL_ID)),
            expected_version=bound.persistence_version,
        )

    unchanged = conversations.get(bound.conversation_id)
    assert unchanged == bound


@pytest.mark.parametrize("backend", ["memory", "sql"])
def test_direct_save_cannot_replace_the_bound_decision_context(
    backend: str,
    sqlite_factory: sessionmaker[Session],
) -> None:
    snapshots = _snapshot_repository(sqlite_factory)
    snapshot = snapshots.add(_snapshot())
    conversations = _conversation_repository(backend, sqlite_factory)
    created = conversations.create(owner=snapshot.owner)
    bound = DecisionSnapshotBinder(snapshots, conversations).bind(
        created.conversation_id,
        decision_id=DECISION_ID,
        context_version=1,
        owner=snapshot.owner,
        expected_conversation_version=created.persistence_version,
    )
    replacement = replace(
        snapshot.to_reference(),
        context_version=2,
        evaluated_product_ids=(IPHONE_ID, PIXEL_ID),
    )

    with pytest.raises(ConversationContextDriftError):
        conversations.save(
            replace(bound, decision_context=replacement),
            expected_version=bound.persistence_version,
        )

    assert conversations.get(bound.conversation_id) == bound


def test_snapshot_repository_uses_only_the_existing_operational_table(
    sqlite_factory: sessionmaker[Session],
) -> None:
    _snapshot_repository(sqlite_factory).add(_snapshot())
    engine = sqlite_factory.kw["bind"]

    assert inspect(engine).get_table_names() == ["operational_entities"]
