"""Launch readiness API — dashboard, demo launcher, config, checklist (Sprint 22)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import (
    get_db,
    get_launch_config_service,
    get_launch_dashboard_service,
    get_launch_demo_service,
    get_launch_performance_service,
)
from app.core.validation import validate_settings
from app.domain.exceptions import (
    LaunchAuthorizationError,
    LaunchNotFoundError,
    LaunchValidationError,
)
from app.launch.feature_flags import get_feature_flags
from app.schemas.health import ServiceStatus
from app.schemas.launch import ChecklistUpdateRequest, ConfigImportRequest, DemoSwitchRequest
from app.services.launch_config_service import LaunchConfigService
from app.services.launch_dashboard_service import LaunchDashboardService
from app.services.launch_demo_service import LaunchDemoService
from app.services.launch_performance_service import LaunchPerformanceService

router = APIRouter(prefix="/launch", tags=["launch-readiness"])


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LaunchValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, LaunchAuthorizationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    if isinstance(exc, LaunchNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _require_launch_enabled() -> None:
    if not settings.launch_readiness_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Launch readiness surface is disabled",
        )


def _require_admin(authorization: str | None) -> None:
    """Demo admin gate — bearer demo-token-internal-admin (no real IAM)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise LaunchAuthorizationError("Admin bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if token != "demo-token-internal-admin":
        raise LaunchAuthorizationError("Internal admin token required for this action")


@router.get(
    "/meta",
    summary="Launch readiness metadata and limitations",
)
def launch_meta() -> dict[str, Any]:
    _require_launch_enabled()
    return {
        "sprint": 22,
        "name": "Launch Readiness & Production Preparation",
        "enabled": settings.launch_readiness_enabled,
        "environment": settings.app_env,
        "docs": [
            "docs/LAUNCH_CHECKLIST.md",
            "docs/DEPLOYMENT.md",
            "docs/PRODUCTION.md",
            "docs/SECURITY.md",
            "docs/OPERATIONS.md",
            "docs/MONITORING.md",
            "docs/BACKUP_RESTORE.md",
        ],
        "limitations": [
            "No real cloud deployment",
            "No production database",
            "No payment processing",
            "No real email / SMS / push",
            "No subscription billing",
            "No production secrets",
            "Demo/in-memory safe",
        ],
    }


@router.get(
    "/dashboard",
    summary="Admin launch dashboard — metrics, health, flags, checklist",
)
async def launch_dashboard(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    service: LaunchDashboardService = Depends(get_launch_dashboard_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
    except LaunchAuthorizationError as exc:
        raise _map_error(exc) from exc

    db_status = ServiceStatus.UP
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = ServiceStatus.DOWN

    return service.dashboard(
        database_status=db_status.value,
        api_health={
            "status": "up" if db_status == ServiceStatus.UP else "degraded",
            "database": db_status.value,
            "probes": {
                "health": "/api/v1/health",
                "ready": "/api/v1/ready",
                "live": "/api/v1/live",
                "root_health": "/health",
                "root_ready": "/ready",
                "root_live": "/live",
            },
        },
    )


@router.get("/feature-flags", summary="List effective feature flags")
def feature_flags() -> dict[str, Any]:
    _require_launch_enabled()
    flags = get_feature_flags()
    return {"flags": flags.snapshot(), "as_dict": flags.as_dict()}


@router.get("/system-status", summary="Production settings and system status snapshot")
def system_status() -> dict[str, Any]:
    _require_launch_enabled()
    validation = validate_settings()
    return {
        "environment": settings.app_env,
        "debug": settings.app_debug,
        "docs_enabled": settings.docs_enabled,
        "rate_limiting_enabled": settings.rate_limiting_enabled,
        "security_headers_enabled": settings.security_headers_enabled,
        "structured_logging_enabled": settings.structured_logging_enabled,
        "performance_cache_enabled": settings.performance_cache_enabled,
        "cors_origins": list(settings.cors_origins),
        "validation": {
            "ok": validation.ok,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        },
        "note": "Secrets are never included in this payload.",
    }


@router.get("/demo", summary="Demo launcher status and personas")
def demo_status(
    service: LaunchDemoService = Depends(get_launch_demo_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    return service.status()


@router.get("/demo/personas", summary="List demo launcher personas")
def demo_personas(
    service: LaunchDemoService = Depends(get_launch_demo_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    return {"personas": service.list_personas()}


@router.post("/demo/switch", summary="Switch active demo persona")
def demo_switch(
    body: DemoSwitchRequest,
    service: LaunchDemoService = Depends(get_launch_demo_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        return service.switch(body.persona)
    except (LaunchValidationError, LaunchNotFoundError) as exc:
        raise _map_error(exc) from exc


@router.get("/checklist", summary="Launch checklist status")
def launch_checklist(
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    return service.checklist()


@router.patch("/checklist/{item_id}", summary="Update a launch checklist item")
def update_checklist(
    item_id: str,
    body: ChecklistUpdateRequest,
    authorization: str | None = Header(default=None),
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
        return service.update_checklist_item(item_id, completed=body.completed, notes=body.notes)
    except (LaunchAuthorizationError, LaunchNotFoundError, LaunchValidationError) as exc:
        raise _map_error(exc) from exc


@router.post("/config/export", summary="Export redacted configuration snapshot")
def export_config(
    authorization: str | None = Header(default=None),
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
        return service.export_config()
    except LaunchAuthorizationError as exc:
        raise _map_error(exc) from exc


@router.get("/config/exports", summary="List configuration export snapshots")
def list_exports(
    authorization: str | None = Header(default=None),
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
        return {"items": service.list_exports()}
    except LaunchAuthorizationError as exc:
        raise _map_error(exc) from exc


@router.get("/config/exports/{snapshot_id}", summary="Fetch a configuration export")
def get_export(
    snapshot_id: str,
    authorization: str | None = Header(default=None),
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
        return service.get_export(snapshot_id)
    except (LaunchAuthorizationError, LaunchNotFoundError) as exc:
        raise _map_error(exc) from exc


@router.post("/config/import", summary="Import configuration for review (does not mutate runtime)")
def import_config(
    body: ConfigImportRequest,
    authorization: str | None = Header(default=None),
    service: LaunchConfigService = Depends(get_launch_config_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
        return service.import_config(body.payload)
    except (LaunchAuthorizationError, LaunchValidationError) as exc:
        raise _map_error(exc) from exc


@router.get("/performance", summary="Performance cache stats")
def performance_stats(
    service: LaunchPerformanceService = Depends(get_launch_performance_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    return service.stats()


@router.post("/performance/clear", summary="Clear performance cache")
def performance_clear(
    authorization: str | None = Header(default=None),
    service: LaunchPerformanceService = Depends(get_launch_performance_service),
) -> dict[str, Any]:
    _require_launch_enabled()
    try:
        _require_admin(authorization)
    except LaunchAuthorizationError as exc:
        raise _map_error(exc) from exc
    cleared = service.invalidate_namespace("*")
    return {"cleared": cleared, "stats": service.stats()}
