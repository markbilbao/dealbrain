"""Sprint 40.7: a body conversation id must not adopt a stored decision owner."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
)
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.research.routing import _CONFIGURED_BUCKET
from app.research.shopify_global_catalog_access_stage import SPRINT_38_STATUS
from app.research.shopify_global_catalog_execution import REAL_SHOPIFY_CALLS
from app.research.sprint38_live_execution import (
    SHOPIFY_LIVE_CALL_PERMITTED,
    SPRINT_38_ENGINEERING_STATUS,
)
from app.services.answer_from_evidence import AnswerFromEvidenceService
from app.services.propose_research import ProposeResearchService
from app.services.refine_session_recommendation import RefineSessionRecommendationService
from app.services.research_execution import AuthorizedExecutionLedger

from tests.unit.test_phase_29_4a_answer_from_evidence import (
    DECISION_ID as ANSWER_DECISION_ID,
)
from tests.unit.test_phase_29_4a_answer_from_evidence import (
    START as ANSWER_START,
)
from tests.unit.test_phase_29_4a_answer_from_evidence import (
    _owner as answer_owner,
)
from tests.unit.test_phase_29_4a_answer_from_evidence import (
    _snapshot as answer_snapshot,
)
from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    DECISION_ID as REFINE_DECISION_ID,
)
from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    START as REFINE_START,
)
from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    _owner as refine_owner,
)
from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    _presentation,
)
from tests.unit.test_sprint39_5_post_merge_classification import CURRENT_CLASS_C

ROOT = Path(__file__).resolve().parents[2]
OTHER_DECISION_ID = "00000000-0000-4000-8000-00000000007b"
FOREIGN_FACT = "FOREIGN_OWNER_B_SECRET_EVIDENCE"
SERVICES = (
    "app/services/answer_from_evidence.py",
    "app/services/refine_session_recommendation.py",
    "app/services/propose_research.py",
)


class _GuardedConversations:
    """Delegates owner-scoped reads and records an unscoped get()."""

    def __init__(self, inner: InMemoryConversationRepository) -> None:
        self.inner = inner
        self.unscoped_gets: list[str] = []

    def get(self, conversation_id: str):
        self.unscoped_gets.append(conversation_id)
        return self.inner.get(conversation_id)

    def get_for_owner(self, conversation_id: str, owner: ConversationOwner):
        return self.inner.get_for_owner(conversation_id, owner)

    def __getattr__(self, name: str):
        return getattr(self.inner, name)


class _RecordingSnapshots:
    """Records the owner principal used for each owner-scoped snapshot read."""

    def __init__(self, inner: InMemoryDecisionSnapshotRepository) -> None:
        self.inner = inner
        self.owner_reads: list[tuple[str, str]] = []

    def get_for_owner(
        self,
        decision_id: str,
        context_version: int,
        owner: ConversationOwner,
    ):
        self.owner_reads.append((decision_id, owner.principal_id))
        return self.inner.get_for_owner(decision_id, context_version, owner)

    def __getattr__(self, name: str):
        return getattr(self.inner, name)


def _world(owner_factory, snapshot_factory, clock):
    owner_a = owner_factory("guest-a")
    owner_b = owner_factory("guest-b")
    snapshot_a = snapshot_factory(owner_a)
    foreign = snapshot_factory(owner_b)
    secret = replace(foreign.evidence[0], fact=FOREIGN_FACT)
    snapshot_b = replace(
        foreign,
        decision_id=OTHER_DECISION_ID,
        evidence=(secret, *foreign.evidence[1:]),
    )
    snapshots = InMemoryDecisionSnapshotRepository(clock=clock)
    snapshots.add(snapshot_a)
    snapshots.add(snapshot_b)
    conversations = InMemoryConversationRepository(clock=clock, ttl_seconds=3600)
    recording = _RecordingSnapshots(snapshots)
    guard = _GuardedConversations(conversations)
    bound = guard.create(owner=owner_a, decision_context=snapshot_a.to_reference())
    return {
        "owner_a": owner_a,
        "owner_b": owner_b,
        "snapshot_a": snapshot_a,
        "snapshot_b": snapshot_b,
        "recording": recording,
        "guard": guard,
        "conversation_id": bound.conversation_id,
        "clock": clock,
    }


def _answer_world():
    world = _world(answer_owner, answer_snapshot, lambda: ANSWER_START)
    world["service"] = AnswerFromEvidenceService(
        snapshots=world["recording"],
        conversations=world["guard"],
        clock=world["clock"],
    )
    world["decision_id"] = ANSWER_DECISION_ID
    return world


def _refine_world():
    world = _world(refine_owner, _presentation, lambda: REFINE_START)
    world["service"] = RefineSessionRecommendationService(
        snapshots=world["recording"],
        conversations=world["guard"],
        clock=world["clock"],
    )
    world["decision_id"] = REFINE_DECISION_ID
    return world


def _research_world():
    world = _world(refine_owner, _presentation, lambda: REFINE_START)
    world["service"] = ProposeResearchService(
        snapshots=world["recording"],
        conversations=world["guard"],
        clock=world["clock"],
        execution_ledger=AuthorizedExecutionLedger(),
    )
    world["decision_id"] = REFINE_DECISION_ID
    return world


def _assert_closed(world, exc: BaseException) -> None:
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert FOREIGN_FACT not in str(exc)
    stored = world["guard"].inner.get_for_owner(
        world["conversation_id"],
        world["owner_a"],
    )
    assert stored is not None
    assert stored.owner is not None
    assert stored.owner.has_same_identity(world["owner_a"])


def test_decision_services_do_not_read_conversations_by_body_id() -> None:
    for relative in SERVICES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "self._conversations.get(" not in source
        assert "bound_owner = context.owner" not in source


def test_answer_ownerless_body_conversation_cannot_read_uuid_snapshot() -> None:
    world = _answer_world()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].answer(
            {
                "query": "Which one has better battery?",
                "decision_id": world["decision_id"],
                "conversation_id": world["conversation_id"],
            }
        )
    _assert_closed(world, caught.value)


def test_answer_foreign_owner_cannot_read_bound_conversation() -> None:
    world = _answer_world()
    with pytest.raises(ShoppingAssistantNotFoundError) as caught:
        world["service"].answer(
            {
                "query": "Which one has better battery?",
                "decision_id": world["decision_id"],
                "conversation_id": world["conversation_id"],
            },
            owner=world["owner_b"],
        )
    _assert_closed(world, caught.value)


def test_answer_verified_owner_reads_own_bound_conversation() -> None:
    world = _answer_world()
    response = world["service"].answer(
        {
            "query": "Which one has better battery?",
            "decision_id": world["decision_id"],
            "conversation_id": world["conversation_id"],
        },
        owner=world["owner_a"],
    )
    assert response.processing["action"] == "answer_from_evidence"
    assert "battery" in response.answer.lower()
    assert FOREIGN_FACT not in response.answer
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == [(world["decision_id"], "guest-a")]


def test_answer_body_ids_cannot_adopt_another_stored_owner() -> None:
    world = _answer_world()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].answer(
            {
                "query": "Which one has better battery?",
                "decision_id": OTHER_DECISION_ID,
                "conversation_id": world["conversation_id"],
            }
        )
    _assert_closed(world, caught.value)

    owned = world["service"].answer(
        {
            "query": "Which one has better battery?",
            "decision_id": OTHER_DECISION_ID,
            "conversation_id": world["conversation_id"],
        },
        owner=world["owner_a"],
    )
    assert FOREIGN_FACT not in owned.answer
    assert "battery" in owned.answer.lower()
    assert world["recording"].owner_reads == [(world["decision_id"], "guest-a")]
    assert all(owner_id == "guest-a" for _, owner_id in world["recording"].owner_reads)


def test_answer_fixture_does_not_load_an_unverified_overlay() -> None:
    world = _answer_world()
    response = world["service"].answer(
        {
            "query": "Which one has better battery?",
            "decision_id": "headphones-standard",
            "conversation_id": world["conversation_id"],
        }
    )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert FOREIGN_FACT not in response.answer
    assert response.processing["decision_id"] == "headphones-standard"


def test_refine_ownerless_body_conversation_cannot_read_uuid_snapshot() -> None:
    world = _refine_world()
    seeded = world["service"].refine(
        {"query": "Comfort matters more.", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded.processing["session_refinement_version"] == 1
    world["recording"].owner_reads.clear()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].refine(
            {
                "query": "Battery life matters more.",
                "decision_id": world["decision_id"],
                "conversation_id": seeded.conversation_id,
            }
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert FOREIGN_FACT not in str(caught.value)
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None
    assert stored.session_refinement is not None
    assert stored.session_refinement.refinement_version == 1


def test_refine_foreign_owner_cannot_read_another_overlay() -> None:
    world = _refine_world()
    seeded = world["service"].refine(
        {"query": "Comfort matters more.", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    world["recording"].owner_reads.clear()
    with pytest.raises(ShoppingAssistantNotFoundError) as caught:
        world["service"].refine(
            {
                "query": "Battery life matters more.",
                "decision_id": world["decision_id"],
                "conversation_id": seeded.conversation_id,
            },
            owner=world["owner_b"],
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert "Bose" not in str(caught.value)
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None
    assert stored.session_refinement is not None
    assert stored.session_refinement.session_best_piq_product_id


def test_refine_verified_owner_continues_own_overlay() -> None:
    world = _refine_world()
    seeded = world["service"].refine(
        {"query": "Comfort matters more.", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    followed = world["service"].refine(
        {
            "query": "Battery life matters more.",
            "decision_id": world["decision_id"],
            "conversation_id": seeded.conversation_id,
        },
        owner=world["owner_a"],
    )
    assert followed.processing["session_refinement_version"] == 2
    assert followed.conversation_id == seeded.conversation_id
    assert world["guard"].unscoped_gets == []
    assert {owner_id for _, owner_id in world["recording"].owner_reads} == {"guest-a"}


def test_refine_body_ids_cannot_adopt_another_stored_owner() -> None:
    world = _refine_world()
    seeded = world["service"].refine(
        {"query": "Comfort matters more.", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    world["recording"].owner_reads.clear()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].refine(
            {
                "query": "Comfort matters more.",
                "decision_id": OTHER_DECISION_ID,
                "conversation_id": seeded.conversation_id,
            }
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert FOREIGN_FACT not in str(caught.value)

    owned = world["service"].refine(
        {
            "query": "Battery life matters more.",
            "decision_id": OTHER_DECISION_ID,
            "conversation_id": seeded.conversation_id,
        },
        owner=world["owner_a"],
    )
    assert FOREIGN_FACT not in owned.answer
    assert world["recording"].owner_reads == [(world["decision_id"], "guest-a")]


def test_refine_fixture_does_not_load_an_unverified_overlay() -> None:
    world = _refine_world()
    seeded = world["service"].refine(
        {"query": "Comfort matters more.", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None and stored.session_refinement is not None
    bumped = replace(stored.session_refinement, refinement_version=7)
    world["guard"].inner.save(
        replace(stored, session_refinement=bumped),
        expected_version=stored.persistence_version,
    )
    world["recording"].owner_reads.clear()
    response = world["service"].refine(
        {
            "query": "Comfort matters more.",
            "decision_id": "headphones-standard",
            "conversation_id": seeded.conversation_id,
        }
    )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert response.processing.get("session_refinement_version") != 8
    kept = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert kept is not None and kept.session_refinement is not None
    assert kept.session_refinement.refinement_version == 7


def test_research_ownerless_body_conversation_cannot_read_proposal() -> None:
    world = _research_world()
    seeded = world["service"].handle(
        {"query": "What about AirPods Max?", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded is not None
    proposal_id = seeded.processing["proposal_id"]
    world["recording"].owner_reads.clear()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].handle(
            {
                "query": "Maybe.",
                "decision_id": world["decision_id"],
                "conversation_id": seeded.conversation_id,
            }
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert proposal_id not in str(caught.value)
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None and stored.research_proposal is not None
    assert stored.research_proposal.proposal_id == proposal_id
    assert stored.research_proposal.status == "pending_confirmation"


def test_research_foreign_owner_cannot_read_pending_proposal() -> None:
    world = _research_world()
    seeded = world["service"].handle(
        {"query": "What about AirPods Max?", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded is not None
    world["recording"].owner_reads.clear()
    with pytest.raises(ShoppingAssistantNotFoundError) as caught:
        world["service"].handle(
            {
                "query": "Maybe.",
                "decision_id": world["decision_id"],
                "conversation_id": seeded.conversation_id,
            },
            owner=world["owner_b"],
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert "AirPods" not in str(caught.value)
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None and stored.research_proposal is not None
    assert stored.research_proposal.is_pending


def test_research_verified_owner_reads_own_pending_proposal() -> None:
    world = _research_world()
    seeded = world["service"].handle(
        {"query": "What about AirPods Max?", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded is not None
    followed = world["service"].handle(
        {
            "query": "Maybe.",
            "decision_id": world["decision_id"],
            "conversation_id": seeded.conversation_id,
        },
        owner=world["owner_a"],
    )
    assert followed is not None
    assert followed.processing["proposal_id"] == seeded.processing["proposal_id"]
    assert followed.processing["proposal_status"] == "pending_confirmation"
    assert "AirPods Max" in followed.answer
    assert world["guard"].unscoped_gets == []
    assert {owner_id for _, owner_id in world["recording"].owner_reads} == {"guest-a"}


def test_research_body_ids_cannot_adopt_another_stored_owner() -> None:
    world = _research_world()
    seeded = world["service"].handle(
        {"query": "What about AirPods Max?", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded is not None
    proposal_text = seeded.answer
    world["recording"].owner_reads.clear()
    with pytest.raises(DecisionSnapshotOwnershipError) as caught:
        world["service"].handle(
            {
                "query": "Maybe.",
                "decision_id": OTHER_DECISION_ID,
                "conversation_id": seeded.conversation_id,
            }
        )
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    assert proposal_text not in str(caught.value)
    assert FOREIGN_FACT not in str(caught.value)

    owned = world["service"].handle(
        {
            "query": "Maybe.",
            "decision_id": OTHER_DECISION_ID,
            "conversation_id": seeded.conversation_id,
        },
        owner=world["owner_a"],
    )
    assert owned is not None
    assert owned.processing["proposal_id"] == seeded.processing["proposal_id"]
    assert FOREIGN_FACT not in owned.answer
    assert world["recording"].owner_reads == [(world["decision_id"], "guest-a")]


def test_research_fixture_does_not_load_an_unverified_proposal() -> None:
    world = _research_world()
    seeded = world["service"].handle(
        {"query": "What about AirPods Max?", "decision_id": world["decision_id"]},
        owner=world["owner_a"],
    )
    assert seeded is not None
    world["recording"].owner_reads.clear()
    response = world["service"].handle(
        {
            "query": "Maybe.",
            "decision_id": "headphones-standard",
            "conversation_id": seeded.conversation_id,
        }
    )
    assert response is None
    assert world["guard"].unscoped_gets == []
    assert world["recording"].owner_reads == []
    stored = world["guard"].inner.get_for_owner(seeded.conversation_id, world["owner_a"])
    assert stored is not None and stored.research_proposal is not None
    assert stored.research_proposal.proposal_id == seeded.processing["proposal_id"]
    assert stored.research_proposal.status == "pending_confirmation"


def test_slice_status_does_not_close_sprint_40() -> None:
    evidence = (
        ROOT / "docs/roadmap/evidence/SPRINT_40_7_DECISION_PATH_OWNER_BINDING_2026-10-13.md"
    ).read_text(encoding="utf-8")
    sprint = (ROOT / "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md").read_text(
        encoding="utf-8"
    )
    gaps = (ROOT / "docs/roadmap/GAP_INVENTORY.md").read_text(encoding="utf-8")
    readme = (ROOT / "docs/roadmap/sprints/README.md").read_text(encoding="utf-8")
    reconciliation = (
        ROOT / "docs/roadmap/evidence/SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md"
    ).read_text(encoding="utf-8")
    assert "df051a2e122816928bb85edb75c5f27290c1aaaa" in evidence
    assert "IMPLEMENTED-NOT-PROVEN" in evidence
    assert "R1" in evidence and "R13" in evidence
    assert "R14" in evidence and "R18" in evidence
    assert "PARTIAL" in evidence
    assert "not PROVEN" in evidence
    assert "**Status:** Planned" in sprint
    assert "Sprint 40.7" in sprint
    assert "Sprint 40.7" in roadmap
    assert "Sprint 40.7" in gaps
    assert "Sprint 40.7" in readme
    assert "It is not implemented in this change." in reconciliation
    assert "| R1 | AuthN/AuthZ/object-level review | PARTIAL |" in reconciliation
    assert "| R13 | Bind every conversation" in reconciliation
    assert "| R18 | Redact conversation bodies" in reconciliation
    assert SPRINT_38_STATUS == "IN PROGRESS"
    assert SPRINT_38_ENGINEERING_STATUS == "ENGINEERING COMPLETE"
    assert len(CURRENT_CLASS_C) == 19
    assert SHOPIFY_LIVE_CALL_PERMITTED is False
    assert REAL_SHOPIFY_CALLS == 0
    assert _CONFIGURED_BUCKET == 0
    assert "Sprint 41 stays UNSTARTED" in evidence
    assert "No deploy was performed." in evidence
    assert "No Shopify call was made." in evidence
