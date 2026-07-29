"""Feature flag registry for launch readiness (Sprint 22).

Flags are derived from Settings so operators can toggle surfaces without code
changes. Flags never alter DealScore or organic ranking weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, settings


@dataclass(frozen=True, slots=True)
class FeatureFlag:
    """A single named feature flag with its effective value."""

    name: str
    enabled: bool
    description: str
    category: str


class FeatureFlagRegistry:
    """Read-only view of launch and product feature flags."""

    def __init__(self, cfg: Settings | None = None) -> None:
        self._cfg = cfg or settings

    def all_flags(self) -> list[FeatureFlag]:
        cfg = self._cfg
        return [
            FeatureFlag(
                "launch_readiness_enabled",
                cfg.launch_readiness_enabled,
                "Sprint 22 launch dashboard, probes, and ops tooling",
                "launch",
            ),
            FeatureFlag(
                "rate_limiting_enabled",
                cfg.rate_limiting_enabled,
                "HTTP rate limiting for auth, search, affiliate, merchant",
                "security",
            ),
            FeatureFlag(
                "security_headers_enabled",
                cfg.security_headers_enabled,
                "CSP, HSTS, frame options, and related response headers",
                "security",
            ),
            FeatureFlag(
                "structured_logging_enabled",
                cfg.structured_logging_enabled,
                "JSON structured request and event logging",
                "ops",
            ),
            FeatureFlag(
                "demo_launcher_enabled",
                cfg.demo_launcher_enabled,
                "Persona switching and seeded demo launcher",
                "demo",
            ),
            FeatureFlag(
                "performance_cache_enabled",
                cfg.performance_cache_enabled,
                "Short-TTL dedupe cache for repeated read queries",
                "performance",
            ),
            FeatureFlag(
                "user_platform_enabled",
                cfg.user_platform_enabled,
                "User accounts, auth, saved items",
                "product",
            ),
            FeatureFlag(
                "marketplace_data_enabled",
                cfg.marketplace_data_enabled,
                "Marketplace sync / import connectors",
                "product",
            ),
            FeatureFlag(
                "watchlists_alerts_enabled",
                cfg.watchlists_alerts_enabled,
                "Watchlists, alert rules, notifications, dashboard",
                "product",
            ),
            FeatureFlag(
                "affiliate_enabled",
                cfg.affiliate_enabled,
                "Affiliate link generation and reporting (post-rank)",
                "product",
            ),
            FeatureFlag(
                "merchant_platform_enabled",
                cfg.merchant_platform_enabled,
                "Merchant org workspace and admin review",
                "product",
            ),
            FeatureFlag(
                "ai_review_enabled",
                cfg.ai_review_enabled,
                "AI review summaries (live HTTP separately gated)",
                "ai",
            ),
            FeatureFlag(
                "ai_shopping_enabled",
                cfg.ai_shopping_enabled,
                "AI shopping assistant (live HTTP separately gated)",
                "ai",
            ),
            FeatureFlag(
                "community_enabled",
                cfg.community_enabled,
                "Community intelligence connectors",
                "product",
            ),
            FeatureFlag(
                "knowledge_graph_enabled",
                cfg.knowledge_graph_enabled,
                "In-memory knowledge graph queries",
                "product",
            ),
            FeatureFlag(
                "personal_agent_enabled",
                cfg.personal_agent_enabled,
                "Personal AI shopping agent profiles",
                "product",
            ),
        ]

    def as_dict(self) -> dict[str, bool]:
        return {flag.name: flag.enabled for flag in self.all_flags()}

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "name": f.name,
                "enabled": f.enabled,
                "description": f.description,
                "category": f.category,
            }
            for f in self.all_flags()
        ]


def get_feature_flags(cfg: Settings | None = None) -> FeatureFlagRegistry:
    return FeatureFlagRegistry(cfg)
