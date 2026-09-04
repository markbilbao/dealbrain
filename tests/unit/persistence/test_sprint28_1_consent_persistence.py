"""Sprint 28.1 consent persistence — operational_entities, restart, deletion."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.domain.entities.early_access import EarlyAccessRegistration
from app.domain.entities.user_platform import PolicyAcceptanceRecord, User
from app.infrastructure.database.models.operational_entity import OperationalEntityModel
from app.infrastructure.database.repositories.early_access_repository import (
    SqlAlchemyEarlyAccessRepository,
)
from app.infrastructure.database.repositories.user_platform_repository import (
    SqlAlchemyUserPlatformStore,
)
from app.infrastructure.persistence.session import reset_sync_engine
from app.infrastructure.persistence.stores import CONSENT_RECORDS
from app.privacy.lifecycle import ACCOUNT_DELETE_CONFIRMATION, AccountLifecycleService
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def sqlite_factory(tmp_path: Path):
    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'sprint28-consent.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield factory
    engine.dispose()
    reset_sync_engine()


def _user(user_id: str, email: str) -> User:
    now = datetime.now(UTC)
    return User(
        user_id=user_id,
        email=email,
        password_hash="hashed",
        display_name="Tester",
        created_at=now,
        updated_at=now,
    )


def _consent(user_id: str, *, record_id: str = "c1") -> PolicyAcceptanceRecord:
    return PolicyAcceptanceRecord(
        record_id=record_id,
        user_id=user_id,
        policy_type="terms",
        version_id="terms-persist-v1",
        accepted_at=datetime.now(UTC),
        source="registration",
        actor=user_id,
    )


def test_consent_survives_restart_with_unique_identity(
    sqlite_factory: sessionmaker[Session],
) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    record = _consent("u-consent")
    saved = store.consents.save(record)
    assert saved.accepted_at == record.accepted_at

    restarted = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    loaded = restarted.consents.get("u-consent", "terms", "terms-persist-v1")
    assert loaded == record
    again = restarted.consents.save(
        PolicyAcceptanceRecord(
            record_id="c2",
            user_id="u-consent",
            policy_type="terms",
            version_id="terms-persist-v1",
            accepted_at=datetime.now(UTC),
            source="account",
        )
    )
    assert again.record_id == "c1"
    assert again.accepted_at == record.accepted_at

    with sqlite_factory() as session:
        rows = session.scalars(
            select(OperationalEntityModel).where(OperationalEntityModel.store == CONSENT_RECORDS)
        ).all()
        assert len(rows) == 1
        assert rows[0].secondary_key == record.identity_key
        assert rows[0].owner_id == "u-consent"


def test_sql_deletion_removes_consents_and_leaves_early_access(
    sqlite_factory: sessionmaker[Session],
) -> None:
    store = SqlAlchemyUserPlatformStore(session_factory=sqlite_factory)
    early_access = SqlAlchemyEarlyAccessRepository(session_factory=sqlite_factory)
    user = _user("u-del", "same@example.com")
    store.users.save(user)
    store.consents.save(_consent("u-del"))
    now = datetime.now(UTC)
    early_access.create_if_absent(
        EarlyAccessRegistration(
            id="ea-1",
            full_name="Same Person",
            email="same@example.com",
            normalized_email="same@example.com",
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
            created_at=now,
            updated_at=now,
        )
    )

    lifecycle = AccountLifecycleService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        saved=store.saved,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        audit=AuditLogger(store.audit),
    )
    result = lifecycle.delete_account(user, confirmation=ACCOUNT_DELETE_CONFIRMATION)
    assert result.status == "deleted"
    assert result.consent_records_deleted == 1
    assert store.users.get_by_id("u-del") is None
    assert store.consents.list_for_user("u-del") == []
    remaining = early_access.get_by_normalized_email("same@example.com")
    assert remaining is not None
    assert remaining.email == "same@example.com"
