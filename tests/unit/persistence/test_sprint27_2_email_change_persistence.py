"""Sprint 27.2 email-change records persist in operational_entities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.domain.entities.user_platform import EMAIL_CHANGE_PURPOSE, EmailChangeRequest
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.user_platform_repository import (
    SqlAlchemyUserPlatformStore,
)
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import EMAIL_CHANGES
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint27-2-email-change.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _record(*, change_id: str = "chg-1", user_id: str = "u-1") -> EmailChangeRequest:
    now = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    return EmailChangeRequest(
        change_id=change_id,
        user_id=user_id,
        token_hash="hashed-token",
        new_email="new@example.com",
        created_at=now,
        expires_at=now + timedelta(days=1),
        purpose=EMAIL_CHANGE_PURPOSE,
    )


def test_email_change_survives_restart(sqlite_factory: sessionmaker[Session]) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    saved = store.email_changes.save(_record())
    assert saved.purpose == EMAIL_CHANGE_PURPOSE

    restarted = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    loaded = restarted.email_changes.get_by_token_hash("hashed-token")
    assert loaded == saved
    with sqlite_factory() as session:
        rows = session.scalars(
            select(OperationalEntityModel).where(OperationalEntityModel.store == EMAIL_CHANGES)
        ).all()
    assert len(rows) == 1
    assert rows[0].owner_id == "u-1"


def test_email_change_newest_request_invalidates_prior(
    sqlite_factory: sessionmaker[Session],
) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    first = store.email_changes.save(_record(change_id="chg-1"))
    store.email_changes.invalidate_for_user(first.user_id)
    second = store.email_changes.save(
        EmailChangeRequest(
            change_id="chg-2",
            user_id=first.user_id,
            token_hash="hashed-token-2",
            new_email="newer@example.com",
            created_at=first.created_at + timedelta(minutes=1),
            expires_at=first.expires_at,
            purpose=EMAIL_CHANGE_PURPOSE,
        )
    )
    prior = store.email_changes.get_by_token_hash("hashed-token")
    assert prior is not None
    assert prior.consumed is True
    assert store.email_changes.get_by_token_hash("hashed-token-2") == second
    assert store.email_changes.delete_for_user(first.user_id) == 2
    assert store.email_changes.get_by_token_hash("hashed-token-2") is None
