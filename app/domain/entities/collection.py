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


class CollectionJobStatus(StrEnum):
    """Operational status for a managed collection job."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    RUNNING = "running"


class CollectionTriggerType(StrEnum):
    """How a collection run was started."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    RETRY = "retry"


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
class RetryVisibility:
    """Retry metadata exposed without sleeping or background waiting."""

    attempt: int
    max_attempts: int
    delay_seconds: float
    next_retry_at: datetime | None = None
    final_failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "delay_seconds": self.delay_seconds,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "final_failure_reason": self.final_failure_reason,
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
    retry: RetryVisibility | None = None

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
            "retry": self.retry.to_dict() if self.retry else None,
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
    trigger: CollectionTriggerType = CollectionTriggerType.MANUAL
    error_summaries: tuple[str, ...] = ()
    retry: RetryVisibility | None = None
    idempotency_key: str | None = None

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

    def duration_ms(self) -> int | None:
        seconds = self.duration_seconds()
        if seconds is None:
            return None
        return int(round(seconds * 1000))

    def is_terminal(self) -> bool:
        return self.completed_at is not None and self.status in {
            CollectionStatus.COMPLETED,
            CollectionStatus.PARTIALLY_COMPLETED,
            CollectionStatus.FAILED,
            CollectionStatus.CANCELLED,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        """Structured summary suitable for logging (no raw payloads)."""
        return {
            "run_id": self.run_id,
            "query": self.query,
            "marketplaces_attempted": list(self.marketplaces_attempted),
            "marketplaces_completed": list(self.marketplaces_completed),
            "duration_seconds": self.duration_seconds(),
            "duration_ms": self.duration_ms(),
            "collected_count": self.collected_count,
            "stored_snapshot_count": self.stored_snapshot_count,
            "skipped_count": self.skipped_count,
            "failure_count": self.failure_count,
            "status": self.status.value,
            "job_id": self.job_id,
            "trigger": self.trigger.value,
            "error_summaries": list(self.error_summaries),
            "retry": self.retry.to_dict() if self.retry else None,
            "idempotency_key": self.idempotency_key,
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
    name: str = ""
    paused: bool = False
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failure_count: int = 0
    updated_at: datetime | None = None

    @property
    def interval_minutes(self) -> int:
        return max(1, (self.interval_seconds + 59) // 60) if self.interval_seconds > 0 else 0

    @property
    def status(self) -> CollectionJobStatus:
        if self.running:
            return CollectionJobStatus.RUNNING
        if not self.enabled:
            return CollectionJobStatus.DISABLED
        if self.paused:
            return CollectionJobStatus.PAUSED
        return CollectionJobStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name or self.query,
            "query": self.query,
            "marketplaces": list(self.marketplaces),
            "interval_seconds": self.interval_seconds,
            "interval_minutes": self.interval_minutes,
            "enabled": self.enabled,
            "status": self.status.value,
            "paused": self.paused,
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at or self.created_at).isoformat(),
            "next_run_at": self.next_run_at.isoformat(),
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_success_at": (
                self.last_success_at.isoformat() if self.last_success_at else None
            ),
            "last_failure_at": (
                self.last_failure_at.isoformat() if self.last_failure_at else None
            ),
            "consecutive_failure_count": self.consecutive_failure_count,
            "scenario": self.scenario,
            "running": self.running,
        }


@dataclass(frozen=True, slots=True)
class CollectorAvailability:
    """Whether a registered mock collector passes its health check."""

    marketplace: str
    available: bool

    def to_dict(self) -> dict[str, Any]:
        return {"marketplace": self.marketplace, "available": self.available}


@dataclass(frozen=True, slots=True)
class CollectionOperationalStatus:
    """Aggregate operational view of the collection subsystem."""

    total_jobs: int
    enabled_jobs: int
    paused_jobs: int
    jobs_currently_due: int
    jobs_with_recent_failures: int
    last_successful_collection: datetime | None
    last_failed_collection: datetime | None
    total_snapshots_collected: int
    scheduler_status: str
    collector_availability: tuple[CollectorAvailability, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "enabled_jobs": self.enabled_jobs,
            "paused_jobs": self.paused_jobs,
            "jobs_currently_due": self.jobs_currently_due,
            "jobs_with_recent_failures": self.jobs_with_recent_failures,
            "last_successful_collection": (
                self.last_successful_collection.isoformat()
                if self.last_successful_collection
                else None
            ),
            "last_failed_collection": (
                self.last_failed_collection.isoformat()
                if self.last_failed_collection
                else None
            ),
            "total_snapshots_collected": self.total_snapshots_collected,
            "scheduler_status": self.scheduler_status,
            "collector_availability": [
                item.to_dict() for item in self.collector_availability
            ],
        }


@dataclass(frozen=True, slots=True)
class CollectionSubsystemHealth:
    """Liveness view for the collection operations subsystem."""

    status: str
    subsystem: str
    running: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "subsystem": self.subsystem,
            "running": self.running,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class CollectionReadinessCheck:
    """One readiness probe result."""

    name: str
    ready: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ready": self.ready, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class CollectionSubsystemReadiness:
    """Readiness view — local dependency checks only, no network calls."""

    ready: bool
    status: str
    checks: tuple[CollectionReadinessCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }
