"""Sprint 40 reconciliation after the merged security-readiness package.

The review reclassifies R1–R21 and does not implement the selected slice.
"""

from __future__ import annotations

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
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)

from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT / "docs/roadmap/evidence/SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md"
)
PRIOR = (
    ROOT / "docs/roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md"
)
PACKAGE = ROOT / "docs/roadmap/evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
START_SHA = "e4a8802e7edd87e234996e2f86be4ca2dee31c3e"
SLICE = "Add one deterministic SAST gate in CI over application code."

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


def test_verdict_selects_one_sast_gate_and_leaves_it_unimplemented() -> None:
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
    assert "Container scanning and IaC security scanning are not bundled with it." in text
    assert "No CodeQL workflow exists." in text
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
    assert "CI #495" in text
    assert "Build Image #176" in text
    assert "4484 passed, 5 skipped" in text
    assert "71 packages, 0 vulnerabilities, 0 exceptions" in text
    assert "R11 is not PROVEN" in text
    assert "SECURITY GO: NOT DECIDED" in text
    assert "accepted bounded guest-session design" in text
    assert "this audit does not invent one" in text
    assert "Signed provenance is not a Sprint 40 engineering blocker." in text
    assert "Origin enforcement is the beta CSRF control" in text


def test_historical_records_are_not_rewritten() -> None:
    prior = PRIOR.read_text(encoding="utf-8")
    package = PACKAGE.read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    assert "| MISSING | 1 (R11) |" in prior
    assert "R11 stays MISSING and is the selected slice." in prior
    assert "Before this package | MISSING" in package
    assert "After this package | IMPLEMENTED-NOT-PROVEN" in package
    assert "not rewrite" in text
    assert "CLOSED BY IMPLEMENTATION for the original no-scanner condition" in text
    assert "STILL OPEN" in text
    assert "No current repository evidence proves a reachable SSRF." in text
    assert "immutable_snapshot_owner" in text
    assert "product-definition conflict" in text
    assert "A successful Docker build is not container vulnerability scanning." in text
    assert "`terraform validate` is not the Terraform class." in text
    assert "In-process rate limits only" in text


def test_account_cookie_checks_session_revocation_and_guest_cookie_does_not() -> None:
    source = (ROOT / "app/consumer/owner_authorization.py").read_text(encoding="utf-8")
    assert 'if owner.principal_type == "guest":' in source
    assert "return owner" in source
    assert "if session.revoked:" in source
    assert "sessions.get_by_id(owner.session_id)" in source
    account = (ROOT / "app/static/consumer/js/account.js").read_text(encoding="utf-8")
    assert '"/api/v1/auth/logout"' in account
    assert '"/account/clear-device"' in account
    auth = (ROOT / "app/auth/service.py").read_text(encoding="utf-8")
    assert "def hash_token" in auth
    assert "hashlib.sha256" in auth
    assert "revoke_all_for_user" in auth


def test_scanners_and_url_trust_match_the_reading() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "scripts/secret_scan_25a.py" in ci
    assert "scripts/check_pip_audit_baseline.py" in ci
    assert "terraform validate" in ci
    assert "codeql" not in ci.lower()
    assert "aquasecurity/trivy-action" not in ci.lower()
    assert "checkov" not in ci.lower()
    assert "tfsec" not in ci.lower()
    audit = AUDIT.read_text(encoding="utf-8")
    assert "It does not scan `app/`." in audit or "Scan globs omit `app/`." in audit
    assert SHOPIFY_PRODUCTION_CATALOG_ENDPOINT == "https://catalog.shopify.com/api/ucp/mcp"
    url_trust = (ROOT / "app/security/url_trust.py").read_text(encoding="utf-8")
    assert "def validate_browser_destination" in url_trust
    assert "def validate_server_fetch_url" in url_trust
    assert FAILED_LOGIN_LOCK_THRESHOLD == 20
    assert FAILED_LOGIN_LOCK_DURATION_SECONDS == 15 * 60
    assert FAILED_LOGIN_FAILURE_RETENTION_SECONDS == 15 * 60


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
    assert "no public security consequence" in text


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
