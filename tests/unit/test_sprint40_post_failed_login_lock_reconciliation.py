"""Sprint 40 reconciliation after the durable failed-login lock.

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
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)

from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/roadmap/evidence/SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md"
PRIOR = ROOT / "docs/roadmap/evidence/SPRINT_40_POST_40_7_RECONCILIATION_2026-10-13.md"
LOCK = ROOT / "docs/roadmap/evidence/SPRINT_40_FAILED_LOGIN_LOCK_2026-10-13.md"
SPRINT40 = ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md"
ROADMAP = ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md"
GAPS = ROOT / "docs/roadmap/GAP_INVENTORY.md"
README = ROOT / "docs/roadmap/sprints/README.md"
START_SHA = "bfdac461250d67f8e144df0811e707410b685437"
SLICE = (
    "Ordinary shopping-assistant message submission must not apply twice "
    "when the same client request is retried."
)

EXPECTED: dict[str, str] = {
    "R1": "IMPLEMENTED-NOT-PROVEN",
    "R2": "PARTIAL",
    "R3": "PARTIAL",
    "R4": "PARTIAL",
    "R5": "PARTIAL",
    "R6": "PARTIAL",
    "R7": "PARTIAL",
    "R8": "PARTIAL",
    "R9": "IMPLEMENTED-NOT-PROVEN",
    "R10": "PARTIAL",
    "R11": "MISSING",
    "R12": "PARTIAL",
    "R13": "PARTIAL",
    "R14": "IMPLEMENTED-NOT-PROVEN",
    "R15": "PARTIAL",
    "R16": "PARTIAL",
    "R17": "PARTIAL",
    "R18": "IMPLEMENTED-NOT-PROVEN",
    "R19": "PARTIAL",
    "R20": "PARTIAL",
    "R21": "PARTIAL",
}

_DECISION_SERVICES = (
    "app/services/answer_from_evidence.py",
    "app/services/refine_session_recommendation.py",
    "app/services/propose_research.py",
)


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
    assert sum(1 for value in EXPECTED.values() if value == "IMPLEMENTED-NOT-PROVEN") == 4
    assert sum(1 for value in EXPECTED.values() if value == "PARTIAL") == 16
    assert sum(1 for value in EXPECTED.values() if value == "MISSING") == 1
    assert "BLOCKED-DEPENDENCY" not in set(EXPECTED.values())
    assert "NOT-APPLICABLE" not in set(EXPECTED.values())
    assert "No Included requirement is PROVEN." in text
    assert "| PROVEN | 0 |" in text
    assert "| IMPLEMENTED-NOT-PROVEN | 4 (R1, R9, R14, R18) |" in text
    assert "| PARTIAL | 16 (R2–R8, R10, R12, R13, R15–R17, R19–R21) |" in text
    assert "| MISSING | 1 (R11) |" in text


def test_verdict_selects_one_unimplemented_slice() -> None:
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
    assert "CI #484" in text
    assert "Build Image #172" in text
    assert "4445 passed, 5 skipped" in text
    assert "71 packages, 0 vulnerabilities, 0 exceptions" in text
    assert "not named Sprint 40.8" in sprint
    assert "not named Sprint 40.8" in roadmap
    assert "R11 stays MISSING." in text
    assert "does not outrank ordinary message replay" in text


def test_historical_records_stay_additive() -> None:
    prior = PRIOR.read_text(encoding="utf-8")
    lock = LOCK.read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    gaps = GAPS.read_text(encoding="utf-8")
    assert "| R9 | Account lockout or equivalent | PARTIAL |" in prior
    assert "Failed logins must stay limited after the shared auth window expires." in prior
    assert "R9 | IMPLEMENTED-NOT-PROVEN" in lock
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
    assert "A successful Docker build is not container vulnerability scanning." in text
    assert "`terraform validate` remains syntax validation." in text
    assert "does not close this HIGH" in text


def test_owner_binding_and_ownerless_decision_guard() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for relative in _DECISION_SERVICES:
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
    assert "cannot carry a decision" in text


def test_durable_login_lock_stays_implemented_not_proven() -> None:
    auth = (ROOT / "app/auth/service.py").read_text(encoding="utf-8")
    backend = (ROOT / "app/launch/rate_limit_backend.py").read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    assert FAILED_LOGIN_LOCK_THRESHOLD == 20
    assert FAILED_LOGIN_LOCK_DURATION_SECONDS == 15 * 60
    assert FAILED_LOGIN_FAILURE_RETENTION_SECONDS == 15 * 60
    assert "self._reject_if_login_locked(rate_key)" in auth
    assert "self._rate_limiter.reset(rate_key)" in auth
    assert "max_attempts=20" in backend
    assert "window_seconds=60" in backend
    assert "R9 therefore stays IMPLEMENTED-NOT-PROVEN." in text
    assert "R8 stays PARTIAL." in text
    assert "R16 stays PARTIAL." in text
    assert "Full WAF/CDN remains a non-goal." in text


def test_message_retry_is_still_unprotected() -> None:
    schema = (ROOT / "app/schemas/shopping_assistant.py").read_text(encoding="utf-8")
    endpoint = (ROOT / "app/api/v1/endpoints/shopping_assistant.py").read_text(encoding="utf-8")
    consumer = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    proposal = (ROOT / "app/services/propose_research.py").read_text(encoding="utf-8")
    text = AUDIT.read_text(encoding="utf-8")
    assert "idempotency" not in schema
    assert "emit_ask_product_events(" in endpoint
    assert "Idempotency-Key" not in consumer
    assert "proposal_version + 1" in proposal
    assert "research-auth:" in proposal or "derive_authorization_idempotency_key" in (
        ROOT / "app/services/research_authorization.py"
    ).read_text(encoding="utf-8")
    assert "Identical question text is not the replay identity." in text
    assert SLICE in text


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
