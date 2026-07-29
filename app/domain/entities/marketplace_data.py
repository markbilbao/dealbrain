"""Marketplace Data Synchronization domain entities — Sprint 18.

Provider-neutral models for connectors, imports, normalization, sync,
freshness, and provenance. Fixture and imported data must never be labeled live.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SourceMode(StrEnum):
    """How marketplace data was obtained.

    ``FIXTURE`` — deterministic demo/canned data.
    ``IMPORTED`` — structured file import (CSV/JSON).
    ``LIVE`` — returned by a configured live connector (never inferred from recency).
    """

    FIXTURE = "fixture"
    IMPORTED = "imported"
    LIVE = "live"


class SourceStatus(StrEnum):
    """Operational status of a marketplace source."""

    ACTIVE = "active"
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"
    ERROR = "error"


class ConnectorCapability(StrEnum):
    """Capabilities a marketplace connector may declare."""

    VALIDATE_CONFIGURATION = "validate_configuration"
    TEST_CONNECTION = "test_connection"
    FETCH_PRODUCTS = "fetch_products"
    FETCH_PRODUCT = "fetch_product"
    FETCH_OFFERS = "fetch_offers"
    FETCH_PRICES = "fetch_prices"
    FETCH_INVENTORY = "fetch_inventory"
    FETCH_SELLERS = "fetch_sellers"
    FETCH_REVIEWS = "fetch_reviews"
    CONTINUE_FROM_CHECKPOINT = "continue_from_checkpoint"
    REPORT_RATE_LIMIT = "report_rate_limit"
    REPORT_HEALTH = "report_health"


class ConnectorHealthStatus(StrEnum):
    """Connector health classification."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"


class FreshnessStatus(StrEnum):
    """Data freshness classification."""

    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class ProductAvailability(StrEnum):
    """Normalized product availability."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED = "limited"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class SyncJobStatus(StrEnum):
    """Synchronization job lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncMode(StrEnum):
    """Full vs incremental synchronization."""

    FULL = "full"
    INCREMENTAL = "incremental"


class ImportBatchStatus(StrEnum):
    """Import batch lifecycle."""

    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


class MatchAmbiguityStatus(StrEnum):
    """Product match ambiguity classification."""

    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    CONFLICT = "conflict"


class SyncConflictKind(StrEnum):
    """Kinds of sync/matching conflicts requiring review."""

    AMBIGUOUS_MATCH = "ambiguous_match"
    LOW_CONFIDENCE_MATCH = "low_confidence_match"
    FIELD_CONFLICT = "field_conflict"
    DUPLICATE_OFFER = "duplicate_offer"
    VALIDATION_FAILURE = "validation_failure"


SOURCE_MODE_LABELS: dict[SourceMode, str] = {
    SourceMode.FIXTURE: "Demo / fixture data — not live marketplace pricing",
    SourceMode.IMPORTED: "Imported data — not live marketplace pricing",
    SourceMode.LIVE: "Live connector data",
}

SIMULATED_LIVE_LABEL = "SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION"


@dataclass(frozen=True, slots=True)
class ConnectorCredentialReference:
    """Opaque reference to a credential — never stores secret values."""

    reference_id: str
    provider: str
    label: str
    configured: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "provider": self.provider,
            "label": self.label,
            "configured": self.configured,
            # Secrets are never serialized.
        }


