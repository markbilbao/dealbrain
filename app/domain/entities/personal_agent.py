"""Personal AI Shopping Agent domain entities and value objects.

Fixture-backed customer profiles used to personalize DealBrain recommendations.
No login, cloud sync, or purchase-history claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

DataStatus = Literal["mock", "imported", "live"]
ConfidenceBand = Literal["High", "Medium", "Low"]

BuyingVerdict = Literal[
    "excellent_choice",
    "good_value",
    "worth_waiting",
    "price_likely_to_drop",
    "not_recommended",
    "alternative_available",
    "upgrade_not_worthwhile",
    "too_expensive",
    "poor_community_trust",
]

PREFERENCE_DIMENSIONS: tuple[str, ...] = (
    "budget_fit",
    "brand_affinity",
    "feature_match",
    "marketplace_preference",
    "community_sentiment",
    "review_quality",
    "knowledge_graph_proximity",
    "availability",
    "deal_score",
)


@dataclass(frozen=True, slots=True)
class CustomerProfile:
    """Reusable customer preference profile (fixture / demo only in v1)."""

    profile_id: str
    display_name: str
    persona: str
    budget: float | None = None
    currency: str = "PHP"
    country: str = "PH"
    preferred_marketplaces: tuple[str, ...] = ()
    favorite_brands: tuple[str, ...] = ()
    disliked_brands: tuple[str, ...] = ()
    preferred_screen_sizes: tuple[str, ...] = ()
    preferred_colors: tuple[str, ...] = ()
    gaming: bool = False
    office_work: bool = False
    student: bool = False
    creator: bool = False
    traveler: bool = False
    battery_priority: float = 0.5
    performance_priority: float = 0.5
    camera_priority: float = 0.5
    storage_priority: float = 0.5
    price_sensitivity: float = 0.5
    upgrade_frequency: str = "occasional"
    owned_products: tuple[str, ...] = ()
    wishlist: tuple[str, ...] = ()
    favorite_categories: tuple[str, ...] = ()
    accessories_owned: tuple[str, ...] = ()
    description: str = ""
    data_status: DataStatus = "mock"

    def use_cases(self) -> tuple[str, ...]:
        cases: list[str] = []
        if self.gaming:
            cases.append("gaming")
        if self.office_work:
            cases.append("productivity")
        if self.student:
            cases.append("student")
        if self.creator:
            cases.append("content_creation")
        if self.traveler:
            cases.append("travel")
        if self.camera_priority >= 0.7:
            cases.append("photography")
        if self.battery_priority >= 0.7:
            cases.append("battery_life")
        return tuple(cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "persona": self.persona,
            "budget": self.budget,
            "currency": self.currency,
            "country": self.country,
            "preferred_marketplaces": list(self.preferred_marketplaces),
            "favorite_brands": list(self.favorite_brands),
            "disliked_brands": list(self.disliked_brands),
            "preferred_screen_sizes": list(self.preferred_screen_sizes),
            "preferred_colors": list(self.preferred_colors),
            "gaming": self.gaming,
            "office_work": self.office_work,
            "student": self.student,
            "creator": self.creator,
            "traveler": self.traveler,
            "battery_priority": self.battery_priority,
            "performance_priority": self.performance_priority,
            "camera_priority": self.camera_priority,
            "storage_priority": self.storage_priority,
            "price_sensitivity": self.price_sensitivity,
            "upgrade_frequency": self.upgrade_frequency,
            "owned_products": list(self.owned_products),
            "wishlist": list(self.wishlist),
            "favorite_categories": list(self.favorite_categories),
            "accessories_owned": list(self.accessories_owned),
            "description": self.description,
            "data_status": self.data_status,
            "use_cases": list(self.use_cases()),
        }


@dataclass(frozen=True, slots=True)
class PreferenceDimensionScore:
    """Single normalized preference dimension with evidence."""

    dimension: str
    score: float
    weight: float
    weighted_score: float
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 4),
            "weight": round(self.weight, 4),
            "weighted_score": round(self.weighted_score, 4),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class PreferenceScoreResult:
    """Normalized weighted preference scoring for one product vs a profile."""

    profile_id: str
    product_id: str
    total_score: float
    dimensions: tuple[PreferenceDimensionScore, ...]
    confidence: float
    confidence_band: ConfidenceBand
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "product_id": self.product_id,
            "total_score": round(self.total_score, 4),
            "dimensions": [item.to_dict() for item in self.dimensions],
            "confidence": round(self.confidence, 4),
            "confidence_band": self.confidence_band,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class PersonalDealScore:
    """Personalized DealScore combining global DealScore and profile fit."""

    product_id: str
    profile_id: str
    personal_deal_score: float
    global_deal_score: float | None
    preference_fit: float
    budget_fit: float
    brand_affinity: float
    ownership_compatibility: float
    community_trust: float
    factors: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "profile_id": self.profile_id,
            "personal_deal_score": round(self.personal_deal_score, 2),
            "global_deal_score": (
                round(self.global_deal_score, 2) if self.global_deal_score is not None else None
            ),
            "preference_fit": round(self.preference_fit, 4),
            "budget_fit": round(self.budget_fit, 4),
            "brand_affinity": round(self.brand_affinity, 4),
            "ownership_compatibility": round(self.ownership_compatibility, 4),
            "community_trust": round(self.community_trust, 4),
            "factors": list(self.factors),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class BuyingAdvice:
    """Structured buying advice with evidence-backed explanation."""

    product_id: str
    profile_id: str
    verdict: BuyingVerdict
    label: str
    summary: str
    explanation: str
    evidence: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    personal_deal_score: float | None = None
    alternative_product_id: str | None = None
    alternative_product_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "profile_id": self.profile_id,
            "verdict": self.verdict,
            "label": self.label,
            "summary": self.summary,
            "explanation": self.explanation,
            "evidence": list(self.evidence),
            "evidence_ids": list(self.evidence_ids),
            "personal_deal_score": (
                round(self.personal_deal_score, 2)
                if self.personal_deal_score is not None
                else None
            ),
            "alternative_product_id": self.alternative_product_id,
            "alternative_product_name": self.alternative_product_name,
        }


@dataclass(frozen=True, slots=True)
class PersonalRecommendation:
    """Personalized product recommendation for a profile."""

    product_id: str
    product_name: str
    profile_id: str
    reason: str
    explanation: str
    known_price: float | None
    currency: str
    marketplace: str | None
    personal_deal_score: float
    global_deal_score: float | None
    preference_score: float
    confidence: float
    advice: BuyingAdvice | None = None
    evidence_ids: tuple[str, ...] = ()
    preference_dimensions: tuple[PreferenceDimensionScore, ...] = ()
    rating: float | None = None
    review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "profile_id": self.profile_id,
            "reason": self.reason,
            "explanation": self.explanation,
            "known_price": self.known_price,
            "currency": self.currency,
            "marketplace": self.marketplace,
            "personal_deal_score": round(self.personal_deal_score, 2),
            "global_deal_score": (
                round(self.global_deal_score, 2) if self.global_deal_score is not None else None
            ),
            "preference_score": round(self.preference_score, 4),
            "confidence": round(self.confidence, 4),
            "advice": self.advice.to_dict() if self.advice else None,
            "evidence_ids": list(self.evidence_ids),
            "preference_dimensions": [item.to_dict() for item in self.preference_dimensions],
            "rating": self.rating,
            "review_count": self.review_count,
        }


@dataclass(frozen=True, slots=True)
class PersonalDealsResult:
    """Ranked personalized deals for a profile."""

    profile_id: str
    recommendations: tuple[PersonalRecommendation, ...]
    data_status: DataStatus = "mock"
    warnings: tuple[str, ...] = ()
    generated_at: datetime | None = None
    processing: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "recommendations": [item.to_dict() for item in self.recommendations],
            "data_status": self.data_status,
            "warnings": list(self.warnings),
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "processing": dict(self.processing),
        }


@dataclass(frozen=True, slots=True)
class PersonalDemoPayload:
    """Demo payload with active profile and top personalized deals."""

    active_profile: CustomerProfile
    profiles: tuple[CustomerProfile, ...]
    deals: PersonalDealsResult
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_profile": self.active_profile.to_dict(),
            "profiles": [item.to_dict() for item in self.profiles],
            "deals": self.deals.to_dict(),
            "limitations": list(self.limitations),
        }
