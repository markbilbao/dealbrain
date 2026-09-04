"""Sprint 28.1 legal publication gate — unpublished by default, drafts never served."""

from __future__ import annotations

from pathlib import Path

from app.core.dependencies import get_legal_publication_catalog
from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
    LegalPublicationCatalog,
    PolicyVersion,
    catalog_from_settings,
    looks_like_counsel_draft,
    published_policy,
    unpublished_catalog,
)
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
PRIVACY_DRAFT = ROOT / "docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md"
TERMS_DRAFT = ROOT / "docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md"


def test_production_catalog_has_no_published_versions() -> None:
    from app.core.config import Settings

    catalog = catalog_from_settings(Settings())
    assert catalog.published("terms") is None
    assert catalog.published("privacy") is None
    assert unpublished_catalog().published("terms") is None


def test_privacy_and_terms_are_404_when_unpublished() -> None:
    client = TestClient(create_app())
    privacy = client.get("/privacy")
    terms = client.get("/terms")
    assert privacy.status_code == 404
    assert terms.status_code == 404
    for body in (privacy.text, terms.text):
        for marker in COUNSEL_DRAFT_CONTENT_MARKERS:
            assert marker not in body
        assert "[COUNSEL TO CONFIRM]" not in body


def test_counsel_draft_files_are_not_publicly_routed() -> None:
    client = TestClient(create_app())
    relative_privacy = PRIVACY_DRAFT.relative_to(ROOT).as_posix()
    relative_terms = TERMS_DRAFT.relative_to(ROOT).as_posix()
    for path in (
        f"/{relative_privacy}",
        f"/{relative_terms}",
        "/static/early_access/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md",
        "/static/consumer/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md",
        "/docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md",
        "/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md",
    ):
        response = client.get(path)
        assert response.status_code in {404, 405, 307, 308}
        for marker in COUNSEL_DRAFT_CONTENT_MARKERS:
            assert marker not in response.text


def test_counsel_draft_path_cannot_be_published() -> None:
    catalog = LegalPublicationCatalog(
        (
            published_policy(
                policy_type="privacy",
                version_id="should-not-publish",
                html_path=str(PRIVACY_DRAFT),
            ),
        )
    )
    assert catalog.published("privacy") is None
    assert looks_like_counsel_draft(PRIVACY_DRAFT.read_text(encoding="utf-8"))


def test_approved_but_not_published_is_not_served(tmp_path: Path) -> None:
    html = tmp_path / "privacy.html"
    html.write_text("<html><body><h1>Approved Privacy</h1></body></html>", encoding="utf-8")
    catalog = LegalPublicationCatalog(
        (
            PolicyVersion(
                policy_type="privacy",
                version_id="privacy-approved-only",
                publication_status="approved",
                acceptance_required=True,
                html_path=str(html),
                public_path="/privacy",
            ),
        )
    )
    assert catalog.published("privacy") is None
    app = create_app()
    app.dependency_overrides[get_legal_publication_catalog] = lambda: catalog
    client = TestClient(app)
    response = client.get("/privacy")
    assert response.status_code == 404
    assert "Approved Privacy" not in response.text
    app.dependency_overrides.clear()


def test_published_test_catalog_serves_approved_html_only(tmp_path: Path) -> None:
    html = tmp_path / "privacy.html"
    html.write_text("<html><body><h1>Approved Privacy</h1></body></html>", encoding="utf-8")
    catalog = LegalPublicationCatalog(
        (
            published_policy(
                policy_type="privacy",
                version_id="privacy-test-v1",
                html_path=str(html),
            ),
        )
    )
    app = create_app()
    app.dependency_overrides[get_legal_publication_catalog] = lambda: catalog
    client = TestClient(app)
    response = client.get("/privacy")
    assert response.status_code == 200
    assert "Approved Privacy" in response.text
    assert "DRAFT — COUNSEL REVIEW REQUIRED" not in response.text
    assert unpublished_catalog().published("privacy") is None
    app.dependency_overrides.clear()


def test_no_public_approved_claim_on_unpublished_routes() -> None:
    client = TestClient(create_app())
    for path in ("/privacy", "/terms", "/"):
        body = client.get(path).text.lower()
        assert "approved privacy policy" not in body
        assert "approved terms of service" not in body
