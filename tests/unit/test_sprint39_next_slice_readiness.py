"""Sprint 39 next-slice readiness.

The 2026-10-08 audit selects the slice and does not reclassify rows.
Sprint 39.5 adds the two server events. The post-merge reconciliation
moves those two closure classes from C to B. They are not A.
"""

from __future__ import annotations

from pathlib import Path

from app.analytics.schema import CLIENT_EVENT_NAMES, EVENT_NAMES
from app.research.shopify_global_catalog_access_stage import SPRINT_38_STATUS
from app.research.sprint38_live_execution import SPRINT_38_ENGINEERING_STATUS

from tests.unit.test_sprint39_closure_readiness_audit import (
    CONSENT_AWARE,
    CONVERSATIONAL,
    EVENTS,
    _classified_rows,
    _section,
)

ROOT = Path(__file__).resolve().parents[2]
READINESS = ROOT / "docs/roadmap/evidence/SPRINT_39_NEXT_SLICE_READINESS_AUDIT_2026-10-08.md"
CLOSURE = ROOT / "docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"
SPRINT39 = ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"
SLICE = "canonical Results recommendation and PiqScore view observation"
SLICE_ROWS = ("Recommendation views", "DealScore / PiqScore views")

# classification, can implement, slice membership, dependency phrase
EXPECTED: dict[str, tuple[str, str, str, str]] = {
    "DAU / MAU": (
        "BLOCKED-PRIVACY",
        "No",
        "no",
        "privacy-safe account activity digest",
    ),
    "searches": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "non-fixture search result transition",
    ),
    "search success": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "same missing search result transition",
    ),
    "search failure": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "Mock connectors do not fail",
    ),
    "search zero": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "mock title miss is not a production zero-result transition",
    ),
    "search partial": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No partial search transition exists",
    ),
    "search started": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No search-started transition exists",
    ),
    "latency": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "No product latency population is defined",
    ),
    "merchant coverage": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "No merchant-coverage formula is defined",
    ),
    "market coverage": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "No market-coverage formula is defined",
    ),
    "Recommendation views": (
        "READY-B",
        "Yes",
        "yes",
        "Staging proof waits on Sprint 29 / 31 / 38",
    ),
    "DealScore / PiqScore views": (
        "READY-B",
        "Yes",
        "yes",
        "The same canonical Results serve",
    ),
    "funnel abandonment": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "No abandonment denominator is defined",
    ),
    "frontend errors": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No frontend error transition exists",
    ),
    "backend errors": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No sanitized backend-error transition exists",
    ),
    "merchant errors": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "`research_failed` is a different row",
    ),
    "AI errors": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No product AI-error transition exists",
    ),
    "slow pages": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "Slow is undefined for pages",
    ),
    "slow endpoints": (
        "BLOCKED-DEFINITION",
        "No",
        "no",
        "Slow is undefined for endpoints",
    ),
    "support-contact analytics": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "No request-scoped support contact exists",
    ),
    "conversation expiry": (
        "BLOCKED-DOMAIN",
        "No",
        "no",
        "`cleanup_expired` has no production caller",
    ),
}


def _readiness_rows(text: str) -> dict[str, list[str]]:
    section = text.split("## Readiness table", 1)[1].split(
        "## Blocked rows by category",
        1,
    )[0]
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| Class C"):
            continue
        if line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) == 10, line
        assert cells[0] not in rows
        rows[cells[0]] = cells
    return rows


def test_readiness_table_covers_the_21_class_c_rows() -> None:
    text = READINESS.read_text(encoding="utf-8")
    rows = _readiness_rows(text)
    assert list(rows) == list(EXPECTED)
    assert len(rows) == 21
    assert "Class C count remains 21" in text
    for name, (kind, implement, membership, phrase) in EXPECTED.items():
        cells = rows[name]
        assert cells[4] == kind
        assert cells[6] == implement
        assert cells[7] == "No"
        assert cells[8] == membership
        assert phrase in cells[5] or phrase in cells[9]
        assert cells[4] not in {"A", "B", "C", "D", "E", "F", "G"}


