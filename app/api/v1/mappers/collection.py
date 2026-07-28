"""Map Marketplace Collection domain results to HTTP response schemas."""

from __future__ import annotations

from app.domain.entities.collection import (
    CollectedListing,
    CollectionFailure,
    CollectionJob,
    CollectionResult,
    CollectionRun,
)
from app.schemas.collection import (
    CollectedListingPayload,
    CollectionFailurePayload,
    CollectionJobPayload,
    CollectionResultPayload,
    CollectionRunPayload,
)


def to_run_payload(run: CollectionRun) -> CollectionRunPayload:
    return CollectionRunPayload(
        run_id=run.run_id,
        query=run.query,
        marketplaces=list(run.marketplaces),
        status=run.status.value,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        observed_at=run.observed_at.isoformat() if run.observed_at else None,
        job_id=run.job_id,
        collected_count=run.collected_count,
        stored_snapshot_count=run.stored_snapshot_count,
        skipped_count=run.skipped_count,
        failure_count=run.failure_count,
        duration_seconds=run.duration_seconds(),
        marketplaces_attempted=list(run.marketplaces_attempted),
        marketplaces_completed=list(run.marketplaces_completed),
        warnings=list(run.warnings),
        results=[to_result_payload(result) for result in run.results],
    )


def to_result_payload(result: CollectionResult) -> CollectionResultPayload:
    return CollectionResultPayload(
        run_id=result.run_id,
        marketplace=result.marketplace,
        query=result.query,
        target_id=result.target_id,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat(),
        listing_count=result.listing_count,
        successful_listing_count=result.successful_listing_count,
        failed_listing_count=result.failed_listing_count,
        listings=[to_listing_payload(item) for item in result.listings],
        errors=[to_failure_payload(error) for error in result.errors],
        status=result.status.value,
        warnings=list(result.warnings),
    )


def to_listing_payload(item: CollectedListing) -> CollectedListingPayload:
    listing = item.listing
    return CollectedListingPayload(
        marketplace=listing.marketplace,
        product_id=listing.product_id,
        title=listing.title,
        price=listing.price,
        currency=listing.currency,
        seller=listing.seller,
        rating=listing.rating,
        url=listing.url,
        availability=listing.availability.value,
        source_marketplace=item.source_marketplace,
        collected_at=item.collected_at.isoformat(),
        is_duplicate=item.is_duplicate,
    )


def to_failure_payload(error: CollectionFailure) -> CollectionFailurePayload:
    return CollectionFailurePayload(
        marketplace=error.marketplace,
        code=error.code,
        message=error.message,
        retryable=error.retryable,
        listing_id=error.listing_id,
    )


def to_job_payload(job: CollectionJob) -> CollectionJobPayload:
    return CollectionJobPayload(
        job_id=job.job_id,
        query=job.query,
        marketplaces=list(job.marketplaces),
        interval_seconds=job.interval_seconds,
        enabled=job.enabled,
        created_at=job.created_at.isoformat(),
        next_run_at=job.next_run_at.isoformat(),
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        scenario=job.scenario,
        running=job.running,
    )
