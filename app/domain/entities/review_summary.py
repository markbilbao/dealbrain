"""AI Review Summary domain entities and value objects.

Deterministic shopping insights derived from review intelligence inputs.
Identifiers and timestamps are injected by callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.entities.review_analysis import AnalysisDisagreement, EvidenceClaim


@dataclass(frozen=True, slots=True)
class Pros:
    """Ranked positive themes extracted from review text."""

    items: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"items": list(self.items)}


@dataclass(frozen=True, slots=True)
class Cons:
    """Ranked negative themes extracted from review text."""

    items: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"items": list(self.items)}


@dataclass(frozen=True, slots=True)
class Warning:
    """Buyer caution derived from recurring complaint themes."""

    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"message": self.message}


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Purchase recommendation label for the summarized product."""

    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label}


@dataclass(frozen=True, slots=True)
class ReviewInsight:
    """Single theme insight with polarity and frequency rank."""

    theme: str
    label: str
    polarity: str  # "pro" | "con" | "warning"
    frequency: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme,
            "label": self.label,
            "polarity": self.polarity,
            "frequency": self.frequency,
        }


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """Product-level AI review summary (mock / multi-model providers)."""

    summary_id: str
    product_id: str
    product: str
    overall_sentiment: str
    summary: str
    pros: Pros
    cons: Cons
    warnings: tuple[Warning, ...]
    recommendation: Recommendation
    insights: tuple[ReviewInsight, ...]
    average_rating: float | None
    total_review_count: int
    provider: str
    generated_at: datetime
    # Multi-model metadata (defaults preserve Sprint 12 deterministic behavior).
    mode: str = "economy"
    providers_used: tuple[str, ...] = ()
    models_used: tuple[str, ...] = ()
    fallback_used: bool = False
    fallback_reason: str | None = None
    agreement_score: float | None = None
    consensus_confidence: float | None = None
    disagreements: tuple[AnalysisDisagreement, ...] = ()
    evidence_pros: tuple[EvidenceClaim, ...] = ()
    evidence_cons: tuple[EvidenceClaim, ...] = ()
    evidence_warnings: tuple[EvidenceClaim, ...] = ()
    processing: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "product_id": self.product_id,
            "product": self.product,
            "overall_sentiment": self.overall_sentiment,
            "summary": self.summary,
            "pros": list(self.pros.items),
            "cons": list(self.cons.items),
            "warnings": [item.message for item in self.warnings],
            "recommendation": self.recommendation.label,
            "insights": [item.to_dict() for item in self.insights],
            "average_rating": self.average_rating,
            "total_review_count": self.total_review_count,
            "provider": self.provider,
            "generated_at": self.generated_at.isoformat(),
            "mode": self.mode,
            "providers_used": list(self.providers_used),
            "models_used": list(self.models_used),
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "agreement_score": self.agreement_score,
            "consensus_confidence": self.consensus_confidence,
            "disagreements": [item.to_dict() for item in self.disagreements],
            "evidence": {
                "pros": [item.to_dict() for item in self.evidence_pros],
                "cons": [item.to_dict() for item in self.evidence_cons],
                "warnings": [item.to_dict() for item in self.evidence_warnings],
            },
            "processing": dict(self.processing),
        }
