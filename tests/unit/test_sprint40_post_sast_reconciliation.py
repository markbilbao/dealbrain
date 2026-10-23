"""Sprint 40 reconciliation after the merged Bandit SAST gate.

The review reclassifies R1–R21 and does not implement the selected slice.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.domain.entities.shopping_assistant import (
    ConversationContext,
    ConversationOwner,
    DecisionContextReference,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.launch.failed_login_lock import (
    FAILED_LOGIN_FAILURE_RETENTION_SECONDS,
    FAILED_LOGIN_LOCK_DURATION_SECONDS,
    FAILED_LOGIN_LOCK_THRESHOLD,
)
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_access_stage import SPRINT_38_STATUS
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.shopify_global_catalog_transport import SHOPIFY_PRODUCTION_CATALOG_ENDPOINT
from app.research.sprint38_live_execution import (
    LIVE_RESEARCH_EXECUTION_OPERATIONAL,
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)

from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_40_POST_SAST_RECONCILIATION_2026-10-15.md"
PRIOR = (
    ROOT / "docs/roadmap/evidence/SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md"
)
SAST = ROOT / "docs/roadmap/evidence/SPRINT_40_SAST_GATE_2026-10-14.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
BASELINE = ROOT / "tests/security/baselines/bandit.baseline.json"
START_SHA = "80a4506485c7f4a6a566c495120723995dfc2c17"
SLICE = (
    "Extend the deterministic secret-scanning gate to application source with an "
    "explicit reviewed exact-exception mechanism for intentional safe demo constants."
)
WITHDRAWN_CONTAINER_SLICE = (
    "Add one deterministic container-vulnerability scan of the locally built "
    "runtime image, and fail publication before that image is pushed."
)

EXPECTED: dict[str, str] = {
    "R1": "IMPLEMENTED-NOT-PROVEN",
    "R2": "IMPLEMENTED-NOT-PROVEN",
    "R3": "IMPLEMENTED-NOT-PROVEN",
    "R4": "IMPLEMENTED-NOT-PROVEN",
    "R5": "IMPLEMENTED-NOT-PROVEN",
    "R6": "PARTIAL",
    "R7": "IMPLEMENTED-NOT-PROVEN",
    "R8": "IMPLEMENTED-NOT-PROVEN",
    "R9": "IMPLEMENTED-NOT-PROVEN",
    "R10": "PARTIAL",
    "R11": "IMPLEMENTED-NOT-PROVEN",
    "R12": "PARTIAL",
    "R13": "PARTIAL",
    "R14": "IMPLEMENTED-NOT-PROVEN",
    "R15": "PARTIAL",
    "R16": "PARTIAL",
    "R17": "IMPLEMENTED-NOT-PROVEN",
    "R18": "IMPLEMENTED-NOT-PROVEN",
    "R19": "PARTIAL",
    "R20": "IMPLEMENTED-NOT-PROVEN",
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
        if not cells[0][1:].isdigit():
            continue
        found[cells[0]] = cells[2]
    return found


def _owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-1",
        session_id="session-1",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def _decision() -> DecisionContextReference:
    digest = "ab" * 32
    return DecisionContextReference(
        decision_id="decision-1",
        context_version=1,
        evaluated_product_ids=("product-1",),
        canonical_piqscore_snapshot_sha256=digest,
        recommendation_snapshot_sha256=digest,
    )


def test_matrix_classes_match_the_reconciliation() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert _classes(text) == EXPECTED
    assert sum(1 for value in EXPECTED.values() if value == "PROVEN") == 0
    assert sum(1 for value in EXPECTED.values() if value == "IMPLEMENTED-NOT-PROVEN") == 13
    assert sum(1 for value in EXPECTED.values() if value == "PARTIAL") == 8
    assert sum(1 for value in EXPECTED.values() if value == "MISSING") == 0
    assert "BLOCKED-DEPENDENCY" not in set(EXPECTED.values())
    assert "NOT-APPLICABLE" not in set(EXPECTED.values())
    assert "No Included requirement is PROVEN." in text
    assert "| PROVEN | 0 |" in text
    assert (
        "| IMPLEMENTED-NOT-PROVEN | 13 (R1, R2, R3, R4, R5, R7, R8, R9, R11, R14, R17, R18, R20) |"
        in text
    )
    assert "| PARTIAL | 8 (R6, R10, R12, R13, R15, R16, R19, R21) |" in text
    assert "| MISSING | 0 |" in text


def test_verdict_selects_application_secret_scan_and_leaves_it_unimplemented() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    sprint = SPRINT40.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    assert "**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE." in text
    assert "It is not implemented in this change." in text
    assert f"**Selected next engineering slice:** {SLICE}" in text
    assert "This slice is not named Sprint 40.8." in text
    assert "Runtime code is unchanged." in text
    assert "All five are required for this row and for Sprint 40 ENGINEERING COMPLETE." in text
    assert "It does not name a scanner brand." in text
    assert "**What must be scanned:** B." in text
    assert "A successful Docker build is not container vulnerability scanning." in text
    assert "`terraform validate` is not IaC security scanning." in text
    assert "The SAST capability stays IMPLEMENTED-NOT-PROVEN." in text
    assert "CI does not prove the capability." in text or "is not PROVEN from CI alone." in text
    assert START_SHA in text
    assert START_SHA in sprint
    assert START_SHA in roadmap
    assert START_SHA in gaps
    assert START_SHA in readme
    assert SLICE in sprint
    assert SLICE in roadmap
    assert SLICE in gaps
    assert SLICE in readme
    assert sprint.startswith("# Sprint 40")
    assert "**Status:** Planned" in sprint.split("## Current reading", 1)[0]
    assert "This section does not rewrite the Planned status" in sprint
    assert "ENGINEERING COMPLETE" not in text.split("Not ENGINEERING COMPLETE")[0]
    assert "CI #499" in text
    assert "Build Image #178" in text
    assert "4511 passed, 5 skipped" in text
    assert "649" in text
    assert "35 exact" in text
    assert "73 packages, 0 vulnerabilities, 0 exceptions" in text
    assert "R11 is not PROVEN" in text
    assert "SECURITY GO: NOT DECIDED" in text
    assert "requires an owner decision" in text
    assert "no public security consequence" in text
    assert "That selection is withdrawn." in text
    assert "Bandit is not a secret scanner." in text
    assert "This is not a completed secret-scanning capability for Sprint 40." in text
    assert "This audit does not add `app/**/*` to `SCAN_GLOBS`." in text
    assert "DEMO_PASSWORD" in text
    assert "INTERNAL_LAUNCH_ADMIN_TOKEN" in text
    assert "app/user/fixtures.py" in text
    assert "app/launch/internal_auth.py" in text
    assert "| Secrets | Yes | Incomplete |" in text
    assert "| Dependency | Yes | Present |" in text
    assert "| SAST | Yes | IMPLEMENTED-NOT-PROVEN |" in text
    assert "| Container vulnerability scanning | Yes | Absent |" in text
    assert "| Terraform / IaC security | Yes | Absent |" in text
    assert "R6 stays PARTIAL" in text
    assert f"**Selected next engineering slice:** {WITHDRAWN_CONTAINER_SLICE}" not in text
    scanner = (ROOT / "scripts/secret_scan_25a.py").read_text(encoding="utf-8")
    globs = scanner.split("SCAN_GLOBS = (", 1)[1].split(")", 1)[0]
    assert '"infra/**/*"' in globs
    assert '".env*.example"' in globs
    assert '"scripts/**/*"' in globs
    assert '".github/workflows/**/*"' in globs


def test_historical_records_are_not_rewritten() -> None:
    prior = PRIOR.read_text(encoding="utf-8")
    sast = SAST.read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    assert "SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`." in prior
    assert "**Selected next engineering slice:** Add one deterministic SAST gate in CI" in prior
    assert "It does not select a later engineering slice." in sast
    assert "The SAST capability is IMPLEMENTED-NOT-PROVEN." in sast
    assert "not copied forward" in text
    assert "CLOSED BY IMPLEMENTATION for the original no-scanner condition" in text
    assert "STILL OPEN" in text
    assert "does not broaden" in text
    assert "In-process rate limits only" in text
    assert "immutable_snapshot_owner" in text


def test_sast_gate_shape_still_matches_the_reading() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert baseline["scanner"] == "bandit"
    assert baseline["scanner_version"] == "1.9.4"
    assert baseline["scope"] == "app/**/*.py"
    assert len(baseline["exceptions"]) == 34
    assert not any(item["path"] == "app/launch/internal_auth.py" for item in baseline["exceptions"])
    assert not any("*" in item["path"] or "*" in item["test_id"] for item in baseline["exceptions"])
    gate = (ROOT / "scripts/check_sast_baseline.py").read_text(encoding="utf-8")
    assert 'BANDIT_VERSION = "1.9.4"' in gate
    assert '"--ignore-nosec"' in gate
    assert "stale baseline exception" in gate
    assert "unbaselined SAST finding" in gate
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in ci
    assert "security-events" not in ci
    assert "scripts/check_sast_baseline.py" in ci
    assert "scripts/check_pip_audit_baseline.py" in ci
    assert "scripts/secret_scan_25a.py" in ci
    assert "terraform validate" in ci
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12-alpine3.24" in dockerfile
    assert (
        "ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff"
        in dockerfile
    )
    build = (ROOT / ".github/workflows/build-image.yml").read_text(encoding="utf-8")
    assert "push: false" in build
    assert "push: true" not in build
    assert "trivy" not in build.lower()
    lowered = build.lower()
    assert lowered.index("container vulnerability gate") < lowered.index("log in to ghcr")
    assert lowered.index("log in to ghcr") < lowered.index("docker push")
    assert "checkov" not in ci.lower()
    assert "tfsec" not in ci.lower()
    assert SHOPIFY_PRODUCTION_CATALOG_ENDPOINT == "https://catalog.shopify.com/api/ucp/mcp"
    assert FAILED_LOGIN_LOCK_THRESHOLD == 20
    assert FAILED_LOGIN_LOCK_DURATION_SECONDS == 15 * 60
    assert FAILED_LOGIN_FAILURE_RETENTION_SECONDS == 15 * 60
    assert LIVE_RESEARCH_EXECUTION_OPERATIONAL is False


def test_ownerless_decision_still_fails_closed() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="decision-bound conversation requires an owner"):
        ConversationContext(
            conversation_id="ownerless-decision",
            turns=(),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            decision_context=_decision(),
        )
    repository = InMemoryConversationRepository()
    created = repository.create(owner=None)
    assert created.owner is None
    assert created.decision_context is None
    assert repository.get_for_owner(created.conversation_id, _owner()) is None
    assert "R13 stays PARTIAL" in text


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
