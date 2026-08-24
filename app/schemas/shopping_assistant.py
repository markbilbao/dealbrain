"""AI Shopping Assistant API request and response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ShoppingAssistantQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    mode: Literal["economy", "balanced", "maximum"] | None = None
    conversation_id: str | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    use_cases: list[str] = Field(default_factory=list)
    category: str | None = None
    products: list[str] = Field(default_factory=list)
    profile_id: str | None = Field(default=None, max_length=128)
    user_id: str | None = Field(default=None, max_length=128)
    decision_id: str | None = Field(default=None, max_length=128)
    context_version: int | None = Field(default=None, ge=1)
    surface: Literal["results", "compare", "why"] | None = None


class EvidencePayload(BaseModel):
    type: str
    source_id: str
    description: str
    evidence_id: str | None = None
    product_id: str | None = None
    value: str | float | int | None = None


class RecommendationPayload(BaseModel):
    product_id: str
    product_name: str
    reason: str
    known_price: float | None = None
    currency: str = "PHP"
    marketplace: str | None = None
    deal_score: float | None = Field(default=None, title="PiqScore")
    confidence: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    rating: float | None = None
    review_count: int = 0


class ConfidencePayload(BaseModel):
    score: float
    band: str
    factors: list[str] = Field(default_factory=list)


class WarningPayload(BaseModel):
    message: str
    code: str | None = None


class CategoryWinnerPayload(BaseModel):
    category: str
    product_id: str
    product_name: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class ComparisonPayload(BaseModel):
    product_ids: list[str] = Field(default_factory=list)
    product_names: list[str] = Field(default_factory=list)
    category_winners: list[CategoryWinnerPayload] = Field(default_factory=list)
    strengths: dict[str, list[str]] = Field(default_factory=dict)
    weaknesses: dict[str, list[str]] = Field(default_factory=dict)
    price_difference: float | None = None
    currency: str | None = None
    review_differences: list[str] = Field(default_factory=list)
    recommended_use_case: str | None = None
    overall_recommendation: str = ""
    unresolved_uncertainty: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class DisagreementPayload(BaseModel):
    field: str
    providers: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    detail: str = ""


class ShoppingAssistantResponse(BaseModel):
    query: str
    intent: str
    answer: str
    top_recommendation: RecommendationPayload | None = None
    alternatives: list[RecommendationPayload] = Field(default_factory=list)
    evidence: list[EvidencePayload] = Field(default_factory=list)
    warnings: list[WarningPayload] = Field(default_factory=list)
    data_status: str = "mock"
    providers_used: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    confidence: ConfidencePayload
    mode: str = "economy"
    comparison: ComparisonPayload | None = None
    conversation_id: str | None = None
    disagreements: list[DisagreementPayload] = Field(default_factory=list)
    fallback_reason: str | None = None
    buy_now_or_wait: str | None = None
    processing: dict[str, Any] = Field(default_factory=dict)
    generated_at: str | None = None
    allowed_modes: list[str] = Field(default_factory=list)
    personal_recommendation: dict[str, Any] | None = None
    profile_id: str | None = None
    disclaimer: str = (
        "Shopping assistant answers are evidence-grounded over PiqSavi mock/imported "
        "data by default. External AI providers are disabled unless enabled server-side. "
        "The assistant cannot guarantee prices, authenticity, or future price changes. "
        "Personalization uses fixture profiles only when a profile_id is provided."
    )
    action: str | None = None
    answer_status: str | None = None
    decision_id: str | None = None
    session_best_piq_product_id: str | None = None
    original_best_piq_product_id: str | None = None
    recommendation_changed: bool | None = None
    requires_research_confirmation: bool | None = None
    research_proposal: dict[str, Any] | None = None


class ShoppingAssistantDemoMeta(BaseModel):
    example_queries: list[str] = Field(default_factory=list)
    allowed_modes: list[str] = Field(default_factory=list)
    data_status: str = "mock"
    ai_enabled: bool = False
