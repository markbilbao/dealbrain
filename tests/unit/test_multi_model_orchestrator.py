"""Tests for consensus, modes, fallback, and mode restrictions."""

from __future__ import annotations

import json

from app.domain.entities.review_analysis import (
    EvidenceClaim,
    ProviderAnalysis,
    ReviewAnalysisRequest,
    ReviewEvidenceItem,
)
from app.infrastructure.ai.review_providers import (
    ClaudeReviewProvider,
    DeterministicReviewProvider,
    GeminiReviewProvider,
    OpenAIReviewProvider,
)
from app.infrastructure.ai.transports import ScriptedTransport
from app.intelligence.review_summary.consensus import ConsensusService
from app.intelligence.review_summary.orchestrator import MultiModelReviewOrchestrator
from app.intelligence.review_summary.registry import AIProviderRegistry

REVIEWS = (
    ReviewEvidenceItem("rv-001", "Battery lasts all day."),
    ReviewEvidenceItem("rv-002", "Camera is excellent."),
    ReviewEvidenceItem("rv-003", "Heats during gaming."),
    ReviewEvidenceItem("rv-004", "Accessories in the box felt cheap."),
)


def _request() -> ReviewAnalysisRequest:
    return ReviewAnalysisRequest(
        product_id="p1",
        product="Demo Phone",
        reviews=REVIEWS,
        average_rating=4.7,
        total_review_count=500,
        timeout_seconds=5,
    )


def _payload(
    *,
    provider_label: str,
    sentiment: str = "very_positive",
    recommendation: str = "highly_recommended",
    extra_pro: str | None = None,
) -> str:
    pros = [
        {
            "claim": "Excellent camera",
            "evidence_review_ids": ["rv-002"],
            "confidence": 0.9,
        },
        {
            "claim": "Long battery life",
            "evidence_review_ids": ["rv-001"],
            "confidence": 0.88,
        },
    ]
    if extra_pro:
        pros.append(
            {
                "claim": extra_pro,
                "evidence_review_ids": ["rv-002"],
                "confidence": 0.7,
            }
        )
    return json.dumps(
        {
            "product_id": "p1",
            "overall_sentiment": sentiment,
            "summary": f"{provider_label} summary about camera and battery.",
            "pros": pros,
            "cons": [
                {
                    "claim": "Warms under heavy gaming",
                    "evidence_review_ids": ["rv-003"],
                    "confidence": 0.8,
                }
            ],
            "warnings": [
                {
                    "claim": "Some complaints about accessories",
                    "evidence_review_ids": ["rv-004"],
                    "confidence": 0.7,
                }
            ],
            "recommendation": recommendation,
            "confidence": 0.85,
        }
    )


def _registry_with_scripted(
    *,
    openai_ok: bool = True,
    anthropic_ok: bool = True,
    gemini_ok: bool = True,
    openai_sentiment: str = "very_positive",
    anthropic_sentiment: str = "very_positive",
    gemini_sentiment: str = "positive",
) -> AIProviderRegistry:
    def maybe(ok: bool, name: str, sentiment: str, cls: type):
        if not ok:
            return cls(
                api_key="",
                live_http_enabled=True,
                ai_review_enabled=True,
            )
        return cls(
            api_key="sk-test",
            live_http_enabled=True,
            ai_review_enabled=True,
            transport=ScriptedTransport(
                content=_payload(provider_label=name, sentiment=sentiment)
            ),
        )

    return AIProviderRegistry(
        [
            maybe(openai_ok, "openai", openai_sentiment, OpenAIReviewProvider),
            maybe(anthropic_ok, "anthropic", anthropic_sentiment, ClaudeReviewProvider),
            maybe(gemini_ok, "gemini", gemini_sentiment, GeminiReviewProvider),
            DeterministicReviewProvider(),
        ]
    )


