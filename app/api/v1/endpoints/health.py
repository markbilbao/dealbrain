"""Health check endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return application and dependency health status."""
    db_status = ServiceStatus.UP

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = ServiceStatus.DOWN

    overall_status = ServiceStatus.UP if db_status == ServiceStatus.UP else ServiceStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        service=settings.app_name,
        environment=settings.app_env,
        database=db_status,
    )
