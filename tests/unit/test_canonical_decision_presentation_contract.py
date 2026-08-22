"""Schema 1.2 canonical decision presentation contract tests."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.location import DeliveryContext
from app.consumer.pages import render_page
from app.consumer.pricing import MoneyComponent
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
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V1_1,
    SCHEMA_VERSION_V1_2,
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.domain.exceptions import DecisionSnapshotIntegrityError
from app.infrastructure.persistence.memory_decision_snapshot_repository import (
    InMemoryDecisionSnapshotRepository,
)
from app.services.answer_from_evidence import compose_evidence_answer
from app.services.canonical_offer_economics import (
    attach_offer_economics,
    capture_offer_economics,
    delivery_from_location,
)
from app.services.canonical_presentation_contract import attach_presentation_contract
from app.services.decision_evidence_packet import packet_from_snapshot
from jsonschema import Draft202012Validator, FormatChecker

START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000052"
SONY_ID = "sony-wh-1000xm5-canonical"
BOSE_ID = "bose-qc-ultra-canonical"
ROOT = Path(__file__).resolve().parents[2]


def _owner() -> ConversationOwner:
    return ConversationOwner(
        principal_type="guest",
        principal_id="guest-presentation",
        session_id="session-presentation",
        expires_at=START + timedelta(minutes=30),
    )


def _score(value: float, digest: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest * 64,
    )


def _base_snapshot() -> CanonicalDecisionSnapshot:
    return CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=_owner(),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=SONY_ID,
                display_name="Sony WH-1000XM5",
                variant="black",
                canonical_piqscore=_score(90, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=BOSE_ID,
                display_name="Bose QuietComfort Ultra",
                variant="black",
                canonical_piqscore=_score(88, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="consider",
            best_piq_product_id=BOSE_ID,
            alternative_product_ids=(SONY_ID,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="canonical-comfort-bose",
                product_id=BOSE_ID,
                topic="comfort",
                fact="canonical comfort evidence",
                source="captured-offer://comfort/bose",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
            DecisionEvidenceSnapshot(
                evidence_id="canonical-anc-sony",
                product_id=SONY_ID,
                topic="anc",
                fact="canonical ANC evidence",
                source="captured-offer://anc/sony",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="e" * 64,
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


def _economics_snapshot() -> CanonicalDecisionSnapshot:
    return attach_offer_economics(
        _base_snapshot(),
        (
            capture_offer_economics(
                offer_id="offer-sony",
                product_id=SONY_ID,
                listing=_money("listing", 19990),
                shipping=_money("shipping", None, "unknown"),
                taxes=_money("tax", None, "unknown"),
                price_state="price_before_shipping",
                dominant_amount=19990,
                merchant="Captured Merchant",
                provenance_source="captured-offer://merchant/sony",
            ),
            capture_offer_economics(
                offer_id="offer-bose",
                product_id=BOSE_ID,
                listing=_money("listing", 18990),
                shipping=_money("shipping", None, "unknown"),
                taxes=_money("tax", None, "unknown"),
                price_state="price_before_shipping",
                dominant_amount=18990,
                merchant="Other Merchant",
                provenance_source="captured-offer://merchant/bose",
            ),
        ),
        delivery=delivery_from_location(city="Taguig City", postal_code="1630", country="PH"),
        data_classification="canonical_decision",
    )


def _presentation(**kwargs) -> CanonicalDecisionSnapshot:
    return attach_presentation_contract(
        _economics_snapshot(),
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
                top_priority="Comfort",
                use_case="Long flights",
                urgency="This week",
                required_features=("Strong ANC",),
            ),
        ),
        product_presentation=kwargs.get(
            "product_presentation",
            (
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
                            evidence_ids=("canonical-comfort-bose",),
                        ),
                        CanonicalFitAttribute(
                            key="anc",
                            label="Noise cancellation",
                            value="Strong",
                            status="known",
                            evidence_ids=("canonical-anc-sony",),
                        ),
                    ),
                ),
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
                            evidence_ids=("canonical-comfort-bose",),
                        ),
                        CanonicalFitAttribute(
                            key="anc",
                            label="Noise cancellation",
                            value="Class-leading",
                            status="known",
                            evidence_ids=("canonical-anc-sony",),
                        ),
                        CanonicalFitAttribute(
                            key="multipoint",
                            label="Multipoint",
                            value="Supported",
                            status="known",
                            evidence_ids=("canonical-anc-sony",),
                        ),
                    ),
                ),
            ),
        ),
        recommendation_reasons=kwargs.get(
            "recommendation_reasons",
            (
                CanonicalRecommendationReason(
                    reason=(
                        "Bose was recommended because comfort was the highest priority "
                        "and it fit the evaluated budget and travel use case."
                    ),
                    evidence_ids=("canonical-comfort-bose",),
                    shopper_priority="Comfort",
                    product_id=BOSE_ID,
                    related_attribute="comfort",
                ),
            ),
        ),
        best_for=kwargs.get(
            "best_for",
            (
                CanonicalBestFor(
                    label="Frequent travelers prioritizing comfort",
                    evidence_ids=("canonical-comfort-bose",),
                ),
            ),
        ),
        alternative_tradeoffs=kwargs.get(
            "alternative_tradeoffs",
            (
                CanonicalAlternativeTradeoff(
                    product_id=SONY_ID,
                    reason="Sony may be better if ANC performance matters more than comfort.",
                    evidence_ids=("canonical-anc-sony",),
                ),
            ),
        ),
        data_classification="canonical_decision",
    )


def test_schema_1_0_digest_unchanged_without_presentation() -> None:
    snapshot = _base_snapshot()
    assert snapshot.schema_version == SCHEMA_VERSION_V1
    payload = snapshot.to_dict()
    assert "qualification" not in payload
    assert "shopper_context" not in payload
    assert "product_presentation" not in payload
    assert payload["schema_version"] == "1.0"
    assert snapshot.content_sha256 == _base_snapshot().content_sha256


def test_schema_1_1_digest_unchanged_without_presentation() -> None:
    snapshot = _economics_snapshot()
    assert snapshot.schema_version == SCHEMA_VERSION_V1_1
    payload = snapshot.to_dict()
    assert "qualification" not in payload
    assert payload["schema_version"] == "1.1"
    assert snapshot.content_sha256 == _economics_snapshot().content_sha256


def test_schema_1_2_serializes_persists_and_validates() -> None:
    snapshot = _presentation()
    assert snapshot.schema_version == SCHEMA_VERSION_V1_2
    payload = snapshot.to_dict()
    assert payload["schema_version"] == "1.2"
    assert payload["qualification"]["state"] == "qualified"
    assert payload["shopper_context"]["top_priority"] == "Comfort"
    Draft202012Validator(
        json.loads((ROOT / "schemas/sprint29-decision-context-v1.2.schema.json").read_text()),
        format_checker=FormatChecker(),
    ).validate(payload)
    repo = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    repo.add(snapshot)
    loaded = repo.get(DECISION_ID, 1)
    assert loaded is not None
    assert loaded.content_sha256 == snapshot.content_sha256
    assert loaded.shopper_context is not None
    assert loaded.shopper_context.top_priority == "Comfort"


def test_qualification_does_not_change_piqscore_or_best_piq() -> None:
    before = _economics_snapshot()
    after = _presentation()
    assert after.recommendation.best_piq_product_id == before.recommendation.best_piq_product_id
    assert after.canonical_piqscore_set_sha256 == before.canonical_piqscore_set_sha256
    assert after.evaluated_products[0].canonical_piqscore.value == 90
    view = page_view_from_snapshot(
        after,
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.is_qualified is True
    assert view.recommendation_qualified_message is not None
    assert "Shipping" in view.recommendation_qualified_message
    unqualified = attach_presentation_contract(
        before,
        qualification=CanonicalQualification(state="unqualified"),
        data_classification="canonical_decision",
    )
    plain = page_view_from_snapshot(
        unqualified,
        page="results",
        session_location=DeliveryContext(),
    )
    assert plain.best_piq.is_qualified is False
    absent = page_view_from_snapshot(
        before,
        page="results",
        session_location=DeliveryContext(),
    )
    assert absent.best_piq.is_qualified is False
    assert absent.recommendation_qualified_message is None


def test_shopper_context_is_historical_and_not_session_mutated() -> None:
    snapshot = _presentation()
    digest = snapshot.content_sha256
    later = replace(
        snapshot,
        shopper_context=CanonicalShopperContext(top_priority="Battery"),
    )
    assert later.content_sha256 != digest
    assert snapshot.shopper_context is not None
    assert snapshot.shopper_context.top_priority == "Comfort"
    assert snapshot.content_sha256 == digest


def test_product_metadata_and_offer_url_without_fixture_fallback() -> None:
    view = page_view_from_snapshot(
        _presentation(),
        page="results",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    assert view.best_piq.brand == "Bose"
    assert view.best_piq.model == "QuietComfort Ultra"
    assert view.best_piq.category == "Headphones"
    assert view.best_piq.offer_url == "https://merchant.example/bose-qc-ultra"
    html = render_page(view)
    assert "https://merchant.example/bose-qc-ultra" in html
    assert "js-ask-form" in html
    assert "headphones-standard" not in html
    missing = page_view_from_snapshot(
        _economics_snapshot(),
        page="results",
        session_location=DeliveryContext(),
    )
    assert missing.best_piq.offer_url == ""
    assert "View offer" not in render_page(missing)


def test_fit_rows_use_canonical_attributes_only() -> None:
    view = page_view_from_snapshot(
        _presentation(),
        page="compare",
        session_location=DeliveryContext(),
    )
    labels = {row.label for row in view.compare_fit_rows}
    assert "Comfort" in labels
    assert "Noise cancellation" in labels
    assert "Multipoint" in labels
    comfort = next(row for row in view.compare_fit_rows if row.label == "Comfort")
    assert "Excellent clamp comfort" in comfort.values
    assert all("Lazada" not in value for row in view.compare_fit_rows for value in row.values)


def test_why_sections_use_captured_reasoning() -> None:
    view = page_view_from_snapshot(
        _presentation(),
        page="why",
        session_location=DeliveryContext(city="Taguig City", postal_code="1630", source="manual"),
    )
    titles = [section.title for section in view.why_sections]
    assert titles == [
        "Why PiqSavi recommends this",
        "What to know before you buy",
        "Best for",
        "When an alternative may be better",
        "What PiqSavi considered",
        "What we don’t know",
    ]
    assert "comfort was the highest priority" in view.why_sections[0].narrative
    assert any("Frequent travelers" in text for _, text in view.why_sections[2].bullets)
    assert any("ANC performance" in text for _, text in view.why_sections[3].bullets)
    assert any("shipping" in text.lower() for _, text in view.why_sections[5].bullets)
    html = render_page(view)
    assert "js-ask-form" in html


def test_ask_answers_from_presentation_contract_and_stays_read_only() -> None:
    snapshot = _presentation()
    packet = packet_from_snapshot(snapshot)
    assert packet.is_qualified is True
    questions = {
        "Why is this best for me?": "comfort was the highest priority",
        "What was my top priority?": "Comfort",
        "Why is this qualified?": "qualified Best Piq",
        "What is this product best for?": "Frequent travelers",
        "What trade-off did you consider?": "ANC performance",
        "Which model did you evaluate?": "QuietComfort Ultra",
        "Where can I buy it?": "https://merchant.example/bose-qc-ultra",
        "Does it support multipoint?": "Multipoint",
    }
    for question, expected in questions.items():
        result = compose_evidence_answer(question, packet)
        assert expected.lower() in result.answer.lower()
        assert result.status in {"answered", "partially_answered"}
    preference = compose_evidence_answer("Actually comfort matters more now.", packet)
    assert preference.status == "preference_change_not_applied"
    assert snapshot.content_sha256 == _presentation().content_sha256
    missing = packet_from_snapshot(_economics_snapshot())
    assert (
        compose_evidence_answer("What was my top priority?", missing).status
        == "insufficient_evidence"
    )
    assert compose_evidence_answer("Where can I buy it?", missing).status == "insufficient_evidence"


def test_cross_surface_consistency_for_schema_1_2() -> None:
    snapshot = _presentation()
    results = page_view_from_snapshot(snapshot, page="results", session_location=DeliveryContext())
    compare = page_view_from_snapshot(snapshot, page="compare", session_location=DeliveryContext())
    why = page_view_from_snapshot(snapshot, page="why", session_location=DeliveryContext())
    packet = packet_from_snapshot(snapshot)
    for view in (results, compare, why):
        assert view.decision_id == DECISION_ID
        assert view.best_piq.product_id == BOSE_ID
        assert view.best_piq.is_qualified is True
        assert view.shopper.top_priority == "Comfort"
        assert view.best_piq.offer_url.startswith("https://")
        assert "js-ask-form" in render_page(view)
    assert packet.best_piq_product_id == BOSE_ID
    assert packet.is_qualified is True
    assert any(item.topic == "priority" for item in packet.facts)


def test_integrity_covers_presentation_fields() -> None:
    snapshot = _presentation()
    repo = InMemoryDecisionSnapshotRepository(clock=lambda: START)
    repo.add(snapshot)
    mutated = replace(
        snapshot,
        shopper_context=CanonicalShopperContext(top_priority="Battery"),
    )
    repo._records[(DECISION_ID, 1)] = (mutated, snapshot.content_sha256)  # noqa: SLF001
    with pytest.raises(DecisionSnapshotIntegrityError):
        repo.get(DECISION_ID, 1)


@pytest.mark.parametrize(
    "field",
    ("qualification", "product_identity", "fit", "reason", "offer_url"),
)
def test_tampering_presentation_fields_changes_digest(field: str) -> None:
    original = _presentation()
    if field == "qualification":
        changed = attach_presentation_contract(
            original,
            qualification=CanonicalQualification(
                state="unqualified",
            ),
        )
    elif field == "product_identity":
        changed = attach_presentation_contract(
            original,
            product_presentation=(
                replace(original.product_presentation[0], brand="NotBose"),
                original.product_presentation[1],
            ),
        )
    elif field == "fit":
        first = original.product_presentation[0]
        changed = attach_presentation_contract(
            original,
            product_presentation=(
                replace(
                    first,
                    fit_attributes=(
                        replace(first.fit_attributes[0], value="Poor"),
                        *first.fit_attributes[1:],
                    ),
                ),
                original.product_presentation[1],
            ),
        )
    elif field == "reason":
        changed = attach_presentation_contract(
            original,
            recommendation_reasons=(
                CanonicalRecommendationReason(reason="Invented later.", product_id=BOSE_ID),
            ),
        )
    else:
        changed = attach_presentation_contract(
            original,
            product_presentation=(
                replace(original.product_presentation[0], offer_url="https://other.example/offer"),
                original.product_presentation[1],
            ),
        )
    assert changed.content_sha256 != original.content_sha256


def test_unsafe_offer_url_is_rejected() -> None:
    with pytest.raises(ValueError):
        CanonicalProductPresentation(
            product_id=BOSE_ID,
            offer_url="javascript:alert(1)",
        )


def test_legacy_pages_do_not_backfill_presentation() -> None:
    view = page_view_from_snapshot(
        _economics_snapshot(),
        page="why",
        session_location=DeliveryContext(),
    )
    assert view.shopper.top_priority == "Not captured"
    assert view.best_piq.is_qualified is False
    assert all(value == "—" for row in view.compare_fit_rows for value in row.values)
    assert "headphones-standard" not in render_page(view)


def test_refine_and_propose_remain_absent() -> None:
    source = (ROOT / "app/services/canonical_presentation_contract.py").read_text()
    adapter = (ROOT / "app/consumer/canonical_presentation.py").read_text()
    js = (ROOT / "app/static/consumer/js/consumer.js").read_text()
    assert "def refine_session_recommendation" not in source
    assert "def propose_research" not in source
    assert "refine_session_recommendation" not in adapter
    assert "propose_research" not in adapter
    assert "refine_session_recommendation" not in js
    assert "propose_research" not in js
