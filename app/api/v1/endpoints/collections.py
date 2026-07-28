"""Marketplace Collection API endpoints.

Routes delegate to :class:`MarketplaceCollectionService` and the in-memory
scheduler. No live marketplace scraping or background workers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.collection import to_job_payload, to_run_payload
from app.core.dependencies import (
    get_collection_scheduler,
    get_marketplace_collection_service,
)
from app.domain.exceptions import (
    CollectionJobNotFoundError,
    CollectionRunNotFoundError,
    CollectionValidationError,
)
from app.domain.interfaces.collection_scheduler import CollectionScheduler
from app.schemas.collection import (
    CollectionJobCreateRequest,
    CollectionJobListResponse,
    CollectionJobPayload,
    CollectionRunDueResponse,
    CollectionRunListResponse,
    CollectionRunPayload,
    CollectionRunRequest,
)
from app.services.marketplace_collection_service import MarketplaceCollectionService

router = APIRouter(prefix="/collections")


@router.post(
    "/run",
    response_model=CollectionRunPayload,
    summary="Run a manual mock marketplace collection",
)
async def run_collection(
    body: CollectionRunRequest,
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
) -> CollectionRunPayload:
    """Collect mocked listings and record Price History snapshots."""
    try:
        run = await service.run_collection(
            query=body.query,
            marketplaces=body.marketplaces or None,
            observed_at=body.observed_at,
            scenario=body.scenario,
        )
    except CollectionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_run_payload(run)


@router.get(
    "/runs",
    response_model=CollectionRunListResponse,
    summary="List recent collection runs",
)
async def list_collection_runs(
    limit: int = Query(20, ge=1, le=100),
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
) -> CollectionRunListResponse:
    runs = service.list_runs(limit=limit)
    return CollectionRunListResponse(runs=[to_run_payload(run) for run in runs])


@router.get(
    "/runs/{run_id}",
    response_model=CollectionRunPayload,
    summary="Get a collection run by id",
)
async def get_collection_run(
    run_id: str,
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
) -> CollectionRunPayload:
    try:
        run = service.get_run(run_id)
    except CollectionRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return to_run_payload(run)


@router.post(
    "/jobs",
    response_model=CollectionJobPayload,
    summary="Create a scheduled collection job",
)
async def create_collection_job(
    body: CollectionJobCreateRequest,
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
    scheduler: CollectionScheduler = Depends(get_collection_scheduler),
) -> CollectionJobPayload:
    try:
        job = service.create_job(
            query=body.query,
            marketplaces=body.marketplaces,
            interval_seconds=body.interval_seconds,
            enabled=body.enabled,
            scenario=body.scenario,
            next_run_at=body.next_run_at,
        )
        scheduler.register_job(job)
    except CollectionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    return to_job_payload(job)


@router.get(
    "/jobs",
    response_model=CollectionJobListResponse,
    summary="List scheduled collection jobs",
)
async def list_collection_jobs(
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
) -> CollectionJobListResponse:
    jobs = service.list_jobs()
    return CollectionJobListResponse(jobs=[to_job_payload(job) for job in jobs])


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scheduled collection job",
)
async def delete_collection_job(
    job_id: str,
    service: MarketplaceCollectionService = Depends(get_marketplace_collection_service),
    scheduler: CollectionScheduler = Depends(get_collection_scheduler),
) -> None:
    try:
        service.delete_job(job_id)
        scheduler.remove_job(job_id)
    except CollectionJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/jobs/run-due",
    response_model=CollectionRunDueResponse,
    summary="Execute due scheduled collection jobs",
)
async def run_due_collection_jobs(
    scheduler: CollectionScheduler = Depends(get_collection_scheduler),
) -> CollectionRunDueResponse:
    """Run enabled jobs whose next_run_at is due. No background threads."""
    runs = await scheduler.run_due_jobs()
    return CollectionRunDueResponse(
        runs=[to_run_payload(run) for run in runs],
        jobs_executed=len(runs),
    )
