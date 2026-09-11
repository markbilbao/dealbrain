"""Owner-authorized Early Access legal/content-layer activation contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.dependencies import get_early_access_service
from app.domain.entities.early_access import EarlyAccessRegistration
from app.early_access.memory import InMemoryEarlyAccessRepository
from app.infrastructure.persistence.codec import decode_entity, encode_entity
from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
    OWNER_AUTHORIZED_PRIVACY_VERSION_ID,
    OWNER_AUTHORIZED_TERMS_VERSION_ID,
    catalog_from_settings,
    default_legal_publication_root,
    looks_like_counsel_draft,
    unpublished_catalog,
)
from app.main import create_app
from app.privacy.tracking import non_essential_tracking_allowed, tracking_mode
from app.services.early_access_service import EarlyAccessService
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app/static/early_access/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/early_access/early-access.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/early_access/early-access.css").read_text(encoding="utf-8")
PRIVACY_HTML = (
    ROOT / "docs/legal/published/privacy-2026-09-11.html"
).read_text(encoding="utf-8")
TERMS_HTML = (ROOT / "docs/legal/published/terms-2026-09-11.html").read_text(encoding="utf-8")
EVIDENCE = (
    ROOT / "docs/roadmap/evidence/EARLY_ACCESS_OWNER_AUTHORIZED_LEGAL_ACTIVATION_2026-09-11.md"
).read_text(encoding="utf-8")
COOKIE_NOTICE = (
    ROOT / "docs/legal/PIQSAVI_COOKIE_TRACKING_NOTICE_FACTUAL_CURRENTNESS_2026-09-11.md"
).read_text(encoding="utf-8")

DRAFT_MARKERS = (
    *COUNSEL_DRAFT_CONTENT_MARKERS,
    "[COUNSEL TO CONFIRM]",
    "DRAFT — COUNSEL REVIEW REQUIRED",
    "Not for publication",
)


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "country": "PH",
        "shopping_interest": "phones",
        "policies_acknowledged": True,
    }
    body.update(overrides)
    return body


def _client(repo: InMemoryEarlyAccessRepository | None = None) -> TestClient:
    app = create_app()
    if repo is not None:
        app.dependency_overrides[get_early_access_service] = lambda: EarlyAccessService(repo)
    return TestClient(app)


def test_privacy_and_terms_are_published_with_stable_version_ids() -> None:
    from app.core.config import Settings

    catalog = catalog_from_settings(Settings())
    assert catalog.published("privacy") is not None
    assert catalog.published("terms") is not None
    assert catalog.published_version_id("privacy") == OWNER_AUTHORIZED_PRIVACY_VERSION_ID
    assert catalog.published_version_id("terms") == OWNER_AUTHORIZED_TERMS_VERSION_ID
    client = TestClient(create_app())
    privacy = client.get("/privacy")
    terms = client.get("/terms")
    assert privacy.status_code == 200
    assert terms.status_code == 200
    assert OWNER_AUTHORIZED_PRIVACY_VERSION_ID in privacy.text
    assert OWNER_AUTHORIZED_TERMS_VERSION_ID in terms.text
    assert "Effective date: 11 September 2026" in privacy.text
    assert "Publication date: 11 September 2026" in privacy.text
    assert "Effective date: 11 September 2026" in terms.text
    assert "privacy@piqsavi.com" in privacy.text
    assert "support@piqsavi.com" in terms.text
    for body in (privacy.text, terms.text):
        for marker in DRAFT_MARKERS:
            assert marker not in body


def test_unpublished_catalog_still_fail_closes() -> None:
    catalog = unpublished_catalog()
    assert catalog.published("privacy") is None
    assert catalog.published("terms") is None
    app = create_app()
    from app.core.dependencies import get_legal_publication_catalog

    app.dependency_overrides[get_legal_publication_catalog] = unpublished_catalog
    client = TestClient(app)
    assert client.get("/privacy").status_code == 404
    assert client.get("/terms").status_code == 404
    app.dependency_overrides.clear()


def test_working_drafts_and_counsel_drafts_are_not_served() -> None:
    client = TestClient(create_app())
    for path in (
        "/docs/legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md",
        "/docs/legal/PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT.md",
        "/docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md",
        "/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md",
        "/static/early_access/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md",
    ):
        response = client.get(path)
        assert response.status_code in {404, 405, 307, 308}
        for marker in COUNSEL_DRAFT_CONTENT_MARKERS:
            assert marker not in response.text
    assert looks_like_counsel_draft(
        (ROOT / "docs/legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md").read_text(encoding="utf-8")
    )
    assert looks_like_counsel_draft(PRIVACY_HTML) is False
    assert looks_like_counsel_draft(TERMS_HTML) is False


def test_published_html_lives_only_under_publication_root() -> None:
    root = default_legal_publication_root()
    assert (root / "privacy-2026-09-11.html").is_file()
    assert (root / "terms-2026-09-11.html").is_file()
    assert "self-service account deletion" in PRIVACY_HTML
    assert "account-owned personal-data export" in PRIVACY_HTML
    assert "piqsavi_decision_owner" in PRIVACY_HTML
    assert "localStorage" in PRIVACY_HTML
    assert "self-service account deletion" in TERMS_HTML
    assert "governing law" not in TERMS_HTML.lower()
    assert "indemnif" not in TERMS_HTML.lower()
    assert "liability cap" not in TERMS_HTML.lower()


def test_early_access_footer_links_are_active() -> None:
    assert 'href="/privacy"' in HTML
    assert 'href="/terms"' in HTML
    assert "data-legal-gated" not in HTML
    assert 'aria-disabled="true"' not in HTML
    client = TestClient(create_app())
    page = client.get("/").text
    assert 'href="/privacy"' in page
    assert 'href="/terms"' in page
    assert "data-legal-gated" not in page
    assert 'aria-disabled="true"' not in page


def test_checkbox_is_unchecked_required_and_separate_from_updates_note() -> None:
    assert 'name="policies_acknowledged"' in HTML
    assert 'id="ea-policies-acknowledged"' in HTML
    assert 'type="checkbox"' in HTML
    assert "checked" not in HTML.split('id="ea-policies-acknowledged"', 1)[1].split(">", 1)[0]
    assert "I agree to the" in HTML
    assert 'href="/terms">Terms of Service</a>' in HTML
    assert 'href="/privacy">Privacy Policy</a>' in HTML
    assert "No spam. Just important PiqSavi early-access updates." in HTML
    assert HTML.index("policies_acknowledged") < HTML.index(
        "No spam. Just important PiqSavi early-access updates."
    )
    assert "marketing" not in HTML.lower()
    assert "affiliate tracking" not in HTML.lower()
    assert "data sale" not in HTML.lower()
    assert "newsletter" not in HTML.lower()
    assert "err-policies-acknowledged" in HTML
    assert 'for="ea-policies-acknowledged"' in HTML
    assert "if (!values.policies_acknowledged)" in JS
    assert "field-ack" in CSS


def test_signup_fails_without_acknowledgement() -> None:
    repo = InMemoryEarlyAccessRepository()
    client = _client(repo)
    response = client.post("/api/v1/early-access", json=_payload(policies_acknowledged=False))
    assert response.status_code == 400
    assert "Terms of Service" in response.text
    assert repo.list_all() == []


def test_signup_succeeds_and_persists_versions_and_timestamp() -> None:
    repo = InMemoryEarlyAccessRepository()
    before = datetime.now(UTC)
    client = _client(repo)
    response = client.post("/api/v1/early-access", json=_payload())
    after = datetime.now(UTC)
    assert response.status_code == 200
    assert response.json()["outcome"] == "success"
    stored = repo.list_all()
    assert len(stored) == 1
    record = stored[0]
    assert record.terms_version_id == OWNER_AUTHORIZED_TERMS_VERSION_ID
    assert record.privacy_version_id == OWNER_AUTHORIZED_PRIVACY_VERSION_ID
    assert record.policies_acknowledged_at is not None
    assert before <= record.policies_acknowledged_at <= after
    assert record.email == "ada@example.com"


def test_client_cannot_supply_policy_versions() -> None:
    repo = InMemoryEarlyAccessRepository()
    client = _client(repo)
    response = client.post(
        "/api/v1/early-access",
        json=_payload(terms_version_id="fake-terms", privacy_version_id="fake-privacy"),
    )
    assert response.status_code == 200
    record = repo.list_all()[0]
    assert record.terms_version_id == OWNER_AUTHORIZED_TERMS_VERSION_ID
    assert record.privacy_version_id == OWNER_AUTHORIZED_PRIVACY_VERSION_ID


def test_historical_signups_are_not_backfilled() -> None:
    stamp = datetime(2026, 8, 1, tzinfo=UTC)
    historical = EarlyAccessRegistration(
        id="hist-1",
        full_name="Historical User",
        email="old@example.com",
        normalized_email="old@example.com",
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
    encoded = encode_entity(historical)
    encoded["fields"].pop("terms_version_id", None)
    encoded["fields"].pop("privacy_version_id", None)
    encoded["fields"].pop("policies_acknowledged_at", None)
    loaded = decode_entity(EarlyAccessRegistration, encoded)
    assert loaded.terms_version_id is None
    assert loaded.privacy_version_id is None
    assert loaded.policies_acknowledged_at is None
    repo = InMemoryEarlyAccessRepository()
    repo.create_if_absent(loaded)
    client = _client(repo)
    duplicate = client.post(
        "/api/v1/early-access",
        json=_payload(email="old@example.com", full_name="Someone Else"),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["outcome"] == "already_registered"
    stored = repo.get_by_normalized_email("old@example.com")
    assert stored is not None
    assert stored.terms_version_id is None
    assert stored.privacy_version_id is None
    assert stored.policies_acknowledged_at is None


def test_no_marketing_consent_or_tracking_introduced() -> None:
    assert tracking_mode() == "essential_only"
    assert non_essential_tracking_allowed() is False
    status = TestClient(create_app()).get("/api/v1/legal/publication-status").json()
    assert status["non_essential_tracking_allowed"] is False
    assert status["banner_implemented"] is False
    assert status["analytics_provider"] is None
    assert status["cmp_vendor"] is None
    assert "google analytics" not in HTML.lower()
    assert "gtm" not in HTML.lower()
    assert "affiliate=" not in HTML.lower()
    assert "No spam. Just important PiqSavi early-access updates." in HTML
    assert "subscribe" not in HTML.lower()
    assert "piqsavi_decision_owner" in COOKIE_NOTICE
    assert "Google Analytics" in COOKIE_NOTICE
    assert "does not currently operate a cookie-consent banner" in COOKIE_NOTICE


def test_demo_and_unfinished_shopping_remain_hidden() -> None:
    lowered = HTML.lower()
    assert "/demo" not in HTML
    assert "/search" not in HTML
    assert "/results" not in HTML
    assert "shopee" not in lowered
    assert "lazada" not in lowered
    page = TestClient(create_app()).get("/").text
    assert "/demo" not in page
    assert "shopee" not in page.lower()
    assert "lazada" not in page.lower()


def test_acceptance_logs_are_not_public() -> None:
    client = TestClient(create_app())
    for path in (
        "/api/v1/early-access",
        "/api/v1/early-access/",
        "/api/v1/early-access/export",
        "/api/v1/early-access/registrations",
        "/api/v1/early-access/acknowledgements",
    ):
        response = client.get(path)
        assert response.status_code in {404, 405}


def test_evidence_records_owner_authorization_not_new_counsel_approval() -> None:
    assert "owner-authorized implementation decisions" in EVIDENCE
    assert "does **not** mean counsel gave new unconditional approval" in EVIDENCE
    assert OWNER_AUTHORIZED_PRIVACY_VERSION_ID in EVIDENCE
    assert OWNER_AUTHORIZED_TERMS_VERSION_ID in EVIDENCE
    assert (
        "EARLY ACCESS LEGAL/CONTENT LAYER READY — STAGING VERIFICATION REQUIRED"
        in EVIDENCE
    )
    assert "PRODUCTION INFRASTRUCTURE CUTOVER REMAINS" in EVIDENCE
    assert "No production deploy" in EVIDENCE
    assert "Do **not** merge" in EVIDENCE
