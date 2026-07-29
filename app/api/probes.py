"""Root-level health probes for orchestrators (Sprint 22).

Docker/Kubernetes-style probes at /health, /ready, /live in addition to
versioned /api/v1/* endpoints.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_launch_health_service
from app.schemas.health import ServiceStatus
from app.schemas.launch import EnhancedHealthResponse, LiveResponse, ReadyResponse
from app.services.launch_health_service import LaunchHealthService

router = APIRouter(tags=["probes"])


async def _probe_database(db: AsyncSession) -> tuple[ServiceStatus, float | None]:
    started = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        return ServiceStatus.UP, (time.perf_counter() - started) * 1000.0
    except Exception:
        return ServiceStatus.DOWN, (time.perf_counter() - started) * 1000.0


@router.get("/live", response_model=LiveResponse, summary="Liveness probe")
async def root_live(
    health: LaunchHealthService = Depends(get_launch_health_service),
) -> LiveResponse:
    return LiveResponse(**health.live())


@router.get("/ready", response_model=ReadyResponse, summary="Readiness probe")
async def root_ready(
    response: Response,
    db: AsyncSession = Depends(get_db),
    health: LaunchHealthService = Depends(get_launch_health_service),
) -> ReadyResponse:
    db_status, _ = await _probe_database(db)
    payload = health.ready(database_status=db_status)
    if not payload["ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(**payload)


@router.get("/health", response_model=EnhancedHealthResponse, summary="Health probe")
async def root_health(
    db: AsyncSession = Depends(get_db),
    health: LaunchHealthService = Depends(get_launch_health_service),
) -> EnhancedHealthResponse:
    db_status, latency = await _probe_database(db)
    report = health.health(database_status=db_status, db_latency_ms=latency)
    return EnhancedHealthResponse(
        status=report.status,
        service=report.service,
        environment=report.environment,
        database=report.database,
        cache=report.cache,
        version=report.version,
        uptime_seconds=report.uptime_seconds,
        started_at=report.started_at.isoformat() if report.started_at else None,
        dependencies=[
            {
                "name": d.name,
                "status": d.status,
                "detail": d.detail,
                "latency_ms": d.latency_ms,
            }
            for d in report.dependencies
        ],
        checks=dict(report.checks),
    )
