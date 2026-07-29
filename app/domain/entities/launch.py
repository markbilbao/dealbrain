"""Domain entities for launch readiness (Sprint 22)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

HealthLevel = Literal["up", "down", "degraded"]


@dataclass(frozen=True, slots=True)
class DependencyCheck:
    name: str
    status: HealthLevel
    detail: str = ""
    latency_ms: float | None = None


@dataclass(frozen=True, slots=True)
class SystemHealthReport:
    status: HealthLevel
    service: str
    environment: str
    version: str
    uptime_seconds: float
    started_at: datetime | None
    database: HealthLevel
    cache: HealthLevel
    dependencies: tuple[DependencyCheck, ...] = ()
    checks: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LaunchMetrics:
    users: int
    watchlists: int
    merchants: int
    affiliate_clicks: int
    alerts: int
    notifications: int
    products: int
    offers: int
    campaigns: int
