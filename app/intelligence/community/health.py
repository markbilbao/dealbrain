"""Community connector health service."""

from __future__ import annotations

from typing import Any

from app.intelligence.community.registry import CommunityRegistry


class CommunityHealthService:
    """Report connector health / enablement without contacting live APIs by default."""

    def __init__(self, registry: CommunityRegistry) -> None:
        self._registry = registry

    def check(self) -> dict[str, Any]:
        status = self._registry.status_map()
        healthy = sum(1 for item in status.values() if item.get("healthy"))
        enabled = sum(1 for item in status.values() if item.get("enabled"))
        return {
            "healthy_connectors": healthy,
            "enabled_connectors": enabled,
            "total_connectors": len(status),
            "connectors": status,
            "overall": "ok" if healthy > 0 else "degraded",
        }

    def is_source_healthy(self, source: str) -> bool:
        provider = self._registry.get(source)
        if provider is None:
            return False
        return provider.health_check()
