"""AI Review Summary API request and response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReviewInsightPayload(BaseModel):
    theme: str
    label: str
    polarity: str
    frequency: int


class EvidenceClaimPayload(BaseModel):
    claim: str
    evidence_review_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class EvidenceBundlePayload(BaseModel):
    pros: list[EvidenceClaimPayload] = Field(default_factory=list)
    cons: list[EvidenceClaimPayload] = Field(default_factory=list)
    warnings: list[EvidenceClaimPayload] = Field(default_factory=list)


class DisagreementPayload(BaseModel):
    field: str
    providers: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    detail: str = ""


class ReviewSummaryResponse(BaseModel):
    product: str
    product_id: str
    overall_sentiment: str
    summary: str
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: str
    average_rating: float | None = None
    total_review_count: int = 0
    insights: list[ReviewInsightPayload] = Field(default_factory=list)
    provider: str = "deterministic-mock"
    summary_id: str | None = None
    generated_at: str | None = None
    # Multi-model metadata
    mode: str = "economy"
    providers_used: list[str] = Field(default_factory=list)
    models_used: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: str | None = None
    agreement_score: float | None = None
    consensus_confidence: float | None = None
    disagreements: list[DisagreementPayload] = Field(default_factory=list)
    evidence: EvidenceBundlePayload = Field(default_factory=EvidenceBundlePayload)
    processing: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Review analysis uses a provider-neutral architecture. External AI "
        "providers are disabled by default; deterministic fallback is always "
        "available. Outputs can be inaccurate and must remain evidence-grounded."
    )
