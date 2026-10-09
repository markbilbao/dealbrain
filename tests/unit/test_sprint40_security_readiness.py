"""Sprint 40 security readiness audit.

The review selects one engineering slice and does not implement it.
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
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
SPRINT39 = ROOT / "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
START_SHA = "0452c40610ac61cd9dce4af361718cb4fd2c02d7"
SLICE = "Non-decision assistant body-identity authorization"

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
    "R18": "PARTIAL",
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


def test_matrix_classes_match_the_audit() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert _classes(text) == EXPECTED
    assert "PROVEN" not in set(EXPECTED.values())
    assert "NOT-APPLICABLE" not in set(EXPECTED.values())
    assert "BLOCKED-DEPENDENCY" not in set(EXPECTED.values())
    assert "No Included requirement is PROVEN." in text


def test_verdict_selects_one_unimplemented_slice() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    assert "**Audit verdict:** One bounded Sprint 40 engineering slice is selected." in text
    assert "It is not implemented in this change." in text
    assert f"**Selected next engineering slice:** {SLICE}." in text
    assert "Choice:** A." in text
    assert "B is not selected." in text
    assert "C is not selected." in text
    assert "Runtime code is unchanged." in text
    assert START_SHA in text
    assert START_SHA in sprint
    assert START_SHA in roadmap
    assert START_SHA in gaps
    assert "engineering not started" in readme
    assert SLICE in sprint
    assert SLICE in roadmap
    assert SLICE in gaps
    assert SLICE in readme
    assert sprint.startswith("# Sprint 40")
    assert "**Status:** Planned" in sprint
    assert "This section does not rewrite the Planned status" in sprint


def test_sprint_38_and_sprint_39_stay_unchanged() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    sprint39 = SPRINT39.read_text(encoding="utf-8")
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert "Sprint 38 stays IN PROGRESS" in text
    assert "ENGINEERING COMPLETE" in text
    assert "closure validation stays blocked on Sprint 41" in text
    assert "Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE." in text
    assert "The Sprint 39 Class C count remains 19." in text
    assert "The Sprint 39 selected next engineering slice remains NONE." in text
    assert len(CURRENT_CLASS_C) == 19
    assert "not ENGINEERING COMPLETE" in sprint39
    assert "Selected next engineering slice remains NONE" in sprint39 or (
        "Selected next engineering slice:** NONE" in sprint39
        or "**Selected next engineering slice:** NONE" in sprint39
    )
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert "Routing stays 0." in text
    assert "No Shopify call was made." in text
    assert "No deploy was performed." in text
    assert "Affiliate tracking was not enabled." in text


def test_historical_findings_are_not_rewritten_or_upgraded() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    assert "This audit adds no new HIGH." in text
    assert "does not promote them to launch-blocking" in text
    assert "In-process rate limits only" in gaps
    assert "CSRF not enforced" in gaps
    assert "CSP `'unsafe-inline'`" in gaps
    assert "No Dependabot/CodeQL/Trivy/pip-audit" in gaps
    assert "URL validation / SSRF hardening incomplete" in gaps
    assert "does not rewrite section I" in gaps
    assert "CI #453" in text
    assert "Build Image #161" in text
