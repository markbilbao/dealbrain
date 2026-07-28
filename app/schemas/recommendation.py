"""Shopping recommendation API request and response schemas."""

from pydantic import BaseModel, Field

from app.schemas.dealscore import DealScoreResultItem


class AlternativeRecommendationPayload(BaseModel):
    """Alternate listing suggestion under a different buying priority."""

    listing_id: str
    label: str
    reason: str


class RecommendationPayload(BaseModel):
    """Explainable purchase recommendation."""

    decision: str
    recommended_listing_id: str | None = None
    headline: str
    summary: str
    reasoning: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float
    alternatives: list[AlternativeRecommendationPayload] = Field(default_factory=list)


class ShoppingRecommendationSearchResponse(BaseModel):
    """Shopping recommendation search response."""

    query: str
    currency: str
    recommendation: RecommendationPayload
    ranked_results: list[DealScoreResultItem] = Field(default_factory=list)
