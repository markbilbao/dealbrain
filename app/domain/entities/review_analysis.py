"""Normalized multi-model review analysis domain types.

Provider adapters must emit these structures. Application consensus logic
compares them deterministically — no provider judges its own correctness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

SentimentCode = Literal["very_positive", "positive", "mixed", "negative"]
RecommendationCode = Literal[
    "highly_recommended",
    "recommended",
    "consider_alternatives",
    "not_recommended",
]
AnalysisMode = Literal["economy", "balanced", "maximum"]
ProviderStatus = Literal[
    "ok",
    "unavailable",
    "timeout",
    "rate_limited",
    "malformed",
    "validation_failed",
    "error",
    "skipped",
]

SENTIMENT_DISPLAY: dict[str, str] = {
    "very_positive": "Very Positive",
    "positive": "Positive",
    "mixed": "Mixed",
    "negative": "Negative",
}
RECOMMENDATION_DISPLAY: dict[str, str] = {
    "highly_recommended": "Highly Recommended",
    "recommended": "Recommended",
    "consider_alternatives": "Consider Carefully",
    "not_recommended": "Not Recommended",
}
DISPLAY_TO_SENTIMENT = {v: k for k, v in SENTIMENT_DISPLAY.items()}
DISPLAY_TO_RECOMMENDATION = {v: k for k, v in RECOMMENDATION_DISPLAY.items()}

MODE_RANK: dict[str, int] = {"economy": 0, "balanced": 1, "maximum": 2}


@dataclass(frozen=True, slots=True)
class ReviewEvidenceItem:
    """Single review text supplied to providers (evidence source)."""

    review_id: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"review_id": self.review_id, "text": self.text}


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """A claim that must cite supporting review evidence IDs."""

    claim: str
    evidence_review_ids: tuple[str, ...]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "evidence_review_ids": list(self.evidence_review_ids),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class ProviderUsageMetadata:
    """Optional token / cost metadata — never includes secrets or prompts."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    estimated_cost_usd: float | None = None
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True, slots=True)
class ProviderAnalysis:
    """Normalized analysis emitted by one AIReviewProvider."""

    product_id: str
    overall_sentiment: SentimentCode
    summary: str
    pros: tuple[EvidenceClaim, ...]
    cons: tuple[EvidenceClaim, ...]
    warnings: tuple[EvidenceClaim, ...]
    recommendation: RecommendationCode
    confidence: float
    provider: str
    model: str
    status: ProviderStatus = "ok"
    error_code: str | None = None
    usage: ProviderUsageMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "overall_sentiment": self.overall_sentiment,
            "summary": self.summary,
            "pros": [item.to_dict() for item in self.pros],
            "cons": [item.to_dict() for item in self.cons],
            "warnings": [item.to_dict() for item in self.warnings],
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "error_code": self.error_code,
            "usage": self.usage.to_dict() if self.usage else None,
        }


@dataclass(frozen=True, slots=True)
class ReviewAnalysisRequest:
    """Input bundle passed to every provider adapter."""

    product_id: str
    product: str
    reviews: tuple[ReviewEvidenceItem, ...]
    average_rating: float | None
    total_review_count: int
    timeout_seconds: float = 20.0


@dataclass(frozen=True, slots=True)
class AnalysisDisagreement:
    """Important disagreement preserved for MAXIMUM / BALANCED modes."""

    field: str
    providers: tuple[str, ...]
    values: tuple[str, ...]
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "providers": list(self.providers),
            "values": list(self.values),
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class ConsensusMetadata:
    """Deterministic consensus bookkeeping (no provider self-grading)."""

    mode: AnalysisMode
    providers_requested: int
    providers_completed: int
    agreement_score: float
    consensus_confidence: float
    provider_results: tuple[ProviderAnalysis, ...]
    disagreements: tuple[AnalysisDisagreement, ...]
    fallback_used: bool = False
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "providers_requested": self.providers_requested,
            "providers_completed": self.providers_completed,
            "agreement_score": self.agreement_score,
            "consensus_confidence": self.consensus_confidence,
            "provider_results": [item.to_dict() for item in self.provider_results],
            "disagreements": [item.to_dict() for item in self.disagreements],
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
        }


@dataclass(frozen=True, slots=True)
class OrchestratedAnalysis:
    """Final orchestrated result ready for API mapping."""

    analysis: ProviderAnalysis
    consensus: ConsensusMetadata
    generated_at: datetime
    providers_used: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": self.analysis.to_dict(),
            "consensus": self.consensus.to_dict(),
            "generated_at": self.generated_at.isoformat(),
            "providers_used": list(self.providers_used),
        }
