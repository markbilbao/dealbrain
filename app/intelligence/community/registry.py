"""Pluggable registry of community source providers."""

from __future__ import annotations

from app.domain.entities.community_intelligence import CommunitySource
from app.domain.interfaces.community_intelligence_repository import CommunityProvider


class CommunityRegistry:
    """Name → CommunityProvider lookup. Future connectors register here."""

    def __init__(self, providers: list[CommunityProvider] | None = None) -> None:
        self._providers: dict[str, CommunityProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: CommunityProvider) -> None:
        self._providers[provider.source_name] = provider

    def get(self, source: CommunitySource | str) -> CommunityProvider | None:
        return self._providers.get(str(source))

    def all(self) -> list[CommunityProvider]:
        return list(self._providers.values())

    def enabled(self) -> list[CommunityProvider]:
        return [provider for provider in self._providers.values() if provider.is_enabled()]

    def available(self) -> list[CommunityProvider]:
        return [provider for provider in self._providers.values() if provider.is_available()]

    def sources(self) -> list[str]:
        return list(self._providers.keys())

    def status_map(self) -> dict[str, dict[str, bool]]:
        return {
            name: {
                "enabled": provider.is_enabled(),
                "available": provider.is_available(),
                "healthy": provider.health_check(),
            }
            for name, provider in self._providers.items()
        }
