"""Unit tests for deterministic shopping assistant ranking and validation."""

from __future__ import annotations

from app.domain.entities.shopping_assistant import (
    AssistantConfidence,
    AssistantWarning,
    ShoppingAssistantResponse,
    ShoppingEvidence,
    ShoppingRecommendation,
)
from app.intelligence.shopping_assistant.buy_now_wait import build_buy_now_or_wait
from app.intelligence.shopping_assistant.candidates import ProductCandidateService
from app.intelligence.shopping_assistant.comparison import ProductComparisonService
from app.intelligence.shopping_assistant.confidence import ConfidenceCalculator, confidence_band
from app.intelligence.shopping_assistant.evidence import ShoppingEvidenceService
from app.intelligence.shopping_assistant.intent import ShoppingIntentService
from app.intelligence.shopping_assistant.recommendation import ShoppingRecommendationRanker
from app.intelligence.shopping_assistant.validator import ShoppingResponseValidator


def _pipeline(query: str):
    intent = ShoppingIntentService().parse(query)
    candidates = ProductCandidateService().find_candidates(intent)
    evidence = ShoppingEvidenceService().build_for_candidates(candidates[:5])
    ranked = ShoppingRecommendationRanker().rank(candidates, evidence, intent)
    return intent, candidates, evidence, ranked


def test_budget_filtering_and_recommendation_ranking() -> None:
    intent, candidates, evidence, ranked = _pipeline(
        "What is the best gaming laptop under ₱60,000?"
    )
    assert intent.intent == "recommendation"
    assert candidates
    assert all(item.known_price is None or item.known_price <= 60000 for item in candidates)
    assert ranked
    assert ranked[0].deal_score is not None
    assert ranked[0].product_name.startswith("Lenovo LOQ")
    assert ranked[0].evidence_ids


def test_evidence_mapping_includes_core_types() -> None:
    _, candidates, evidence, _ = _pipeline("Best gaming laptop under 60000 PHP")
    types = {item.type for item in evidence}
    assert "price" in types
    assert "deal_score" in types
    assert "rating" in types
    assert "marketplace" in types


def test_product_comparison() -> None:
    intent = ShoppingIntentService().parse(
        "Compare iPhone 17 Pro Max and Galaxy S25 Ultra for camera and battery"
    )
    # Ensure catalog names resolve — use overrides with known names.
    from app.intelligence.shopping_assistant.fixtures import get_catalog

    names = [item["product_name"] for item in get_catalog()]
    intent = ShoppingIntentService(names).parse(
        "Compare iPhone 17 Pro Max and Samsung Galaxy S25 Ultra for camera and battery"
    )
    candidates = ProductCandidateService().find_candidates(intent)
    evidence = ShoppingEvidenceService().build_for_candidates(candidates[:2])
    comparison = ProductComparisonService().compare(
        candidates[:2],
        evidence,
        priorities=intent.constraints.priorities,
    )
    assert comparison is not None
    assert len(comparison.product_ids) == 2
    assert comparison.category_winners
    assert comparison.overall_recommendation
    assert comparison.unresolved_uncertainty


def test_buy_now_or_wait_near_low() -> None:
    _, candidates, evidence, _ = _pipeline("Should I buy the Lenovo LOQ 15 now or wait?")
    focus = next(item for item in candidates if "LOQ" in item.product_name)
    text = build_buy_now_or_wait(focus, evidence)
    assert text is not None
    assert "lowest price" in text.lower() or "near" in text.lower()
    assert "uncertain" in text.lower() or "not a guarantee" in text.lower()


def test_buy_now_or_wait_missing_history() -> None:
    text = build_buy_now_or_wait(None, [])
    assert "not enough" in text.lower()


def test_confidence_bands_and_calculation() -> None:
    assert confidence_band(0.8) == "High"
    assert confidence_band(0.55) == "Medium"
    assert confidence_band(0.2) == "Low"
    _, candidates, evidence, ranked = _pipeline("Best gaming laptop under 60000")
    conf = ConfidenceCalculator().calculate(
        candidates=candidates[:3],
        evidence=evidence,
        top=ranked[0] if ranked else None,
    )
    assert isinstance(conf.score, float)
    assert conf.band in {"High", "Medium", "Low"}
    assert conf.factors


def test_unsupported_claim_rejection() -> None:
    response = ShoppingAssistantResponse(
        query="q",
        intent="recommendation",
        answer="This is the lowest price online and guaranteed authentic.",
        top_recommendation=ShoppingRecommendation(
            product_id="x",
            product_name="X",
            reason="r",
            known_price=100.0,
            currency="PHP",
            marketplace="Shopee",
            deal_score=80.0,
            confidence=0.7,
            evidence_ids=("x:price",),
        ),
        alternatives=(),
        evidence=(
            ShoppingEvidence(
                evidence_id="x:price",
                type="price",
                source_id="Shopee",
                description="Known offer price 100 PHP on Shopee",
                product_id="x",
                value=100.0,
            ),
        ),
        warnings=(),
        data_status="mock",
        providers_used=("deterministic",),
        fallback_used=True,
        confidence=AssistantConfidence(score=0.7, band="Medium"),
    )
    validated = ShoppingResponseValidator().validate(response)
    assert "unsupported claim removed" in validated.answer.lower()
    assert any(item.code == "unsupported_claim" for item in validated.warnings)
    assert any(item.code == "mock_data" for item in validated.warnings)


def test_missing_data_handling() -> None:
    intent, candidates, evidence, ranked = _pipeline("Best imaginary hoverboard under ₱10")
    assert intent.intent == "recommendation"
    # Either empty candidates or no viable ranked items under tight budget.
    assert candidates == [] or all((item.known_price or 0) <= 10 for item in candidates)
    assert ranked == [] or ranked[0].known_price is None or ranked[0].known_price <= 10


def test_mock_data_labeling_warning() -> None:
    response = ShoppingAssistantResponse(
        query="q",
        intent="general",
        answer="ok",
        top_recommendation=None,
        alternatives=(),
        evidence=(),
        warnings=(AssistantWarning(message="note"),),
        data_status="mock",
        providers_used=(),
        fallback_used=True,
        confidence=AssistantConfidence(score=0.4, band="Low"),
    )
    validated = ShoppingResponseValidator().validate(response)
    assert validated.data_status == "mock"
    assert any("mock" in item.message.lower() for item in validated.warnings)