@dataclass(frozen=True, slots=True)
class ConnectorConfiguration:
    """Non-secret connector configuration."""

    connector_id: str
    marketplace: str
    enabled: bool = True
    base_url: str | None = None
    region: str | None = None
    request_timeout_seconds: float = 15.0
    max_page_size: int = 50
    freshness_fresh_hours: float = 6.0
    freshness_aging_hours: float = 24.0
    freshness_stale_hours: float = 72.0
    credential_reference: ConnectorCredentialReference | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, redact: bool = True) -> dict[str, Any]:
        options = dict(self.options)
        if redact:
            for key in list(options):
                lowered = key.lower()
                if any(
                    token in lowered for token in ("secret", "password", "token", "key", "auth")
                ):
                    options[key] = "***REDACTED***"
        return {
            "connector_id": self.connector_id,
            "marketplace": self.marketplace,
            "enabled": self.enabled,
            "base_url": self.base_url,
            "region": self.region,
            "request_timeout_seconds": self.request_timeout_seconds,
            "max_page_size": self.max_page_size,
            "freshness_fresh_hours": self.freshness_fresh_hours,
            "freshness_aging_hours": self.freshness_aging_hours,
            "freshness_stale_hours": self.freshness_stale_hours,
            "credential_reference": (
                self.credential_reference.to_dict() if self.credential_reference else None
            ),
            "options": options,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceSource:
    """A configured marketplace data source with explicit mode."""

    source_id: str
    name: str
    marketplace: str
    source_mode: SourceMode
    status: SourceStatus
    connector_id: str | None = None
    description: str = ""
    simulated: bool = False
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        label = self.label or SOURCE_MODE_LABELS.get(self.source_mode, self.source_mode.value)
        if self.simulated:
            label = SIMULATED_LIVE_LABEL
        return {
            "source_id": self.source_id,
            "name": self.name,
            "marketplace": self.marketplace,
            "source_mode": self.source_mode.value,
            "status": self.status.value,
            "connector_id": self.connector_id,
            "description": self.description,
            "simulated": self.simulated,
            "label": label,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceConnectorInfo:
    """Public connector metadata (capabilities + mode)."""

    connector_id: str
    name: str
    marketplace: str
    source_mode: SourceMode
    capabilities: tuple[ConnectorCapability, ...]
    simulated: bool = False
    enabled: bool = True
    description: str = ""
    official: bool = False

    def to_dict(self) -> dict[str, Any]:
        label = SOURCE_MODE_LABELS.get(self.source_mode, self.source_mode.value)
        if self.simulated:
            label = SIMULATED_LIVE_LABEL
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "marketplace": self.marketplace,
            "source_mode": self.source_mode.value,
            "capabilities": [c.value for c in self.capabilities],
            "simulated": self.simulated,
            "enabled": self.enabled,
            "description": self.description,
            "official": self.official,
            "label": label,
        }


@dataclass(frozen=True, slots=True)
class ConnectorRateLimit:
    """Rate-limit state reported by a connector."""

    limited: bool
    remaining: int | None = None
    reset_at: datetime | None = None
    retry_after_seconds: float | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "limited": self.limited,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
            "retry_after_seconds": self.retry_after_seconds,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ConnectorError:
    """Explainable connector error."""

    code: str
    message: str
    retryable: bool = False
    observed_at: datetime | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    """Connector health snapshot."""

    connector_id: str
    status: ConnectorHealthStatus
    last_attempted_sync: datetime | None = None
    last_successful_sync: datetime | None = None
    records_processed: int = 0
    records_failed: int = 0
    latency_ms: float | None = None
    rate_limit: ConnectorRateLimit | None = None
    recent_errors: tuple[ConnectorError, ...] = ()
    checkpoint: str | None = None
    consecutive_failures: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "status": self.status.value,
            "last_attempted_sync": (
                self.last_attempted_sync.isoformat() if self.last_attempted_sync else None
            ),
            "last_successful_sync": (
                self.last_successful_sync.isoformat() if self.last_successful_sync else None
            ),
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "latency_ms": self.latency_ms,
            "rate_limit": self.rate_limit.to_dict() if self.rate_limit else None,
            "recent_errors": [e.to_dict() for e in self.recent_errors],
            "checkpoint": self.checkpoint,
            "consecutive_failures": self.consecutive_failures,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ConnectorRun:
    """Single connector fetch/sync attempt."""

    run_id: str
    connector_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: SyncJobStatus = SyncJobStatus.PENDING
    records_fetched: int = 0
    records_failed: int = 0
    checkpoint: str | None = None
    errors: tuple[ConnectorError, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "connector_id": self.connector_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "records_fetched": self.records_fetched,
            "records_failed": self.records_failed,
            "checkpoint": self.checkpoint,
            "errors": [e.to_dict() for e in self.errors],
        }


@dataclass(frozen=True, slots=True)
class DataProvenance:
    """Traceability for a marketplace record through the pipeline."""

    source_mode: SourceMode
    source_id: str
    connector_id: str | None = None
    import_batch_id: str | None = None
    raw_record_id: str | None = None
    observed_at: datetime | None = None
    source_timestamp: datetime | None = None
    ingested_at: datetime | None = None
    confidence: float = 1.0
    notes: str = ""
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        label = SOURCE_MODE_LABELS.get(self.source_mode, self.source_mode.value)
        if self.simulated:
            label = SIMULATED_LIVE_LABEL
        return {
            "source_mode": self.source_mode.value,
            "source_id": self.source_id,
            "connector_id": self.connector_id,
            "import_batch_id": self.import_batch_id,
            "raw_record_id": self.raw_record_id,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
            "confidence": self.confidence,
            "notes": self.notes,
            "simulated": self.simulated,
            "label": label,
        }


@dataclass(frozen=True, slots=True)
class DataFreshness:
    """Freshness assessment for an offer or product observation."""

    status: FreshnessStatus
    source_mode: SourceMode
    last_successful_observation: datetime | None = None
    source_timestamp: datetime | None = None
    ingestion_timestamp: datetime | None = None
    age_hours: float | None = None
    connector_healthy: bool | None = None
    warning: str | None = None
    is_current_live_price: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "source_mode": self.source_mode.value,
            "last_successful_observation": (
                self.last_successful_observation.isoformat()
                if self.last_successful_observation
                else None
            ),
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "ingestion_timestamp": (
                self.ingestion_timestamp.isoformat() if self.ingestion_timestamp else None
            ),
            "age_hours": self.age_hours,
            "connector_healthy": self.connector_healthy,
            "warning": self.warning,
            "is_current_live_price": self.is_current_live_price,
        }


