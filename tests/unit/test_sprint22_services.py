"""Sprint 22 service-level and validation tests."""

from __future__ import annotations

from app.core.config import Settings
from app.core.validation import exportable_settings, validate_settings
from app.launch.cache import TtlCache, cache_key
from app.launch.feature_flags import FeatureFlagRegistry
from app.launch.fixtures import DemoLauncherState
from app.launch.memory import InMemoryLaunchStore
from app.launch.rate_limit import ConfigurableRateLimiter, RateLimitRule, classify_path
from app.launch.redaction import redact_value
from app.services.launch_config_service import LaunchConfigService
from app.services.launch_demo_service import LaunchDemoService
from app.services.launch_health_service import LaunchHealthService
from app.services.launch_performance_service import LaunchPerformanceService


def test_validate_production_rejects_debug() -> None:
    cfg = Settings(
        APP_ENV="production",
        APP_DEBUG=True,
        CORS_ORIGINS="https://app.example",
    )
    result = validate_settings(cfg)
    assert result.ok is False
    assert any("APP_DEBUG" in e for e in result.errors)


def test_exportable_settings_redacts_secrets() -> None:
    payload = exportable_settings()
    assert payload["database_url"] == "***REDACTED***"
    assert "password" not in str(payload).lower() or "***REDACTED***" in str(payload)


def test_redact_value_nested() -> None:
    data = redact_value({"user": "a", "token": "secret", "nested": {"api_key": "x"}})
    assert data["token"] == "***REDACTED***"
    assert data["nested"]["api_key"] == "***REDACTED***"
    assert data["user"] == "a"


def test_ttl_cache_hit_miss() -> None:
    cache = TtlCache(default_ttl_seconds=60, enabled=True)
    assert cache.get("k") is None
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
    stats = cache.stats()
    assert stats.hits == 1
    assert stats.misses == 1


def test_performance_service_memoizes() -> None:
    cache = TtlCache(enabled=True)
    perf = LaunchPerformanceService(cache)
    calls = {"n": 0}

    def factory() -> int:
        calls["n"] += 1
        return 42

    assert perf.cached("search", factory, "q1") == 42
    assert perf.cached("search", factory, "q1") == 42
    assert calls["n"] == 1


def test_classify_path_buckets() -> None:
    assert classify_path("POST", "/api/v1/auth/login") == "login"
    assert classify_path("POST", "/api/v1/auth/register") == "registration"
    assert classify_path("GET", "/api/v1/affiliate/report") == "affiliate"
    assert classify_path("GET", "/api/v1/merchants/org-x") == "merchant"
    assert classify_path("GET", "/api/v1/marketplace/search") == "search"
    assert classify_path("GET", "/api/v1/recommendations/search") == "recommendations"


def test_rate_limiter_window() -> None:
    limiter = ConfigurableRateLimiter(
        {"default": RateLimitRule("default", 2, 60)},
        enabled=True,
    )
    assert limiter.check("default", "ip:1").allowed is True
    assert limiter.check("default", "ip:1").allowed is True
    denied = limiter.check("default", "ip:1")
    assert denied.allowed is False
    assert denied.retry_after_seconds >= 1


def test_demo_launcher_personas() -> None:
    service = LaunchDemoService(DemoLauncherState())
    personas = service.list_personas()
    assert {p["persona"] for p in personas} == {
        "anonymous",
        "registered",
        "merchant",
        "admin",
    }
    switched = service.switch("admin")
    assert switched["active_persona"] == "admin"


def test_config_import_does_not_apply_secrets() -> None:
    store = InMemoryLaunchStore()
    service = LaunchConfigService(store)
    result = service.import_config(
        {"app_env": "staging", "openai_api_key": "sk-real", "rate_limiting_enabled": True}
    )
    assert result["applied_to_runtime"] is False
    assert "openai_api_key" not in result["payload"]
    assert result["payload"]["app_env"] == "staging"


def test_health_live_ready() -> None:
    cache = TtlCache(enabled=True)
    health = LaunchHealthService(cache=cache)
    live = health.live()
    assert live["live"] is True
    ready = health.ready()
    assert ready["ready"] is True
    report = health.health()
    assert report.version
    assert report.cache == "up"


def test_feature_flag_registry() -> None:
    flags = FeatureFlagRegistry().as_dict()
    assert "launch_readiness_enabled" in flags
    assert "dealscore" not in flags  # ranking is not a toggleable bias flag


def test_cache_key_stable() -> None:
    assert cache_key("search", "q") == cache_key("search", "q")
    assert cache_key("search", "q") != cache_key("search", "other")
