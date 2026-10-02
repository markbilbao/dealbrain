"""Sprint 39 closure-readiness audit. Does not close the sprint or deploy."""

from __future__ import annotations

from pathlib import Path

from app.analytics.retention import PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS
from app.privacy.tracking import ANALYTICS_PROVIDER, CMP_VENDOR, EXT_22_STATUS
from app.research.shopify_global_catalog_access_stage import (
    SPRINT_38_STATUS,
    SPRINT_41_STATUS,
)
from app.research.sprint38_live_execution import SPRINT_38_ENGINEERING_STATUS

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"
EVIDENCE = ROOT / "docs/roadmap/evidence/SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md"
SPRINT39 = ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"
REGISTER = ROOT / "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md"
VERDICT = (
    "SPRINT 39 ENGINEERING COMPLETE — "
    "CLOSURE VALIDATION BLOCKED ON UPSTREAM/DOWNSTREAM GATES"
)


def _status_line(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return next(line for line in lines if line.startswith("**Status:**"))


def _register_status(row_id: str) -> str:
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {row_id} |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            return cells[7]
    raise AssertionError(f"missing register row {row_id}")


def test_audit_keeps_sprint_39_in_progress() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    sprint39 = SPRINT39.read_text(encoding="utf-8")
    status = _status_line(SPRINT39)
    assert VERDICT in audit
    assert VERDICT in status
    assert "Class C count: 0." in audit
    assert "This audit does not close Sprint 39." in audit
    assert "Not COMPLETE / CLOSED." in audit
    assert "Not PRODUCTION PROVEN." in audit
    assert "Not LAUNCH READY." in audit
    assert status.startswith("**Status:** IN PROGRESS")
    assert "Not COMPLETE" in status
    assert "COMPLETE / CLOSED" not in status.split("Not COMPLETE / CLOSED")[0]
    assert "**Status:** IN PROGRESS" in sprint39
    assert "no affiliate conversion/revenue metric is required" in sprint39


def test_staging_evidence_keeps_both_deploys() -> None:
    evidence = EVIDENCE.read_text(encoding="utf-8")
    assert "36822959068" in evidence
    assert "287cdf11ff61bfdb09d412d1cb88927c86e3c799" in evidence
    assert "contradictory_event" in evidence
    assert "36847902925" in evidence
    assert "374c9e2f45cb1810626c4138b3a145d3cff170a0" in evidence
    assert "rel-20261001T083510Z-374c9e2f45cb" in evidence
    assert "1578ca76-d354-4c09-ab83-bf952364dcce" in evidence
    assert "0e16b66d-7487-43aa-99e4-4111db6c0622" in evidence
    assert "b3f221f6-ac56-4544-a8d3-fea3cec86590" in evidence
    assert "suppressed_no_consent" in evidence
    assert "decision_started | 0" in evidence
    assert "Do not delete it" in evidence
    assert "subject hashes" in evidence
    assert "anonymous_subject" not in evidence
    assert "message text | not recorded" in evidence


def test_audit_does_not_start_providers_or_change_sprint_38() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    assert "Do not start EXT-15" in audit
    assert "EXT-22 stays `not_started`" in audit
    assert "does not call Google Search Console" in audit
    assert "Not Class C" in audit
    assert "no partial identity join" in audit.lower() or "not add a partial identity join" in audit
    assert _register_status("EXT-15") == "`not_started`"
    assert _register_status("EXT-17") == "`provisioned`"
    assert _register_status("EXT-22") == "`not_started`"
    assert _register_status("EXT-29") == "`not_started`"
    assert ANALYTICS_PROVIDER is None
    assert CMP_VENDOR is None
    assert EXT_22_STATUS == "not_started"
    assert PRODUCT_ANALYTICS_ENGINEERING_TTL_DAYS == 400
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert SPRINT_41_STATUS == "UNSTARTED"