@dataclass(frozen=True, slots=True)
class RawMarketplaceRecord:
    """Preserved raw marketplace payload for traceability."""

    record_id: str
    source_mode: SourceMode
    source_id: str
    marketplace: str
    payload: dict[str, Any]
    ingested_at: datetime
    connector_id: str | None = None
    import_batch_id: str | None = None
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "source_mode": self.source_mode.value,
            "source_id": self.source_id,
            "marketplace": self.marketplace,
            "payload": dict(self.payload),
            "ingested_at": self.ingested_at.isoformat(),
            "connector_id": self.connector_id,
            "import_batch_id": self.import_batch_id,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceSeller:
    """Normalized seller identity."""

    seller_id: str
    name: str
    marketplace: str
    rating: float | None = None
    review_count: int | None = None
    url: str | None = None
    source_mode: SourceMode = SourceMode.FIXTURE

    def to_dict(self) -> dict[str, Any]:
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "marketplace": self.marketplace,
            "rating": self.rating,
            "review_count": self.review_count,
            "url": self.url,
            "source_mode": self.source_mode.value,
        }


@dataclass(frozen=True, slots=True)
class NormalizedMarketplaceProduct:
    """Canonical normalized product fields from a marketplace record."""

    product_id: str
    marketplace_product_id: str
    marketplace: str
    title: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    description: str | None = None
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    image_url: str | None = None
    marketplace_url: str | None = None
    condition: str | None = None
    warranty: str | None = None
    source_mode: SourceMode = SourceMode.FIXTURE
    provenance: DataProvenance | None = None
    freshness: DataFreshness | None = None
    confidence: float = 1.0
    raw_record_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "marketplace_product_id": self.marketplace_product_id,
            "marketplace": self.marketplace,
            "title": self.title,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "description": self.description,
            "sku": self.sku,
            "upc": self.upc,
            "ean": self.ean,
            "gtin": self.gtin,
            "image_url": self.image_url,
            "marketplace_url": self.marketplace_url,
            "condition": self.condition,
            "warranty": self.warranty,
            "source_mode": self.source_mode.value,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "confidence": self.confidence,
            "raw_record_id": self.raw_record_id,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceOffer:
    """Normalized marketplace offer with pricing and provenance."""

    offer_id: str
    product_id: str
    marketplace: str
    marketplace_product_id: str
    title: str
    currency: str
    regular_price: float | None
    sale_price: float | None
    shipping_cost: float
    total_price: float
    availability: ProductAvailability
    inventory_quantity: int | None = None
    seller: MarketplaceSeller | None = None
    marketplace_url: str | None = None
    image_url: str | None = None
    condition: str | None = None
    warranty: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    sku: str | None = None
    source_mode: SourceMode = SourceMode.FIXTURE
    provenance: DataProvenance | None = None
    freshness: DataFreshness | None = None
    confidence: float = 1.0
    matched_canonical_product_id: str | None = None
    match_confidence: float | None = None
    match_reasons: tuple[str, ...] = ()
    match_ambiguity: MatchAmbiguityStatus = MatchAmbiguityStatus.UNMATCHED
    observed_at: datetime | None = None
    raw_record_id: str | None = None
    simulated: bool = False

    def to_dict(self) -> dict[str, Any]:
        label = SOURCE_MODE_LABELS.get(self.source_mode, self.source_mode.value)
        if self.simulated:
            label = SIMULATED_LIVE_LABEL
        return {
            "offer_id": self.offer_id,
            "product_id": self.product_id,
            "marketplace": self.marketplace,
            "marketplace_product_id": self.marketplace_product_id,
            "title": self.title,
            "currency": self.currency,
            "regular_price": self.regular_price,
            "sale_price": self.sale_price,
            "shipping_cost": self.shipping_cost,
            "total_price": self.total_price,
            "availability": self.availability.value,
            "inventory_quantity": self.inventory_quantity,
            "seller": self.seller.to_dict() if self.seller else None,
            "marketplace_url": self.marketplace_url,
            "image_url": self.image_url,
            "condition": self.condition,
            "warranty": self.warranty,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "sku": self.sku,
            "source_mode": self.source_mode.value,
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "confidence": self.confidence,
            "matched_canonical_product_id": self.matched_canonical_product_id,
            "match_confidence": self.match_confidence,
            "match_reasons": list(self.match_reasons),
            "match_ambiguity": self.match_ambiguity.value,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "raw_record_id": self.raw_record_id,
            "simulated": self.simulated,
            "label": label,
        }


