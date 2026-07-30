"""Collection Operations API endpoints.

Operational control for marketplace collection jobs and run history.
Mock collectors only — no live scraping or external network calls.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.collection_operations import (
    to_ops_health_payload,
    to_ops_job_payload,
    to_ops_readiness_payload,
    to_ops_run_payload,
    to_ops_status_payload,
)
from app.core.dependencies import get_collection_operations_service
from app.domain.exceptions import (
    CollectionConcurrentRunError,
    CollectionJobNotFoundError,
    CollectionJobNotRunnableError,
    CollectionRunNotFoundError,
    CollectionValidationError,
)
from app.schemas.api_common import build_pagination_meta
from app.schemas.collection_operations import (
    CollectionOpsHealthPayload,
    CollectionOpsJobCreateRequest,
    CollectionOpsJobListResponse,
    CollectionOpsJobPayload,
    CollectionOpsJobUpdateRequest,
    CollectionOpsManualRunRequest,
    CollectionOpsReadinessPayload,
    CollectionOpsRunDueResponse,
    CollectionOpsRunListResponse,
    CollectionOpsRunPayload,
    CollectionOpsStatusPayload,
)
from app.services.collection_operations_service import CollectionOperationsService

router = APIRouter(prefix="/collection-operations")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CollectionValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, (CollectionJobNotFoundError, CollectionRunNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CollectionJobNotRunnableError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, CollectionConcurrentRunError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/status",
    response_model=CollectionOpsStatusPayload,
    summary="Collection operational status",
)
async def get_collection_status(
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsStatusPayload:
    return to_ops_status_payload(service.get_operational_status())


@router.get(
    "/jobs",
    response_model=CollectionOpsJobListResponse,
    summary="List collection jobs",
)
async def list_jobs(
    status_filter: str | None = Query(None, alias="status"),
    marketplace: str | None = None,
    enabled: bool | None = None,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobListResponse:
    jobs = service.list_jobs(
        status=status_filter,
        marketplace=marketplace,
        enabled=enabled,
    )
    return CollectionOpsJobListResponse(jobs=[to_ops_job_payload(job) for job in jobs])


@router.post(
    "/jobs",
    response_model=CollectionOpsJobPayload,
    summary="Create a collection job",
)
async def create_job(
    body: CollectionOpsJobCreateRequest,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobPayload:
    try:
        job = service.create_job(
            name=body.name,
            query=body.query,
            marketplaces=body.marketplaces,
            interval_minutes=body.interval_minutes,
            enabled=body.enabled,
            scenario=body.scenario,
            next_run_at=body.next_run_at,
        )
    except CollectionValidationError as exc:
        raise _map_error(exc) from exc
    return to_ops_job_payload(job)


@router.get(
    "/jobs/{job_id}",
    response_model=CollectionOpsJobPayload,
    summary="Get a collection job",
)
async def get_job(
    job_id: str,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobPayload:
    try:
        job = service.get_job(job_id)
    except CollectionJobNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_ops_job_payload(job)


@router.patch(
    "/jobs/{job_id}",
    response_model=CollectionOpsJobPayload,
    summary="Update a collection job",
)
async def update_job(
    job_id: str,
    body: CollectionOpsJobUpdateRequest,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobPayload:
    try:
        job = service.update_job(
            job_id,
            name=body.name,
            query=body.query,
            marketplaces=body.marketplaces,
            interval_minutes=body.interval_minutes,
            enabled=body.enabled,
            scenario=body.scenario,
            next_run_at=body.next_run_at,
        )
    except (CollectionValidationError, CollectionJobNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_ops_job_payload(job)


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection job",
)
async def delete_job(
    job_id: str,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> None:
    try:
        service.delete_job(job_id)
    except CollectionJobNotFoundError as exc:
        raise _map_error(exc) from exc


@router.post(
    "/jobs/{job_id}/pause",
    response_model=CollectionOpsJobPayload,
    summary="Pause a collection job",
)
async def pause_job(
    job_id: str,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobPayload:
    try:
        job = service.pause_job(job_id)
    except CollectionJobNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_ops_job_payload(job)


@router.post(
    "/jobs/{job_id}/resume",
    response_model=CollectionOpsJobPayload,
    summary="Resume a collection job",
)
async def resume_job(
    job_id: str,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsJobPayload:
    try:
        job = service.resume_job(job_id)
    except CollectionJobNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_ops_job_payload(job)


@router.post(
    "/jobs/{job_id}/run",
    response_model=CollectionOpsRunPayload,
    summary="Manually trigger a collection job",
)
async def run_job(
    job_id: str,
    body: CollectionOpsManualRunRequest | None = None,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsRunPayload:
    request = body or CollectionOpsManualRunRequest()
    try:
        run = await service.run_job(
            job_id,
            idempotency_key=request.idempotency_key,
            override=request.override,
        )
    except (
        CollectionJobNotFoundError,
        CollectionJobNotRunnableError,
        CollectionConcurrentRunError,
        CollectionValidationError,
    ) as exc:
        raise _map_error(exc) from exc
    return to_ops_run_payload(run)


@router.get(
    "/jobs/{job_id}/runs",
    response_model=CollectionOpsRunListResponse,
    summary="List runs for a collection job",
)
async def list_job_runs(
    job_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsRunListResponse:
    try:
        runs = service.list_runs_for_job(job_id, limit=offset + limit + 1)
    except CollectionJobNotFoundError as exc:
        raise _map_error(exc) from exc
    payloads = [to_ops_run_payload(run) for run in runs]
    window = payloads[offset:]
    has_more = len(window) > limit
    page = window[:limit]
    return CollectionOpsRunListResponse(
        runs=page,
        items=page,
        pagination=build_pagination_meta(
            limit=limit, offset=offset, page_len=len(page), has_more=has_more
        ),
    )


@router.get(
    "/runs",
    response_model=CollectionOpsRunListResponse,
    summary="List recent collection runs",
)
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    failed_only: bool = Query(False),
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsRunListResponse:
    runs = service.list_runs(limit=offset + limit + 1, failed_only=failed_only)
    payloads = [to_ops_run_payload(run) for run in runs]
    window = payloads[offset:]
    has_more = len(window) > limit
    page = window[:limit]
    return CollectionOpsRunListResponse(
        runs=page,
        items=page,
        pagination=build_pagination_meta(
            limit=limit, offset=offset, page_len=len(page), has_more=has_more
        ),
    )


@router.get(
    "/runs/{run_id}",
    response_model=CollectionOpsRunPayload,
    summary="Get a collection run",
)
async def get_run(
    run_id: str,
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsRunPayload:
    try:
        run = service.get_run(run_id)
    except CollectionRunNotFoundError as exc:
        raise _map_error(exc) from exc
    return to_ops_run_payload(run)


@router.post(
    "/run-due",
    response_model=CollectionOpsRunDueResponse,
    summary="Run all due collection jobs",
)
async def run_due(
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsRunDueResponse:
    runs = await service.run_due_jobs()
    return CollectionOpsRunDueResponse(
        runs=[to_ops_run_payload(run) for run in runs],
        jobs_executed=len(runs),
    )


@router.get(
    "/health",
    response_model=CollectionOpsHealthPayload,
    summary="Collection operations health",
)
async def collection_health(
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsHealthPayload:
    return to_ops_health_payload(service.health())


@router.get(
    "/readiness",
    response_model=CollectionOpsReadinessPayload,
    summary="Collection operations readiness",
)
async def collection_readiness(
    service: CollectionOperationsService = Depends(get_collection_operations_service),
) -> CollectionOpsReadinessPayload:
    return to_ops_readiness_payload(service.readiness())
