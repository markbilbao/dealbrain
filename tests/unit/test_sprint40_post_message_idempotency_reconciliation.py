"""Sprint 40 reconciliation after shopping-assistant submission idempotency.

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
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_access_stage import SPRINT_38_STATUS
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)
from app.shopping.submission_idempotency import (
    PROCESSING_HORIZON_SECONDS,
    SUBMISSION_RETENTION_SECONDS,
)

from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT / "docs/roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md"
)
PRIOR = ROOT / "docs/roadmap/evidence/SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md"
LEDGER = ROOT / "docs/roadmap/evidence/SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
START_SHA = "32b5a0292195588625e8e515badd5e176cbeb6e8"
SLICE = (
    "Write the Sprint 40 security-readiness package: a penetration-test readiness checklist, "
    "a security incident-response runbook, a vulnerability-response process, and a Sprint 44 "
    "security go/no-go draft."
)

EXPECTED: dict[str, str] = {
    "R1": "IMPLEMENTED-NOT-PROVEN",
    "R2": "PARTIAL",
    "R3": "IMPLEMENTED-NOT-PROVEN",
    "R4": "PARTIAL",
    "R5": "IMPLEMENTED-NOT-PROVEN",
    "R6": "PARTIAL",
    "R7": "IMPLEMENTED-NOT-PROVEN",
    "R8": "PARTIAL",
    "R9": "IMPLEMENTED-NOT-PROVEN",
    "R10": "PARTIAL",
    "R11": "MISSING",
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
    assert sum(1 for value in EXPECTED.values() if value == "IMPLEMENTED-NOT-PROVEN") == 9
    assert sum(1 for value in EXPECTED.values() if value == "PARTIAL") == 11
    assert sum(1 for value in EXPECTED.values() if value == "MISSING") == 1
    assert "BLOCKED-DEPENDENCY" not in set(EXPECTED.values())
    assert "NOT-APPLICABLE" not in set(EXPECTED.values())
    assert "No Included requirement is PROVEN." in text
    assert "| PROVEN | 0 |" in text
    assert "| IMPLEMENTED-NOT-PROVEN | 9 (R1, R3, R5, R7, R9, R14, R17, R18, R20) |" in text
    assert "| PARTIAL | 11 (R2, R4, R6, R8, R10, R12, R13, R15, R16, R19, R21) |" in text
    assert "| MISSING | 1 (R11) |" in text


def test_verdict_selects_the_security_package_and_leaves_it_unimplemented() -> None:
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
    assert "**Status:** Planned" in sprint
    assert "This section does not rewrite the Planned status" in sprint
    assert "ENGINEERING COMPLETE" not in text.split("Not ENGINEERING COMPLETE")[0]
    assert "CI #491" in text
    assert "Build Image #174" in text
    assert "4471 passed, 5 skipped" in text
    assert "71 packages, 0 vulnerabilities, 0 exceptions" in text
    assert "R17 is IMPLEMENTED-NOT-PROVEN." in text
    assert "R16 stays PARTIAL." in text
    assert "Signed provenance is not a Sprint 40 engineering blocker." in text
    assert "Origin enforcement is the beta control" in text


def test_historical_message_gap_is_not_rewritten() -> None:
    prior = PRIOR.read_text(encoding="utf-8")
    ledger = LEDGER.read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    assert "| R17 | Add idempotency and replay protection" in prior
    assert "Ordinary message submission has no idempotency field." in prior
    assert "R17 | IMPLEMENTED-NOT-PROVEN" in ledger
    assert "not rewrite" in text
    assert "CLOSED BY IMPLEMENTATION for the dependency class" in text
    assert "STILL OPEN" in text
    assert "No current repository evidence proves a reachable SSRF." in text
    assert "immutable_snapshot_owner" in text
    assert "product-definition conflict" in text
    assert "A successful Docker build is not container vulnerability scanning." in text
    assert "`terraform validate` remains syntax validation." in text


def test_r17_ledger_matches_the_implemented_not_proven_reading() -> None:
    endpoint = (ROOT / "app/api/v1/endpoints/shopping_assistant.py").read_text(encoding="utf-8")
    consumer = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    scope = (ROOT / "app/shopping/submission_idempotency.py").read_text(encoding="utf-8")
    store = (ROOT / "app/infrastructure/database/shopping_submission_store.py").read_text(
        encoding="utf-8"
    )
    research = (ROOT / "app/services/research_authorization.py").read_text(encoding="utf-8")
    assert "parse_submission_key" in endpoint
    assert "if applied.fresh:" in endpoint
    assert "emit_ask_product_events(" in endpoint
    assert "service.query(" in endpoint
    assert "pendingAskSubmission.body === body" in consumer
    assert "crypto.randomUUID" in consumer
    assert '"Idempotency-Key": key' in consumer
    assert "profile_id" not in submission_scope_names(scope)
    assert "user_id" in scope
    assert "def submission_authority_scope" in scope
    assert SUBMISSION_RETENTION_SECONDS == 24 * 60 * 60
    assert PROCESSING_HORIZON_SECONDS == 15 * 60
    assert 'state="indeterminate"' in store
    assert "SqlShoppingSubmissionStore" in scope
    assert "research-auth:" in research
    assert "client_confirmation_token" in research


def submission_scope_names(source: str) -> tuple[str, ...]:
    start = source.index("def submission_authority_scope")
    end = source.index("def _require_opaque_parts")
    function = source[start:end]
    return tuple(name for name in ("profile_id", "user_id") if name in function)


def test_owner_binding_still_rejects_an_ownerless_decision() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for relative in (
        "app/services/answer_from_evidence.py",
        "app/services/refine_session_recommendation.py",
        "app/services/propose_research.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "self._conversations.get(" not in source
        assert "bound_owner = context.owner" not in source
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
    assert "not a reachable public path" in text


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
