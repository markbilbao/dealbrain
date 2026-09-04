"""Sprint 28.1 personal-data export foundation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import get_user_platform_service
from app.domain.entities.user_platform import PolicyAcceptanceRecord
from app.legal.publication import LegalPublicationCatalog, published_policy
from app.main import create_app
from app.privacy.inventory import (
    EXPORT_SCHEMA,
    PERSONAL_DATA_EXPORT_CATEGORIES,
    SECURITY_FIELDS_EXCLUDED_FROM_EXPORT,
)
from app.privacy.lifecycle import ACCOUNT_DELETE_CONFIRMATION, AccountLifecycleService
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

PASSWORD = "ValidPass123!"


def _platform(store: InMemoryUserPlatformStore | None = None, *, catalog=None):
    store = store or InMemoryUserPlatformStore()
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        legal_catalog=catalog,
        audit=audit,
    )
    lifecycle = AccountLifecycleService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        saved=store.saved,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        audit=audit,
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        lifecycle=lifecycle,
        consents=store.consents,
        audit=audit,
    )
    return store, service


def _client(service: UserPlatformService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    return TestClient(app)


def test_unauthenticated_export_rejected() -> None:
    _store, service = _platform()
    client = _client(service)
    response = client.get("/api/v1/auth/account/export")
    assert response.status_code == 401


def test_export_contains_own_data_and_inventory_categories() -> None:
    store, service = _platform()
    other = service.register(
        email="other-export@example.com",
        password=PASSWORD,
        display_name="Other Person",
    )
    service.save_product(
        other.access_token,
        {"product_id": "secret-product", "product_name": "Should Not Leak"},
    )
    mine = service.register(
        email="mine-export@example.com",
        password=PASSWORD,
        display_name="Me",
    )
    service.save_product(
        mine.access_token,
        {"product_id": "my-product", "product_name": "My Headphones"},
    )
    client = _client(service)
    response = client.get(
        "/api/v1/auth/account/export",
        headers={"Authorization": f"Bearer {mine.access_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["export_schema"] == EXPORT_SCHEMA
    for category in PERSONAL_DATA_EXPORT_CATEGORIES:
        assert category in payload, category
    assert payload["account"]["email"] == "mine-export@example.com"
    assert payload["account"]["display_name"] == "Me"
    names = [item["product_name"] for item in payload["saved_products"]]
    assert "My Headphones" in names
    assert "Should Not Leak" not in names
    dumped = json.dumps(payload)
    assert "other-export@example.com" not in dumped
    assert "Other Person" not in dumped
    assert "secret-product" not in dumped
    for field in SECURITY_FIELDS_EXCLUDED_FROM_EXPORT:
        assert field not in dumped
    assert store.users.get_by_id(mine.user.user_id).password_hash not in dumped


def test_export_includes_consent_records(tmp_path: Path) -> None:
    html = tmp_path / "terms.html"
    html.write_text("<html><body><h1>Approved Terms</h1></body></html>", encoding="utf-8")
    catalog = LegalPublicationCatalog(
        (
            published_policy(
                policy_type="terms",
                version_id="export-terms-v1",
                html_path=str(html),
                acceptance_required=False,
            ),
        )
    )
    store, service = _platform(catalog=catalog)
    mine = service.register(email="consent-export@example.com", password=PASSWORD, display_name="C")
    store.consents.save(
        PolicyAcceptanceRecord(
            record_id=" cons-1".strip(),
            user_id=mine.user.user_id,
            policy_type="terms",
            version_id="export-terms-v1",
            accepted_at=datetime.now(UTC),
            source="test",
            actor=mine.user.user_id,
        )
    )
    client = _client(service)
    payload = client.get(
        "/api/v1/auth/account/export",
        headers={"Authorization": f"Bearer {mine.access_token}"},
    ).json()
    assert payload["consent_records"]
    assert payload["consent_records"][0]["version_id"] == "export-terms-v1"
    assert payload["consent_records"][0]["policy_type"] == "terms"


def test_export_does_not_include_raw_tokens() -> None:
    _store, service = _platform()
    mine = service.register(email="token-export@example.com", password=PASSWORD, display_name="Tok")
    client = _client(service)
    payload = client.get(
        "/api/v1/auth/account/export",
        headers={"Authorization": f"Bearer {mine.access_token}"},
    ).json()
    dumped = json.dumps(payload)
    assert mine.access_token not in dumped
    for session in payload["sessions"]:
        assert "token_hash" not in session
        assert "csrf_token" not in session


def test_deleted_account_cannot_export() -> None:
    _store, service = _platform()
    mine = service.register(email="gone-export@example.com", password=PASSWORD, display_name="Gone")
    client = _client(service)
    headers = {"Authorization": f"Bearer {mine.access_token}"}
    deleted = client.post(
        "/api/v1/auth/account/delete",
        json={"confirmation": ACCOUNT_DELETE_CONFIRMATION, "password": PASSWORD},
        headers=headers,
    )
    assert deleted.status_code == 200
    response = client.get("/api/v1/auth/account/export", headers=headers)
    assert response.status_code == 401
