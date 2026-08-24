"""Phase 29.4C propose_research: pending proposals, no execution, immutability."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.core.dependencies import get_shopping_decision_snapshot_repository
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    DecisionSnapshotIntegrityError,
    ShoppingAssistantNotFoundError,
)
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.main import create_app
from app.services.answer_from_evidence import compose_evidence_answer
from app.services.decision_evidence_packet import packet_from_snapshot, unavailable_packet
from app.services.propose_research import (
    ProposeResearchService,
    compose_research_proposal,
    detect_research_need,
    is_ambiguous_confirmation,
    is_cancellation,
    is_explicit_confirmation,
    is_research_request,
)
from app.services.refine_session_recommendation import (
    compose_session_refinement,
    is_refinement_request,
)
from app.services.shopping_assistant_service import ShoppingAssistantService
from httpx import ASGITransport, AsyncClient

from tests.unit.test_phase_29_4b_refine_session_recommendation import (
    BOSE_ID,
    DECISION_ID,
    SENN_ID,
    SONY_ID,
    START,
    _owner,
    _presentation,
)

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN_ID = "00000000-0000-4000-8000-000000000099"
HTTP_DECISION_ID = "00000000-0000-4000-8000-00000000029c"


def _service(snapshot=None):
    snap = snapshot or _presentation()
    snapshots = InMemoryDecisionSnapshotRepository()
    snapshots.add(snap)
    conversations = InMemoryConversationRepository()
    service = ProposeResearchService(
        snapshots=snapshots,
        conversations=conversations,
        clock=lambda: START,
        id_factory=lambda: str(uuid4()),
    )
    return service, snapshots, conversations, snap


def _assistant(snapshot=None):
    snap = snapshot or _presentation()
    snapshots = InMemoryDecisionSnapshotRepository()
    snapshots.add(snap)
    conversations = InMemoryConversationRepository()
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=lambda: START,
    )
    return assistant, snapshots, conversations, snap


def test_outside_product_proposes_research_without_adding_it() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
    )
    result = compose_research_proposal("What about AirPods Max?", packet, snapshot=snapshot)
    assert result is not None
    assert result.status == "pending_confirmation"
    assert result.proposal is not None
    assert result.proposal.reason == "outside_evaluated_set"
    assert result.proposal.confirmation_required is True
    assert "AirPods Max" in result.answer
    assert "wasn't part" in result.answer
    assert "Would you like me" in result.answer
    assert "AirPods Max" in result.proposal.outside_set_product_names
    assert "airpods" not in {item.lower() for item in snapshot.evaluated_product_ids}
    assert snapshot.evaluated_product_ids == before[3]
    assert snapshot.recommendation.best_piq_product_id == SONY_ID
    assert snapshot.content_sha256 == before[0]
    assert snapshot.canonical_piqscore_set_sha256 == before[1]
    assert "search the whole internet" not in result.answer.lower()
    assert "http" not in result.answer.lower()


def test_insufficient_microphone_evidence_becomes_proposal() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    refine = compose_session_refinement(
        "Microphone quality is now the most important thing.",
        packet,
        snapshot=snapshot,
    )
    assert refine.status == "insufficient_evidence"
    result = compose_research_proposal(
        "Microphone quality is now the most important thing.",
        packet,
        snapshot=snapshot,
    )
    assert result is not None
    assert result.status == "pending_confirmation"
    assert result.proposal is not None
    assert result.proposal.reason == "insufficient_evidence"
    assert "microphone" in result.answer.lower()
    assert "would you like me" in result.answer.lower()
    assert snapshot.recommendation.best_piq_product_id == SONY_ID
    assert "invent" not in result.answer.lower()


def test_current_price_requires_freshness_proposal() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    historical = compose_evidence_answer("What price did you evaluate?", packet)
    assert historical.status in {"answered", "partially_answered"}
    result = compose_research_proposal("What's the price today?", packet, snapshot=snapshot)
    assert result is not None
    assert result.proposal is not None
    assert result.proposal.reason == "freshness_required"
    assert result.proposal.freshness_required is True
    assert "today" in result.answer.lower() or "current" in result.answer.lower()
    assert "19,990" not in result.answer
    assert "14,990" not in result.answer
    assert "today's price" in result.answer.lower() or "historical" in result.answer.lower()
    assert "not treated" in result.answer.lower()


def test_source_request_is_capability_safe() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    inventory = compose_evidence_answer("Did you check Amazon?", packet)
    assert inventory.status == "answered"
    result = compose_research_proposal("Check Amazon too.", packet, snapshot=snapshot)
    assert result is not None
    assert result.proposal is not None
    assert result.proposal.reason == "requested_source"
    assert "amazon" in result.proposal.requested_sources
    assert "i'll check amazon" not in result.answer.lower()
    assert "if that source is available" in result.answer.lower()
    assert "checked" not in result.answer.lower() or "have not checked" in result.answer.lower()


def test_find_something_cheaper_flags_expansion() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_research_proposal("Find something cheaper.", packet, snapshot=snapshot)
    assert result is not None
    assert result.proposal is not None
    assert result.proposal.reason == "evaluated_set_expansion"
    assert result.proposal.expansion_required is True
    assert snapshot.evaluated_product_ids == (SONY_ID, BOSE_ID, SENN_ID)
    assert snapshot.recommendation.best_piq_product_id == SONY_ID
    assert "beyond the products already evaluated" in result.answer.lower()


def test_destination_reevaluation_does_not_reprice() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    before = snapshot.content_sha256
    before_economics = snapshot.offer_economics
    result = compose_research_proposal(
        "What if I ship it to Cebu?",
        packet,
        snapshot=snapshot,
    )
    assert result is not None
    assert result.proposal is not None
    assert result.proposal.reason == "reevaluation_required"
    assert result.proposal.destination_label
    assert "cebu" in result.proposal.destination_label.lower()
    assert "have not repriced" in result.answer.lower()
    assert snapshot.content_sha256 == before
    assert snapshot.offer_economics == before_economics


def test_existing_evidence_stays_on_answer_from_evidence() -> None:
    assistant, _, _, _ = _assistant()
    response = assistant.query(
        {"query": "Does Sony support multipoint?", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert response.processing["action"] == "answer_from_evidence"
    assert "multipoint" in response.answer.lower() or "supported" in response.answer.lower()


def test_sufficient_preference_change_stays_on_refinement() -> None:
    assistant, _, _, _ = _assistant()
    response = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert response.processing["action"] == "refine_session_recommendation"
    assert response.processing["session_best_piq_product_id"] == BOSE_ID
    assert response.processing["requires_research_confirmation"] is False


def test_insufficient_preference_change_handoff_does_not_start_research() -> None:
    assistant, snapshots, conversations, snapshot = _assistant()
    response = assistant.query(
        {
            "query": "Microphone quality is now the most important thing.",
            "decision_id": DECISION_ID,
        },
        owner=_owner(),
    )
    assert response.processing["action"] == "propose_research"
    assert response.processing["requires_research_confirmation"] is True
    assert response.processing["execution_started"] is False
    assert response.processing["research_executed"] is False
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.recommendation.best_piq_product_id == SONY_ID
    context = conversations.get(response.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.status == "pending_confirmation"


def test_pending_proposal_is_owner_bound_and_inert() -> None:
    service, snapshots, conversations, snapshot = _service()
    response = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert response is not None
    assert response.processing["action"] == "propose_research"
    assert response.processing["proposal_status"] == "pending_confirmation"
    assert response.processing["requires_research_confirmation"] is True
    assert response.processing["execution_started"] is False
    context = conversations.get(response.conversation_id)
    assert context is not None
    assert context.owner is not None
    assert context.owner.has_same_identity(_owner())
    assert context.research_proposal is not None
    assert context.research_proposal.is_pending
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == snapshot.content_sha256


def test_ambiguous_confirmation_does_not_authorize() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    maybe = service.handle(
        {
            "query": "Maybe.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert maybe is not None
    assert maybe.processing["proposal_status"] == "pending_confirmation"
    assert maybe.processing["execution_started"] is False
    assert is_ambiguous_confirmation("Maybe.")
    assert not is_explicit_confirmation("Maybe.")
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.status == "pending_confirmation"


def test_cancel_clears_pending_proposal() -> None:
    service, _, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    cancelled = service.handle(
        {
            "query": "Never mind.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert cancelled is not None
    assert cancelled.processing["answer_status"] == "cancelled"
    assert cancelled.processing["execution_started"] is False
    assert is_cancellation("Never mind.")
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is None


def test_replace_swaps_active_proposal() -> None:
    service, snapshots, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    first_id = first.processing["proposal_id"]
    second = service.handle(
        {
            "query": "Actually compare Beats Studio Pro instead.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert second is not None
    assert second.processing["proposal_id"] != first_id
    assert "Beats Studio Pro" in second.answer
    assert "AirPods Max" not in second.processing["research_proposal"]["outside_set_product_names"]
    assert second.processing["research_proposal"]["replaced_proposal_id"] == first_id
    assert snapshots.get(DECISION_ID, 1).evaluated_product_ids == (
        SONY_ID,
        BOSE_ID,
        SENN_ID,
    )
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.outside_set_product_names == ("Beats Studio Pro",)


def test_owner_isolation_and_unknown_decision() -> None:
    service, snapshots, _, snapshot = _service()
    response = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert response is not None
    stranger = ConversationOwner(
        principal_type="guest",
        principal_id="other-guest",
        session_id="session-other-guest",
        expires_at=START + timedelta(minutes=30),
    )
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.handle(
            {
                "query": "What about AirPods Max?",
                "decision_id": DECISION_ID,
                "conversation_id": response.conversation_id,
            },
            owner=stranger,
        )
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.handle(
            {"query": "What about AirPods Max?", "decision_id": UNKNOWN_ID},
            owner=_owner(),
        )
    assert snapshots.get_for_owner(DECISION_ID, 1, stranger) is None
    stored = snapshots.get(DECISION_ID, 1)
    assert stored is not None
    snapshots._records[(DECISION_ID, 1)] = (  # noqa: SLF001
        replace(
            stored,
            recommendation=replace(stored.recommendation, snapshot_sha256="0" * 64),
        ),
        stored.content_sha256,
    )
    with pytest.raises(DecisionSnapshotIntegrityError):
        service.handle(
            {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
            owner=_owner(),
        )


def test_session_refinement_survives_research_proposal() -> None:
    assistant, snapshots, conversations, snapshot = _assistant()
    refine = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert refine.processing["session_best_piq_product_id"] == BOSE_ID
    proposed = assistant.query(
        {
            "query": "What about AirPods Max?",
            "decision_id": DECISION_ID,
            "conversation_id": refine.conversation_id,
        },
        owner=_owner(),
    )
    assert proposed.processing["action"] == "propose_research"
    assert proposed.processing["session_best_piq_product_id"] == BOSE_ID
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.recommendation.best_piq_product_id == SONY_ID
    context = conversations.get(refine.conversation_id)
    assert context is not None
    assert context.session_refinement is not None
    assert context.session_refinement.session_best_piq_product_id == BOSE_ID
    assert context.research_proposal is not None


def test_no_side_effects_or_network_imports() -> None:
    source = (ROOT / "app/services/propose_research.py").read_text(encoding="utf-8")
    assert "httpx" not in source
    assert "requests." not in source
    assert "urllib" not in source
    assert "aiohttp" not in source
    assert "web_search" not in source
    assert "marketplace" not in source.lower() or "do not" in source.lower()
    snapshot = _presentation()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products),
        snapshot.evaluated_product_ids,
    )
    compose_research_proposal(
        "What about AirPods Max?", packet_from_snapshot(snapshot), snapshot=snapshot
    )
    compose_research_proposal(
        "What's the price today?", packet_from_snapshot(snapshot), snapshot=snapshot
    )
    compose_research_proposal(
        "Find something cheaper.", packet_from_snapshot(snapshot), snapshot=snapshot
    )
    assert snapshot.content_sha256 == before[0]
    assert snapshot.canonical_piqscore_set_sha256 == before[1]
    assert tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products) == before[2]
    assert snapshot.evaluated_product_ids == before[3]


def test_production_uuid_does_not_borrow_fixture_scope() -> None:
    packet = unavailable_packet(DECISION_ID, 1)
    result = compose_research_proposal(
        "Does this include a 2-year local warranty?",
        packet,
    )
    assert result is not None
    assert "Sony" not in result.answer
    assert "Bose" not in result.answer
    assert "Sennheiser" not in result.answer
    assert "18,990" not in result.answer
    assert result.proposal is not None
    assert result.proposal.outside_set_product_names == ()


def test_routing_preserves_29_4a_and_29_4b() -> None:
    assistant, _, _, _ = _assistant()
    why = assistant.query(
        {
            "query": "Why is Bose now your pick?" if False else "Why is Sony best?",
            "decision_id": DECISION_ID,
        },
        owner=_owner(),
    )
    assert why.processing["action"] == "answer_from_evidence"
    comfort = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert comfort.processing["action"] == "refine_session_recommendation"
    outside = assistant.query(
        {
            "query": "What about AirPods Max?",
            "decision_id": DECISION_ID,
            "conversation_id": comfort.conversation_id,
        },
        owner=_owner(),
    )
    assert outside.processing["action"] == "propose_research"
    assert is_research_request("What about AirPods Max?")
    assert is_research_request("What's the price today?")
    assert is_research_request("Find something cheaper.")
    assert not is_research_request("Did you check Amazon?")
    assert not is_refinement_request("What about AirPods Max?")


def test_explicit_confirmation_does_not_execute() -> None:
    service, snapshots, conversations, snapshot = _service()
    first = service.handle(
        {"query": "What about AirPods Max?", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    assert first is not None
    confirmed = service.handle(
        {
            "query": "Yes, research AirPods Max.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
            "proposal_id": first.processing["proposal_id"],
            "proposal_version": first.processing["proposal_version"],
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert confirmed is not None
    assert (
        confirmed.processing["answer_status"]
        == "research_confirmation_received_but_execution_unavailable"
    )
    assert confirmed.processing["execution_started"] is False
    assert confirmed.processing["research_executed"] is False
    assert confirmed.processing["execution_available"] is False
    assert confirmed.processing["authorization_created"] is True
    assert confirmed.processing["authorization_status"] == "authorized_pending_execution"
    assert confirmed.processing["research_authorization_id"]
    assert "approved" in confirmed.answer.lower()
    assert "not available" in confirmed.answer.lower()
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.evaluated_product_ids == (SONY_ID, BOSE_ID, SENN_ID)
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.research_proposal is not None
    assert context.research_proposal.status == (
        "research_confirmation_received_but_execution_unavailable"
    )
    assert is_explicit_confirmation("Go ahead.")
    assert is_explicit_confirmation("Yes, check the current prices.")


def test_warranty_question_without_evidence_proposes_research() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    evidence = compose_evidence_answer("Does this include a 2-year local warranty?", packet)
    assert evidence.status == "insufficient_evidence"
    result = compose_research_proposal(
        "Does this include a 2-year local warranty?",
        packet,
        snapshot=snapshot,
    )
    assert result is not None
    assert result.proposal is not None
    assert result.proposal.reason == "insufficient_evidence"
    assert "warranty" in result.answer.lower()


def test_classifier_helpers() -> None:
    packet = packet_from_snapshot(_presentation())
    assert detect_research_need("What about AirPods Max?", packet).reason == "outside_evaluated_set"
    assert detect_research_need("What's the price today?", packet).reason == "freshness_required"
    assert detect_research_need("Check Lazada too.", packet).reason == "requested_source"
    assert detect_research_need("Find something cheaper.", packet).expansion_required
    assert detect_research_need("Why is Sony best?", packet) is None
    assert detect_research_need("Comfort matters more.", packet) is None
    assert detect_research_need("Did you check Amazon?", packet) is None


def test_29_4a_and_29_4b_files_still_do_not_define_propose_research() -> None:
    source = (ROOT / "app/services/answer_from_evidence.py").read_text(encoding="utf-8")
    refine = (ROOT / "app/services/refine_session_recommendation.py").read_text(encoding="utf-8")
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "def propose_research" not in source
    assert "def propose_research" not in refine
    assert "propose_research" not in js
    assert "Researching…" not in js
    assert "Researching..." not in js
    assert "data-proposal-id" in js
    assert "data-proposal-version" in js


@pytest.mark.asyncio
async def test_http_owner_can_propose_from_ask() -> None:
    snapshot = replace(_presentation(), decision_id=HTTP_DECISION_ID)
    repo = get_shopping_decision_snapshot_repository()
    repo.add(snapshot)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(OWNER_COOKIE, owner_cookie_payload(_owner()))
        ask = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "What about AirPods Max?",
                "decision_id": HTTP_DECISION_ID,
                "surface": "results",
            },
        )
        assert ask.status_code == 200, ask.text
        body = ask.json()
        assert body["action"] == "propose_research"
        assert body["requires_research_confirmation"] is True
        assert body["research_proposal"]["status"] == "pending_confirmation"
        assert "AirPods Max" in body["answer"]
        results = await client.get(f"/results/{HTTP_DECISION_ID}")
        assert results.status_code == 200
        assert 'data-best-piq="' + SONY_ID in results.text
        assert "AirPods Max" not in results.text
        confirm = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Yes, research that",
                "decision_id": HTTP_DECISION_ID,
                "conversation_id": body["conversation_id"],
                "surface": "results",
                "proposal_id": body["research_proposal"]["proposal_id"],
                "proposal_version": body["research_proposal"]["proposal_version"],
            },
        )
        assert confirm.status_code == 200
        assert confirm.json()["research_proposal"]["status"] == (
            "research_confirmation_received_but_execution_unavailable"
        )
        assert confirm.json()["requires_research_confirmation"] is False
        assert confirm.json()["execution_available"] is False
        assert confirm.json()["research_handoff_created"] is True
        assert confirm.json()["research_handoff_status"] == "authorized_pending_execution"
        assert confirm.json()["research_handoff_id"]
