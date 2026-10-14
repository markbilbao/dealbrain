"""Guard the Sprint 40 security-readiness package.

The package is process evidence. These checks look for required safety
statements and links. They do not hash the prose.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PENTEST = ROOT / "docs/security/PENETRATION_TEST_READINESS.md"
INCIDENT = ROOT / "docs/runbooks/SECURITY_INCIDENT_RESPONSE.md"
VULN = ROOT / "docs/security/VULNERABILITY_RESPONSE.md"
DRAFT = ROOT / "docs/roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md"
EVIDENCE = ROOT / "docs/roadmap/evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md"
SECURITY = ROOT / "docs/SECURITY.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
PRIOR = (
    ROOT / "docs/roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md"
)
START_SHA = "e088cba9a87175e387038afb98a1754fe8cc885e"

ROADMAP_LINKS = (
    "SPRINT_40_SECURITY_ABUSE_HARDENING.md",
    "SPRINT_42_PRODUCTION_OPERATIONS_DR.md",
    "SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md",
    "GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md",
)


def test_package_files_exist() -> None:
    for path in (PENTEST, INCIDENT, VULN, DRAFT, EVIDENCE):
        assert path.is_file(), path


def test_penetration_checklist_does_not_claim_execution() -> None:
    text = PENTEST.read_text(encoding="utf-8")
    assert "No penetration test has been executed." in text
    assert "No item in this checklist is TESTED / PASSED." in text
    assert "READY TO TEST" in text
    assert "Repository tests are not a penetration-test result." in text
    assert "Do not perform a denial-of-service or load attack." in text
    assert "Affiliate activation stays off." in text
    assert "SHOPIFY_LIVE_CALL_PERMITTED" in text
    assert "TESTED / PASSED" in text
    for heading in (
        "## Scope definition",
        "## Authentication and authorization",
        "## Request integrity",
        "## Injection and browser",
        "## Data and privacy",
        "## Abuse",
        "## Safe-test rules",
        "## Evidence template",
    ):
        assert heading in text
    for link in ROADMAP_LINKS:
        assert link in text


def test_incident_runbook_does_not_invent_paging() -> None:
    text = INCIDENT.read_text(encoding="utf-8")
    assert "This runbook does not configure paging." in text
    assert "Production incident response is not operational." in text
    assert "Sprint 42 owns production monitoring, alerts, paging" in text
    assert (
        "No PagerDuty service, Slack channel, phone number, or security mailbox is named here."
        in text
    )
    assert "SEV-1 Critical" in text
    assert "SEV-2 High" in text
    assert "SEV-3 Medium" in text
    assert "SEV-4 Low" in text
    assert "Do not relabel existing Sprint 40 findings with these severities." in text
    for phase in (
        "### 1. Identify",
        "### 2. Triage",
        "### 3. Contain",
        "### 4. Preserve evidence",
        "### 5. Eradicate and remediate",
        "### 6. Recover",
        "### 7. Validate",
        "### 8. Communicate",
        "### 9. Post-incident review",
    ):
        assert phase in text
    assert "Incident Commander" in text
    assert "Privacy/Legal Owner" in text
    for link in ROADMAP_LINKS:
        assert link in text


def test_vulnerability_process_requires_regression_and_retest() -> None:
    text = VULN.read_text(encoding="utf-8")
    assert "INTERNAL TARGETS" in text
    assert "A vulnerability cannot be closed only because code was written." in text
    assert "### 9. Regression test" in text
    assert "### 12. Retest" in text
    assert "This process does not create or approve a risk acceptance." in text
    assert "SAST is not present." in text
    assert "Container vulnerability scanning is not present." in text
    assert "IaC security scanning is not present." in text
    assert "pip-audit 2.10.1" in text
    assert "Triage within 1 business day." in text
    assert "Triage within 3 business days." in text
    assert "Triage within 5 business days." in text
    for link in ROADMAP_LINKS:
        assert link in text


def test_sprint44_draft_stays_unapproved() -> None:
    text = DRAFT.read_text(encoding="utf-8")
    assert "DRAFT / NOT APPROVED" in text
    assert "SECURITY GO: NOT DECIDED" in text
    assert "SECURITY GO: GO" not in text
    assert "not ENGINEERING COMPLETE" in text
    assert "not LAUNCH READY" in text
    assert "IMPLEMENTED-NOT-PROVEN findings are not closed." in text
    assert "R11 is IMPLEMENTED-NOT-PROVEN." in text
    assert "R11 is not PROVEN." in text
    assert "No penetration test has been executed." in text
    assert "NOT SELECTED" in text
    assert "Sprint 41" in text
    assert "Sprint 42" in text
    assert "Sprint 45" in text
    for link in ROADMAP_LINKS:
        assert link in text


def test_r11_is_implemented_not_proven_and_historical_missing_remains() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    prior = PRIOR.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    assert START_SHA in evidence
    assert "Before this package | MISSING" in evidence
    assert "After this package | IMPLEMENTED-NOT-PROVEN" in evidence
    assert "R11 is not PROVEN." in evidence
    assert "R11 is PROVEN" not in evidence
    assert "| MISSING | 1 (R11) |" in prior
    assert "R11 stays MISSING and is the selected slice." in sprint
    assert "R11 is IMPLEMENTED-NOT-PROVEN. R11 is not PROVEN." in sprint
    assert sprint.startswith("# Sprint 40")
    assert "**Status:** Planned" in sprint.split("## Current reading", 1)[0]
    for document in (PENTEST, INCIDENT, VULN, DRAFT, EVIDENCE, SECURITY):
        text = document.read_text(encoding="utf-8")
        assert "R11 is PROVEN" not in text


def test_current_roadmap_notes_link_the_package() -> None:
    security = SECURITY.read_text(encoding="utf-8")
    assert "security/PENETRATION_TEST_READINESS.md" in security
    assert "runbooks/SECURITY_INCIDENT_RESPONSE.md" in security
    assert "security/VULNERABILITY_RESPONSE.md" in security
    assert "SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md" in security
    assert "Execution evidence and approval evidence are still pending." in security
    assert "Sprint 22" in security
    for path in (ROADMAP, GAPS, README, SPRINT40, SECURITY):
        text = path.read_text(encoding="utf-8")
        assert "SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md" in text
        assert START_SHA in text
        assert "not ENGINEERING COMPLETE" in text
