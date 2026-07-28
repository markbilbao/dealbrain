"""Map Collection Operations domain objects to HTTP schemas."""

from __future__ import annotations

from app.domain.entities.collection import (
    CollectionJob,
    CollectionOperationalStatus,
    CollectionRun,
    CollectionSubsystemHealth,
    CollectionSubsystemReadiness,
)
from app.schemas.collection_operations import (
    CollectionOpsHealthPayload,
    CollectionOpsJobPayload,
    CollectionOpsReadinessCheckPayload,
    CollectionOpsReadinessPayload,
    CollectionOpsRunPayload,
    CollectionOpsStatusPayload,
    CollectorAvailabilityPayload,
    RetryVisibilityPayload,
)


def to_ops_job_payload(job: CollectionJob) -> CollectionOpsJobPayload:
    return CollectionOpsJobPayload(
        job_id=job.job_id,
        name=job.name or job.query,
        query=job.query,
        marketplaces=list(job.marketplaces),
        interval_minutes=job.interval_minutes,
        enabled=job.enabled,
        status=job.status.value,
        next_run_at=job.next_run_at.isoformat(),
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        last_success_at=job.last_success_at.isoformat() if job.last_success_at else None,
        last_failure_at=job.last_failure_at.isoformat() if job.last_failure_at else None,
        consecutive_failure_count=job.consecutive_failure_count,
        created_at=job.created_at.isoformat(),
        updated_at=(job.updated_at or job.created_at).isoformat(),
        scenario=job.scenario,
        paused=job.paused,
        running=job.running,
    )


def to_ops_run_payload(run: CollectionRun) -> CollectionOpsRunPayload:
    retry = None
    if run.retry is not None:
        retry = RetryVisibilityPayload(
            attempt=run.retry.attempt,
            max_attempts=run.retry.max_attempts,
            delay_seconds=run.retry.delay_seconds,
            next_retry_at=(
                run.retry.next_retry_at.isoformat() if run.retry.next_retry_at else None
            ),
            final_failure_reason=run.retry.final_failure_reason,
        )
    return CollectionOpsRunPayload(
        run_id=run.run_id,
        job_id=run.job_id,
        trigger=run.trigger.value,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        status=run.status.value,
        marketplaces_attempted=list(run.marketplaces_attempted),
        marketplaces_completed=list(run.marketplaces_completed),
        collected_count=run.collected_count,
        stored_snapshot_count=run.stored_snapshot_count,
        skipped_count=run.skipped_count,
        failure_count=run.failure_count,
        duration_ms=run.duration_ms(),
        error_summaries=list(run.error_summaries),
        retry=retry,
        query=run.query,
        idempotency_key=run.idempotency_key,
        warnings=list(run.warnings),
    )


def to_ops_status_payload(
    status: CollectionOperationalStatus,
) -> CollectionOpsStatusPayload:
    return CollectionOpsStatusPayload(
        total_jobs=status.total_jobs,
        enabled_jobs=status.enabled_jobs,
        paused_jobs=status.paused_jobs,
        jobs_currently_due=status.jobs_currently_due,
        jobs_with_recent_failures=status.jobs_with_recent_failures,
        last_successful_collection=(
            status.last_successful_collection.isoformat()
            if status.last_successful_collection
            else None
        ),
        last_failed_collection=(
            status.last_failed_collection.isoformat()
            if status.last_failed_collection
            else None
        ),
        total_snapshots_collected=status.total_snapshots_collected,
        scheduler_status=status.scheduler_status,
        collector_availability=[
            CollectorAvailabilityPayload(
                marketplace=item.marketplace,
                available=item.available,
            )
            for item in status.collector_availability
        ],
    )


def to_ops_health_payload(health: CollectionSubsystemHealth) -> CollectionOpsHealthPayload:
    return CollectionOpsHealthPayload(
        status=health.status,
        subsystem=health.subsystem,
        running=health.running,
        detail=health.detail,
    )


def to_ops_readiness_payload(
    readiness: CollectionSubsystemReadiness,
) -> CollectionOpsReadinessPayload:
    return CollectionOpsReadinessPayload(
        ready=readiness.ready,
        status=readiness.status,
        checks=[
            CollectionOpsReadinessCheckPayload(
                name=check.name,
                ready=check.ready,
                detail=check.detail,
            )
            for check in readiness.checks
        ],
    )
