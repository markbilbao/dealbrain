"""Review & Rating Intelligence API request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewCollectRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    product_label: str | None = None
    marketplaces: list[str] | None = None


class ReviewSnapshotPayload(BaseModel):
    snapshot_id: str
    product_id: str
    product_label: str | None = None
    marketplace: str
    average_rating: float
    review_count: int
    five_star_count: int
    four_star_count: int
    three_star_count: int
    two_star_count: int
    one_star_count: int
    seller_rating: float | None = None
    seller_followers: int | None = None
    seller_products: int | None = None
    collected_at: str


class MarketplaceReviewPayload(BaseModel):
    marketplace: str
    rating: float
    reviews: int
    seller_rating: float | None = None
    seller_followers: int | None = None
    seller_products: int | None = None
    five_star_count: int = 0
    four_star_count: int = 0
    three_star_count: int = 0
    two_star_count: int = 0
    one_star_count: int = 0
    collected_at: str | None = None
    snapshot_id: str | None = None


class ReviewCollectResponse(BaseModel):
    product_id: str
    product: str
    snapshots: list[ReviewSnapshotPayload] = Field(default_factory=list)
    collected_count: int = 0
    collected_at: str
    overall_rating: float | None = None
    total_review_count: int = 0
    disclaimer: str = (
        "Mock collectors only — no live scraping, HTTP requests, or browser automation."
    )


class ReviewLatestResponse(BaseModel):
    product_id: str
    product: str
    overall_rating: float | None = None
    total_review_count: int = 0
    marketplaces: list[MarketplaceReviewPayload] = Field(default_factory=list)


class ReviewHistoryResponse(BaseModel):
    product_id: str
    product: str
    snapshots: list[ReviewSnapshotPayload] = Field(default_factory=list)
    count: int = 0


class ReviewCompareResponse(BaseModel):
    product: str
    product_id: str
    overall_rating: float | None = None
    total_review_count: int = 0
    marketplaces: list[MarketplaceReviewPayload] = Field(default_factory=list)
