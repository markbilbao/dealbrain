"""Marketplace collection domain entities and value objects.

Identifiers and timestamps are injected by callers — core types never generate
random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.domain.entities.marketplace_listing import MarketplaceListing


class CollectionStatus(StrEnum):
    """Lifecycle status for collection jobs, runs, and per-marketplace results."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class CollectionTarget:
    """What a collector should gather for one marketplace invocation."""

    query: str
    marketplace: str | None = None
    target_id: str | None = None
    scenario: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "marketplace": self.marketplace,
            "target_id": self.target_id,
            "scenario": self.scenario,
        }


@dataclass(frozen=True, slots=True)
class CollectedListing:
    """A normalized listing produced by a marketplace collector."""

    listing: MarketplaceListing
    source_marketplace: str
    collected_at: datetime
    is_duplicate: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = self.listing.to_dict()
        payload.update(
            {
                "source_marketplace": self.source_marketplace,
                "collected_at": self.collected_at.isoformat(),
                "is_duplicate": self.is_duplicate,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class CollectionFailure:
    """Explainable failure captured during collection."""

    marketplace: str
    code: str
    message: str
    retryable: bool = False
    listing_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "marketplace": self.marketplace,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "listing_id": self.listing_id,
        }


@dataclass(frozen=True, slots=True)
class CollectionResult:
    """Outcome of collecting from a single marketplace for one target."""

    run_id: str
    marketplace: str
    query: str
    target_id: str | None
    started_at: datetime
    completed_at: datetime
    listing_count: int
    successful_listing_count: int
    failed_listing_count: int
    listings: tuple[CollectedListing, ...] = ()
    errors: tuple[CollectionFailure, ...] = ()
    status: CollectionStatus = CollectionStatus.COMPLETED
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "marketplace": self.marketplace,
            "query": self.query,
            "target_id": self.target_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "listing_count": self.listing_count,
            "successful_listing_count": self.successful_listing_count,
            "failed_listing_count": self.failed_listing_count,
            "listings": [item.to_dict() for item in self.listings],
            "errors": [error.to_dict() for error in self.errors],
            "status": self.status.value,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CollectionRun:
    """Aggregated multi-marketplace collection run with snapshot accounting."""

    run_id: str
    query: str
    marketplaces: tuple[str, ...]
    status: CollectionStatus
    started_at: datetime
    completed_at: datetime | None
    results: tuple[CollectionResult, ...] = ()
    stored_snapshot_count: int = 0
    skipped_count: int = 0
    failure_count: int = 0
    warnings: tuple[str, ...] = ()
    observed_at: datetime | None = None
    job_id: str | None = None

    @property
    def collected_count(self) -> int:
        return sum(result.successful_listing_count for result in self.results)

    @property
    def marketplaces_attempted(self) -> tuple[str, ...]:
        return self.marketplaces

    @property
    def marketplaces_completed(self) -> tuple[str, ...]:
        return tuple(
            result.marketplace
            for result in self.results
            if result.status
            in {CollectionStatus.COMPLETED, CollectionStatus.PARTIALLY_COMPLETED}
        )

    def duration_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def to_summary_dict(self) -> dict[str, Any]:
        """Structured summary suitable for logging (no raw payloads)."""
        return {
            "run_id": self.run_id,
            "query": self.query,
            "marketplaces_attempted": list(self.marketplaces_attempted),
            "marketplaces_completed": list(self.marketplaces_completed),
            "duration_seconds": self.duration_seconds(),
            "collected_count": self.collected_count,
            "stored_snapshot_count": self.stored_snapshot_count,
            "skipped_count": self.skipped_count,
            "failure_count": self.failure_count,
            "status": self.status.value,
            "job_id": self.job_id,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.to_summary_dict()
        payload.update(
            {
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "observed_at": self.observed_at.isoformat() if self.observed_at else None,
                "results": [result.to_dict() for result in self.results],
                "warnings": list(self.warnings),
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class CollectionJob:
    """Scheduled collection job definition with deterministic run metadata."""

    job_id: str
    query: str
    marketplaces: tuple[str, ...]
    interval_seconds: int
    enabled: bool
    created_at: datetime
    next_run_at: datetime
    last_run_at: datetime | None = None
    scenario: str | None = None
    running: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "query": self.query,
            "marketplaces": list(self.marketplaces),
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "next_run_at": self.next_run_at.isoformat(),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "scenario": self.scenario,
            "running": self.running,
        }