def test_selected_slice_names_only_the_two_ready_rows() -> None:
    text = READINESS.read_text(encoding="utf-8")
    sprint = SPRINT39.read_text(encoding="utf-8")
    roadmap = (ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md").read_text(
        encoding="utf-8"
    )
    assert "READY-A rows:** none." in text
    assert f"**Selected next engineering slice:** {SLICE}." in text
    for name in SLICE_ROWS:
        assert name in text
        assert EXPECTED[name][0] == "READY-B"
        assert EXPECTED[name][2] == "yes"
    excluded = [name for name, spec in EXPECTED.items() if spec[2] == "no"]
    assert len(excluded) == 19
    assert "Rows explicitly not in the slice:" in text
    for name in excluded:
        assert (
            name
            in text.split("Rows explicitly not in the slice:", 1)[1].split(
                "## Family findings",
                1,
            )[0]
        )
    for document in (text, sprint, roadmap):
        assert SLICE in document
        assert "Recommendation views" in document
        assert "DealScore / PiqScore views" in document
    assert "recommendation_viewed" in text
    assert "piqscore_viewed" in text
    assert "recommendation_viewed" in EVENT_NAMES
    assert "piqscore_viewed" in EVENT_NAMES
    assert "recommendation_viewed" not in CLIENT_EVENT_NAMES
    assert "piqscore_viewed" not in CLIENT_EVENT_NAMES
    assert "dealscore_viewed" not in EVENT_NAMES
    assert "Sprint 39.5" in sprint
    assert "No staging proof is claimed" in sprint
    assert "Class C count remains 21" in sprint


def test_sprint_39_status_and_closure_classes_stay_put() -> None:
    readiness = READINESS.read_text(encoding="utf-8")
    closure = CLOSURE.read_text(encoding="utf-8")
    sprint = SPRINT39.read_text(encoding="utf-8")
    assert sprint.startswith("# Sprint 39")
    assert "**Status:** IN PROGRESS" in sprint
    assert "not ENGINEERING COMPLETE" in sprint
    assert "current Class C count is 21" in sprint
    assert "Class C count remains 21" in readiness
    assert "does not change any Included-requirements A/B/C classification" in readiness
    assert "IN PROGRESS" in readiness
    assert "not ENGINEERING COMPLETE" in readiness
    events = _classified_rows(
        _section(closure, "### Events list", "### Consent-aware measurement list")
    )
    consent = _classified_rows(
        _section(
            closure,
            "### Consent-aware measurement list",
            "### Conversational Continuity list",
        )
    )
    conversational = _classified_rows(
        _section(
            closure,
            "### Conversational Continuity list",
            "Class C rows, current after Sprint 39.4, are:",
        )
    )
    assert events == EVENTS
    assert consent == CONSENT_AWARE
    assert conversational == CONVERSATIONAL
    assert events["Recommendation views"] == "C"
    assert events["DealScore / PiqScore views"] == "C"
    assert "No classification in the Included-requirements tables changes." in closure


def test_parallel_sprint_status_is_unchanged() -> None:
    text = READINESS.read_text(encoding="utf-8")
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert "Sprint 38 stays IN PROGRESS" in text
    assert "ENGINEERING COMPLETE" in text
    assert "Sprint 40 may still run in parallel" in text
    assert "does not start Sprint 40" in text
    assert "No deploy was performed." in text
    assert "No Shopify call was made." in text
    assert "Runtime code is unchanged." in text


def test_post_merge_note_retires_the_unimplemented_slice_reading() -> None:
    text = READINESS.read_text(encoding="utf-8")
    verdict = next(line for line in text.splitlines() if line.startswith("**Audit verdict:**"))
    assert verdict == (
        "**Audit verdict:** One bounded next engineering slice is selected. "
        "It is not implemented in this audit."
    )
    note = text.split(
        "Sprint 39.5 post-merge classification reconciliation (2026-10-08)",
        1,
    )[1]
    assert "Class C count remains 21" in text
    assert "no longer represents an unimplemented selected slice" in note
    assert "current Class C count is 19" in note
    assert "closure Class B" in note
    assert "They are not A." in note
    assert "No staging proof exists." in note
    assert "No next engineering slice is selected by this reconciliation." in note
    assert "does not assume the findings above are enough" in note
