"""Sprint 39 remaining-19 readiness.

The review selects no engineering slice and does not change closure classes.
"""

from __future__ import annotations

from pathlib import Path

from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_access_stage import SPRINT_38_STATUS
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)

from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
READINESS = ROOT / "docs/roadmap/evidence/SPRINT_39_REMAINING_19_READINESS_AUDIT_2026-10-08.md"
CLOSURE = ROOT / "docs/roadmap/evidence/SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md"
SPRINT39 = ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
START_SHA = "49a94f04948152567d4547c29f04e59268642273"

# prior, fresh, owner, implement now, candidate slice
EXPECTED: dict[str, tuple[str, str, str, str, str]] = {
    "DAU / MAU": (
        "BLOCKED-PRIVACY",
        "BLOCKED-PRIVACY",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "searches": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "search success": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "search failure": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "search zero": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "search partial": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "search started": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "latency": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "merchant coverage": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "market coverage": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "funnel abandonment": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "frontend errors": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "backend errors": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "merchant errors": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "AI errors": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
    "slow pages": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "slow endpoints": (
        "BLOCKED-DEFINITION",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "support-contact analytics": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DEFINITION",
        "product-definition decision",
        "No",
        "no",
    ),
    "conversation expiry": (
        "BLOCKED-DOMAIN",
        "BLOCKED-DOMAIN",
        "ROADMAP OWNERSHIP GAP",
        "No",
        "no",
    ),
}

DEFINITION_ROWS = (
    "latency",
    "merchant coverage",
    "market coverage",
    "funnel abandonment",
    "slow pages",
    "slow endpoints",
    "support-contact analytics",
)
OWNERSHIP_GAP_ROWS = (
    "DAU / MAU",
    "searches",
    "search success",
    "search failure",
    "search zero",
    "search partial",
    "search started",
    "frontend errors",
    "backend errors",
    "merchant errors",
    "AI errors",
    "conversation expiry",
)


def _rows(text: str) -> dict[str, list[str]]:
    section = text.split("## Readiness table", 1)[1].split("## Blocked rows by category", 1)[0]
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| Class C") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        assert len(cells) == 12, line
        assert cells[0] not in rows
        rows[cells[0]] = cells
    return rows


def test_readiness_table_lists_each_current_class_c_row_once() -> None:
    text = READINESS.read_text(encoding="utf-8")
    rows = _rows(text)
    assert tuple(rows) == CURRENT_CLASS_C
    assert len(rows) == 19
    assert len(CURRENT_CLASS_C) == 19
    for name, (prior, fresh, owner, implement, candidate) in EXPECTED.items():
        cells = rows[name]
        assert cells[4] == prior
        assert cells[5] == fresh
        assert cells[7] == owner
        assert cells[8] == implement
        assert cells[9] == "No"
        assert cells[10] == candidate
        assert fresh not in {"A", "B", "C"}
        assert owner in {"ROADMAP OWNERSHIP GAP", "product-definition decision"}
        assert cells[11]
    for name in ("Recommendation views", "DealScore / PiqScore views"):
        assert name not in rows


def test_none_is_selected_and_the_blocker_owner_matrix_exists() -> None:
    text = READINESS.read_text(encoding="utf-8")
    assert "**Selected next engineering slice:** NONE" in text
    assert "**READY-A rows:** none." in text
    assert "**READY-B rows:** none." in text
    assert "**READY-DEFINITION rows:** none." in text
    matrix = text.split("## Blocker-owner matrix", 1)[1].split("## Recommendation", 1)[0]
    assert "Product-definition decision" in matrix
    assert "ROADMAP OWNERSHIP GAP" in matrix
    assert "Privacy architecture" in matrix
    assert "Real product or domain transition" in matrix
    assert "| Another sprint | none |" in matrix
    definition = matrix.split("Product-definition decision", 1)[1].split("Real product", 1)[0]
    for name in DEFINITION_ROWS:
        assert name in definition
    gap = matrix.split("| ROADMAP OWNERSHIP GAP |", 1)[1]
    for name in OWNERSHIP_GAP_ROWS:
        assert name in gap
    assert "DAU / MAU" in matrix.split("Privacy architecture", 1)[1].split("Another sprint", 1)[0]
    recommendation = text.split("## Recommendation", 1)[1]
    assert "Remain open while Sprint 40 proceeds in parallel (A)." in recommendation
    assert (
        "product-definition decision for the seven BLOCKED-DEFINITION rows (C)." in recommendation
    )
    assert "twelve rows whose missing prerequisite has no sprint owner (D)." in recommendation
    assert "not B" in recommendation
    assert "Do not mark Sprint 39 engineering complete." in recommendation


def test_historical_counts_and_closure_classes_stay_put() -> None:
    text = READINESS.read_text(encoding="utf-8")
    sprint = SPRINT39.read_text(encoding="utf-8")
    closure = CLOSURE.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "pre-Sprint-39.4 Class C count was 27" in text
    assert "After Sprint 39.4 the Class C count was 21" in text
    assert "Current Class C count remains 19" in text
    assert "does not change any Included-requirements A/B/C classification" in text
    assert "No row below moves from C to A or B" in text
    assert "Recommendation views remain B" in text
    assert "DealScore / PiqScore views remain B" in text
    assert "They are not A" in text or "Neither is A" in text
    assert START_SHA in text
    assert START_SHA in sprint
    assert START_SHA in closure
    assert START_SHA in roadmap
    for document in (text, sprint, roadmap, closure):
        assert "Selected next engineering slice:** NONE" in document or (
            "Selected next engineering slice: NONE" in document
            or "**Selected next engineering slice:** NONE" in document
        )
    assert sprint.startswith("# Sprint 39")
    assert "**Status:** IN PROGRESS" in sprint
    assert "not ENGINEERING COMPLETE" in sprint
    assert "IN PROGRESS" in text
    assert "not ENGINEERING COMPLETE" in text
    assert "| Recommendation views | B |" in closure
    assert "| DealScore / PiqScore views | B |" in closure
    assert "Current Class C count is 19." in closure
    assert "Pre-Sprint-39.4 Class C count: 27." in closure
    assert "After Sprint 39.4 Class C count: 21." in closure
    assert "After Sprint 39.5 Class C count: 19." in closure


def test_sprint_38_and_production_truth_are_unchanged() -> None:
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
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert "Routing stays 0." in text
