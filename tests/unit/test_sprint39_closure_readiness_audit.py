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
VERDICT = "SPRINT 39 IN PROGRESS — TRUE SPRINT 39 ENGINEERING BLOCKERS REMAIN"
WITHDRAWN = (
    "SPRINT 39 ENGINEERING COMPLETE — CLOSURE VALIDATION BLOCKED ON UPSTREAM/DOWNSTREAM GATES"
)
ASK_USED = "A for open. B for a submitted question"

# Current Included requirements, expanded to one row each. Priority is not a class.
EVENTS = {
    "registrations": "C",
    "verified registrations": "C",
    "login success": "C",
    "login failure": "C",
    "DAU / MAU": "C",
    "searches": "C",
    "success": "C",
    "failure": "C",
    "zero": "C",
    "partial": "C",
    "latency": "C",
    "merchant coverage": "C",
    "market coverage": "C",
    "Recommendation views": "C",
    "DealScore / PiqScore views": "C",
    "explanation views": "B",
    "CTR": "B",
    "funnel abandonment": "C",
    "retention": "B",
    "frontend errors": "C",
    "backend errors": "C",
    "merchant errors": "C",
    "AI errors": "C",
    "slow pages": "C",
    "slow endpoints": "C",
    "feedback": "A",
    "bugs": "A",
    "support": "A",
    "deletion metrics": "C",
    "consent state": "A",
}
CONSENT_AWARE = {
    "search started": "C",
    "research started / completed": "B",
    "decision started": "B",
    "decision completed": "B",
    "Results viewed": "B",
    "Compare opened": "B",
    "Why opened": "B",
    "Ask PiqSavi used": ASK_USED,
    "Recommendation refinement attempted / applied": "B",
    "research proposed": "B",
    "research confirmed": "B",
    "Save": "F",
    "Watch": "F",
    "View offer / outbound merchant click": "B",
    "return visits": "B",
    "repeat decisions": "B",
    "insufficient evidence": "B",
    "connector / research failure": "B",
    "incorrect-information report": "A",
    "Recommendation helpful / not helpful": "A",
    "support contact": "C",
}
CONVERSATIONAL = {
    "Ask open": "A",
    "Ask close": "A",
    "question submission": "B",
    "evidence answer": "B",
    "insufficient evidence": "B",
    "refinement": "B",
    "research proposal": "B",
    "confirmation": "B",
    "decline": "B",
    "start": "B",
    "partial": "F",
    "completion": "B",
    "failure": "B",
    "updated Results": "B",
    "reopen": "F",
    "expiry": "C",
    "authentication transition": "C",
}


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
    live = next(line for line in audit.splitlines() if line.startswith("**Audit verdict:**"))
    withdrawn = next(line for line in audit.splitlines() if "Withdrawn verdict:" in line)
    assert live == f"**Audit verdict:** {VERDICT}"
    assert WITHDRAWN not in live
    assert WITHDRAWN in withdrawn
    assert "is withdrawn" in withdrawn
    assert "Priority alone is not supersession." in withdrawn
    assert VERDICT in status
    assert "ENGINEERING COMPLETE reading is withdrawn" in status
    assert "Class C count: 27." in audit
    assert "Class C count: 0." not in audit
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


def _section(audit: str, heading: str, end: str) -> str:
    return audit.split(heading, 1)[1].split(end, 1)[0]


def _classified_rows(section: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| Item ") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) >= 4, line
        name, classification = cells[0], cells[3]
        assert name not in rows, name
        rows[name] = classification
    return rows


def test_included_requirements_are_classified_item_by_item() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    sprint39 = SPRINT39.read_text(encoding="utf-8")
    included = sprint39.split("## Included requirements", 1)[1].split("### SEO measurement", 1)[0]
    assert "registrations, verified registrations, login success/failure" in included
    assert "DAU/MAU" in included
    assert "searches, success/failure/zero/partial" in included
    assert "merchant/market coverage" in included
    assert "frontend/backend/merchant/AI errors" in included
    assert "slow pages/endpoints" in included
    assert "deletion metrics" in included
    assert "search started" in included
    assert "Save" in included and "Watch" in included
    assert "reopen, expiry, and authentication transition" in included
    priority = sprint39.split("**Priority measurements**", 1)[1].split(
        "## Included requirements", 1
    )[0]
    lowered = priority.lower()
    assert "supersed" not in lowered
    assert "removed" not in lowered

    events = _classified_rows(
        _section(audit, "### Events list", "### Consent-aware measurement list")
    )
    consent = _classified_rows(
        _section(audit, "### Consent-aware measurement list", "### Conversational Continuity list")
    )
    conversational = _classified_rows(
        _section(audit, "### Conversational Continuity list", "Class C rows are:")
    )
    assert events == EVENTS
    assert consent == CONSENT_AWARE
    assert conversational == CONVERSATIONAL

    class_c = [name for name, kind in events.items() if kind == "C"]
    class_c += [name for name, kind in consent.items() if kind == "C"]
    class_c += [name for name, kind in conversational.items() if kind == "C"]
    assert len(class_c) == 27
    assert "Class C count: 27." in audit
    for name in (
        "registrations",
        "verified registrations",
        "login success",
        "login failure",
        "DAU / MAU",
        "searches",
        "search started",
        "latency",
        "merchant coverage",
        "market coverage",
        "frontend errors",
        "backend errors",
        "merchant errors",
        "AI errors",
        "slow pages",
        "slow endpoints",
        "deletion metrics",
        "support contact",
        "expiry",
        "authentication transition",
    ):
        assert name in class_c
    assert events["success"] == "C"
    assert events["failure"] == "C"
    assert events["zero"] == "C"
    assert events["partial"] == "C"
    assert "Save" not in class_c
    assert "Watch" not in class_c
    assert consent["Save"] == "F"
    assert consent["Watch"] == "F"
    assert conversational["reopen"] == "F"
    assert "G" not in events.values()
    assert "G" not in consent.values()
    assert "G" not in conversational.values()
    assert "No Included-requirements item in these three lists is classified G." in audit
    historical = _section(audit, "### Historical wording", "## Answers to the ownership questions")
    assert "| Sprint 39.1 residual list | G as a closure checklist |" in historical
    assert "does not remove the Included requirements" in historical
