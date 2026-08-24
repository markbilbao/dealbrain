"""Phase 29.4B refine_session_recommendation: session overlay, evidence bounds."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.decision_owner import OWNER_COOKIE, owner_cookie_payload
from app.consumer.location import DeliveryContext
from app.consumer.pages import render_page
from app.consumer.pricing import MoneyComponent
from app.consumer.session_overlay import (
    apply_session_overlay_to_packet,
    apply_session_overlay_to_view,
)
from app.core.dependencies import get_shopping_decision_snapshot_repository
from app.domain.entities.decision_presentation import (
    CanonicalAlternativeTradeoff,
    CanonicalBestFor,
    CanonicalFitAttribute,
    CanonicalProductPresentation,
    CanonicalQualification,
    CanonicalRecommendationReason,
    CanonicalShopperContext,
)
from app.domain.entities.decision_snapshot import (
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.session_refinement import SessionPriorities
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
from app.services.canonical_offer_economics import (
    attach_offer_economics,
    capture_offer_economics,
    delivery_from_location,
)
from app.services.canonical_presentation_contract import attach_presentation_contract
from app.services.decision_evidence_packet import packet_from_snapshot
from app.services.refine_session_recommendation import (
    RefineSessionRecommendationService,
    compose_session_refinement,
    is_refinement_request,
)
from app.services.shopping_assistant_service import ShoppingAssistantService
from httpx import ASGITransport, AsyncClient

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000294"
SONY_ID = "sony-wh-1000xm5-session"
BOSE_ID = "bose-qc-ultra-session"
SENN_ID = "sennheiser-momentum-session"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000099"
ROOT = Path(__file__).resolve().parents[2]


def _owner(principal_id: str = "guest-29-4b") -> ConversationOwner:
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


def _base_snapshot(owner: ConversationOwner | None = None) -> CanonicalDecisionSnapshot:
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=owner or _owner(),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=SONY_ID,
                display_name="Sony WH-1000XM5",
                variant="black",
                canonical_piqscore=_score(94, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=BOSE_ID,
                display_name="Bose QuietComfort Ultra",
                variant="black",
                canonical_piqscore=_score(91, "b"),
            ),
            EvaluatedProductSnapshot(
                product_id=SENN_ID,
                display_name="Sennheiser Momentum 4",
                variant="black",
                canonical_piqscore=_score(88, "c"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=SONY_ID,
            alternative_product_ids=(BOSE_ID, SENN_ID),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="session-anc-sony",
                product_id=SONY_ID,
                topic="anc",
                fact="Sony has class-leading noise cancellation",
                source="captured-offer://anc/sony",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="session-comfort-bose",
                product_id=BOSE_ID,
                topic="comfort",
                fact="Bose has excellent clamp comfort",
                source="captured-offer://comfort/bose",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="session-battery-senn",
                product_id=SENN_ID,
                topic="battery",
                fact="Sennheiser has 60 hour battery life",
                source="captured-offer://battery/senn",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="f" * 64,
            ),
        ),
        unknowns=("shipping to the selected delivery location is not verified",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
        data_classification="canonical_decision",
    )


def _money(kind: str, amount: float | None, status: str = "verified") -> MoneyComponent:
    return MoneyComponent(
        kind=kind,  # type: ignore[arg-type]
        label=kind,
        amount=amount,
        status=status,  # type: ignore[arg-type]
        applies=status != "not_applicable",
    )


def _economics_snapshot(
    owner: ConversationOwner | None = None,
    *,
    sony_amount: float = 19990,
    bose_amount: float = 14990,
    senn_amount: float | None = 16990,
    senn_status: str = "verified",
) -> CanonicalDecisionSnapshot:
    return attach_offer_economics(
        _base_snapshot(owner),
        (
            capture_offer_economics(
                offer_id="offer-sony",
                product_id=SONY_ID,
                listing=_money("listing", sony_amount),
                shipping=_money("shipping", 0),
                taxes=_money("tax", None, "not_applicable"),
                price_state="final_effective_cost",
                dominant_amount=sony_amount,
                merchant="Captured Merchant A",
                provenance_source="captured-offer://merchant/sony",
            ),
            capture_offer_economics(
                offer_id="offer-bose",
                product_id=BOSE_ID,
                listing=_money("listing", bose_amount),
                shipping=_money("shipping", 0),
                taxes=_money("tax", None, "not_applicable"),
                price_state="final_effective_cost",
                dominant_amount=bose_amount,
                merchant="Captured Merchant B",
                provenance_source="captured-offer://merchant/bose",
            ),
            capture_offer_economics(
                offer_id="offer-senn",
                product_id=SENN_ID,
                listing=_money("listing", senn_amount, senn_status),
                shipping=_money("shipping", 0 if senn_status == "verified" else None, senn_status),
                taxes=_money("tax", None, "not_applicable"),
                price_state="final_effective_cost"
                if senn_status == "verified"
                else "price_before_shipping",
                dominant_amount=senn_amount,
                merchant="Captured Merchant C",
                provenance_source="captured-offer://merchant/senn",
            ),
        ),
        delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        data_classification="canonical_decision",
    )


def _presentation(owner: ConversationOwner | None = None, **kwargs) -> CanonicalDecisionSnapshot:
    return attach_presentation_contract(
        _economics_snapshot(owner),
        qualification=kwargs.get(
            "qualification",
            CanonicalQualification(
                state="qualified",
                reasons=("Shipping to the selected delivery location could not be verified.",),
                material_unknowns=("shipping to the selected delivery location is not verified",),
                could_change_recommendation=True,
            ),
        ),
        shopper_context=kwargs.get(
            "shopper_context",
            CanonicalShopperContext(
                budget_label="Up to ₱20,000",
                top_priority="ANC",
                priorities=("ANC", "Comfort"),
                use_case="Commute",
                required_features=("Strong ANC",),
            ),
        ),
        product_presentation=kwargs.get(
            "product_presentation",
            (
                CanonicalProductPresentation(
                    product_id=SONY_ID,
                    brand="Sony",
                    model="WH-1000XM5",
                    category="Headphones",
                    offer_url="https://merchant.example/sony-wh-1000xm5",
                    fit_attributes=(
                        CanonicalFitAttribute(
                            key="comfort",
                            label="Comfort",
                            value="Firm",
                            status="known",
                            evidence_ids=("session-comfort-bose",),
                        ),
                        CanonicalFitAttribute(
                            key="anc",
                            label="Noise cancellation",
                            value="Class-leading",
                            status="known",
                            evidence_ids=("session-anc-sony",),
                        ),
                        CanonicalFitAttribute(
                            key="multipoint",
                            label="Multipoint",
                            value="Supported",
                            status="known",
                            evidence_ids=("session-anc-sony",),
                        ),
                    ),
                ),
                CanonicalProductPresentation(
                    product_id=BOSE_ID,
                    brand="Bose",
                    model="QuietComfort Ultra",
                    category="Headphones",
                    offer_url="https://merchant.example/bose-qc-ultra",
                    fit_attributes=(
                        CanonicalFitAttribute(
                            key="comfort",
                            label="Comfort",
                            value="Excellent clamp comfort",
                            status="known",
                            evidence_ids=("session-comfort-bose",),
                        ),
                        CanonicalFitAttribute(
                            key="anc",
                            label="Noise cancellation",
                            value="Strong",
                            status="known",
                            evidence_ids=("session-anc-sony",),
                        ),
                        CanonicalFitAttribute(
                            key="multipoint",
                            label="Multipoint",
                            value="Unknown",
                            status="unknown",
                            evidence_ids=(),
                        ),
                    ),
                ),
                CanonicalProductPresentation(
                    product_id=SENN_ID,
                    brand="Sennheiser",
                    model="Momentum 4",
                    category="Headphones",
                    offer_url="https://merchant.example/sennheiser-momentum-4",
                    fit_attributes=(
                        CanonicalFitAttribute(
                            key="comfort",
                            label="Comfort",
                            value="Good",
                            status="known",
                            evidence_ids=("session-comfort-bose",),
                        ),
                        CanonicalFitAttribute(
                            key="battery",
                            label="Battery",
                            value="60",
                            unit="hours",
                            status="known",
                            evidence_ids=("session-battery-senn",),
                        ),
                        CanonicalFitAttribute(
                            key="multipoint",
                            label="Multipoint",
                            value="Unsupported",
                            status="known",
                            evidence_ids=("session-battery-senn",),
                        ),
                    ),
                ),
            ),
        ),
        recommendation_reasons=kwargs.get(
            "recommendation_reasons",
            (
                CanonicalRecommendationReason(
                    reason="Sony was recommended because ANC was the highest priority.",
                    evidence_ids=("session-anc-sony",),
                    shopper_priority="ANC",
                    product_id=SONY_ID,
                    related_attribute="anc",
                ),
            ),
        ),
        best_for=kwargs.get(
            "best_for",
            (
                CanonicalBestFor(
                    label="Commuters prioritizing ANC",
                    evidence_ids=("session-anc-sony",),
                ),
            ),
        ),
        alternative_tradeoffs=kwargs.get(
            "alternative_tradeoffs",
            (
                CanonicalAlternativeTradeoff(
                    product_id=BOSE_ID,
                    reason="Bose may be better if comfort matters more than ANC.",
                    evidence_ids=("session-comfort-bose",),
                ),
                CanonicalAlternativeTradeoff(
                    product_id=SENN_ID,
                    reason="Sennheiser may be better if battery life matters more.",
                    evidence_ids=("session-battery-senn",),
                ),
            ),
        ),
        data_classification="canonical_decision",
    )


def _service(
    snapshot: CanonicalDecisionSnapshot | None = None,
) -> tuple[
    RefineSessionRecommendationService,
    InMemoryDecisionSnapshotRepository,
    InMemoryConversationRepository,
    CanonicalDecisionSnapshot,
]:
    snap = snapshot or _presentation()
    snapshots = InMemoryDecisionSnapshotRepository()
    snapshots.add(snap)
    conversations = InMemoryConversationRepository()
    service = RefineSessionRecommendationService(
        snapshots=snapshots,
        conversations=conversations,
        clock=lambda: START,
    )
    return service, snapshots, conversations, snap


def test_routing_distinguishes_refine_from_evidence_questions() -> None:
    assert is_refinement_request("Comfort is more important than ANC.")
    assert is_refinement_request("I care more about battery life now.")
    assert is_refinement_request("My budget is now ₱15,000.")
    assert is_refinement_request("Multipoint is required.")
    assert is_refinement_request("Go back to my original priorities.")
    assert not is_refinement_request("Why is Sony best?")
    assert not is_refinement_request("What sources did you use?")
    assert not is_refinement_request("Which one still has better ANC?")
    assert not is_refinement_request("What was my top priority?")


def test_basic_refinement_switches_best_piq_and_preserves_scores() -> None:
    snapshot = _presentation()
    before = snapshot.content_sha256
    scores = snapshot.canonical_piqscore_set_sha256
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Comfort matters more than ANC.", packet, snapshot=snapshot)
    assert result.status == "recommendation_changed"
    assert result.applied is True
    assert result.overlay is not None
    assert result.overlay.original_best_piq_product_id == SONY_ID
    assert result.overlay.session_best_piq_product_id == BOSE_ID
    assert result.overlay.refinement_version == 1
    assert result.overlay.canonical_context_version == 1
    assert snapshot.content_sha256 == before
    assert snapshot.canonical_piqscore_set_sha256 == scores
    assert snapshot.recommendation.best_piq_product_id == SONY_ID
    assert "94" not in result.answer or "PiqScore" in result.answer
    assert "Bose" in result.answer
    assert "Sony" in result.answer


def test_piqscore_bytes_unchanged_after_service_refine() -> None:
    service, snapshots, _, snapshot = _service()
    before = (
        snapshot.content_sha256,
        snapshot.canonical_piqscore_set_sha256,
        snapshot.recommendation.snapshot_sha256,
        snapshot.recommendation.best_piq_product_id,
        tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products),
    )
    response = service.refine(
        {"query": "Comfort matters more to me now.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == before[0]
    assert loaded.canonical_piqscore_set_sha256 == before[1]
    assert loaded.recommendation.snapshot_sha256 == before[2]
    assert loaded.recommendation.best_piq_product_id == SONY_ID
    assert tuple(item.canonical_piqscore.value for item in loaded.evaluated_products) == before[4]
    assert response.processing["action"] == "refine_session_recommendation"
    assert response.processing["session_best_piq_product_id"] == BOSE_ID
    assert response.processing["affiliate_influence"] is False
    assert response.processing["requires_research_confirmation"] is False
    assert "personal piqscore" not in response.answer.lower()


def test_recommendation_can_remain_unchanged_while_recording_priority() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("ANC matters more to me now.", packet, snapshot=snapshot)
    assert result.status == "recommendation_unchanged"
    assert result.applied is True
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert result.overlay.priorities.top_priority == "anc"
    assert result.overlay.refinement_version == 1
    assert "still" in result.answer.lower()


def test_insufficient_evidence_does_not_fabricate_a_switch() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement(
        "Microphone quality is now my #1 priority.",
        packet,
        snapshot=snapshot,
    )
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert "don't have enough captured" in result.answer.lower()
    assert snapshot.recommendation.best_piq_product_id == SONY_ID


def test_outside_evaluated_set_is_not_refined() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("I'd rather get AirPods Max.", packet, snapshot=snapshot)
    assert result.status == "outside_evaluated_set"
    assert result.applied is False
    assert "no new product search" in result.answer.lower()
    assert "airpods" in result.answer.lower()


def test_research_expansion_is_unsupported_and_does_not_search() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Find something cheaper.", packet, snapshot=snapshot)
    assert result.status == "unsupported_refinement"
    assert result.applied is False
    assert "did not search" in result.answer.lower()


def test_budget_selects_known_affordable_offer() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("My budget is now ₱15,000.", packet, snapshot=snapshot)
    assert result.status == "recommendation_changed"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == BOSE_ID
    assert result.overlay.priorities.budget_max == 15000


def test_budget_unknown_cost_is_not_treated_as_affordable() -> None:
    snapshot = _economics_snapshot(senn_amount=None, senn_status="unknown")
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("My budget is now ₱15,000.", packet, snapshot=snapshot)
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id != SENN_ID
    assert "unknown" in result.answer.lower() or result.overlay.session_best_piq_product_id == BOSE_ID


def test_budget_none_fit() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("My budget is now ₱5,000.", packet, snapshot=snapshot)
    assert result.status == "none_fit_constraint"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID


def test_required_feature_known_true_unknown_not_false() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Multipoint is required.", packet, snapshot=snapshot)
    assert result.status == "recommendation_unchanged" or result.applied
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert "unknown" in " ".join(result.overlay.reasons).lower() or "multipoint" in result.answer.lower()


def test_required_feature_missing_evidence_is_insufficient() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Warranty support is required.", packet, snapshot=snapshot)
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert "don't have enough captured" in result.answer.lower() or "unknown is not treated as false" in result.answer.lower()


def test_multiple_refinements_evolve_session_not_snapshot() -> None:
    service, snapshots, conversations, snapshot = _service()
    first = service.refine(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    conversation_id = first.conversation_id
    second = service.refine(
        {
            "query": "Battery is also important.",
            "decision_id": DECISION_ID,
            "conversation_id": conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    third = service.refine(
        {
            "query": "Price matters less than both. Comfort still matters more.",
            "decision_id": DECISION_ID,
            "conversation_id": conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    loaded = snapshots.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == snapshot.content_sha256
    assert loaded.recommendation.best_piq_product_id == SONY_ID
    assert second.processing["session_refinement_version"] == 2
    assert third.processing["session_refinement_version"] == 3
    context = conversations.get(conversation_id)
    assert context is not None
    assert context.session_refinement is not None
    assert context.session_refinement.refinement_version == 3
    assert context.decision_context is not None
    assert context.decision_context.context_version == 1


def test_reset_restores_original_recommendation() -> None:
    service, _, conversations, snapshot = _service()
    first = service.refine(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    reset = service.refine(
        {
            "query": "Use my original priorities again.",
            "decision_id": DECISION_ID,
            "conversation_id": first.conversation_id,
        },
        owner=_owner(),
        snapshot=snapshot,
    )
    assert reset.processing["answer_status"] == "reset_to_original"
    assert reset.processing["session_best_piq_product_id"] == SONY_ID
    context = conversations.get(first.conversation_id)
    assert context is not None
    assert context.session_refinement is not None
    assert context.session_refinement.session_best_piq_product_id == SONY_ID
    assert snapshot.recommendation.best_piq_product_id == SONY_ID


def test_highest_piqscore_can_differ_from_session_best_piq() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Comfort matters more.", packet, snapshot=snapshot)
    assert result.overlay is not None
    scores = {item.product_id: item.canonical_piqscore.value for item in snapshot.evaluated_products}
    assert scores[SONY_ID] == 94
    assert scores[BOSE_ID] == 91
    assert result.overlay.session_best_piq_product_id == BOSE_ID
    view = apply_session_overlay_to_view(
        page_view_from_snapshot(snapshot, page="results", session_location=DeliveryContext()),
        result.overlay,
    )
    assert view.best_piq.product_id == BOSE_ID
    assert view.highest_piqscore_product_id == SONY_ID
    assert view.best_piq.piqscore.value == 91
    sony = next(card for card in view.compared if card.product_id == SONY_ID)
    assert sony.piqscore.value == 94
    assert sony.is_best_piq is False
    html = render_page(view)
    assert "Best Piq for You" in html
    assert "94" in html
    assert "91" in html


def test_qualification_is_not_silently_removed() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Comfort matters more.", packet, snapshot=snapshot)
    assert result.overlay is not None
    assert result.overlay.qualification_state == "qualified"
    view = apply_session_overlay_to_view(
        page_view_from_snapshot(snapshot, page="why", session_location=DeliveryContext()),
        result.overlay,
    )
    assert view.qualification_state == "qualified"


def test_owner_isolation_and_unknown_uuid() -> None:
    service, snapshots, _, snapshot = _service()
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.refine(
            {"query": "Comfort matters more.", "decision_id": DECISION_ID},
            owner=_owner("other-guest"),
        )
    with pytest.raises(ShoppingAssistantNotFoundError):
        service.refine(
            {"query": "Comfort matters more.", "decision_id": UNKNOWN_ID},
            owner=_owner(),
        )


def test_tampered_snapshot_cannot_be_refined() -> None:
    snapshots = InMemoryDecisionSnapshotRepository()
    snapshot = _presentation()
    snapshots.add(snapshot)
    tampered = replace(snapshot, unknowns=("tampered",))
    snapshots._records[(DECISION_ID, 1)] = (  # noqa: SLF001
        tampered,
        snapshot.content_sha256,
    )
    service = RefineSessionRecommendationService(snapshots=snapshots)
    with pytest.raises((DecisionSnapshotIntegrityError, ShoppingAssistantNotFoundError)):
        service.refine(
            {"query": "Comfort matters more.", "decision_id": DECISION_ID},
            owner=_owner(),
        )


def test_legacy_snapshot_without_presentation_returns_insufficient_for_comfort() -> None:
    snapshot = _base_snapshot()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Comfort matters more.", packet, snapshot=snapshot)
    assert result.status in {"recommendation_changed", "insufficient_evidence"}
    if result.status == "recommendation_changed":
        assert result.overlay is not None
        assert result.overlay.session_best_piq_product_id == BOSE_ID
    assert snapshot.recommendation.best_piq_product_id == SONY_ID


def test_ambiguous_request_asks_one_clarification() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("I just want the better one.", packet, snapshot=snapshot)
    assert result.status == "ambiguous_request"
    assert result.applied is False


def test_ask_routing_and_follow_up_use_session_context() -> None:
    snapshot = _presentation()
    snapshots = InMemoryDecisionSnapshotRepository()
    snapshots.add(snapshot)
    conversations = InMemoryConversationRepository()
    assistant = ShoppingAssistantService(
        snapshot_repository=snapshots,
        conversation_repository=conversations,
        clock=lambda: START,
    )
    refine = assistant.query(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
    )
    assert refine.processing["action"] == "refine_session_recommendation"
    assert refine.processing["session_best_piq_product_id"] == BOSE_ID
    evidence = assistant.query(
        {
            "query": "Why did you switch from Sony?",
            "decision_id": DECISION_ID,
            "conversation_id": refine.conversation_id,
        },
        owner=_owner(),
    )
    assert evidence.processing["action"] == "answer_from_evidence"
    assert "Bose" in evidence.answer
    anc = assistant.query(
        {
            "query": "Which one still has better ANC?",
            "decision_id": DECISION_ID,
            "conversation_id": refine.conversation_id,
        },
        owner=_owner(),
    )
    assert anc.processing["action"] == "answer_from_evidence"
    assert "Sony" in anc.answer or "ANC" in anc.answer or "noise" in anc.answer.lower()


def test_cross_surface_overlay_is_consistent() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    result = compose_session_refinement("Comfort matters more.", packet, snapshot=snapshot)
    location = DeliveryContext()
    views = [
        apply_session_overlay_to_view(
            page_view_from_snapshot(snapshot, page=page, session_location=location),
            result.overlay,
        )
        for page in ("results", "compare", "why")
    ]
    assert {view.best_piq.product_id for view in views} == {BOSE_ID}
    assert {view.highest_piqscore_product_id for view in views} == {SONY_ID}
    assert all(view.canonical_piqscore_set_sha256 == snapshot.canonical_piqscore_set_sha256 for view in views)
    why = views[2]
    assert "Originally" in why.why_sections[0].narrative
    assert "comfort" in why.why_sections[0].narrative.lower()


def test_session_priorities_do_not_write_account_preferences() -> None:
    service, _, conversations, snapshot = _service()
    response = service.refine(
        {"query": "Comfort matters more.", "decision_id": DECISION_ID},
        owner=_owner(),
        snapshot=snapshot,
    )
    context = conversations.get(response.conversation_id)
    assert context is not None
    assert context.session_refinement is not None
    assert isinstance(context.session_refinement.priorities, SessionPriorities)
    assert snapshot.shopper_context is not None
    assert snapshot.shopper_context.top_priority == "ANC"
    assert "account" not in response.processing
    assert response.profile_id is None


def test_no_research_side_effects_and_29_4c_absent() -> None:
    source = (ROOT / "app/services/refine_session_recommendation.py").read_text(encoding="utf-8")
    assert "def refine" in source or "def compose_session_refinement" in source
    assert "def propose_research" not in source
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text(encoding="utf-8")
    assert "propose_research" not in js
    assert "refine_session_recommendation" not in js
    assert "httpx" not in source
    assert "requests.get" not in source
    snapshot = _presentation()
    before = snapshot.content_sha256
    compose_session_refinement("Comfort matters more.", packet_from_snapshot(snapshot), snapshot=snapshot)
    assert snapshot.content_sha256 == before


def test_composer_preference_path_still_does_not_mutate_packet() -> None:
    packet = packet_from_snapshot(_presentation())
    before = packet.best_piq_product_id
    result = compose_evidence_answer("Comfort matters more to me now.", packet)
    assert result.status == "preference_change_not_applied"
    assert result.packet.best_piq_product_id == before


@pytest.mark.asyncio
async def test_http_owner_can_refine_and_pages_show_session_best() -> None:
    snapshot = _presentation()
    repo = get_shopping_decision_snapshot_repository()
    repo.add(snapshot)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(OWNER_COOKIE, owner_cookie_payload(_owner()))
        refine = await client.post(
            "/api/v1/shopping-assistant/query",
            json={"query": "Comfort matters more.", "decision_id": DECISION_ID, "surface": "results"},
        )
        assert refine.status_code == 200, refine.text
        body = refine.json()
        assert body["action"] == "refine_session_recommendation"
        assert body["session_best_piq_product_id"] == BOSE_ID
        assert body["original_best_piq_product_id"] == SONY_ID
        results = await client.get(f"/results/{DECISION_ID}")
        compare = await client.get(f"/compare/{DECISION_ID}")
        why = await client.get(f"/why-best-piq/{DECISION_ID}")
        assert results.status_code == 200
        assert compare.status_code == 200
        assert why.status_code == 200
        assert 'data-best-piq="' + BOSE_ID in results.text
        assert 'data-best-piq="' + BOSE_ID in compare.text
        assert 'data-best-piq="' + BOSE_ID in why.text
        assert "94" in results.text
        assert "js-ask-form" in results.text
        assert "js-ask-form" in compare.text
        assert "js-ask-form" in why.text
        ask = await client.post(
            "/api/v1/shopping-assistant/query",
            json={
                "query": "Why did you switch from Sony?",
                "decision_id": DECISION_ID,
                "conversation_id": body["conversation_id"],
                "surface": "why",
            },
        )
        assert ask.status_code == 200
        assert ask.json()["action"] == "answer_from_evidence"
        assert "Bose" in ask.json()["answer"]


def test_no_hidden_score_or_qualitative_ranker() -> None:
    source = (ROOT / "app/services/refine_session_recommendation.py").read_text(encoding="utf-8")
    assert "_qualitative_rank" not in source
    assert "_POSITIVE_RANK" not in source
    assert "Personal PiqScore" not in source
    assert "adjusted piqscore" not in source.lower()
    snapshot = _presentation()
    result = compose_session_refinement("Comfort matters more.", packet_from_snapshot(snapshot), snapshot=snapshot)
    scores = tuple(item.canonical_piqscore.value for item in snapshot.evaluated_products)
    assert scores == (94.0, 91.0, 88.0)
    assert "piqscore" not in (result.overlay.reasons[0].lower() if result.overlay and result.overlay.reasons else "")


def test_incomparable_fit_text_does_not_invent_a_winner() -> None:
    snapshot = _presentation(
        alternative_tradeoffs=(),
        recommendation_reasons=(),
        product_presentation=(
            CanonicalProductPresentation(
                product_id=SONY_ID,
                brand="Sony",
                model="WH-1000XM5",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="comfort",
                        label="Comfort",
                        value="Excellent",
                        status="known",
                        evidence_ids=("session-comfort-bose",),
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=BOSE_ID,
                brand="Bose",
                model="QuietComfort Ultra",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="comfort",
                        label="Comfort",
                        value="Good",
                        status="known",
                        evidence_ids=("session-comfort-bose",),
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=SENN_ID,
                brand="Sennheiser",
                model="Momentum 4",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="comfort",
                        label="Comfort",
                        value="Fair",
                        status="known",
                        evidence_ids=("session-comfort-bose",),
                    ),
                ),
            ),
        ),
    )
    result = compose_session_refinement(
        "Comfort matters more.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert "not comparable" in result.answer.lower() or "don't have enough" in result.answer.lower()


def test_keyword_count_alone_does_not_win() -> None:
    snapshot = _presentation(
        alternative_tradeoffs=(),
        recommendation_reasons=(),
        product_presentation=(
            CanonicalProductPresentation(
                product_id=SONY_ID,
                brand="Sony",
                model="WH-1000XM5",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="comfort",
                        label="Comfort",
                        value="Known comfort comfort comfort",
                        status="known",
                        evidence_ids=("session-comfort-bose",),
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=BOSE_ID,
                brand="Bose",
                model="QuietComfort Ultra",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="comfort",
                        label="Comfort",
                        value="Known",
                        status="known",
                        evidence_ids=("session-comfort-bose",),
                    ),
                ),
            ),
        ),
    )
    result = compose_session_refinement(
        "Comfort matters more.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID


def test_tie_does_not_force_a_switch() -> None:
    snapshot = _presentation(
        alternative_tradeoffs=(
            CanonicalAlternativeTradeoff(
                product_id=BOSE_ID,
                reason="Bose may be better if comfort matters more.",
                evidence_ids=("session-comfort-bose",),
            ),
            CanonicalAlternativeTradeoff(
                product_id=SONY_ID,
                reason="Sony may be better if comfort matters more.",
                evidence_ids=("session-comfort-bose",),
            ),
        )
    )
    result = compose_session_refinement(
        "Comfort matters more.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "recommendation_unchanged"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID


def test_hard_feature_true_unknown_false() -> None:
    snapshot = _presentation()
    result = compose_session_refinement(
        "Multipoint is required.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert result.status in {"recommendation_unchanged", "recommendation_changed"}
    joined = " ".join(result.overlay.reasons) + result.answer
    assert "unknown" in joined.lower()
    assert result.overlay.qualification is not None
    assert "unknown" in " ".join(result.overlay.qualification.material_unknowns).lower() or "unknown" in joined.lower()
    assert result.overlay.session_best_piq_product_id != BOSE_ID


def test_hard_feature_all_unknown_is_insufficient() -> None:
    snapshot = _presentation(
        product_presentation=(
            CanonicalProductPresentation(
                product_id=SONY_ID,
                brand="Sony",
                model="WH-1000XM5",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="multipoint",
                        label="Multipoint",
                        value="Unknown",
                        status="unknown",
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=BOSE_ID,
                brand="Bose",
                model="QuietComfort Ultra",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="multipoint",
                        label="Multipoint",
                        value="Unknown",
                        status="unknown",
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=SENN_ID,
                brand="Sennheiser",
                model="Momentum 4",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="multipoint",
                        label="Multipoint",
                        value="Unknown",
                        status="unknown",
                    ),
                ),
            ),
        )
    )
    result = compose_session_refinement(
        "Multipoint is required.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID
    assert "will not invent" in result.answer.lower() or "don't have captured evidence" in result.answer.lower()


def test_budget_estimated_landed_cost_is_not_confirmed_affordable() -> None:
    snapshot = attach_presentation_contract(
        attach_offer_economics(
            _base_snapshot(),
            (
                capture_offer_economics(
                    offer_id="offer-sony",
                    product_id=SONY_ID,
                    listing=_money("listing", 19990),
                    shipping=_money("shipping", 0),
                    taxes=_money("tax", None, "not_applicable"),
                    price_state="final_effective_cost",
                    dominant_amount=19990,
                    merchant="Captured Merchant A",
                    provenance_source="captured-offer://merchant/sony",
                ),
                capture_offer_economics(
                    offer_id="offer-bose",
                    product_id=BOSE_ID,
                    listing=_money("listing", 9000),
                    shipping=_money("shipping", 0, "estimated"),
                    taxes=_money("tax", None, "not_applicable"),
                    price_state="estimated_landed_cost",
                    dominant_amount=9000,
                    merchant="Captured Merchant B",
                    provenance_source="captured-offer://merchant/bose",
                ),
                capture_offer_economics(
                    offer_id="offer-senn",
                    product_id=SENN_ID,
                    listing=_money("listing", 16990),
                    shipping=_money("shipping", 0),
                    taxes=_money("tax", None, "not_applicable"),
                    price_state="final_effective_cost",
                    dominant_amount=16990,
                    merchant="Captured Merchant C",
                    provenance_source="captured-offer://merchant/senn",
                ),
            ),
            delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        )
    )
    result = compose_session_refinement(
        "My budget is now ₱15,000.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "none_fit_constraint"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id != BOSE_ID
    assert "estimated" in result.answer.lower() or "complete" in result.answer.lower()


def test_budget_price_before_shipping_is_not_confirmed_affordable() -> None:
    snapshot = _economics_snapshot(senn_amount=4000, senn_status="unknown")
    result = compose_session_refinement(
        "My budget is now ₱15,000.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id != SENN_ID
    assert result.status in {"recommendation_changed", "recommendation_unchanged", "none_fit_constraint"}


def test_budget_import_unknown_is_not_confirmed_affordable() -> None:
    snapshot = attach_presentation_contract(
        attach_offer_economics(
            _base_snapshot(),
            (
                capture_offer_economics(
                    offer_id="offer-sony",
                    product_id=SONY_ID,
                    listing=_money("listing", 19990),
                    shipping=_money("shipping", 0),
                    taxes=_money("tax", None, "not_applicable"),
                    price_state="final_effective_cost",
                    dominant_amount=19990,
                    merchant="Captured Merchant A",
                    provenance_source="captured-offer://merchant/sony",
                ),
                capture_offer_economics(
                    offer_id="offer-bose",
                    product_id=BOSE_ID,
                    listing=_money("listing", 14990),
                    shipping=_money("shipping", 0),
                    taxes=_money("tax", None, "not_applicable"),
                    import_charges=_money("import", None, "unknown"),
                    price_state="final_effective_cost",
                    dominant_amount=14990,
                    merchant="Captured Merchant B",
                    provenance_source="captured-offer://merchant/bose",
                ),
                capture_offer_economics(
                    offer_id="offer-senn",
                    product_id=SENN_ID,
                    listing=_money("listing", 16990),
                    shipping=_money("shipping", 0),
                    taxes=_money("tax", None, "not_applicable"),
                    price_state="final_effective_cost",
                    dominant_amount=16990,
                    merchant="Captured Merchant C",
                    provenance_source="captured-offer://merchant/senn",
                ),
            ),
            delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        )
    )
    result = compose_session_refinement(
        "My budget is now ₱15,000.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id != BOSE_ID
    assert "import" in result.answer.lower() or result.status == "none_fit_constraint"


def test_session_qualification_complete_evidence_can_be_unqualified() -> None:
    snapshot = _presentation(
        qualification=CanonicalQualification(state="unqualified"),
    )
    result = compose_session_refinement(
        "Comfort matters more.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "recommendation_changed"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == BOSE_ID
    assert result.overlay.qualification is not None
    assert result.overlay.qualification.state == "unqualified"
    assert result.overlay.qualification.could_change_recommendation is False


def test_session_qualification_when_unknown_could_reverse() -> None:
    snapshot = _presentation(
        qualification=CanonicalQualification(state="unqualified"),
        alternative_tradeoffs=(),
        recommendation_reasons=(),
        product_presentation=(
            CanonicalProductPresentation(
                product_id=SONY_ID,
                brand="Sony",
                model="WH-1000XM5",
                fit_attributes=(),
            ),
            CanonicalProductPresentation(
                product_id=BOSE_ID,
                brand="Bose",
                model="QuietComfort Ultra",
                fit_attributes=(
                    CanonicalFitAttribute(
                        key="warranty",
                        label="Warranty",
                        value="Supported",
                        status="known",
                        evidence_ids=("session-battery-senn",),
                    ),
                ),
            ),
            CanonicalProductPresentation(
                product_id=SENN_ID,
                brand="Sennheiser",
                model="Momentum 4",
                fit_attributes=(),
            ),
        ),
    )
    result = compose_session_refinement(
        "Warranty is now most important.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "recommendation_changed"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == BOSE_ID
    assert result.overlay.qualification is not None
    assert result.overlay.qualification.state == "qualified"
    assert result.overlay.qualification.could_change_recommendation is True
    assert result.overlay.qualification.material_unknowns


def test_session_qualification_too_weak_is_insufficient() -> None:
    snapshot = _presentation(
        qualification=CanonicalQualification(state="unqualified"),
        alternative_tradeoffs=(),
        recommendation_reasons=(),
    )
    result = compose_session_refinement(
        "Microphone quality is now my #1 priority.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    assert result.status == "insufficient_evidence"
    assert result.overlay is not None
    assert result.overlay.session_best_piq_product_id == SONY_ID


def test_cross_surface_uses_same_session_qualification() -> None:
    snapshot = _presentation()
    result = compose_session_refinement(
        "Comfort matters more.",
        packet_from_snapshot(snapshot),
        snapshot=snapshot,
    )
    location = DeliveryContext()
    views = [
        apply_session_overlay_to_view(
            page_view_from_snapshot(snapshot, page=page, session_location=location),
            result.overlay,
        )
        for page in ("results", "compare", "why")
    ]
    assert {view.best_piq.product_id for view in views} == {BOSE_ID}
    assert {view.qualification_state for view in views} == {"qualified"}
    messages = {view.recommendation_qualified_message for view in views}
    assert len(messages) == 1
    assert all(view.canonical_piqscore_set_sha256 == snapshot.canonical_piqscore_set_sha256 for view in views)
    assert result.overlay is not None
    assert result.overlay.refinement_version == 1
    packet = apply_session_overlay_to_packet(packet_from_snapshot(snapshot), result.overlay)
    assert packet.best_piq_product_id == BOSE_ID
    assert packet.qualification_state == "qualified"
    assert any(item.evidence_id == "session-qualification" for item in packet.facts)
