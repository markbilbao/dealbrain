"""Launch admin dashboard metrics (Sprint 22).

Aggregates demo/in-memory counts only. Never touches DealScore weights or
affiliate ranking. Merchant isolation is preserved by reading org-scoped stores.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import Settings, settings
from app.core.validation import validate_settings
from app.domain.entities.launch import LaunchMetrics
from app.launch.cache import TtlCache, cache_key
from app.launch.feature_flags import FeatureFlagRegistry
from app.launch.memory import InMemoryLaunchStore
from app.launch.runtime import uptime_seconds
from app.services.launch_health_service import LaunchHealthService


class LaunchDashboardService:
    """Build the launch readiness admin dashboard payload."""

    def __init__(
        self,
        *,
        health_service: LaunchHealthService,
        feature_flags: FeatureFlagRegistry,
        store: InMemoryLaunchStore,
        cache: TtlCache,
        user_counter: Callable[[], int],
        watchlist_counter: Callable[[], int],
        merchant_counter: Callable[[], int],
        affiliate_click_counter: Callable[[], int],
        alert_counter: Callable[[], int],
        notification_counter: Callable[[], int],
        product_counter: Callable[[], int],
        offer_counter: Callable[[], int],
        campaign_counter: Callable[[], int],
        cfg: Settings | None = None,
    ) -> None:
        self._health = health_service
        self._flags = feature_flags
        self._store = store
        self._cache = cache
        self._user_counter = user_counter
        self._watchlist_counter = watchlist_counter
        self._merchant_counter = merchant_counter
        self._affiliate_click_counter = affiliate_click_counter
        self._alert_counter = alert_counter
        self._notification_counter = notification_counter
        self._product_counter = product_counter
        self._offer_counter = offer_counter
        self._campaign_counter = campaign_counter
        self._cfg = cfg or settings

    def metrics(self) -> LaunchMetrics:
        key = cache_key("launch_metrics")
        return self._cache.get_or_set(
            key,
            lambda: LaunchMetrics(
                users=self._safe_count(self._user_counter),
                watchlists=self._safe_count(self._watchlist_counter),
                merchants=self._safe_count(self._merchant_counter),
                affiliate_clicks=self._safe_count(self._affiliate_click_counter),
                alerts=self._safe_count(self._alert_counter),
                notifications=self._safe_count(self._notification_counter),
                products=self._safe_count(self._product_counter),
                offers=self._safe_count(self._offer_counter),
                campaigns=self._safe_count(self._campaign_counter),
            ),
            ttl_seconds=self._cfg.performance_cache_ttl_seconds,
        )

    def dashboard(
        self,
        *,
        database_status: str = "up",
        api_health: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metrics = self.metrics()
        validation = validate_settings(self._cfg)
        checklist = self._store.checklist_summary()
        cache_stats = self._cache.stats()
        return {
            "title": "PiqSavi Launch Dashboard",
            "environment": self._cfg.app_env,
            "uptime_seconds": round(uptime_seconds(), 3),
            "metrics": {
                "users": metrics.users,
                "watchlists": metrics.watchlists,
                "merchants": metrics.merchants,
                "affiliate_clicks": metrics.affiliate_clicks,
                "alerts": metrics.alerts,
                "notifications": metrics.notifications,
                "products": metrics.products,
                "offers": metrics.offers,
                "campaigns": metrics.campaigns,
            },
            "api_health": api_health
            or {
                "status": "up" if database_status != "down" else "degraded",
                "database": database_status,
            },
            "system_status": {
                "app_env": self._cfg.app_env,
                "app_debug": self._cfg.app_debug,
                "rate_limiting": self._cfg.rate_limiting_enabled,
                "security_headers": self._cfg.security_headers_enabled,
                "structured_logging": self._cfg.structured_logging_enabled,
                "performance_cache": self._cfg.performance_cache_enabled,
                "cache_stats": {
                    "hits": cache_stats.hits,
                    "misses": cache_stats.misses,
                    "stores": cache_stats.stores,
                    "evictions": cache_stats.evictions,
                    "size": cache_stats.size,
                },
            },
            "feature_flags": self._flags.snapshot(),
            "configuration_validation": {
                "ok": validation.ok,
                "errors": list(validation.errors),
                "warnings": list(validation.warnings),
            },
            "launch_checklist": checklist,
            "limitations": [
                "Demo/in-memory metrics only — not a production warehouse.",
                "No real cloud deployment, payments, email, SMS, or push.",
                "Organic PiqScore and recommendation ranking are unchanged.",
                "Affiliate generation remains post-rank only.",
                "Merchant isolation is preserved; no cross-org leakage.",
            ],
        }

    @staticmethod
    def _safe_count(counter: Callable[[], int]) -> int:
        try:
            return int(counter())
        except Exception:
            return 0
