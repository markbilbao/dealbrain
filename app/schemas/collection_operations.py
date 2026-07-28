"""Collection Operations API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CollectionOpsJobCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    marketplaces: list[str] = Field(..., min_length=1)
    interval_minutes: int = Field(..., ge=1)
    enabled: bool = True
    scenario: str | None = None
    next_run_at: datetime | None = None


class CollectionOpsJobUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    query: str | None = Field(default=None, min_length=1)
    marketplaces: list[str] | None = Field(default=None, min_length=1)
    interval_minutes: int | None = Field(default=None, ge=1)
    enabled: bool | None = None
    scenario: str | None = None
    next_run_at: datetime | None = None


class CollectionOpsManualRunRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=1)
    override: bool = False


class RetryVisibilityPayload(BaseModel):
    attempt: int
    max_attempts: int
    delay_seconds: float
    next_retry_at: str | None = None
    final_failure_reason: str | None = None


class CollectionOpsJobPayload(BaseModel):
    job_id: str
    name: str
    query: str
    marketplaces: list[str]
    interval_minutes: int
    enabled: bool
    status: str
    next_run_at: str
    last_run_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failure_count: int = 0
    created_at: str
    updated_at: str
    scenario: str | None = None
    paused: bool = False
    running: bool = False


class CollectionOpsJobListResponse(BaseModel):
    jobs: list[CollectionOpsJobPayload] = Field(default_factory=list)


class CollectionOpsRunPayload(BaseModel):
    run_id: str
    job_id: str | None = None
    trigger: str
    started_at: str
    completed_at: str | None = None
    status: str
    marketplaces_attempted: list[str] = Field(default_factory=list)
    marketplaces_completed: list[str] = Field(default_factory=list)
    collected_count: int = 0
    stored_snapshot_count: int = 0
    skipped_count: int = 0
    failure_count: int = 0
    duration_ms: int | None = None
    error_summaries: list[str] = Field(default_factory=list)
    retry: RetryVisibilityPayload | None = None
    query: str | None = None
    idempotency_key: str | None = None
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Development collection uses mocked marketplace data. "
        "No live marketplace APIs are called."
    )


class CollectionOpsRunListResponse(BaseModel):
    runs: list[CollectionOpsRunPayload] = Field(default_factory=list)


class CollectionOpsRunDueResponse(BaseModel):
    runs: list[CollectionOpsRunPayload] = Field(default_factory=list)
    jobs_executed: int = 0


class CollectorAvailabilityPayload(BaseModel):
    marketplace: str
    available: bool


class CollectionOpsStatusPayload(BaseModel):
    total_jobs: int
    enabled_jobs: int
    paused_jobs: int
    jobs_currently_due: int
    jobs_with_recent_failures: int
    last_successful_collection: str | None = None
    last_failed_collection: str | None = None
    total_snapshots_collected: int
    scheduler_status: str
    collector_availability: list[CollectorAvailabilityPayload] = Field(default_factory=list)


class CollectionOpsHealthPayload(BaseModel):
    status: str
    subsystem: str
    running: bool
    detail: str


class CollectionOpsReadinessCheckPayload(BaseModel):
    name: str
    ready: bool
    detail: str


class CollectionOpsReadinessPayload(BaseModel):
    ready: bool
    status: str
    checks: list[CollectionOpsReadinessCheckPayload] = Field(default_factory=list)