def test_consensus_agreement_and_disagreements() -> None:
    service = ConsensusService()
    a = ProviderAnalysis(
        product_id="p1",
        overall_sentiment="very_positive",
        summary="A",
        pros=(EvidenceClaim("Excellent camera", ("rv-002",), 0.9),),
        cons=(),
        warnings=(),
        recommendation="highly_recommended",
        confidence=0.9,
        provider="openai",
        model="o",
    )
    b = ProviderAnalysis(
        product_id="p1",
        overall_sentiment="positive",
        summary="B",
        pros=(EvidenceClaim("Unique claim only here", ("rv-001",), 0.7),),
        cons=(),
        warnings=(),
        recommendation="recommended",
        confidence=0.7,
        provider="anthropic",
        model="c",
    )
    merged, meta = service.build(mode="maximum", analyses=[a, b])
    assert meta.agreement_score < 1.0
    assert meta.disagreements
    assert any(item.field == "overall_sentiment" for item in meta.disagreements)
    assert merged.overall_sentiment in {"very_positive", "positive"}


def test_economy_falls_back_to_deterministic_when_primary_missing() -> None:
    registry = _registry_with_scripted(openai_ok=False, anthropic_ok=False, gemini_ok=False)
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="economy",
        primary_provider="openai",
    )
    result = orch.analyze(_request(), mode="economy")
    assert result.analysis.provider == "deterministic"
    assert result.consensus.fallback_used is True
    assert result.consensus.mode == "economy"


def test_economy_uses_primary_when_available() -> None:
    registry = _registry_with_scripted()
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="economy",
        primary_provider="openai",
    )
    result = orch.analyze(_request(), mode="economy")
    assert result.analysis.provider == "openai"
    assert result.consensus.fallback_used is False
    assert "openai" in result.providers_used


def test_balanced_mode_uses_primary_and_secondary() -> None:
    registry = _registry_with_scripted(
        openai_sentiment="very_positive",
        anthropic_sentiment="positive",
    )
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="balanced",
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    result = orch.analyze(_request(), mode="balanced")
    assert result.consensus.mode == "balanced"
    assert set(result.providers_used) == {"openai", "anthropic"}
    assert result.consensus.agreement_score is not None


def test_maximum_mode_reports_disagreements() -> None:
    registry = _registry_with_scripted(
        openai_sentiment="very_positive",
        anthropic_sentiment="very_positive",
        gemini_sentiment="mixed",
    )
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="maximum",
        primary_provider="openai",
    )
    result = orch.analyze(_request(), mode="maximum")
    assert result.consensus.mode == "maximum"
    assert result.consensus.providers_completed == 3
    assert result.consensus.disagreements
    assert result.consensus.agreement_score < 1.0


def test_maximum_partial_failure_still_consensuses() -> None:
    registry = _registry_with_scripted(gemini_ok=False)
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="maximum",
    )
    result = orch.analyze(_request(), mode="maximum")
    assert result.consensus.providers_completed == 2
    assert result.consensus.fallback_used is False
    assert result.analysis.status == "ok"


def test_ai_disabled_forces_deterministic() -> None:
    registry = _registry_with_scripted()
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=False,
        configured_mode="maximum",
    )
    result = orch.analyze(_request(), mode="maximum")
    assert result.analysis.provider == "deterministic"
    assert result.consensus.fallback_used is True
    assert result.consensus.mode == "economy"


def test_client_cannot_exceed_server_mode() -> None:
    registry = _registry_with_scripted()
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
    )
    assert orch.resolve_mode("maximum") == "economy"
    result = orch.analyze(_request(), mode="maximum")
    assert result.consensus.mode == "economy"


def test_all_external_fail_in_maximum_uses_deterministic() -> None:
    registry = _registry_with_scripted(openai_ok=False, anthropic_ok=False, gemini_ok=False)
    orch = MultiModelReviewOrchestrator(
        registry,
        ai_review_enabled=True,
        configured_mode="maximum",
    )
    result = orch.analyze(_request(), mode="maximum")
    assert result.analysis.provider == "deterministic"
    assert result.consensus.fallback_used is True
