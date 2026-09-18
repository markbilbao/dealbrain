"""Current Sprint 29 closeout matrix. Does not mutate the Phase 29.0 freeze."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.validate_sprint29_phase_29_0 import TRACEABILITY_PATH, validate_traceability

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "tests/contracts/fixtures/sprint29-internal-closeout-matrix.json"
CHECKPOINT = ROOT / "docs/roadmap/evidence/SPRINT_29_FINAL_CHECKPOINT_2026-09-18.md"
RECONCILIATION = ROOT / "docs/roadmap/evidence/SPRINT_29_CURRENT_MAIN_RECONCILIATION_2026-09-15.md"
SPRINT_29 = ROOT / "docs/roadmap/sprints/SPRINT_29_PRODUCTION_CONSUMER_WEB_UI.md"
MASTER_ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
CC_SUITE_GLOBS = (
    "tests/unit/test_sprint29_*.py",
    "tests/unit/test_phase_29_4*.py",
    "tests/unit/test_research_authorization_handoff.py",
    "tests/unit/persistence/test_sprint29_*.py",
    "tests/contracts/test_sprint29_phase_29_0_contracts.py",
)
ALLOWED_STATUSES = {
    "already_complete",
    "blocked_31_38",
    "blocked_later",
}
EXPECTED_BASELINE = "4a4fe65fa7438c75208a0052f52b77f929ee3903"
HISTORICAL_BASELINE = "3c514943a8a0ec34d1df97d5a329d3acb4a86e07"
VERDICT = (
    "SPRINT 29 INTERNAL CONSUMER/CONVERSATIONAL CONTRACT COMPLETE — "
    "LIVE RESEARCH ACCEPTANCE REMAINS DEPENDENT"
)
FORBIDDEN_CLOSE_VERDICT = "SPRINT 29 COMPLETE / CLOSED"


def _matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _defined_test_ids() -> set[str]:
    names: set[str] = set()
    for path in ROOT.rglob("test_*.py"):
        if "node_modules" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test_"
            ):
                names.add(node.name)
    return names


def _cc_behavior_test_count() -> int:
    count = 0
    seen: set[Path] = set()
    for pattern in CC_SUITE_GLOBS:
        for path in ROOT.glob(pattern):
            if path in seen:
                continue
            seen.add(path)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(
                    node, ast.FunctionDef | ast.AsyncFunctionDef
                ) and node.name.startswith("test_"):
                    count += 1
    return count


def test_cc01_behavioral_matrix_is_complete() -> None:
    matrix = _matrix()
    entries = matrix["entries"]
    assert matrix["audit_baseline_sha"] == EXPECTED_BASELINE
    assert matrix["supersedes_pr"] == 127
    assert matrix["sprint_closed"] is False
    assert matrix["live_research_claimed"] is False
    assert matrix["shopping_beta_claimed"] is False
    assert matrix["merchant_certification_claimed"] is False
    assert matrix["unconditional_counsel_approval_claimed"] is False
    assert matrix["phase_29_0_freeze_untouched"] is True
    assert matrix["sprint29_owns_remaining_implementation"] is False
    assert "later_sprint_launch_acceptance_does_not_block_close" not in matrix
    assert matrix["minimum_cc_behavior_tests"] >= 20
    assert len(entries) == 24
    assert {entry["acceptance_id"] for entry in entries} == {
        f"CC-01-{number:02d}" for number in range(1, 25)
    }
    assert {entry["status"] for entry in entries} <= ALLOWED_STATUSES
    defined = _defined_test_ids()
    for entry in entries:
        assert entry["evidence_test_id"] in defined
        assert entry["internal_vs_dependent"] in {"internal", "dependent"}
        assert entry["sprint29_owns_remaining_implementation"] is False
    assert any(entry["status"] == "blocked_31_38" for entry in entries)
    assert any(
        entry["acceptance_id"] == "CC-01-24" and entry["status"] == "blocked_later"
        for entry in entries
    )
    assert _cc_behavior_test_count() >= matrix["minimum_cc_behavior_tests"]


def test_phase_29_0_traceability_freeze_remains_planned() -> None:
    validate_traceability()
    frozen = json.loads((ROOT / TRACEABILITY_PATH).read_text(encoding="utf-8"))
    assert {entry["status"] for entry in frozen["entries"]} == {"planned_not_implemented"}


def test_internal_closeout_does_not_claim_live_research() -> None:
    matrix = _matrix()
    audit = RECONCILIATION.read_text(encoding="utf-8")
    checkpoint = CHECKPOINT.read_text(encoding="utf-8")
    sprint = SPRINT_29.read_text(encoding="utf-8")
    roadmap = MASTER_ROADMAP.read_text(encoding="utf-8")
    assert matrix["verdict"] == VERDICT
    assert matrix["sprint_closed"] is False
    assert VERDICT in audit
    assert VERDICT in sprint
    assert VERDICT in checkpoint
    assert FORBIDDEN_CLOSE_VERDICT not in matrix["verdict"]
    assert "Sprint 29 is **not** COMPLETE/CLOSED" in sprint
    assert "Sprint 29 is **not** COMPLETE/CLOSED" in checkpoint
    assert "**Do not** mark Sprint 29 closed" in roadmap
    assert "Full CC-01 staging proof on frozen launch candidate" in roadmap
    assert "Required for EC-02 / EC-22" in roadmap
    assert "No additional internally controllable Sprint 29" in checkpoint
    assert "CC-01-10/11/12/24" in checkpoint
    assert "does **not** mean Sprint 38 must be implemented inside Sprint 29" in checkpoint
    assert HISTORICAL_BASELINE in audit
    assert "PR #127" in checkpoint
    assert "stale" in checkpoint.lower() and "superseded" in checkpoint.lower()
    assert "live merchant research" in checkpoint.lower()
    assert "was not implemented or claimed" in checkpoint
    assert "public shopping beta" in checkpoint.lower()
    assert "Early Access" in checkpoint
    assert "terms-2026-09-11" in audit
    assert "privacy-2026-09-11" in audit
    assert "unconditional counsel approval" in audit.lower()
    assert "no production, staging, aws" in checkpoint.lower()
