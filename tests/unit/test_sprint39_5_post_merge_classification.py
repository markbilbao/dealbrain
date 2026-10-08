"""Sprint 39.5 post-merge classification reconciliation.

Historical counts stay visible. The current closure class of the two
implemented Results rows is B. This reconciliation does not select a slice.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.analytics.schema import CLIENT_EVENT_NAMES, EVENT_NAMES
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_access_stage import (
    SPRINT_38_STATUS,
    SPRINT_41_STATUS,
)
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)

from tests.unit.test_sprint39_closure_readiness_audit import (
    _classified_rows,
    _section,
)

ROOT = Path(__file__).resolve().parents[2]
HEADING = "Sprint 39.5 post-merge classification reconciliation (2026-10-08)"
REASON = "IMPLEMENTED, CLOSURE EVIDENCE BLOCKED ON REAL CANONICAL RESULTS TRAFFIC"
CURRENT_CLASS_C = (
    "DAU / MAU",
    "searches",
    "search success",
    "search failure",
    "search zero",
    "search partial",
    "search started",
    "latency",
    "merchant coverage",
    "market coverage",
    "funnel abandonment",
    "frontend errors",
    "backend errors",
    "merchant errors",
    "AI errors",
    "slow pages",
    "slow endpoints",
    "support-contact analytics",
    "conversation expiry",
)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _after(text: str, marker: str) -> str:
    assert marker in text
    return text.split(marker, 1)[1]


def _numbered(section: str) -> list[str]:
    rows: list[str] = []
    for line in section.splitlines():
        match = re.fullmatch(r"(\d+)\. (.+)", line.strip())
        if match is None:
            if rows:
                break
            continue
        rows.append(match.group(2))
    return rows


def test_historical_counts_stay_and_current_count_is_19() -> None:
    audit = _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md")
    sprint = _text("docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md")
    assert "Pre-Sprint-39.4 Class C count: 27." in audit
    assert "Class C count: 21." in audit
    assert "After Sprint 39.4 Class C count: 21." in audit
    assert "After Sprint 39.5 Class C count: 19." in audit
    assert "Current Class C count is 19." in audit
    assert "Class C count: 0." not in audit
    assert "pre-Sprint-39.4 Class C count was 27" in sprint
    assert "current Class C count is 21" in sprint
    assert "The current Class C count is 19" in sprint
    assert "After Sprint 39.4 the Class C count was 21." in sprint
    for relative in (
        "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md",
        "docs/roadmap/sprints/README.md",
        "docs/roadmap/GAP_INVENTORY.md",
    ):
        text = _text(relative)
        assert "Pre-Sprint-39.4 Class C count was 27" in text or (
            "Pre-Sprint-39.4 Class C count | 27" in text
        )
        assert "current Class C count is 21" in text or "Class C count | 21" in text
        assert "current Class C count is 19" in text or "Class C count | 19" in text


def test_two_rows_are_b_and_the_historical_table_stays_c() -> None:
    audit = _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md")
    events = _classified_rows(
        _section(audit, "### Events list", "### Consent-aware measurement list")
    )
    assert events["Recommendation views"] == "C"
    assert events["DealScore / PiqScore views"] == "C"
    section = _after(audit, HEADING)
    for name in ("Recommendation views", "DealScore / PiqScore views"):
        assert f"| {name} | B | {REASON} |" in section
        assert f"| {name} | A |" not in section
    assert "Neither row is A." in section
    assert "No staging proof is claimed." in section
    assert "No staging proof exists" in section
    assert "Deploy Staging #" not in section
    sprint = _after(
        _text("docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"),
        HEADING,
    )
    for name in ("Recommendation views", "DealScore / PiqScore views"):
        assert f"| {name} | B | {REASON} |" in sprint
    assert "Neither row is A." in sprint
    assert "No staging proof is claimed." in sprint


def test_recommendation_view_reason_names_the_server_gates() -> None:
    section = _after(
        _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"),
        HEADING,
    )
    assert "recommendation_viewed" in section
    for gate in (
        "Results is canonical",
        "Results is not unavailable",
        "authorized snapshot resolves",
        "recommendation marker",
        "analytics consent is allowed",
        "existing valid analytics subject",
    ):
        assert gate in section
    assert "real canonical shopper Results journey is not publicly active" in section
    assert REASON in section


def test_piqscore_view_reason_does_not_invent_dealscore_viewed() -> None:
    section = _after(
        _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"),
        HEADING,
    )
    assert "piqscore_viewed" in section
    assert "visible PiqScore gauge" in section
    assert "no separate visible DealScore control" in section
    assert "no `dealscore_viewed` event was invented" in section
    assert REASON in section
    assert "recommendation_viewed" in EVENT_NAMES
    assert "piqscore_viewed" in EVENT_NAMES
    assert "dealscore_viewed" not in EVENT_NAMES
    assert "recommendation_viewed" not in CLIENT_EVENT_NAMES
    assert "piqscore_viewed" not in CLIENT_EVENT_NAMES


def test_exactly_nineteen_class_c_rows_remain() -> None:
    audit = _after(
        _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"),
        "Class C rows, current after Sprint 39.5, are:",
    )
    sprint = _after(
        _text("docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"),
        "Class C rows, current after Sprint 39.5, are exactly:",
    )
    assert tuple(_numbered(audit)) == CURRENT_CLASS_C
    assert tuple(_numbered(sprint)) == CURRENT_CLASS_C
    assert len(CURRENT_CLASS_C) == 19
    for name in ("Recommendation views", "DealScore / PiqScore views"):
        assert name not in CURRENT_CLASS_C
    historical = _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md")
    old = historical.split("Class C rows, current after Sprint 39.4, are:", 1)[1]
    old = old.split("The pre-Sprint-39.4", 1)[0]
    assert "Recommendation views" in old
    assert "DealScore / PiqScore views" in old


def test_sprint_status_stays_open_and_selects_no_next_slice() -> None:
    sprint = _text("docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md")
    section = _after(sprint, HEADING)
    assert sprint.startswith("# Sprint 39")
    assert "**Status:** IN PROGRESS" in sprint
    assert "is not ENGINEERING COMPLETE" in section
    assert "not COMPLETE / CLOSED" in section
    assert "not PRODUCTION PROVEN" in section
    assert "not LAUNCH READY" in section
    assert "No next engineering slice is selected by this reconciliation." in section
    assert "fresh bounded readiness review of the remaining 19 Class C rows" in section
    assert "does not assume that audit already contains enough evidence" in section
    assert "Sprint 39.1 merged" in section
    assert "Sprint 39.5 merged" in section
    assert "PR #184 is merged" in section
    assert "8f64cdee3e4e115edbdee56428cfbe4b0570e305" in section
    assert "CI #449" in section
    assert "Build Image #159" in section
    readiness = _after(
        _text("docs/roadmap/evidence/SPRINT_39_NEXT_SLICE_READINESS_AUDIT_2026-10-08.md"),
        HEADING,
    )
    assert "no longer represents an unimplemented selected slice" in readiness
    assert "current Class C count is 19" in readiness
    assert "closure Class B" in readiness
    assert "They are not A." in readiness
    assert "No staging proof exists." in readiness
    assert "No next engineering slice is selected by this reconciliation." in readiness
    assert "does not assume the findings above are enough" in readiness
    verdict = _text(
        "docs/roadmap/evidence/SPRINT_39_NEXT_SLICE_READINESS_AUDIT_2026-10-08.md"
    ).splitlines()[2]
    assert verdict == (
        "**Audit verdict:** One bounded next engineering slice is selected. "
        "It is not implemented in this audit."
    )


def test_sprint_38_and_production_truth_are_unchanged() -> None:
    section = _after(
        _text("docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"),
        HEADING,
    )
    sprint38 = _text("docs/roadmap/evidence/SPRINT_38_CLOSURE_READINESS_AUDIT_2026-09-30.md")
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert SPRINT_41_STATUS == "UNSTARTED"
    assert "SPRINT 38 ENGINEERING COMPLETE — CLOSURE VALIDATION BLOCKED ON SPRINT 41" in sprint38
    assert HEADING not in sprint38
    assert "Sprint 38 remains IN PROGRESS and ENGINEERING COMPLETE" in section
    assert "blocked on Sprint 41" in section
    assert "does not change Sprint 38" in section
    assert "does not start Sprint 40" in section
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert "No deploy was performed" in section
    assert "No Shopify call was made." in section
    assert "Public Results stays disabled." in section
