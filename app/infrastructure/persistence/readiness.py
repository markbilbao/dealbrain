"""Deep persistence readiness checks consumed by Sprint 22 health probes."""

from __future__ import annotations

from typing import Any, Literal

from app.core.config import Settings, settings
from app.infrastructure.persistence.binding import (
    REQUIRED_PRODUCTION_BACKENDS,
    describe_component_backends,
    resolve_backend,
)
from app.infrastructure.persistence.session import ping_sync_database

ReadinessLevel = Literal["LIVE", "READY", "DEGRADED", "NOT_READY"]


def evaluate_persistence_readiness(cfg: Settings | None = None) -> dict[str, Any]:
    """Return machine-readable persistence readiness for launch probes.

    Distinguishes shallow connectivity checks from deep adapter/schema checks.
    Does not claim the whole product is production-ready solely because
    persistence exists.
    """
    cfg = cfg or settings
    components = describe_component_backends(cfg)
    db_ok = ping_sync_database() if any(
        c["backend"] == "sqlalchemy" for c in components
    ) or cfg.is_production else True

    schema_ok = True
    schema_detail = "not required (memory-only selection)"
    if any(c["backend"] == "sqlalchemy" for c in components) or cfg.is_production:
        if not db_ok:
            schema_ok = False
            schema_detail = "database unreachable"
        else:
            try:
                from app.infrastructure.persistence.session import require_operational_schema

                require_operational_schema()
                schema_detail = "operational_entities present"
            except Exception as exc:  # noqa: BLE001
                schema_ok = False
                schema_detail = str(exc)

    components.append(
        {
            "name": "persistence.database",
            "status": "ready" if db_ok else "not_ready",
            "detail": "SELECT 1 (sync)" if db_ok else "database ping failed",
            "depth": "shallow",
        }
    )
    components.append(
        {
            "name": "persistence.schema",
            "status": "ready" if schema_ok else "not_ready",
            "detail": schema_detail,
            "depth": "deep",
        }
    )

    memory_domains = [
        d for d in REQUIRED_PRODUCTION_BACKENDS if resolve_backend(d, cfg) == "memory"
    ]

    level: ReadinessLevel = "READY"
    if cfg.is_production and (not db_ok or not schema_ok or memory_domains):
        level = "NOT_READY"
    elif not db_ok or not schema_ok:
        level = "NOT_READY" if cfg.is_production else "DEGRADED"
    elif memory_domains and not cfg.is_production:
        level = "DEGRADED" if cfg.app_env == "staging" else "READY"

    return {
        "level": level,
        "ready": level in {"READY", "DEGRADED"} and not (cfg.is_production and level != "READY"),
        "database_ok": db_ok,
        "schema_ok": schema_ok,
        "memory_domains_in_production": memory_domains,
        "components": components,
        "notes": [
            "Shallow: database SELECT 1 connectivity.",
            "Deep: operational_entities schema + required production adapter bindings.",
            "Simulated marketplace connectors and notification transports are not claimed live.",
        ],
    }
