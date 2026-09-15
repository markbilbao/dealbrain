"""Persistence tests for Early Access uniqueness and durability."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.domain.entities.early_access import EarlyAccessRegistration
from app.early_access.memory import InMemoryEarlyAccessRepository
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.early_access_repository import (
    SqlAlchemyEarlyAccessRepository,
)
from app.infrastructure.persistence.errors import PersistenceError
from app.infrastructure.persistence.session import reset_sync_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    db_path = tmp_path / "early_access.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _now() -> datetime:
    return datetime.now(UTC)


def _reg(email: str, *, entity_id: str, name: str = "Ada") -> EarlyAccessRegistration:
    stamp = _now()
    normalized = email.strip().lower()
    return EarlyAccessRegistration(
        id=entity_id,
        full_name=name,
        email=normalized,
        normalized_email=normalized,
        country="US",
        shopping_interest=None,
        source="early_access_landing",
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        utm_term=None,
        referrer=None,
        email_confirmation_status="not_sent",
        email_confirmation_sent_at=None,
        created_at=stamp,
        updated_at=stamp,
    )


def test_durable_registration(sqlite_factory: sessionmaker[Session]) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    stored, created = repo.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    assert created is True
    loaded = repo.get_by_normalized_email("ada@example.com")
    assert loaded is not None
    assert loaded.id == stored.id


def test_normalized_email_uniqueness(sqlite_factory: sessionmaker[Session]) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    first, created = repo.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    second, created_again = repo.create_if_absent(_reg("ada@example.com", entity_id="r2"))
    assert created is True
    assert created_again is False
    assert second.id == first.id
    assert len(repo.list_all()) == 1


def test_duplicate_creates_one_record_only(sqlite_factory: sessionmaker[Session]) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    repo.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    repo.create_if_absent(_reg("ada@example.com", entity_id="r2"))
    repo.create_if_absent(_reg("ada@example.com", entity_id="r3"))
    assert len(repo.list_all()) == 1


def test_historical_payload_without_assent_fields_stays_null(
    sqlite_factory: sessionmaker[Session],
) -> None:
    from app.infrastructure.persistence.codec import decode_entity, encode_entity

    historical = _reg("old@example.com", entity_id="hist-1")
    payload = encode_entity(historical)
    payload["fields"].pop("terms_version_id", None)
    payload["fields"].pop("privacy_version_id", None)
    payload["fields"].pop("policies_acknowledged_at", None)
    loaded = decode_entity(EarlyAccessRegistration, payload)
    assert loaded.terms_version_id is None
    assert loaded.privacy_version_id is None
    assert loaded.policies_acknowledged_at is None
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    repo.create_if_absent(loaded)
    stored = repo.get_by_normalized_email("old@example.com")
    assert stored is not None
    assert stored.terms_version_id is None
    assert stored.policies_acknowledged_at is None


def test_successful_assent_fields_round_trip(sqlite_factory: sessionmaker[Session]) -> None:
    stamp = _now()
    registration = EarlyAccessRegistration(
        id="r-ack",
        full_name="Ada",
        email="ack@example.com",
        normalized_email="ack@example.com",
        country="US",
        shopping_interest=None,
        source="early_access_landing",
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        utm_term=None,
        referrer=None,
        email_confirmation_status="not_sent",
        email_confirmation_sent_at=None,
        created_at=stamp,
        updated_at=stamp,
        terms_version_id="terms-2026-09-11",
        privacy_version_id="privacy-2026-09-11",
        policies_acknowledged_at=stamp,
    )
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    repo.create_if_absent(registration)
    loaded = repo.get_by_normalized_email("ack@example.com")
    assert loaded is not None
    assert loaded.terms_version_id == "terms-2026-09-11"
    assert loaded.privacy_version_id == "privacy-2026-09-11"
    assert loaded.policies_acknowledged_at == stamp


def test_restart_repository_recreation_retrieval(sqlite_factory: sessionmaker[Session]) -> None:
    first = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    first.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    restarted = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    loaded = restarted.get_by_normalized_email("ada@example.com")
    assert loaded is not None
    assert loaded.full_name == "Ada"


def test_concurrent_duplicate_attempts_cannot_create_two_records(
    sqlite_factory: sessionmaker[Session],
) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)

    def _write(i: int) -> bool:
        _entity, created = repo.create_if_absent(
            _reg("same@example.com", entity_id=f"r-{i}", name=f"User {i}")
        )
        return created

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [f.result() for f in as_completed(pool.submit(_write, i) for i in range(8))]

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert len(repo.list_all()) == 1


def test_confirmation_status_transitions_persist(
    sqlite_factory: sessionmaker[Session],
) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    stored, created = repo.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    assert created is True
    pending_at = _now()
    pending = repo.update_email_confirmation(
        stored.id,
        status="pending",
        sent_at=None,
        updated_at=pending_at,
    )
    assert pending.email_confirmation_status == "pending"
    assert pending.email_confirmation_sent_at is None
    sent_at = _now()
    sent = repo.update_email_confirmation(
        stored.id,
        status="sent",
        sent_at=sent_at,
        updated_at=sent_at,
    )
    loaded = repo.get_by_normalized_email("ada@example.com")
    assert loaded is not None
    assert loaded.email_confirmation_status == "sent"
    assert loaded.email_confirmation_sent_at == sent_at
    assert loaded.updated_at == sent_at
    assert loaded.full_name == "Ada"
    failed = repo.update_email_confirmation(
        stored.id,
        status="failed",
        sent_at=None,
        updated_at=_now(),
    )
    assert failed.email_confirmation_status == "failed"
    assert failed.email_confirmation_sent_at is None
    assert len(repo.list_all()) == 1


def test_confirmation_status_missing_id_raises(
    sqlite_factory: sessionmaker[Session],
) -> None:
    repo = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    with pytest.raises(PersistenceError):
        repo.update_email_confirmation(
            "missing",
            status="sent",
            sent_at=_now(),
            updated_at=_now(),
        )


def test_in_memory_confirmation_status_matches_sqlalchemy() -> None:
    repo = InMemoryEarlyAccessRepository()
    stored, created = repo.create_if_absent(_reg("ada@example.com", entity_id="r1"))
    assert created is True
    sent_at = _now()
    updated = repo.update_email_confirmation(
        stored.id,
        status="sent",
        sent_at=sent_at,
        updated_at=sent_at,
    )
    assert updated.email_confirmation_status == "sent"
    assert updated.email_confirmation_sent_at == sent_at
    again, created_again = repo.create_if_absent(_reg("ada@example.com", entity_id="r2"))
    assert created_again is False
    assert again.id == stored.id
    assert again.email_confirmation_status == "sent"
    assert len(repo.list_all()) == 1
    with pytest.raises(KeyError):
        repo.update_email_confirmation(
            "missing",
            status="failed",
            sent_at=None,
            updated_at=_now(),
        )
