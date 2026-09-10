"""Early Access counsel-reconciliation and launch-readiness contracts."""

from __future__ import annotations

from pathlib import Path

from app.legal.publication import (
    COUNSEL_DRAFT_CONTENT_MARKERS,
    catalog_from_settings,
    default_legal_publication_root,
)
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
REGISTER = (ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "docs/roadmap/evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md").read_text(
    encoding="utf-8"
)
READINESS = (
    ROOT
    / "docs/roadmap/evidence/EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md"
).read_text(encoding="utf-8")
HTML = (ROOT / "app/static/early_access/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/early_access/early-access.js").read_text(encoding="utf-8")
PUBLISHED = ROOT / "docs/legal/published"

EIGHT_DOCUMENTS = (
    "Data Processing & Product Behavior Spec",
    "Privacy Policy / Privacy Notice",
    "Terms of Service",
    "Affiliate & Advertising Disclosure",
    "AI & Recommendation Disclosure",
    "Cookie & Tracking Notice",
    "Account Deletion / Export / Retention",
    "Consumer & Marketplace Disclaimer",
)


def _status_cell(row_id: str) -> str:
    for line in REGISTER.splitlines():
        if line.startswith(f"| {row_id} |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            return cells[7]
    raise AssertionError(f"missing register row {row_id}")


def test_ext19_remains_applied_not_approved() -> None:
    assert _status_cell("EXT-19") == "`applied`"
    assert _status_cell("EXT-20") == "`not_started`"
    assert _status_cell("EXT-21") == "`not_started`"
    assert _status_cell("EXT-22") == "`not_started`"
    assert "EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md" in REGISTER
    assert "written **conditional** approval" in REGISTER
    assert "Do **not** use `approved` from a conditional" in REGISTER
    assert "not unconditional legal approval" in REGISTER


def test_sanitized_counsel_record_contains_only_allowed_facts() -> None:
    assert "owner-supplied signed counsel record, verified outside repository" in EVIDENCE
    assert "Atty. Pauline Anne Sambuang" in EVIDENCE
    assert "2026-08-19" in EVIDENCE
    assert "Counsel-cleared to proceed **only after**" in EVIDENCE
    for document in EIGHT_DOCUMENTS:
        assert document in EVIDENCE
    assert "Reviewed — approved as drafted" in EVIDENCE
    assert "Reviewed — approved subject to written edits/conditions" in EVIDENCE
    assert "condition not explicitly documented in sanitized record" in EVIDENCE
    assert "remains `applied`" in EVIDENCE
    assert "not `approved`" in EVIDENCE


def test_sanitized_counsel_record_omits_privileged_and_fee_material() -> None:
    lowered = EVIDENCE.lower()
    assert "privileged" in lowered  # the omission rule is stated
    assert "fee" in lowered  # the omission rule is stated
    assert "php" not in lowered
    assert "invoice" not in lowered
    assert "signature image" in lowered  # listed as not stored
    assert "-----BEGIN" not in EVIDENCE
    assert "%PDF" not in EVIDENCE


def test_reconciliation_matrix_covers_all_eight_documents() -> None:
    assert "## 1. Legal reconciliation matrix" in READINESS
    for document in EIGHT_DOCUMENTS:
        assert document in READINESS
    assert "Aug 25 revision present?" in READINESS
    assert "Cannot compare. August 25 package is not in the agent workspace." in READINESS
    assert "condition not explicitly documented in sanitized record" in READINESS
    assert "6666bb26f40255b9fece39e94bc5ca2b6e3ff2dd" in READINESS


def test_august_25_working_drafts_are_not_in_the_repository() -> None:
    legal = ROOT / "docs/legal"
    unexpected = list(legal.rglob("*WORKING_DRAFT*"))
    assert unexpected == []
    html_files = list(PUBLISHED.glob("*.html"))
    assert html_files == []


def test_production_catalog_and_routes_remain_unpublished() -> None:
    from app.core.config import Settings

    catalog = catalog_from_settings(Settings())
    assert catalog.published("terms") is None
    assert catalog.published("privacy") is None
    client = TestClient(create_app())
    privacy = client.get("/privacy")
    terms = client.get("/terms")
    assert privacy.status_code == 404
    assert terms.status_code == 404
    for body in (privacy.text, terms.text):
        for marker in COUNSEL_DRAFT_CONTENT_MARKERS:
            assert marker not in body
        assert "[COUNSEL TO CONFIRM]" not in body


def test_published_root_still_rejects_counsel_draft_markers() -> None:
    readme = (default_legal_publication_root() / "README.md").read_text(encoding="utf-8")
    collapsed = " ".join(readme.split())
    assert "conditional" in collapsed
    assert "does **not** by itself authorize copying counsel drafts here" in collapsed
    client = TestClient(create_app())
    response = client.get("/docs/legal/published/README.md")
    assert response.status_code in {404, 405, 307, 308}


def test_early_access_legal_links_remain_gated() -> None:
    assert 'href="/privacy"' in HTML
    assert 'href="/terms"' in HTML
    assert 'aria-disabled="true"' in HTML
    assert 'data-legal-gated="true"' in HTML
    assert "event.preventDefault()" in JS
    assert "No spam. Just important PiqSavi early-access updates." in HTML
    assert 'name="terms_accepted"' not in HTML
    assert 'name="privacy_acknowledged"' not in HTML
    assert "I accept the" not in HTML
    assert "I acknowledge the" not in HTML


def test_early_access_scope_stays_acquisition_only() -> None:
    lowered = HTML.lower()
    assert "/demo" not in HTML
    assert "/search" not in HTML
    assert "/results" not in HTML
    assert "shopee" not in lowered
    assert "lazada" not in lowered
    assert HTML.lower().count("affiliate") == 1
    assert "independent of affiliate relationships" in HTML
    assert "affiliate=" not in lowered
    assert "utm_campaign" not in HTML
    client = TestClient(create_app())
    page = client.get("/").text
    assert "/demo" not in page
    assert "data-legal-gated" in page
    assert "shopee" not in page.lower()
    assert "lazada" not in page.lower()


def test_no_public_early_access_registration_list() -> None:
    client = TestClient(create_app())
    for path in (
        "/api/v1/early-access",
        "/api/v1/early-access/",
        "/api/v1/early-access/export",
        "/api/v1/early-access/registrations",
    ):
        response = client.get(path)
        assert response.status_code in {404, 405}
        lowered = response.text.lower()
        assert "email" not in lowered or "not found" in lowered or "method not allowed" in lowered


def test_readiness_record_does_not_claim_cutover_complete() -> None:
    assert "It does **not** claim:" in READINESS
    assert (
        "EARLY ACCESS CODE/LEGAL READINESS COMPLETE — OWNER PRODUCTION CUTOVER "
        "AUTHORIZATION REQUIRED"
    ) in READINESS
    claim_index = READINESS.index("It does **not** claim:")
    slogan_index = READINESS.index("EARLY ACCESS CODE/LEGAL READINESS COMPLETE")
    assert claim_index < slogan_index
    assert "Production cutover is **not** technically ready." in READINESS
    assert "unresolved legal and infrastructure gates remain" in READINESS.lower()
    assert "Not a public beta launch" in READINESS
    assert "No merchant certification" in READINESS
    assert "No live shopping launch" in READINESS
    assert "No affiliate monetization activation" in READINESS
    assert "owner controls merges" in READINESS.lower()


def test_production_deploy_workflow_remains_absent() -> None:
    assert not (ROOT / ".github/workflows/deploy-production.yml").exists()
    assert (ROOT / ".github/workflows/deploy-staging.yml").is_file()
