"""Sprint 29 registration UI must follow the Sprint 28 legal catalog."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.consumer.account_pages import render_register_page
from app.core.dependencies import get_legal_publication_catalog, get_user_platform_store
from app.domain.exceptions import UserPlatformValidationError
from app.legal.publication import LegalPublicationCatalog, published_policy, unpublished_catalog
from app.main import create_app
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient
from httpx import AsyncClient

TEST_TERMS_VERSION = "test-terms-published-v1"
TEST_PRIVACY_VERSION = "test-privacy-published-v1"


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


def test_unpublished_register_html_has_no_required_acceptance() -> None:
    html = render_register_page(next_path="/account", catalog=unpublished_catalog())
    assert 'name="terms_accepted"' not in html
    assert 'name="privacy_acknowledged"' not in html
    assert "I accept the" not in html
    assert "I acknowledge the" not in html
    assert 'data-legal-unpublished="true"' in html
    assert "not published yet" in html


@pytest.mark.asyncio
async def test_live_register_route_uses_unpublished_production_catalog(
    client: AsyncClient,
) -> None:
    response = await client.get("/register")
    assert response.status_code == 200
    assert 'name="terms_accepted"' not in response.text
    assert 'name="privacy_acknowledged"' not in response.text
    assert "I accept the Terms of Service" not in response.text
    assert 'data-legal-unpublished="true"' in response.text


@pytest.mark.asyncio
async def test_unpublished_registration_succeeds_with_false_acceptance(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sprint29-unpublished-legal@example.invalid",
            "password": "Password123",
            "display_name": "Unpublished Legal",
            "terms_accepted": False,
            "privacy_acknowledged": False,
        },
    )
    assert created.status_code == 201
    user_id = created.json()["user"]["user_id"]
    store = get_user_platform_store()
    assert store.consents.list_for_user(user_id) == []


def test_unpublished_true_flags_still_create_no_consent_record() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, unpublished_catalog())
    result = auth.register(
        email="unchecked-truth@example.com",
        password="ValidPass123!",
        display_name="NoConsent",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    assert store.consents.list_for_user(result.user.user_id) == []


def test_published_catalog_register_ui_uses_server_versions(tmp_path: Path) -> None:
    catalog = _published_catalog(tmp_path)
    html = render_register_page(next_path="/account", catalog=catalog)
    assert 'name="terms_accepted"' in html
    assert 'name="privacy_acknowledged"' in html
    assert 'href="/terms"' in html
    assert 'href="/privacy"' in html
    assert TEST_TERMS_VERSION in html
    assert TEST_PRIVACY_VERSION in html
    assert 'data-legal-unpublished="true"' not in html

    app = create_app()
    app.dependency_overrides[get_legal_publication_catalog] = lambda: catalog
    client = TestClient(app)
    response = client.get("/register")
    assert response.status_code == 200
    assert 'name="terms_accepted"' in response.text
    assert TEST_TERMS_VERSION in response.text
    assert TEST_PRIVACY_VERSION in response.text
    app.dependency_overrides.clear()


def test_published_catalog_still_owns_registration_enforcement(tmp_path: Path) -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, _published_catalog(tmp_path))
    with pytest.raises(UserPlatformValidationError, match="Terms of Service"):
        auth.register(
            email="refuse-terms-ui@example.com",
            password="ValidPass123!",
            display_name="Refuse",
            terms_accepted=False,
            privacy_acknowledged=True,
        )
    with pytest.raises(UserPlatformValidationError, match="Privacy Policy"):
        auth.register(
            email="refuse-privacy-ui@example.com",
            password="ValidPass123!",
            display_name="Refuse",
            terms_accepted=True,
            privacy_acknowledged=False,
        )
    accepted = auth.register(
        email="accepted-ui@example.com",
        password="ValidPass123!",
        display_name="Accepted",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    records = store.consents.list_for_user(accepted.user.user_id)
    assert {record.policy_type for record in records} == {"terms", "privacy"}
    assert {record.version_id for record in records} == {TEST_TERMS_VERSION, TEST_PRIVACY_VERSION}
