"""Sprint 40 post-40.6 reconciliation audit.

The review reclassifies R1–R21 and does not implement the selected slice.
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
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md"
HISTORICAL = ROOT / "docs/roadmap/evidence/SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
START_SHA = "483d30a91f70167656b51f976ffb2bb3521a0b7e"
SLICE = "Decision-path body `conversation_id` must not adopt the stored owner."

EXPECTED: dict[str, str] = {
    "R1": "PARTIAL",
    "R2": "PARTIAL",
    "R3": "PARTIAL",
    "R4": "PARTIAL",
    "R5": "PARTIAL",
    "R6": "PARTIAL",
    "R7": "PARTIAL",
    "R8": "PARTIAL",
    "R9": "PARTIAL",
    "R10": "PARTIAL",
    "R11": "MISSING",
    "R12": "PARTIAL",
    "R13": "PARTIAL",
    "R14": "PARTIAL",
    "R15": "PARTIAL",
    "R16": "PARTIAL",
    "R17": "PARTIAL",
    "R18": "IMPLEMENTED-NOT-PROVEN",
    "R19": "PARTIAL",
    "R20": "PARTIAL",
    "R21": "PARTIAL",
}


def _classes(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("| R"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3 or not cells[0].startswith("R"):
            continue
        found[cells[0]] = cells[2]
    return found


def test_matrix_classes_match_the_reconciliation() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert _classes(text) == EXPECTED
    assert list(EXPECTED).count("R18") == 1
    assert sum(1 for value in EXPECTED.values() if value == "PROVEN") == 0
    assert sum(1 for value in EXPECTED.values() if value == "IMPLEMENTED-NOT-PROVEN") == 1
    assert sum(1 for value in EXPECTED.values() if value == "PARTIAL") == 19
    assert sum(1 for value in EXPECTED.values() if value == "MISSING") == 1
    assert "BLOCKED-DEPENDENCY" not in set(EXPECTED.values())
    assert "NOT-APPLICABLE" not in set(EXPECTED.values())
    assert "No Included requirement is PROVEN." in text
    assert "PROVEN 0" in text or "| PROVEN | 0 |" in text


def test_verdict_selects_one_unimplemented_slice() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    assert "**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE." in text
    assert "It is not implemented in this change." in text
    assert f"**Selected next engineering slice:** {SLICE}" in text
    assert "Runtime code is unchanged." in text
    assert START_SHA in text
    assert START_SHA in sprint
    assert START_SHA in roadmap
    assert START_SHA in gaps
    assert SLICE in sprint
    assert SLICE in roadmap
    assert SLICE in gaps
    assert SLICE in readme
    assert sprint.startswith("# Sprint 40")
    assert "**Status:** Planned" in sprint
    assert "This section does not rewrite the Planned status" in sprint
    assert "ENGINEERING COMPLETE" not in text.split("Not ENGINEERING COMPLETE")[0]
    assert "CI #472" in text
    assert "Build Image #168" in text
    assert "4388 passed, 5 skipped" in text
    assert "71 packages, 0 vulnerabilities, 0 exceptions" in text


def test_historical_audit_and_findings_stay_additive() -> None:
    historical = HISTORICAL.read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    assert "No Included requirement is PROVEN." in historical
    assert "| R14 | Do not authorize access using request-body" in historical
    assert "PARTIAL" in historical
    assert "This audit adds no new HIGH." in historical
    assert "does not rewrite section I" in gaps
    assert "In-process rate limits only" in gaps
    assert "CSRF not enforced" in gaps
    assert "CSP `'unsafe-inline'`" in gaps
    assert "No Dependabot/CodeQL/Trivy/pip-audit" in gaps
    assert "URL validation / SSRF hardening incomplete" in gaps
    assert "IMPLEMENTED-NOT-PROVEN" in text
    assert "CLOSED BY IMPLEMENTATION for the dependency class" in text
    assert "STILL OPEN" in text
    assert "No current repository evidence proves a reachable SSRF." in text
    assert "does not assign it a new HIGH or MEDIUM." in text
    assert "immutable_snapshot_owner" in text
    assert "product-definition conflict" in text
    assert "Do not reopen Sprint 38." in text


def test_sprint_38_and_sprint_39_stay_unchanged() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert "Sprint 38 stays IN PROGRESS" in text
    assert "closure validation stays blocked on Sprint 41" in text
    assert "Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE." in text
    assert "The Sprint 39 Class C count remains 19." in text
    assert "The Sprint 39 selected next engineering slice remains NONE." in text
    assert len(CURRENT_CLASS_C) == 19
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert "Routing stays 0." in text
    assert "No Shopify call was made." in text
    assert "No deploy was performed." in text
    assert "Affiliate activation stays off." in text
    assert "Sprint 41 stays UNSTARTED." in text
