"""Marketplace Data Synchronization API schemas — Sprint 18."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MarketplaceSourcePayload(BaseModel):
    source_id: str
    name: str
    marketplace: str
    source_mode: str
    status: str
    connector_id: str | None = None
    description: str = ""
    simulated: bool = False
    label: str = ""


class MarketplaceSourceListResponse(BaseModel):
    sources: list[MarketplaceSourcePayload]
    count: int


class ConnectorCapabilityPayload(BaseModel):
    connector_id: str
    name: str
    marketplace: str
    source_mode: str
    capabilities: list[str]
    simulated: bool = False
    enabled: bool = True
    description: str = ""
    official: bool = False
    label: str = ""
    configuration: dict[str, Any] | None = None
    health: dict[str, Any] | None = None


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorCapabilityPayload]
    count: int


class ConnectorTestResponse(BaseModel):
    connector_id: str
    ok: bool
    message: str
    source_mode: str
    simulated: bool = False
    label: str = ""


class ConnectorHealthPayload(BaseModel):
    connector_id: str
    status: str
    last_attempted_sync: str | None = None
    last_successful_sync: str | None = None
    records_processed: int = 0
    records_failed: int = 0
    latency_ms: float | None = None
    rate_limit: dict[str, Any] | None = None
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)
    checkpoint: str | None = None
    consecutive_failures: int = 0
    message: str = ""


class ImportCreateRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, description="CSV or JSON text content")
    content_type: str | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)
    idempotency_key: str | None = None


class ImportBatchPayload(BaseModel):
    batch_id: str
    source_mode: str
    filename: str
    content_type: str
    status: str
    created_at: str
    completed_at: str | None = None
    records_total: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    records_duplicate: int = 0
    idempotency_key: str | None = None
    field_mapping: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    errors: list[str] = Field(default_factory=list)
    label: str = ""


class ImportErrorPayload(BaseModel):
    record_id: str
    row_number: int
    status: str
    errors: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class ImportErrorListResponse(BaseModel):
    batch_id: str
    errors: list[ImportErrorPayload]
    count: int


class SyncCreateRequest(BaseModel):
    connector_id: str = Field(..., min_length=1)
    mode: str = Field(default="full", pattern="^(full|incremental)$")
    idempotency_key: str | None = None
    query: str | None = None


class SyncJobPayload(BaseModel):
    job_id: str
    connector_id: str
    mode: str
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    cancel_requested: bool = False
    idempotency_key: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class SyncConflictPayload(BaseModel):
    conflict_id: str
    sync_job_id: str
    kind: str
    message: str
    offer_id: str | None = None
    product_id: str | None = None
    confidence: float | None = None
    reasons: list[str] = Field(default_factory=list)
    created_at: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncConflictListResponse(BaseModel):
    sync_job_id: str
    conflicts: list[SyncConflictPayload]
    count: int


class MarketplaceOfferPayload(BaseModel):
    offer_id: str
    product_id: str
    marketplace: str
    marketplace_product_id: str
    title: str
    currency: str
    regular_price: float | None = None
    sale_price: float | None = None
    shipping_cost: float = 0.0
    total_price: float
    availability: str
    inventory_quantity: int | None = None
    seller: dict[str, Any] | None = None
    marketplace_url: str | None = None
    image_url: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    sku: str | None = None
    source_mode: str
    provenance: dict[str, Any] | None = None
    freshness: dict[str, Any] | None = None
    confidence: float = 1.0
    matched_canonical_product_id: str | None = None
    match_confidence: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    match_ambiguity: str = "unmatched"
    observed_at: str | None = None
    simulated: bool = False
    label: str = ""


class MarketplaceOfferListResponse(BaseModel):
    offers: list[MarketplaceOfferPayload]
    count: int


class PriceHistoryListResponse(BaseModel):
    product_id: str
    snapshots: list[dict[str, Any]]
    count: int


class InventoryHistoryListResponse(BaseModel):
    product_id: str
    snapshots: list[dict[str, Any]]
    count: int


class MarketplaceDataDemoResponse(BaseModel):
    fixture_sync: dict[str, Any]
    simulated_live_sync: dict[str, Any]
    offers: int
    label: str
    source_mode_labels: dict[str, str]