@dataclass(frozen=True, slots=True)
class MarketplacePriceSnapshot:
    """Price observation with provenance (distinct from Price History snapshots)."""

    snapshot_id: str
    product_id: str
    offer_id: str
    marketplace: str
    currency: str
    item_price: float
    shipping_cost: float
    total_price: float
    availability: ProductAvailability
    observed_at: datetime
    source_timestamp: datetime | None
    ingested_at: datetime
    source_mode: SourceMode
    seller_name: str | None = None
    provenance: DataProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "product_id": self.product_id,
            "offer_id": self.offer_id,
            "marketplace": self.marketplace,
            "currency": self.currency,
            "item_price": self.item_price,
            "shipping_cost": self.shipping_cost,
            "total_price": self.total_price,
            "availability": self.availability.value,
            "observed_at": self.observed_at.isoformat(),
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "ingested_at": self.ingested_at.isoformat(),
            "source_mode": self.source_mode.value,
            "seller_name": self.seller_name,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


@dataclass(frozen=True, slots=True)
class InventorySnapshot:
    """Inventory / availability observation."""

    snapshot_id: str
    product_id: str
    offer_id: str
    marketplace: str
    availability: ProductAvailability
    quantity: int | None
    observed_at: datetime
    source_timestamp: datetime | None
    ingested_at: datetime
    source_mode: SourceMode
    seller_name: str | None = None
    provenance: DataProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "product_id": self.product_id,
            "offer_id": self.offer_id,
            "marketplace": self.marketplace,
            "availability": self.availability.value,
            "quantity": self.quantity,
            "observed_at": self.observed_at.isoformat(),
            "source_timestamp": (
                self.source_timestamp.isoformat() if self.source_timestamp else None
            ),
            "ingested_at": self.ingested_at.isoformat(),
            "source_mode": self.source_mode.value,
            "seller_name": self.seller_name,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }


@dataclass(frozen=True, slots=True)
class ImportRecord:
    """Single row/record within an import batch."""

    record_id: str
    row_number: int
    status: str
    payload: dict[str, Any]
    errors: tuple[str, ...] = ()
    offer_id: str | None = None
    content_hash: str = ""
    duplicate_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "row_number": self.row_number,
            "status": self.status,
            "payload": dict(self.payload),
            "errors": list(self.errors),
            "offer_id": self.offer_id,
            "content_hash": self.content_hash,
            "duplicate_of": self.duplicate_of,
        }


