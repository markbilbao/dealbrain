"""Environment and startup validation (Sprint 22 + Sprint 25a production gate)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings, settings
from app.domain.exceptions import ConfigurationValidationError
from app.launch.redaction import redact_value

# Exact placeholder values only — never log matched secrets.
_PLACEHOLDER_EXACT = frozenset(
    {
        "",
        "change_me",
        "changeme",
        "replace_me",
        "password",
        "secret",
        "todo",
        "placeholder",
        "example",
        "dealbrain",
        "test",
        "dev",
    }
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    environment: str

    def raise_if_fatal(self, *, enforce: bool = True) -> None:
        if enforce and not self.ok:
            raise ConfigurationValidationError(list(self.errors))


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered in _PLACEHOLDER_EXACT:
        return True
    # Common templated forms: CHANGE_ME, <password>, ${PASSWORD}
    if "change_me" in lowered or "replace_me" in lowered:
        return True
    if lowered.startswith("<") and lowered.endswith(">"):
        return True
    return lowered.startswith("${") and lowered.endswith("}")


def _database_url_has_weak_secret(database_url: str) -> bool:
    """Return True when the DSN password looks missing or placeholder-like.

    Never returns or logs the password itself.
    """
    try:
        parsed = urlparse(database_url)
    except Exception:
        return True
    scheme = (parsed.scheme or "").lower()
    if "@" not in (parsed.netloc or ""):
        # Non-postgres (e.g. sqlite) has no password component — weak for prod.
        return True
    userinfo, _, _host = parsed.netloc.rpartition("@")
    if ":" not in userinfo:
        return True
    _user, _, password = userinfo.partition(":")
    if not password or len(password) < 12 or _looks_like_placeholder(password):
        return True
    return "postgres" not in scheme


def _validate_production_gate(cfg: Settings, errors: list[str], warnings: list[str]) -> None:
    """Fail-closed production configuration gate (Sprint 25a foundation)."""
    if cfg.app_debug:
        errors.append("APP_DEBUG must be false in production")
    if cfg.price_history_seed_demo_mock:
        errors.append("PRICE_HISTORY_SEED_DEMO_MOCK must be false in production")
    if "*" in cfg.cors_origins:
        errors.append("CORS_ORIGINS must not include '*' in production")
    if not cfg.cors_origins:
        errors.append("CORS_ORIGINS must be an explicit non-empty list in production")
    if not cfg.security_headers_enabled:
        warnings.append("SECURITY_HEADERS_ENABLED is false in production")
    if not cfg.rate_limiting_enabled:
        warnings.append("RATE_LIMITING_ENABLED is false in production")
    if cfg.ai_review_live_http or cfg.ai_shopping_live_http or cfg.ai_community_live_http:
        warnings.append("Live AI HTTP is enabled — ensure API keys are vaulted")
    if cfg.app_log_level.upper() == "DEBUG":
        errors.append("APP_LOG_LEVEL must not be DEBUG in production")
    if not cfg.structured_logging_enabled:
        errors.append("STRUCTURED_LOGGING_ENABLED must be true in production")
    if cfg.demo_launcher_enabled:
        errors.append("DEMO_LAUNCHER_ENABLED must be false in production")
    if cfg.allow_demo_reset_tokens:
        errors.append("ALLOW_DEMO_RESET_TOKENS must be false in production")
    if cfg.seed_demo_data:
        errors.append("SEED_DEMO_DATA must be false in production")
    if cfg.openapi_public_docs:
        warnings.append("OPENAPI_PUBLIC_DOCS=true exposes API docs publicly")
    if not cfg.launch_strict_startup:
        errors.append("LAUNCH_STRICT_STARTUP must be true in production")

    if _database_url_has_weak_secret(cfg.database_url):
        errors.append(
            "DATABASE_URL must use a non-placeholder password in production "
            "(value redacted)"
        )

    secret = cfg.app_secret_key or ""
    if len(secret) < 32 or _looks_like_placeholder(secret):
        errors.append(
            "APP_SECRET_KEY must be present and strong in production "
            "(min 32 chars, non-placeholder; value redacted)"
        )

    if not cfg.trusted_hosts:
        warnings.append(
            "TRUSTED_HOSTS is empty — set expected public hostnames for ALB deploy verification"
        )

    # Live AI keys required when live HTTP is on (presence only; never log values).
    if cfg.ai_review_live_http and cfg.ai_primary_provider == "openai" and not cfg.openai_api_key:
        errors.append("OPENAI_API_KEY is required when AI_REVIEW_LIVE_HTTP is true")
    if (
        cfg.ai_review_live_http
        and cfg.ai_primary_provider == "anthropic"
        and not cfg.anthropic_api_key
    ):
        errors.append("ANTHROPIC_API_KEY is required when AI_REVIEW_LIVE_HTTP is true")
    if cfg.ai_review_live_http and cfg.ai_primary_provider == "gemini" and not cfg.gemini_api_key:
        errors.append("GEMINI_API_KEY is required when AI_REVIEW_LIVE_HTTP is true")

    # Persistence backends — no silent in-memory in production.
    from app.infrastructure.persistence.binding import (
        REQUIRED_PRODUCTION_BACKENDS,
        resolve_backend,
    )

    for domain in REQUIRED_PRODUCTION_BACKENDS:
        if resolve_backend(domain, cfg) != "sqlalchemy":
            errors.append(
                f"{domain} persistence must be sqlalchemy in production "
                f"(got {resolve_backend(domain, cfg)})"
            )
    if cfg.canonical_registry_backend == "memory":
        warnings.append(
            "CANONICAL_REGISTRY_BACKEND=memory in production — durable registry recommended"
        )
    if cfg.price_history_backend == "memory":
        warnings.append(
            "PRICE_HISTORY_BACKEND=memory in production — durable price history recommended"
        )


def validate_settings(cfg: Settings | None = None) -> ValidationResult:
    """Validate settings for the active environment.

    Production rules are stricter (fail-closed). Demo/in-memory deployments and
    local/test environments remain valid without real cloud secrets.
    """
    cfg = cfg or settings
    errors: list[str] = []
    warnings: list[str] = []

    if cfg.app_env == "production":
        _validate_production_gate(cfg, errors, warnings)

    if cfg.app_env == "staging":
        if cfg.app_debug:
            warnings.append("APP_DEBUG=true in staging — prefer false for beta rehearsal")
        if not cfg.rate_limiting_enabled:
            warnings.append("Rate limiting disabled in staging")

    if cfg.app_port < 1 or cfg.app_port > 65535:
        errors.append(f"APP_PORT out of range: {cfg.app_port}")

    if not cfg.database_url or "://" not in cfg.database_url:
        errors.append("DATABASE_URL is missing or malformed")
    elif cfg.app_env == "production" and not re.match(
        r"^postgres(ql)?(\+[\w]+)?://",
        cfg.database_url,
        re.IGNORECASE,
    ):
        errors.append("DATABASE_URL must be a PostgreSQL DSN in production")

    if cfg.rate_limit_login_per_minute < 1:
        errors.append("RATE_LIMIT_LOGIN_PER_MINUTE must be >= 1")
    if cfg.rate_limit_default_per_minute < 1:
        errors.append("RATE_LIMIT_DEFAULT_PER_MINUTE must be >= 1")

    # Never treat empty demo AI keys as fatal outside the production live-HTTP gate.
    if cfg.app_env != "production" and cfg.ai_review_enabled and cfg.ai_review_live_http:
        if cfg.ai_primary_provider == "openai" and not cfg.openai_api_key:
            warnings.append("AI_REVIEW live HTTP on but OPENAI_API_KEY is empty")
        if cfg.ai_primary_provider == "anthropic" and not cfg.anthropic_api_key:
            warnings.append("AI_REVIEW live HTTP on but ANTHROPIC_API_KEY is empty")
        if cfg.ai_primary_provider == "gemini" and not cfg.gemini_api_key:
            warnings.append("AI_REVIEW live HTTP on but GEMINI_API_KEY is empty")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        environment=cfg.app_env,
    )


def exportable_settings(cfg: Settings | None = None) -> dict[str, Any]:
    """Export non-secret settings for backup / ops review."""
    cfg = cfg or settings
    raw = {
        "app_name": cfg.app_name,
        "app_env": cfg.app_env,
        "app_debug": cfg.app_debug,
        "app_host": cfg.app_host,
        "app_port": cfg.app_port,
        "app_log_level": cfg.app_log_level,
        "canonical_registry_backend": cfg.canonical_registry_backend,
        "price_history_backend": cfg.price_history_backend,
        "persistence_backend": cfg.persistence_backend,
        "user_platform_backend": cfg.user_platform_backend,
        "marketplace_data_backend": cfg.marketplace_data_backend,
        "alerts_backend": cfg.alerts_backend,
        "notifications_backend": cfg.notifications_backend,
        "affiliate_backend": cfg.affiliate_backend,
        "merchant_backend": cfg.merchant_backend,
        "allow_demo_reset_tokens": cfg.allow_demo_reset_tokens,
        "seed_demo_data": cfg.seed_demo_data,
        "cors_origins": list(cfg.cors_origins),
        "trusted_hosts": list(cfg.trusted_hosts),
        "launch_readiness_enabled": cfg.launch_readiness_enabled,
        "launch_strict_startup": cfg.launch_strict_startup,
        "rate_limiting_enabled": cfg.rate_limiting_enabled,
        "security_headers_enabled": cfg.security_headers_enabled,
        "structured_logging_enabled": cfg.structured_logging_enabled,
        "demo_launcher_enabled": cfg.demo_launcher_enabled,
        "performance_cache_enabled": cfg.performance_cache_enabled,
        "openapi_public_docs": cfg.openapi_public_docs,
        "user_platform_enabled": cfg.user_platform_enabled,
        "marketplace_data_enabled": cfg.marketplace_data_enabled,
        "watchlists_alerts_enabled": cfg.watchlists_alerts_enabled,
        "affiliate_enabled": cfg.affiliate_enabled,
        "merchant_platform_enabled": cfg.merchant_platform_enabled,
        "ai_review_enabled": cfg.ai_review_enabled,
        "ai_shopping_enabled": cfg.ai_shopping_enabled,
        "community_enabled": cfg.community_enabled,
        "knowledge_graph_enabled": cfg.knowledge_graph_enabled,
        "personal_agent_enabled": cfg.personal_agent_enabled,
        "rate_limits": {
            "default_per_minute": cfg.rate_limit_default_per_minute,
            "login_per_minute": cfg.rate_limit_login_per_minute,
            "registration_per_minute": cfg.rate_limit_registration_per_minute,
            "early_access_events_per_minute": cfg.rate_limit_early_access_events_per_minute,
            "affiliate_per_minute": cfg.rate_limit_affiliate_per_minute,
            "merchant_per_minute": cfg.rate_limit_merchant_per_minute,
            "search_per_minute": cfg.rate_limit_search_per_minute,
            "recommendations_per_minute": cfg.rate_limit_recommendations_per_minute,
        },
        "security_headers": {
            "csp": cfg.security_csp,
            "hsts_max_age": cfg.security_hsts_max_age,
            "frame_options": cfg.security_frame_options,
            "referrer_policy": cfg.security_referrer_policy,
            "permissions_policy": cfg.security_permissions_policy,
        },
        # Placeholders only — real secrets never exported.
        "database_url": "***REDACTED***",
        "app_secret_key": "***REDACTED***",
        "openai_api_key": "***REDACTED***",
        "anthropic_api_key": "***REDACTED***",
        "gemini_api_key": "***REDACTED***",
    }
    return redact_value(raw)


def run_startup_validation(cfg: Settings | None = None) -> ValidationResult:
    """Validate settings at startup with a single fail-closed contract.

    Production always raises on fatal configuration errors. Callers must not
    need a separate ``is_production`` check — forgetting one must not weaken
    production. ``LAUNCH_STRICT_STARTUP`` strengthens non-production
    environments but must not weaken production.
    """
    cfg = cfg or settings
    result = validate_settings(cfg)
    enforce = cfg.app_env == "production" or cfg.launch_strict_startup
    result.raise_if_fatal(enforce=enforce)
    return result
