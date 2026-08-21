"""Phase 29.4A answer_from_evidence: evidence answers, boundaries, immutability."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.consumer.location import DeliveryContext, skipped_context
from app.consumer.presentation import build_page_view
from app.domain.entities.decision_snapshot import (
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import (
    DecisionSnapshotIntegrityError,
    DecisionSnapshotOwnershipError,
    ShoppingAssistantNotFoundError,
)
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.services.answer_from_evidence import (
    AnswerFromEvidenceService,
    compose_evidence_answer,
)
from app.services.decision_evidence_packet import packet_from_page_view, packet_from_snapshot
from httpx import AsyncClient

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000029"
IPHONE_ID = "apple-iphone-17-pro-max"
SAMSUNG_ID = "samsung-galaxy-s25-ultra-512gb"
ROOT = Path(__file__).resolve().parents[2]


def _owner(principal_id: str = "guest-29-4a") -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id=principal_id,
        session_id=f"session-{principal_id}",
        expires_at=START + timedelta(minutes=30),
    )


def _score(value: float, digest: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest * 64,
    )


def _snapshot(owner: ConversationOwner | None = None) -> CanonicalDecisionSnapshot:
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=owner or _owner(),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=IPHONE_ID,
                display_name="iPhone 17 Pro Max",
                variant="contract-fixture-variant",
                canonical_piqscore=_score(87, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=SAMSUNG_ID,
                display_name="Samsung Galaxy S25 Ultra 512GB",
                variant="512GB contract-fixture-variant",
                canonical_piqscore=_score(83, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=IPHONE_ID,
            alternative_product_ids=(SAMSUNG_ID,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-iphone",
                product_id=IPHONE_ID,
                topic="battery",
                fact="non-live fixture battery evidence A",
                source="contract-fixture://battery/a",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="fixture-battery-samsung",
                product_id=SAMSUNG_ID,
                topic="battery",
                fact="non-live fixture battery evidence B",
                source="contract-fixture://battery/b",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
            ),
        ),
        unknowns=("live marketplace facts are intentionally absent",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
    )


def _taguig() -> DeliveryContext:
    return DeliveryContext(city="Taguig City", postal_code="1630", source="manual")


def _packet(catalog: str = "headphones-standard", location: DeliveryContext | None = None):
    view = build_page_view(
        decision_id=catalog,
        page="results",
        location=location or _taguig(),
    )
    return packet_from_page_view(view)


def test_product_reasoning_and_recommendation() -> None:
    result = compose_evidence_answer("Why is this Best Piq for me?", _packet())
    assert result.status in {"answered", "partially_answered"}
    assert "Sony" in result.answer
    assert "WH-1000XM5" in result.answer
    assert "PiqScore itself is not personalized" in result.answer


def test_piqscore_can_differ_from_best_piq() -> None:
    result = compose_evidence_answer(
        "Why does Sony have the higher PiqScore?",
        _packet("headphones-score-diff"),
    )
    assert "higher objective PiqScore" in result.answer
    assert "Best Piq for You" in result.answer
    assert "93" in result.answer
    assert "90" in result.answer
    assert "did not rewrite" in result.answer


def test_price_breakdown_and_known_shipping() -> None:
    result = compose_evidence_answer("Does ₱18,990 include shipping?", _packet())
    assert result.status in {"answered", "partially_answered"}
    assert "18,990" in result.answer
    assert "FREE" in result.answer or "shipping" in result.answer.lower()


def test_unknown_shipping_is_not_called_free() -> None:
    location = DeliveryContext(city="Davao City", postal_code="8000", source="manual")
    result = compose_evidence_answer("Does this include shipping?", _packet(location=location))
    assert result.status == "partially_answered"
    assert "not treated as FREE" in result.answer
    assert "Price before shipping" in result.answer


def test_location_and_qualified_recommendation() -> None:
    location = DeliveryContext(city="Davao City", postal_code="8000", source="manual")
    packet = _packet(location=location)
    qualified = compose_evidence_answer("Why is this qualified?", packet)
    assert packet.is_qualified
    assert "qualified" in qualified.answer.lower()
    loc = compose_evidence_answer("What location did you use?", packet)
    assert "Davao" in loc.answer


def test_sources_used_and_source_not_claimed() -> None:
    packet = _packet()
    reddit = compose_evidence_answer("Did you check Reddit?", packet)
    assert "Reddit" in reddit.answer
    amazon = compose_evidence_answer("Did you check Amazon?", packet)
    assert "not listed" in amazon.answer.lower()


def test_explicit_unknowns_and_future_price() -> None:
    packet = _packet()
    unknowns = compose_evidence_answer("What don’t you know?", packet)
    assert unknowns.unknowns
    future = compose_evidence_answer("Will this be cheaper next month?", packet)
    assert future.status == "insufficient_evidence"
    assert "cannot predict" in future.answer.lower() or "does not contain evidence" in future.answer


def test_cross_border_estimated_landed_cost_stays_estimated() -> None:
    result = compose_evidence_answer(
        "Does this include import charges?",
        _packet("headphones-cross-border"),
    )
    assert "estimated" in result.answer.lower()
    assert "not a guaranteed checkout amount" in result.answer.lower()


def test_unverified_voucher_not_applied() -> None:
    result = compose_evidence_answer(
        "Is the voucher included in the price?",
        _packet("headphones-potential-checkout"),
    )
    assert "unverified" in result.answer.lower()
    assert "not treated as" in result.answer.lower() or "not applied" in result.answer.lower()


def test_outside_evaluated_set_does_not_research() -> None:
    result = compose_evidence_answer("Compare this to AirPods Max", _packet())
    assert result.status == "outside_evaluated_set"
    assert "not among the offers evaluated" in result.answer.lower()
    assert "No new product search was started" in result.answer


def test_preference_change_does_not_mutate_recommendation() -> None:
    packet = _packet()
    before = packet.best_piq_product_id
    result = compose_evidence_answer("Comfort matters more to me now.", packet)
    assert result.status == "preference_change_not_applied"
    assert result.packet.best_piq_product_id == before
    assert "has not changed the Recommendation" in result.answer


def test_canonical_snapshot_battery_answer() -> None:
    packet = packet_from_snapshot(_snapshot())
    result = compose_evidence_answer("Which one has better battery?", packet)
    assert result.status == "answered"
    assert "fixture-battery-iphone" in result.evidence_ids
    assert "fixture-battery-samsung" in result.evidence_ids
    assert "Pixel" not in result.answer


def test_canonical_snapshot_missing_price_is_insufficient() -> None:
    result = compose_evidence_answer(
        "Does this include shipping?", packet_from_snapshot(_snapshot())
    )
    assert result.status == "insufficient_evidence"
    assert "FREE" not in result.answer


def test_snapshot_immutability_after_answer() -> None:
    snapshot = _snapshot()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
    )
    service = AnswerFromEvidenceService()
    service.answer(
        {"query": "Which one has better battery?", "decision_id": snapshot.decision_id},
        snapshot=snapshot,
    )
    after = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.evaluated_product_ids,
        snapshot.recommendation.best_piq_product_id,
    )
    assert before == after


def test_owner_mismatch_is_rejected() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    conversations = InMemoryConversationRepository(clock=lambda: START, ttl_seconds=3600)
    owner_a = _owner("guest-a")
    owner_b = _owner("guest-b")
    snapshot = _snapshot(owner=owner_a)
    snapshots.add(snapshot)
    convo = conversations.create(owner=owner_b, decision_context=None)
    service = AnswerFromEvidenceService(
        snapshots=snapshots,
        conversations=conversations,
        clock=lambda: START,
    )
    with pytest.raises((ShoppingAssistantNotFoundError, DecisionSnapshotOwnershipError)):
        service.answer(
            {
                "query": "Which one has better battery?",
                "decision_id": snapshot.decision_id,
                "conversation_id": convo.conversation_id,
            }
        )


def test_uuid_decision_without_owner_is_rejected() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    snapshots.add(_snapshot())
    service = AnswerFromEvidenceService(snapshots=snapshots, clock=lambda: START)
    with pytest.raises((ShoppingAssistantNotFoundError, DecisionSnapshotOwnershipError)):
        service.answer({"query": "Which one has better battery?", "decision_id": DECISION_ID})


def test_bound_conversation_answers_from_snapshot() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    conversations = InMemoryConversationRepository(clock=lambda: START, ttl_seconds=3600)
    owner = _owner()
    snapshot = _snapshot(owner=owner)
    snapshots.add(snapshot)
    convo = conversations.create(owner=owner, decision_context=snapshot.to_reference())
    service = AnswerFromEvidenceService(
        snapshots=snapshots,
        conversations=conversations,
        clock=lambda: START,
    )
    response = service.answer(
        {
            "query": "Which one has better battery?",
            "decision_id": snapshot.decision_id,
            "conversation_id": convo.conversation_id,
        }
    )
    assert response.processing["action"] == "answer_from_evidence"
    assert "battery" in response.answer.lower()
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert snapshot.content_sha256 == loaded.content_sha256


def test_production_does_not_use_fixture_offers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.decision_evidence_packet.fixture_catalogs_permitted",
        lambda: False,
    )
    monkeypatch.setattr("app.consumer.mode.fixture_catalogs_permitted", lambda: False)
    service = AnswerFromEvidenceService()
    response = service.answer(
        {"query": "Does ₱18,990 include shipping?", "decision_id": "headphones-standard"}
    )
    assert "18,990" not in response.answer
    assert "WH-1000XM5" not in response.answer
    assert "Lazada" not in response.answer
    assert response.processing["answer_status"] == "insufficient_evidence"
    assert response.processing["data_classification"] == "canonical_offer_economics_unavailable"


def test_skipped_location_does_not_invent_free_shipping() -> None:
    result = compose_evidence_answer(
        "Is shipping already included?",
        _packet(location=skipped_context()),
    )
    assert "not treated as FREE" in result.answer or "Price before shipping" in result.answer


def test_tampered_snapshot_fails_integrity_check() -> None:
    snapshots = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    snapshot = _snapshot()
    snapshots.add(snapshot)
    mutated = replace(snapshot, unknowns=("tampered unknown",))
    snapshots._records[(DECISION_ID, 1)] = (mutated, snapshot.content_sha256)  # noqa: SLF001
    with pytest.raises(DecisionSnapshotIntegrityError):
        snapshots.get(DECISION_ID, 1)


def test_user_claim_is_not_treated_as_verified_price() -> None:
    result = compose_evidence_answer("I saw this for ₱10,000 on Shopee.", _packet())
    assert "10,000" not in result.answer or "not" in result.answer.lower()
    assert "verified price" not in result.answer.lower()


def test_import_unverified_is_not_complete_landed_cost() -> None:
    result = compose_evidence_answer(
        "Does this include import charges?",
        _packet("headphones-import-unverified"),
    )
    assert result.status in {"partially_answered", "answered"}
    assert "unverified" in result.answer.lower() or "not complete" in result.answer.lower()
    assert "zero" not in result.answer.lower() or "not treated as zero" in result.answer.lower()


def test_phase_29_4b_and_29_4c_remain_unimplemented() -> None:
    source = (ROOT / "app/services/answer_from_evidence.py").read_text(encoding="utf-8")
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "def refine_session_recommendation" not in source
    assert "def propose_research" not in source
    assert "refine_session_recommendation" not in js
    assert "propose_research" not in js
    assert "answer_from_evidence" not in js


@pytest.mark.asyncio
async def test_results_compare_why_ask_same_decision(client: AsyncClient) -> None:
    await client.get(
        "/consumer/location",
        params={
            "action": "save",
            "city": "Taguig City",
            "postal_code": "1630",
            "decision_id": "headphones-standard",
            "next": "/results/headphones-standard",
        },
        follow_redirects=True,
    )
    surfaces = (
        ("results", "/results/headphones-standard"),
        ("compare", "/compare/headphones-standard"),
        ("why", "/why-best-piq/headphones-standard"),
    )
    answers: list[str] = []
    for surface, path in surfaces:
        page = await client.get(path)
        assert page.status_code == 200
        ask = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Does this include shipping?",
                "decision_id": "headphones-standard",
                "surface": surface,
            },
        )
        assert ask.status_code == 200, ask.text
        body = ask.json()
        assert body["action"] == "answer_from_evidence"
        assert body["decision_id"] == "headphones-standard"
        assert "shipping" in body["answer"].lower()
        answers.append(body["answer"])
    assert answers[0]


@pytest.mark.asyncio
async def test_invalid_decision_id_for_uuid_snapshot(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": "Why is this Best Piq for me?",
            "decision_id": "00000000-0000-4000-8000-000000000099",
        },
    )
    assert response.status_code in {404, 400}
