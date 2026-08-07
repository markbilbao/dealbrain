"""Health check schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    """Health status for a service or dependency."""

    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: ServiceStatus = Field(description="Overall application health status")
    service: str = Field(description="Application name")
    environment: str = Field(description="Deployment environment")
    database: ServiceStatus = Field(description="Database connectivity status")

    model_config = {"json_schema_extra": {"example": {
        "status": "up",
        "service": "PiqSavi",
        "environment": "development",
        "database": "up",
    }}}
