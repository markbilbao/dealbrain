"""Sprint 28 remaining internal readiness — audit, tracking, eligibility, contacts."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.config import Settings
from app.core.public_brand import PUBLIC_PRIVACY_EMAIL, PUBLIC_SUPPORT_EMAIL
from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
    LegalPublicationCatalog,
    catalog_from_settings,
    default_legal_publication_root,
    published_policy,
    unpublished_catalog,
)
from app.privacy.consent_audit import (
    CONSUMER_EMPTY_NOTE,
    OPERATOR_NOT_DSAR_NOTE,
    OPERATOR_UNPUBLISHED_NOTE,
    inspect_consent,
    operator_publication_snapshot,
    publication_status_payload,
)
from app.privacy.eligibility import (
    age_policy_published,
    collects_date_of_birth,
    country_notices_published,
    eligibility_snapshot,
    minimum_age_years,
)
from app.privacy.tracking import (
    HTML_TRACKING_MODE_ATTR,
    category_allowed,
    non_essential_tracking_allowed,
    tracking_mode,
    tracking_snapshot,
)
from app.user.memory import InMemoryUserPlatformStore
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]
TEST_TERMS_VERSION = "test-terms-published-v1"
TEST_PRIVACY_VERSION = "test-privacy-published-v1"
FORBIDDEN_AGE_COPY = ("must be 13", "must be 16", "must be 18", "at least 13", "at least 18")
INTERNAL_PUBLIC_API_FIELDS = (
    "counsel_drafts_are_not_public",
    "counsel_owned",
    "ext_22_status",
    "activation_owner",
)
CONSUMER_LEAK_PATTERNS = (
    r"\bSprint\b",
    r"\bEXT-\d+",
    r"\bDealBrain\b",
    r"\bcounsel\b",
    r"\bDSAR\b",
    r"engineering audit",
    r"activation_owner",
    r"\bnot_started\b",
    r"legal@piqsavi\.com",
    r"terms_accepted\s*=\s*false",
    r"privacy_acknowledged\s*=\s*false",
    r"\bHTTP 404\b",
    r"unpublished 404",
)


def _assert_no_consumer_leaks(surface: str, body: str) -> None:
    for pattern in CONSUMER_LEAK_PATTERNS:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        assert match is None, f"{surface} leaked {pattern!r} via {match.group(0)!r}"


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


def test_tracking_is_essential_only_and_non_essential_denied() -> None:
    assert tracking_mode() == "essential_only"
    assert category_allowed("essential") is True
    assert category_allowed("analytics") is False
    assert category_allowed("advertising") is False
    assert non_essential_tracking_allowed() is False
    snapshot = tracking_snapshot()
    assert snapshot["banner_implemented"] is False
    assert snapshot["cmp_vendor"] is None
    assert snapshot["analytics_provider"] is None
    assert snapshot["ext_22_status"] == "not_started"
    assert snapshot["activation_owner"] == "sprint_39"
    public = publication_status_payload(unpublished_catalog())
    for field in INTERNAL_PUBLIC_API_FIELDS:
        assert field not in public
    operator = operator_publication_snapshot(unpublished_catalog())
    assert operator["ext_22_status"] == "not_started"
    assert operator["activation_owner"] == "sprint_39"
    assert eligibility_snapshot()["counsel_owned"] is True


def test_eligibility_placeholders_do_not_invent_an_age() -> None:
    assert minimum_age_years() is None
    assert age_policy_published() is False
    assert collects_date_of_birth() is False
    assert country_notices_published() is False


def test_production_publication_status_is_published() -> None:
    payload = publication_status_payload(catalog_from_settings(Settings()))
    assert payload["terms_published"] is True
    assert payload["privacy_published"] is True
    assert payload["cookie_notice_published"] is False
    assert payload["support_contact"] == PUBLIC_SUPPORT_EMAIL
    assert payload["privacy_contact"] == PUBLIC_PRIVACY_EMAIL
    assert payload["non_essential_tracking_allowed"] is False
    assert payload["age_policy_published"] is False
    for field in INTERNAL_PUBLIC_API_FIELDS:
        assert field not in payload
    operator = operator_publication_snapshot(catalog_from_settings(Settings()))
    assert operator["counsel_drafts_are_not_public"] is True
    assert operator["counsel_owned"] is True


def test_published_directory_has_owner_authorized_html_only() -> None:
    root = default_legal_publication_root()
    assert root.is_dir()
    html_files = {path.name for path in root.glob("*.html")}
    assert html_files == {"privacy-2026-09-11.html", "terms-2026-09-11.html"}
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "counsel drafts" in readme.lower()
    assert "not a new counsel approval" in readme.lower()


def test_unpublished_inspect_consent_does_not_fabricate_records() -> None:
    store = InMemoryUserPlatformStore()
    auth = _auth(store, unpublished_catalog())
    result = auth.register(
        email="audit-empty@example.invalid",
        password="ValidPass123!",
        display_name="Empty Audit",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    snapshot = inspect_consent(
        user_id=result.user.user_id,
        catalog=unpublished_catalog(),
        consents=store.consents,
        audit=AuditLogger(store.audit),
    )
    assert snapshot.unpublished is True
    assert snapshot.records == ()
    assert snapshot.policy_accepted_events == ()
    assert CONSUMER_EMPTY_NOTE in snapshot.notes
    assert all("must not be fabricated" not in note for note in snapshot.notes)
    assert all("DSAR" not in note for note in snapshot.notes)
    assert "must not be fabricated" in OPERATOR_UNPUBLISHED_NOTE
    assert "not a complete legal DSAR" in OPERATOR_NOT_DSAR_NOTE


def test_published_inspect_consent_shows_owner_records_only(tmp_path: Path) -> None:
    catalog = _published_catalog(tmp_path)
    store = InMemoryUserPlatformStore()
    auth = _auth(store, catalog)
    subject = auth.register(
        email="audit-subject@example.invalid",
        password="ValidPass123!",
        display_name="Subject",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    other = auth.register(
        email="audit-other@example.invalid",
        password="ValidPass123!",
        display_name="Other",
        terms_accepted=True,
        privacy_acknowledged=True,
    )
    subject_view = inspect_consent(
        user_id=subject.user.user_id,
        catalog=catalog,
        consents=store.consents,
        audit=AuditLogger(store.audit),
    )
    other_view = inspect_consent(
        user_id=other.user.user_id,
        catalog=catalog,
        consents=store.consents,
        audit=AuditLogger(store.audit),
    )
    assert subject_view.unpublished is False
    types = {record["policy_type"] for record in subject_view.records}
    assert types == {"terms", "privacy"}
    assert all(record["user_id"] == subject.user.user_id for record in subject_view.records)
    assert all(record["user_id"] == other.user.user_id for record in other_view.records)
    assert {record["user_id"] for record in subject_view.records}.isdisjoint(
        {record["user_id"] for record in other_view.records}
    )


@pytest.mark.asyncio
async def test_publication_status_api_is_published(client: AsyncClient) -> None:
    response = await client.get("/api/v1/legal/publication-status")
    assert response.status_code == 200
    body = response.json()
    assert body["terms_published"] is True
    assert body["privacy_published"] is True
    assert body["non_essential_tracking_allowed"] is False
    assert body["banner_implemented"] is False
    assert body["support_contact"] == PUBLIC_SUPPORT_EMAIL
    assert "legal@piqsavi.com" not in json.dumps(body)
    for field in INTERNAL_PUBLIC_API_FIELDS:
        assert field not in body
    _assert_no_consumer_leaks("GET /api/v1/legal/publication-status", json.dumps(body))


@pytest.mark.asyncio
async def test_health_reports_published_legal_and_essential_only(
    client: AsyncClient,
) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert checks["legal_terms_published"] is True
    assert checks["legal_privacy_published"] is True
    assert checks["tracking_mode"] == "essential_only"
    assert checks["non_essential_tracking_allowed"] is False
    assert checks["minimum_age_policy_published"] is False


@pytest.mark.asyncio
async def test_account_consents_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/account/consents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_account_consents_record_published_acceptance(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sprint28-consents-empty@example.invalid",
            "password": "Password123",
            "display_name": "Consents Empty",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert created.status_code == 201
    token = created.json()["access_token"]
    response = await client.get(
        "/api/v1/auth/account/consents",
        headers={"Authorization": f"Bearer {token}"},
        params={"user_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == created.json()["user"]["user_id"]
    assert body["unpublished"] is False
    assert {record["policy_type"] for record in body["records"]} == {"terms", "privacy"}
    assert CONSUMER_EMPTY_NOTE not in body["notes"]
    assert all("DSAR" not in note for note in body["notes"])
    assert all("must not be fabricated" not in note for note in body["notes"])


@pytest.mark.asyncio
async def test_account_consents_ignores_foreign_user_id(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sprint28-consents-http@example.invalid",
            "password": "Password123",
            "display_name": "HTTP Consents",
            "terms_accepted": True,
            "privacy_acknowledged": True,
        },
    )
    assert created.status_code == 201
    token = created.json()["access_token"]
    other_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    response = await client.get(
        "/api/v1/auth/account/consents",
        headers={"Authorization": f"Bearer {token}"},
        params={"user_id": other_id},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == created.json()["user"]["user_id"]
    assert body["user_id"] != other_id
    assert body["records"]
    assert all(record["user_id"] == body["user_id"] for record in body["records"])
    assert all(record["user_id"] != other_id for record in body["records"])


@pytest.mark.asyncio
async def test_support_page_uses_provisioned_contacts_only(client: AsyncClient) -> None:
    page = await client.get("/support")
    assert page.status_code == 200
    assert PUBLIC_SUPPORT_EMAIL in page.text
    assert PUBLIC_PRIVACY_EMAIL in page.text
    assert f"mailto:{PUBLIC_SUPPORT_EMAIL}" in page.text
    assert f"mailto:{PUBLIC_PRIVACY_EMAIL}" in page.text
    assert "mailto:legal@piqsavi.com" not in page.text
    assert "not listed as a live contact" not in page.text
    assert "Sprint 39" not in page.text
    assert f'data-tracking-mode="{HTML_TRACKING_MODE_ATTR}"' in page.text
    _assert_no_consumer_leaks("GET /support", page.text)


@pytest.mark.asyncio
async def test_register_does_not_invent_age_or_dob(client: AsyncClient) -> None:
    page = await client.get("/register")
    assert page.status_code == 200
    assert 'data-eligibility-unpublished="true"' not in page.text
    assert "Legal policies are not yet available for this beta." not in page.text
    assert 'name="terms_accepted"' in page.text
    assert 'name="privacy_acknowledged"' in page.text
    assert "terms_accepted=false" not in page.text
    assert "privacy_acknowledged=false" not in page.text
    assert 'name="date_of_birth"' not in page.text
    assert 'name="dob"' not in page.text
    lower = page.text.lower()
    for phrase in FORBIDDEN_AGE_COPY:
        assert phrase not in lower


@pytest.mark.asyncio
async def test_account_settings_expose_consent_audit_surface(client: AsyncClient) -> None:
    page = await client.get("/account")
    assert page.status_code == 200
    assert 'id="consents"' in page.text
    assert "data-consent-records" in page.text
    assert "Your policy acknowledgements will appear here when applicable." in page.text
    assert page.text.count(CONSUMER_EMPTY_NOTE) == 1
    assert "data-consent-unpublished hidden" in page.text
    assert "not a complete legal DSAR" not in page.text
    assert "engineering audit" not in page.text
    _assert_no_consumer_leaks("GET /account", page.text)


@pytest.mark.asyncio
async def test_private_pages_keep_published_legal_routes_without_drafts(
    client: AsyncClient,
) -> None:
    privacy = await client.get("/privacy")
    terms = await client.get("/terms")
    assert privacy.status_code == 200
    assert terms.status_code == 200
    for body in (privacy.text, terms.text):
        for marker in COUNSEL_DRAFT_CONTENT_MARKERS:
            assert marker not in body


def test_publication_status_script_prints_published_json() -> None:
    script = ROOT / "scripts/privacy/inspect_publication_status.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    payload = json.loads(result.stdout)
    assert payload["terms_published"] is True
    assert payload["privacy_published"] is True
    assert payload["non_essential_tracking_allowed"] is False
    assert payload["counsel_drafts_are_not_public"] is True
    assert payload["ext_22_status"] == "not_started"
    assert payload["activation_owner"] == "sprint_39"


@pytest.mark.asyncio
async def test_results_page_marks_essential_only_tracking(client: AsyncClient) -> None:
    page = await client.get("/results/headphones-standard")
    assert page.status_code == 200
    assert f'data-tracking-mode="{HTML_TRACKING_MODE_ATTR}"' in page.text
    assert "googletagmanager" not in page.text.lower()
    assert "gtag(" not in page.text.lower()


@pytest.mark.asyncio
async def test_consumer_html_and_public_legal_status_hide_internal_terms(
    client: AsyncClient,
) -> None:
    for path in ("/support", "/account", "/register", "/login"):
        page = await client.get(path)
        assert page.status_code == 200
        _assert_no_consumer_leaks(f"GET {path}", page.text)
    account_js = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
    _assert_no_consumer_leaks("account.js", account_js)
    response = await client.get("/api/v1/legal/publication-status")
    assert response.status_code == 200
    _assert_no_consumer_leaks(
        "GET /api/v1/legal/publication-status",
        json.dumps(response.json()),
    )


def test_openapi_publication_status_omits_internal_fields() -> None:
    from app.main import create_app

    schema = create_app().openapi()
    props = schema["components"]["schemas"]["LegalPublicationStatusResponse"]["properties"]
    for field in INTERNAL_PUBLIC_API_FIELDS:
        assert field not in props
    description = schema["paths"]["/api/v1/legal/publication-status"]["get"]["description"]
    _assert_no_consumer_leaks("openapi publication-status description", description)
    schema_description = schema["components"]["schemas"]["LegalPublicationStatusResponse"].get(
        "description", ""
    )
    _assert_no_consumer_leaks("openapi LegalPublicationStatusResponse", schema_description)