@dataclass(frozen=True, slots=True)
class ImportBatch:
    """Structured product import batch (CSV/JSON)."""

    batch_id: str
    source_mode: SourceMode
    filename: str
    content_type: str
    status: ImportBatchStatus
    created_at: datetime
    completed_at: datetime | None = None
    records_total: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    records_duplicate: int = 0
    idempotency_key: str | None = None
    field_mapping: dict[str, str] = field(default_factory=dict)
    summary: str = ""
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "source_mode": self.source_mode.value,
            "filename": self.filename,
            "content_type": self.content_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_total": self.records_total,
            "records_accepted": self.records_accepted,
            "records_rejected": self.records_rejected,
            "records_duplicate": self.records_duplicate,
            "idempotency_key": self.idempotency_key,
            "field_mapping": dict(self.field_mapping),
            "summary": self.summary,
            "errors": list(self.errors),
            "label": SOURCE_MODE_LABELS[SourceMode.IMPORTED],
        }


@dataclass(frozen=True, slots=True)
class SyncCheckpoint:
    """Connector sync checkpoint for incremental continuation."""

    connector_id: str
    cursor: str
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "cursor": self.cursor,
            "updated_at": self.updated_at.isoformat(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class SyncConflict:
    """Conflict or review item from sync/matching."""

    conflict_id: str
    sync_job_id: str
    kind: SyncConflictKind
    message: str
    offer_id: str | None = None
    product_id: str | None = None
    confidence: float | None = None
    reasons: tuple[str, ...] = ()
    created_at: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "sync_job_id": self.sync_job_id,
            "kind": self.kind.value,
            "message": self.message,
            "offer_id": self.offer_id,
            "product_id": self.product_id,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Outcome summary for a sync job."""

    records_fetched: int = 0
    records_normalized: int = 0
    records_written: int = 0
    records_failed: int = 0
    records_duplicate: int = 0
    conflicts: int = 0
    dead_lettered: int = 0
    checkpoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "records_fetched": self.records_fetched,
            "records_normalized": self.records_normalized,
            "records_written": self.records_written,
            "records_failed": self.records_failed,
            "records_duplicate": self.records_duplicate,
            "conflicts": self.conflicts,
            "dead_lettered": self.dead_lettered,
            "checkpoint": self.checkpoint,
        }


@dataclass(frozen=True, slots=True)
class SyncJob:
    """Scheduler-neutral synchronization job."""

    job_id: str
    connector_id: str
    mode: SyncMode
    status: SyncJobStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: SyncResult | None = None
    cancel_requested: bool = False
    idempotency_key: str | None = None
    errors: tuple[ConnectorError, ...] = ()
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "connector_id": self.connector_id,
            "mode": self.mode.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
            "cancel_requested": self.cancel_requested,
            "idempotency_key": self.idempotency_key,
            "errors": [e.to_dict() for e in self.errors],
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ProductMatchDecision:
    """Deterministic product match outcome — never silently merges uncertain rows."""

    matched_product_id: str | None
    confidence: float
    reasons: tuple[str, ...]
    ambiguity: MatchAmbiguityStatus
    candidate_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_product_id": self.matched_product_id,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "ambiguity": self.ambiguity.value,
            "candidate_ids": list(self.candidate_ids),
        }


@dataclass(frozen=True, slots=True)
class DeadLetterRecord:
    """Failed record retained for later inspection (architecture only)."""

    record_id: str
    sync_job_id: str
    reason: str
    payload: dict[str, Any]
    created_at: datetime
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "sync_job_id": self.sync_job_id,
            "reason": self.reason,
            "payload": dict(self.payload),
            "created_at": self.created_at.isoformat(),
            "retryable": self.retryable,
        }


def source_mode_to_data_status(mode: SourceMode) -> str:
    """Map SourceMode onto existing Shopping Assistant ``data_status`` values."""
    if mode == SourceMode.LIVE:
        return "live"
    if mode == SourceMode.IMPORTED:
        return "imported"
    return "mock"
