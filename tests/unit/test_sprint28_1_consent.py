"""Sprint 28.1 consent / policy-version persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import get_user_platform_service
from app.domain.entities.user_platform import PolicyAcceptanceRecord
from app.domain.exceptions import UserPlatformValidationError
from app.legal.publication import LegalPublicationCatalog, PolicyVersion, published_policy
from app.main import create_app
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

TEST_TERMS_VERSION = "test-terms-published-v1"
TEST_PRIVACY_VERSION = "test-privacy-published-v1"
TEST_TERMS_V2 = "test-terms-published-v2"


def _approved_html(path: Path, title: str) -> Path:
    path.write_text(f"<html><body><h1>{title}</h1></body></html>", encoding="utf-8")
    return path


def _published_catalog(tmp_path: Path) -> LegalPublicationCatalog:
    _approved_html(tmp_path / "terms.html", "Approved Terms")
    _approved_html(tmp_path / "privacy.html", "Approved Privacy")
    return LegalPublicationCatalog(
        (
            published_policy(
                policy_type="terms",
                version_id=TEST_TERMS_VERSION,
                html_path="terms.html",
            ),
            published_policy(
                policy_type="privacy",
                version_id=TEST_PRIVACY_VERSION,
                html_path="privacy.html",
            ),
        ),
        publication_root=tmp_path,
    )


def _auth(store: InMemoryUserPlatformStore, catalog=None) -> AuthService:
    return AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        legal_catalog=catalog,
        audit=AuditLogger(store.audit),
    )


def test_unpublished_policy_cannot_be_accepted() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store)
    result = auth.register(
        email="no-accept@example.com",
        password="ValidPass123!",
        display_name="NoAccept",
    )
    with pytest.raises(UserPlatformValidationError, match="No published policy"):
        auth.accept_published_policy(result.user.user_id, "terms", source="account")
    assert store.consents.list_for_user(result.user.user_id) == []


def test_approved_but_unpublished_cannot_satisfy_register(tmp_path: Path) -> None:
    _approved_html(tmp_path / "terms.html", "Approved Terms")
    _approved_html(tmp_path / "privacy.html", "Approved Privacy")
    catalog = LegalPublicationCatalog(
        (
            PolicyVersion(
                policy_type="terms",
                version_id="terms-approved-only",
                publication_status="approved",
                acceptance_required=True,
                html_path="terms.html",
            ),
            PolicyVersion(
                policy_type="privacy",
                version_id="privacy-approved-only",
                publication_status="approved",
                acceptance_required=True,
                html_path="privacy.html",
            ),
        ),
        publication_root=tmp_path,
    )
    store = InMemoryUserPlatformStore()
    auth = _auth(store, catalog)
    result = auth.register(
        email="approved-only@example.com",
        password="ValidPass123!",
        display_name="ApprovedOnly",
        terms_accepted=False,
        privacy_acknowledged=False,
    )
    assert store.consents.list_for_user(result.user.user_id) == []
    with pytest.raises(UserPlatformValidationError, match="No published policy"):
        auth.accept_published_policy(result.user.user_id, "terms", source="account")


def test_unpublished_policy_cannot_be_enforced() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store)
    result = auth.register(
        email="open-reg@example.com",
        password="ValidPass123!",
        display_name="Open",
        terms_accepted=False,
        privacy_acknowledged=False,
    )
    assert result.user.user_id
    assert store.consents.list_for_user(result.user.user_id) == []


def test_unpublished_register_does_not_store_fake_terms_or_privacy() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store)
    result = auth.register(
        email="fresh@example.com",
        password="ValidPass123!",
        display_name="Fresh",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    assert store.consents.list_for_user(result.user.user_id) == []
    events = [e.event_type for e in store.audit.list_events(user_id=result.user.user_id)]
    assert "policy_accepted" not in events


def test_api_ignores_client_supplied_policy_version_ids() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store)
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        consents=store.consents,
        audit=AuditLogger(store.audit),
    )
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "version-spoof@example.com",
            "password": "ValidPass123!",
            "display_name": "Spoof",
            "terms_accepted": True,
            "privacy_acknowledged": True,
            "terms_version_id": "fake-v9",
            "privacy_version_id": "also-fake",
            "published_version_id": "nope",
        },
    )
    assert response.status_code == 201
    user_id = response.json()["user"]["user_id"]
    assert store.consents.list_for_user(user_id) == []
    app.dependency_overrides.clear()


def test_published_catalog_requires_explicit_acceptance(tmp_path: Path) -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, _published_catalog(tmp_path))
    with pytest.raises(UserPlatformValidationError, match="Terms of Service"):
        auth.register(
            email="refuse-terms@example.com",
            password="ValidPass123!",
            display_name="Refuse",
            terms_accepted=False,
            privacy_acknowledged=True,
        )
    with pytest.raises(UserPlatformValidationError, match="Privacy Policy"):
        auth.register(
            email="refuse-privacy@example.com",
            password="ValidPass123!",
            display_name="Refuse",
            terms_accepted=True,
            privacy_acknowledged=False,
        )
    assert store.users.get_by_email("refuse-terms@example.com") is None
    assert store.users.get_by_email("refuse-privacy@example.com") is None


def test_published_acceptance_stores_exact_version_and_timestamp(tmp_path: Path) -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, _published_catalog(tmp_path))
    before = datetime.now(UTC)
    result = auth.register(
        email="accepted@example.com",
        password="ValidPass123!",
        display_name="Accepted",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    after = datetime.now(UTC)
    records = store.consents.list_for_user(result.user.user_id)
    by_type = {record.policy_type: record for record in records}
    assert set(by_type) == {"terms", "privacy"}
    assert by_type["terms"].version_id == TEST_TERMS_VERSION
    assert by_type["privacy"].version_id == TEST_PRIVACY_VERSION
    assert before <= by_type["terms"].accepted_at <= after
    assert before <= by_type["privacy"].accepted_at <= after
    assert by_type["terms"].source == "registration"
    assert by_type["terms"].actor == result.user.user_id
    events = store.audit.list_events(user_id=result.user.user_id)
    assert any(event.event_type == "policy_accepted" for event in events)


def test_duplicate_acceptance_is_first_write_wins(tmp_path: Path) -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, _published_catalog(tmp_path))
    result = auth.register(
        email="dup@example.com",
        password="ValidPass123!",
        display_name="Dup",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    first = store.consents.get(result.user.user_id, "terms", TEST_TERMS_VERSION)
    assert first is not None
    second = auth.accept_published_policy(result.user.user_id, "terms", source="account")
    assert second.record_id == first.record_id
    assert second.accepted_at == first.accepted_at
    records = [
        r for r in store.consents.list_for_user(result.user.user_id) if r.policy_type == "terms"
    ]
    assert len(records) == 1


def test_one_policy_version_does_not_satisfy_another(tmp_path: Path) -> None:
    catalog = _published_catalog(tmp_path)
    store = InMemoryUserPlatformStore()
    auth = _auth(store, catalog)
    result = auth.register(
        email="versioned@example.com",
        password="ValidPass123!",
        display_name="Versioned",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    assert auth.has_accepted(result.user.user_id, "terms", TEST_TERMS_VERSION)
    assert not auth.has_accepted(result.user.user_id, "terms", TEST_TERMS_V2)
    assert not auth.has_accepted(result.user.user_id, "privacy", TEST_TERMS_VERSION)


def test_newsletter_remains_separate_from_legal_consent(tmp_path: Path) -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, _published_catalog(tmp_path))
    result = auth.register(
        email="news@example.com",
        password="ValidPass123!",
        display_name="News",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    settings = store.profiles.get_settings(result.user.user_id)
    assert settings is not None
    assert settings.notification_settings is not None
    assert settings.notification_settings.newsletter is False
    consents = store.consents.list_for_user(result.user.user_id)
    legal_types = {record.policy_type for record in consents}
    assert "newsletter" not in legal_types
    assert "marketing" not in legal_types


def test_test_catalog_does_not_mutate_production_catalog(tmp_path: Path) -> None:
    from app.legal.publication import unpublished_catalog

    published = _published_catalog(tmp_path)
    assert published.is_published("terms")
    production = unpublished_catalog()
    assert production.published("terms") is None
    assert production.published("privacy") is None


def test_consent_record_sql_roundtrip(tmp_path: Path) -> None:
    from app.infrastructure.database.models.operational_entity import OperationalEntityModel
    from app.infrastructure.database.repositories.user_platform_repository import (
        SqlAlchemyUserPlatformStore,
    )
    from app.infrastructure.persistence.session import reset_sync_engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    reset_sync_engine()
    engine = create_engine(f"sqlite:///{tmp_path / 'consent.db'}", future=True)
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    store = SqlAlchemyUserPlatformStore(session_factory=factory)
    now = datetime.now(UTC)
    record = PolicyAcceptanceRecord(
        record_id="c1",
        user_id="u-consent",
        policy_type="terms",
        version_id=TEST_TERMS_VERSION,
        accepted_at=now,
        source="registration",
        actor="u-consent",
    )
    store.consents.save(record)
    listed = store.consents.list_for_user("u-consent")
    assert listed == [record]
    again = store.consents.save(
        PolicyAcceptanceRecord(
            record_id="c2",
            user_id="u-consent",
            policy_type="terms",
            version_id=TEST_TERMS_VERSION,
            accepted_at=now,
            source="account",
        )
    )
    assert again.record_id == "c1"
    assert store.consents.delete_for_user("u-consent") == 1
    assert store.consents.list_for_user("u-consent") == []
    engine.dispose()
    reset_sync_engine()
