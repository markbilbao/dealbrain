"""Environment-aware repository backend selection (Sprint 23).

Production defaults to SQLAlchemy operational persistence and refuses silent
in-memory fallback. Development/demo may explicitly select memory.
"""

from __future__ import annotations

from typing import Literal

from app.core.config import Settings, settings
from app.infrastructure.persistence.errors import PersistenceConfigurationError

BackendName = Literal["memory", "sqlalchemy"]

REQUIRED_PRODUCTION_BACKENDS = (
    "user_platform",
    "marketplace_data",
    "alerts",
    "notifications",
    "affiliate",
    "merchant",
)


def _explicit_or_default(explicit: str | None, default: BackendName) -> BackendName:
    if explicit in ("memory", "sqlalchemy"):
        return explicit  # type: ignore[return-value]
    return default


def resolve_persistence_default(cfg: Settings | None = None) -> BackendName:
    """Global default: sqlalchemy in production, memory otherwise (unless overridden)."""
    cfg = cfg or settings
    if cfg.persistence_backend in ("memory", "sqlalchemy"):
        return cfg.persistence_backend  # type: ignore[return-value]
    return "sqlalchemy" if cfg.is_production else "memory"


def resolve_backend(domain: str, cfg: Settings | None = None) -> BackendName:
    """Resolve backend for a Sprint 17–21 domain."""
    cfg = cfg or settings
    default = resolve_persistence_default(cfg)
    mapping = {
        "user_platform": cfg.user_platform_backend,
        "marketplace_data": cfg.marketplace_data_backend,
        "alerts": cfg.alerts_backend,
        "notifications": cfg.notifications_backend,
        "affiliate": cfg.affiliate_backend,
        "merchant": cfg.merchant_backend,
        "canonical_registry": cfg.canonical_registry_backend,
        "price_history": cfg.price_history_backend,
    }
    if domain not in mapping:
        raise KeyError(f"Unknown persistence domain: {domain}")
    return _explicit_or_default(mapping[domain], default)


def binding_matrix(cfg: Settings | None = None) -> dict[str, dict[str, str]]:
    """Document resolved bindings for ops/readiness."""
    cfg = cfg or settings
    domains = (
        "user_platform",
        "marketplace_data",
        "alerts",
        "notifications",
        "affiliate",
        "merchant",
        "canonical_registry",
        "price_history",
    )
    owners = {
        "user_platform": "17",
        "marketplace_data": "18",
        "alerts": "19",
        "notifications": "19",
        "affiliate": "20",
        "merchant": "21",
        "canonical_registry": "1-3",
        "price_history": "7",
    }
    result: dict[str, dict[str, str]] = {}
    for domain in domains:
        backend = resolve_backend(domain, cfg)
        result[domain] = {
            "interface": domain,
            "persistent_implementation": "sqlalchemy",
            "test_implementation": "memory",
            "environment_selection": backend,
            "owner_sprint": owners[domain],
        }
    return result


def assert_production_persistence(cfg: Settings | None = None) -> None:
    """Fail closed when production would use in-memory operational stores."""
    cfg = cfg or settings
    if not cfg.is_production:
        return
    problems: list[str] = []
    for domain in REQUIRED_PRODUCTION_BACKENDS:
        if resolve_backend(domain, cfg) != "sqlalchemy":
            problems.append(f"{domain} backend is memory (production requires sqlalchemy)")
    if cfg.demo_launcher_enabled:
        problems.append("DEMO_LAUNCHER_ENABLED must be false in production")
    if cfg.allow_demo_reset_tokens:
        problems.append("ALLOW_DEMO_RESET_TOKENS must be false in production")
    if cfg.seed_demo_data:
        problems.append("SEED_DEMO_DATA must be false in production")
    if problems:
        raise PersistenceConfigurationError("; ".join(problems))


def describe_component_backends(cfg: Settings | None = None) -> list[dict[str, str]]:
    """Machine-readable component backend statuses for readiness."""
    cfg = cfg or settings
    components = []
    for domain, meta in binding_matrix(cfg).items():
        backend = meta["environment_selection"]
        if cfg.is_production and domain in REQUIRED_PRODUCTION_BACKENDS and backend == "memory":
            status = "not_ready"
            detail = "in-memory adapter active in production"
        elif backend == "sqlalchemy":
            status = "ready"
            detail = "sqlalchemy adapter selected"
        else:
            status = "degraded" if cfg.is_production else "ready"
            detail = "in-memory adapter (explicit non-production)"
        components.append(
            {
                "name": f"persistence.{domain}",
                "status": status,
                "detail": detail,
                "backend": backend,
                "owner_sprint": meta["owner_sprint"],
            }
        )
    return components
