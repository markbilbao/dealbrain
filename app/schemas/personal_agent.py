"""Personal AI Shopping Agent API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreferenceDimensionPayload(BaseModel):
    dimension: str
    score: float
    weight: float
    weighted_score: float
    evidence: list[str] = Field(default_factory=list)


class CustomerProfilePayload(BaseModel):
    profile_id: str
    display_name: str
    persona: str
    budget: float | None = None
    currency: str = "PHP"
    country: str = "PH"
    preferred_marketplaces: list[str] = Field(default_factory=list)
    favorite_brands: list[str] = Field(default_factory=list)
    disliked_brands: list[str] = Field(default_factory=list)
    preferred_screen_sizes: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
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
    owned_products: list[str] = Field(default_factory=list)
    wishlist: list[str] = Field(default_factory=list)
    favorite_categories: list[str] = Field(default_factory=list)
    accessories_owned: list[str] = Field(default_factory=list)
    description: str = ""
    data_status: str = "mock"
    use_cases: list[str] = Field(default_factory=list)


class PersonalDealScorePayload(BaseModel):
    product_id: str
    profile_id: str
    personal_deal_score: float
    global_deal_score: float | None = None
    preference_fit: float
    budget_fit: float
    brand_affinity: float
    ownership_compatibility: float
    community_trust: float
    factors: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class BuyingAdvicePayload(BaseModel):
    product_id: str
    profile_id: str
    verdict: str
    label: str
    summary: str
    explanation: str
    evidence: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    personal_deal_score: float | None = None
    alternative_product_id: str | None = None
    alternative_product_name: str | None = None


class PersonalRecommendationPayload(BaseModel):
    product_id: str
    product_name: str
    profile_id: str
    reason: str
    explanation: str
    known_price: float | None = None
    currency: str = "PHP"
    marketplace: str | None = None
    personal_deal_score: float
    global_deal_score: float | None = None
    preference_score: float
    confidence: float
    advice: BuyingAdvicePayload | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    preference_dimensions: list[PreferenceDimensionPayload] = Field(default_factory=list)
    rating: float | None = None
    review_count: int = 0


class PersonalDealsResponse(BaseModel):
    profile_id: str
    recommendations: list[PersonalRecommendationPayload] = Field(default_factory=list)
    data_status: str = "mock"
    warnings: list[str] = Field(default_factory=list)
    generated_at: str | None = None
    processing: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Personalized deals use fixture customer profiles and DealBrain mock/imported "
        "catalog evidence. No login, purchase history, or payment data is used."
    )


class PersonalDemoResponse(BaseModel):
    active_profile: CustomerProfilePayload
    profiles: list[CustomerProfilePayload] = Field(default_factory=list)
    deals: PersonalDealsResponse
    limitations: list[str] = Field(default_factory=list)


class PersonalMetaResponse(BaseModel):
    enabled: bool = True
    default_profile_id: str
    profile_count: int = 0
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    data_status: str = "mock"
    authentication: bool = False
    cloud_sync: bool = False
    limitations: list[str] = Field(default_factory=list)
    preference_dimensions: list[str] = Field(default_factory=list)


class ProfileSwitchRequest(BaseModel):
    profile_id: str = Field(..., min_length=1, max_length=128)
