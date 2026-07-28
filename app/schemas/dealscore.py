"""DealScore API request and response schemas."""

from pydantic import BaseModel, Field


class DealScoreComponentsPayload(BaseModel):
    """Named DealScore component scores."""

    price_score: float
    seller_score: float
    shipping_score: float
    availability_score: float
    official_store_score: float
    warranty_score: float
    return_policy_score: float


class DealScorePayload(BaseModel):
    """Explainable DealScore for a single listing."""

    listing_id: str
    marketplace: str
    score: float
    rating: str
    rank: int
    total_cost: float
    components: DealScoreComponentsPayload
    explanation: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    applied_weights: dict[str, float] = Field(default_factory=dict)


class DealScoreListingPayload(BaseModel):
    """Listing fields returned alongside a DealScore ranking row."""

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
    """One ranked listing with its DealScore."""

    rank: int
    listing: DealScoreListingPayload
    deal_score: DealScorePayload


class DealScoreSearchResponse(BaseModel):
    """Ranked DealScore search response."""

    query: str
    currency: str
    market_average_total_cost: float
    recommended_listing_id: str | None = None
    results: list[DealScoreResultItem] = Field(default_factory=list)
