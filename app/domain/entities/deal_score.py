"""DealScore domain value objects — deterministic deal ranking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing


class DealRating(StrEnum):
    """Human-readable DealScore band."""

    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass(frozen=True, slots=True)
class DealScoreComponent:
    """A single weighted scoring dimension."""

    name: str
    score: float
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "score": self.score, "weight": self.weight}


@dataclass(frozen=True, slots=True)
class DealScoreComponents:
    """Named component scores used by the weighted DealScore engine."""

    price_score: float
    seller_score: float
    shipping_score: float
    availability_score: float
    official_store_score: float
    warranty_score: float
    return_policy_score: float

    def to_dict(self) -> dict[str, float]:
        return {
            "price_score": self.price_score,
            "seller_score": self.seller_score,
            "shipping_score": self.shipping_score,
            "availability_score": self.availability_score,
            "official_store_score": self.official_store_score,
            "warranty_score": self.warranty_score,
            "return_policy_score": self.return_policy_score,
        }

    def as_weighted_components(
        self,
        weights: dict[str, float],
    ) -> tuple[DealScoreComponent, ...]:
        """Project named scores into weighted component records."""
        mapping = {
            "price": self.price_score,
            "seller": self.seller_score,
            "shipping": self.shipping_score,
            "availability": self.availability_score,
            "official_store": self.official_store_score,
            "warranty": self.warranty_score,
            "return_policy": self.return_policy_score,
        }
        return tuple(
            DealScoreComponent(name=name, score=mapping[name], weight=weight)
            for name, weight in weights.items()
        )


@dataclass(frozen=True, slots=True)
class DealListingAttributes:
    """Deal-relevant attributes not required on the base marketplace listing."""

    shipping_cost: float | None = None
    is_official_store: bool | None = None
    warranty_months: int | None = None
    return_policy_days: int | None = None


@dataclass(frozen=True, slots=True)
class ScoreableListing:
    """Normalized listing input ready for DealScore evaluation."""

    listing_id: str
    marketplace: str
    title: str
    price: float
    currency: str
    seller: str
    seller_rating: float | None
    url: str
    availability: AvailabilityStatus
    shipping_cost: float | None = None
    is_official_store: bool | None = None
    warranty_months: int | None = None
    return_policy_days: int | None = None
    source_listing: MarketplaceListing | None = None

    @property
    def total_cost(self) -> float | None:
        """Price + shipping when both are finite and non-negative."""
        if self.price < 0:
            return None
        if self.shipping_cost is None:
            return None
        if self.shipping_cost < 0:
            return None
        return round(self.price + self.shipping_cost, 2)


@dataclass(frozen=True, slots=True)
class DealScore:
    """Explainable DealScore for a single listing."""

    listing_id: str
    marketplace: str
    score: float
    rating: DealRating
    rank: int
    total_cost: float
    components: DealScoreComponents
    explanation: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    applied_weights: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "marketplace": self.marketplace,
            "score": self.score,
            "rating": self.rating.value,
            "rank": self.rank,
            "total_cost": self.total_cost,
            "components": self.components.to_dict(),
            "explanation": list(self.explanation),
            "warnings": list(self.warnings),
            "applied_weights": dict(self.applied_weights),
        }


@dataclass(frozen=True, slots=True)
class ListingEvaluation:
    """A marketplace listing paired with its DealScore evaluation."""

    listing: MarketplaceListing
    attributes: DealListingAttributes
    deal_score: DealScore

    @property
    def rank(self) -> int:
        return self.deal_score.rank


@dataclass(frozen=True, slots=True)
class RankingResult:
    """Ranked DealScore outcomes for a search result set."""

    query: str
    currency: str
    market_average_total_cost: float
    recommended_listing_id: str | None
    evaluations: tuple[ListingEvaluation, ...] = ()

    @property
    def recommended(self) -> ListingEvaluation | None:
        if self.recommended_listing_id is None:
            return None
        for evaluation in self.evaluations:
            if evaluation.deal_score.listing_id == self.recommended_listing_id:
                return evaluation
        return None


def rating_for_score(score: float) -> DealRating:
    """Map a numeric DealScore onto a rating band."""
    if score >= 90.0:
        return DealRating.EXCELLENT
    if score >= 80.0:
        return DealRating.VERY_GOOD
    if score >= 70.0:
        return DealRating.GOOD
    if score >= 60.0:
        return DealRating.FAIR
    return DealRating.POOR
