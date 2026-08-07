"""Price History API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class PriceSnapshotCreate(BaseModel):
    """Request body for recording a single price snapshot."""

    canonical_product_id: str = Field(..., min_length=1)
    marketplace: str = Field(..., min_length=1)
    listing_id: str = Field(..., min_length=1)
    currency: str = Field(..., min_length=1, max_length=8)
    item_price: float
    shipping_cost: float = 0.0
    availability: str = "unknown"
    observed_at: datetime
    seller_name: str | None = None
    snapshot_id: str | None = None


class PriceSnapshotsCreateRequest(BaseModel):
    """Request body for recording one or more snapshots."""

    snapshots: list[PriceSnapshotCreate] = Field(..., min_length=1)


class PriceSnapshotPayload(BaseModel):
    """Serialized price snapshot."""

    snapshot_id: str
    canonical_product_id: str
    marketplace: str
    listing_id: str
    seller_name: str | None = None
    currency: str
    item_price: float
    shipping_cost: float
    total_cost: float
    availability: str
    observed_at: datetime


class PriceStatisticsPayload(BaseModel):
    """Aggregate statistics from available PiqSavi history."""

    current_total_cost: float
    lowest_recorded_total_cost: float
    highest_recorded_total_cost: float
    average_total_cost: float
    median_total_cost: float
    observation_count: int
    first_observed: datetime
    last_observed: datetime
    absolute_change: float
    percentage_change: float
    trend: str


class MarketplacePriceSummaryPayload(BaseModel):
    """Per-marketplace rollup from stored observations."""

    marketplace: str
    latest_total_cost: float
    lowest_recorded_total_cost: float
    average_total_cost: float
    observation_count: int
    latest_availability: str
    last_observed: datetime


class PriceSnapshotsCreateResponse(BaseModel):
    """Response after recording snapshots."""

    saved: list[PriceSnapshotPayload]


class PriceHistoryResponse(BaseModel):
    """Product or listing price history response."""

    canonical_product_id: str | None = None
    listing_id: str | None = None
    currency: str
    statistics: PriceStatisticsPayload | None = None
    history: list[PriceSnapshotPayload] = Field(default_factory=list)
    marketplace_summaries: list[MarketplacePriceSummaryPayload] = Field(default_factory=list)
    disclaimer: str = (
        "Lowest recorded price in the available PiqSavi history. "
        "Statistics use only stored observations."
    )


class PriceHistorySearchResponse(BaseModel):
    """Search + record response for price history."""

    query: str
    currency: str
    statistics: PriceStatisticsPayload | None = None
    history: list[PriceSnapshotPayload] = Field(default_factory=list)
    marketplace_summaries: list[MarketplacePriceSummaryPayload] = Field(default_factory=list)
    canonical_product_id: str | None = None
    disclaimer: str = (
        "Lowest recorded price in the available PiqSavi history. "
        "Statistics use only stored observations."
    )
    development_note: str | None = None
