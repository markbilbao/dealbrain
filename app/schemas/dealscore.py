"""DealScore API request and response schemas.

Machine contract identifiers retain DealScore/deal_score naming. Human-readable
OpenAPI descriptions present the public feature name PiqScore.
"""

from pydantic import BaseModel, Field


class DealScoreComponentsPayload(BaseModel):
    """Named PiqScore component scores."""

    price_score: float
    seller_score: float
    shipping_score: float
    availability_score: float
    official_store_score: float
    warranty_score: float
    return_policy_score: float


class DealScorePayload(BaseModel):
    """Explainable PiqScore for a single listing."""

    listing_id: str
    marketplace: str
    score: float = Field(title="PiqScore")
    rating: str
    rank: int
    total_cost: float
    components: DealScoreComponentsPayload
    explanation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    applied_weights: dict[str, float] = Field(default_factory=dict)


class DealScoreListingPayload(BaseModel):
    """Listing fields returned alongside a PiqScore ranking row."""

    marketplace: str
    product_id: str
    title: str
    price: float
    currency: str
    seller: str
    rating: float | None = None
    url: str
    availability: str
    shipping_cost: float | None = None
    is_official_store: bool | None = None
    warranty_months: int | None = None
    return_policy_days: int | None = None
    total_cost: float | None = None


class DealScoreResultItem(BaseModel):
    """One ranked listing with its PiqScore."""

    rank: int
    listing: DealScoreListingPayload
    deal_score: DealScorePayload = Field(title="PiqScore")


class DealScoreSearchResponse(BaseModel):
    """Ranked PiqScore search response."""

    query: str
    currency: str
    market_average_total_cost: float
    recommended_listing_id: str | None = None
    results: list[DealScoreResultItem] = Field(default_factory=list)
