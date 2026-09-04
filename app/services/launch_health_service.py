"""Launch health aggregation service (Sprint 22) with Sprint 23 persistence depth."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app import __version__
from app.auth.email_factory import identity_email_status
from app.core.config import Settings, settings
from app.domain.entities.launch import DependencyCheck, SystemHealthReport
from app.launch.cache import TtlCache
from app.launch.runtime import get_startup_instant, uptime_seconds
from app.schemas.health import ServiceStatus


class LaunchHealthService:
    """Build health / ready / live reports without exposing secrets."""

    def __init__(
        self,
        *,
        cache: TtlCache | None = None,
        cfg: Settings | None = None,
        db_ping: Callable[[], bool] | None = None,
    ) -> None:
        self._cache = cache
        self._cfg = cfg or settings
        self._db_ping = db_ping

    def live(self) -> dict[str, Any]:
        """Liveness — process is up."""
        return {
            "status": ServiceStatus.UP.value,
            "service": self._cfg.app_name,
            "version": __version__,
            "uptime_seconds": round(uptime_seconds(), 3),
            "live": True,
        }

    def ready(
        self,
        *,
        database_status: ServiceStatus = ServiceStatus.UP,
    ) -> dict[str, Any]:
        """Readiness — safe to receive traffic."""
        cache_status = self._cache_status()
        persistence = self._persistence_readiness()
        persistence_blocks = persistence.get("level") == "NOT_READY"
        ready = database_status != ServiceStatus.DOWN and not persistence_blocks
        if ready and persistence.get("level") == "DEGRADED":
            overall = ServiceStatus.DEGRADED
        elif ready:
            overall = ServiceStatus.UP
        else:
            overall = ServiceStatus.DOWN
        return {
            "status": overall.value,
            "ready": ready,
            "service": self._cfg.app_name,
            "version": __version__,
            "database": database_status.value,
            "cache": cache_status.value,
            "uptime_seconds": round(uptime_seconds(), 3),
            "persistence_level": persistence.get("level"),
            "components": persistence.get("components", []),
        }

    def health(
        self,
        *,
        database_status: ServiceStatus = ServiceStatus.UP,
        db_latency_ms: float | None = None,
    ) -> SystemHealthReport:
        cache_status = self._cache_status()
        persistence = self._persistence_readiness()
        deps: list[DependencyCheck] = [
            DependencyCheck(
                name="database",
                status=database_status.value,  # type: ignore[arg-type]
                detail="SELECT 1 probe (shallow)",
                latency_ms=db_latency_ms,
            ),
            DependencyCheck(
                name="cache",
                status=cache_status.value,  # type: ignore[arg-type]
                detail="in-process TTL cache",
            ),
            DependencyCheck(
                name="feature_flags",
                status="up",
                detail="settings-backed registry",
            ),
            DependencyCheck(
                name="rate_limiter",
                status="up" if self._cfg.rate_limiting_enabled else "degraded",
                detail="in-process sliding window",
            ),
            DependencyCheck(
                name="persistence",
                status=self._map_persistence_status(persistence.get("level")),  # type: ignore[arg-type]
                detail=f"level={persistence.get('level')}",
            ),
        ]
        for component in persistence.get("components", [])[:12]:
            status = component.get("status", "degraded")
            mapped: str = "up"
            if status == "not_ready":
                mapped = "down"
            elif status == "degraded":
                mapped = "degraded"
            deps.append(
                DependencyCheck(
                    name=str(component.get("name", "component")),
                    status=mapped,  # type: ignore[arg-type]
                    detail=str(component.get("detail", "")),
                )
            )

        overall = ServiceStatus.UP
        if database_status == ServiceStatus.DOWN or cache_status == ServiceStatus.DOWN:
            overall = ServiceStatus.DEGRADED
        if persistence.get("level") == "NOT_READY":
            overall = ServiceStatus.DOWN if self._cfg.is_production else ServiceStatus.DEGRADED
        elif persistence.get("level") == "DEGRADED" and overall == ServiceStatus.UP:
            overall = ServiceStatus.DEGRADED

        started = get_startup_instant()
        email_status = identity_email_status(self._cfg)
        return SystemHealthReport(
            status=overall.value,  # type: ignore[arg-type]
            service=self._cfg.app_name,
            environment=self._cfg.app_env,
            version=__version__,
            uptime_seconds=round(uptime_seconds(), 3),
            started_at=started,
            database=database_status.value,  # type: ignore[arg-type]
            cache=cache_status.value,  # type: ignore[arg-type]
            dependencies=tuple(deps),
            checks={
                "structured_logging": self._cfg.structured_logging_enabled,
                "security_headers": self._cfg.security_headers_enabled,
                "rate_limiting": self._cfg.rate_limiting_enabled,
                "performance_cache": self._cfg.performance_cache_enabled,
                "launch_readiness": self._cfg.launch_readiness_enabled,
                "persistence_level": persistence.get("level"),
                "persistence_schema_ok": persistence.get("schema_ok"),
                "persistence_database_ok": persistence.get("database_ok"),
                "identity_email_adapter": email_status["adapter"],
                "identity_email_ready": email_status["ready"],
            },
        )

    def _persistence_readiness(self) -> dict[str, Any]:
        try:
            from app.infrastructure.persistence.readiness import evaluate_persistence_readiness

            return evaluate_persistence_readiness(self._cfg)
        except Exception as exc:  # noqa: BLE001
            return {
                "level": "NOT_READY" if self._cfg.is_production else "DEGRADED",
                "ready": False,
                "database_ok": False,
                "schema_ok": False,
                "components": [
                    {
                        "name": "persistence.evaluator",
                        "status": "not_ready",
                        "detail": str(exc),
                    }
                ],
            }

    @staticmethod
    def _map_persistence_status(level: str | None) -> str:
        if level == "READY":
            return "up"
        if level == "DEGRADED":
            return "degraded"
        return "down"

    def _cache_status(self) -> ServiceStatus:
        if self._cache is None:
            return ServiceStatus.DEGRADED
        if not self._cache.enabled:
            return ServiceStatus.DEGRADED
        # Touch cache to confirm operability.
        probe_key = "__health_probe__"
        self._cache.set(probe_key, True, ttl_seconds=5)
        return ServiceStatus.UP if self._cache.get(probe_key) is True else ServiceStatus.DOWN

    def ping_database_sync(self) -> tuple[ServiceStatus, float | None]:
        """Optional sync db ping hook for non-async callers."""
        if self._db_ping is None:
            return ServiceStatus.UP, None
        started = time.perf_counter()
        try:
            ok = self._db_ping()
            latency = (time.perf_counter() - started) * 1000.0
            return (ServiceStatus.UP if ok else ServiceStatus.DOWN), latency
        except Exception:
            return ServiceStatus.DOWN, (time.perf_counter() - started) * 1000.0
