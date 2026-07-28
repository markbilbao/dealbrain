"""Recommendation and explainability domain value objects.

Deterministic buying advice derived from DealScore rankings.
No LLMs and no invented price-history claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.entities.deal_score import RankingResult


class PurchaseDecision(StrEnum):
    """Supported purchase advice outcomes."""

    BUY = "buy"
    CONSIDER = "consider"
    WAIT = "wait"
    AVOID = "avoid"
    INSUFFICIENT_INFORMATION = "insufficient_information"


@dataclass(frozen=True, slots=True)
class RecommendationReason:
    """One ranked explanation supporting the recommendation."""

    text: str
    rank: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "rank": self.rank}


@dataclass(frozen=True, slots=True)
class RecommendationTradeoff:
    """A notable downside or compromise of the recommended choice."""

    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text}


@dataclass(frozen=True, slots=True)
class RecommendationWarning:
    """A caution the buyer should review before acting."""

    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text}


@dataclass(frozen=True, slots=True)
class AlternativeRecommendation:
    """An alternate listing the buyer may prefer under a different priority."""

    listing_id: str
    label: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "label": self.label,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class RecommendationConfidence:
    """Deterministic confidence estimate for a recommendation."""

    value: float
    factors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "factors": list(self.factors)}


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Explainable purchase recommendation for a ranked result set."""

    decision: PurchaseDecision
    recommended_listing_id: str | None
    headline: str
    summary: str
    reasoning: tuple[RecommendationReason, ...] = ()
    tradeoffs: tuple[RecommendationTradeoff, ...] = ()
    warnings: tuple[RecommendationWarning, ...] = ()
    confidence: RecommendationConfidence = field(
        default_factory=lambda: RecommendationConfidence(value=0.0)
    )
    alternatives: tuple[AlternativeRecommendation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "recommended_listing_id": self.recommended_listing_id,
            "headline": self.headline,
            "summary": self.summary,
            "reasoning": [reason.text for reason in self.reasoning],
            "tradeoffs": [tradeoff.text for tradeoff in self.tradeoffs],
            "warnings": [warning.text for warning in self.warnings],
            "confidence": self.confidence.value,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
        }


@dataclass(frozen=True, slots=True)
class ShoppingRecommendationResult:
    """Full shopping recommendation payload including DealScore rankings."""

    query: str
    currency: str
    recommendation: Recommendation
    ranking: RankingResult

    @property
    def alternatives(self) -> tuple[AlternativeRecommendation, ...]:
        return self.recommendation.alternatives
