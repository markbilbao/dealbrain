"""Marketplace Intelligence API request and response schemas."""

from pydantic import BaseModel, Field


class MarketplaceListingPayload(BaseModel):
    """A single normalized listing from one marketplace."""

    marketplace: str
    title: str
    price: float
    currency: str
    seller: str
    rating: float | None = None
    url: str


class MarketplaceSearchResponse(BaseModel):
    """Aggregated marketplace search result."""

    query: str
    results: list[MarketplaceListingPayload] = Field(default_factory=list)
