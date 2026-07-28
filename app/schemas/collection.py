"""Marketplace Collection API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CollectionRunRequest(BaseModel):
    """Manual collection run inputs."""

    query: str = Field(..., min_length=1)
    marketplaces: list[str] = Field(default_factory=list)
    observed_at: datetime | None = None
    scenario: str | None = None


class CollectionJobCreateRequest(BaseModel):
    """Create a scheduled collection job."""

    query: str = Field(..., min_length=1)
    marketplaces: list[str] = Field(..., min_length=1)
    interval_seconds: int = Field(..., gt=0)
    enabled: bool = True
    scenario: str | None = None
    next_run_at: datetime | None = None


class CollectionFailurePayload(BaseModel):
    marketplace: str
    code: str
    message: str
    retryable: bool = False
    listing_id: str | None = None


class CollectedListingPayload(BaseModel):
    marketplace: str
    product_id: str
    title: str
    price: float
    currency: str
    seller: str
    rating: float | None = None
    url: str
    availability: str
    source_marketplace: str
    collected_at: str
    is_duplicate: bool = False


class CollectionResultPayload(BaseModel):
    run_id: str
    marketplace: str
    query: str
    target_id: str | None = None
    started_at: str
    completed_at: str
    listing_count: int
    successful_listing_count: int
    failed_listing_count: int
    listings: list[CollectedListingPayload] = Field(default_factory=list)
    errors: list[CollectionFailurePayload] = Field(default_factory=list)
    status: str
    warnings: list[str] = Field(default_factory=list)


class CollectionRunPayload(BaseModel):
    run_id: str
    query: str
    marketplaces: list[str]
    status: str
    started_at: str
    completed_at: str | None = None
    observed_at: str | None = None
    job_id: str | None = None
    collected_count: int
    stored_snapshot_count: int
    skipped_count: int
    failure_count: int
    duration_seconds: float | None = None
    marketplaces_attempted: list[str] = Field(default_factory=list)
    marketplaces_completed: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    results: list[CollectionResultPayload] = Field(default_factory=list)
    disclaimer: str = (
        "Development collection uses mocked marketplace data. "
        "No live marketplace APIs are called."
    )


class CollectionRunListResponse(BaseModel):
    runs: list[CollectionRunPayload] = Field(default_factory=list)


class CollectionJobPayload(BaseModel):
    job_id: str
    query: str
    marketplaces: list[str]
    interval_seconds: int
    enabled: bool
    created_at: str
    next_run_at: str
    last_run_at: str | None = None
    scenario: str | None = None
    running: bool = False


class CollectionJobListResponse(BaseModel):
    jobs: list[CollectionJobPayload] = Field(default_factory=list)


class CollectionRunDueResponse(BaseModel):
    runs: list[CollectionRunPayload] = Field(default_factory=list)
    jobs_executed: int = 0
