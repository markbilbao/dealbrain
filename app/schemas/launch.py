"""Launch readiness API schemas (Sprint 22)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LiveResponse(BaseModel):
    status: str = Field(description="Process liveness status")
    service: str
    version: str
    uptime_seconds: float
    live: bool = True

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "up",
                "service": "PiqSavi",
                "version": "1.0.0",
                "uptime_seconds": 12.5,
                "live": True,
            }
        }
    }


class ReadyResponse(BaseModel):
    status: str
    ready: bool
    service: str
    version: str
    database: str
    cache: str
    uptime_seconds: float
    persistence_level: str | None = None
    components: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "up",
                "ready": True,
                "service": "PiqSavi",
                "version": "1.0.0",
                "database": "up",
                "cache": "up",
                "uptime_seconds": 12.5,
                "persistence_level": "READY",
                "components": [],
            }
        }
    }


class DependencyStatus(BaseModel):
    name: str
    status: str
    detail: str = ""
    latency_ms: float | None = None


class EnhancedHealthResponse(BaseModel):
    """Extended health payload — keeps Sprint 1 fields and adds launch fields."""

    status: str = Field(description="Overall application health status")
    service: str = Field(description="Application name")
    environment: str = Field(description="Deployment environment")
    database: str = Field(description="Database connectivity status")
    cache: str = Field(default="up", description="In-process cache status")
    version: str = Field(default="1.0.0", description="Application version")
    uptime_seconds: float = Field(default=0.0, description="Seconds since process start")
    started_at: str | None = Field(default=None, description="ISO startup timestamp")
    dependencies: list[DependencyStatus] = Field(default_factory=list)
    checks: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "up",
                "service": "PiqSavi",
                "environment": "development",
                "database": "up",
                "cache": "up",
                "version": "1.0.0",
                "uptime_seconds": 42.0,
                "dependencies": [{"name": "database", "status": "up", "detail": "SELECT 1 probe"}],
                "checks": {"rate_limiting": True},
            }
        }
    }


class DemoSwitchRequest(BaseModel):
    persona: Literal["anonymous", "registered", "merchant", "admin"] = Field(
        description="Demo persona to activate"
    )

    model_config = {"json_schema_extra": {"example": {"persona": "merchant"}}}


class ChecklistUpdateRequest(BaseModel):
    completed: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class ConfigImportRequest(BaseModel):
    payload: dict[str, Any] = Field(description="Previously exported (redacted) config object")

    model_config = {
        "json_schema_extra": {
            "example": {"payload": {"app_env": "staging", "rate_limiting_enabled": True}}
        }
    }
