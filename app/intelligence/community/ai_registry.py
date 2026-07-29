"""Registry for community AI summary providers."""

from __future__ import annotations

from app.domain.interfaces.community_intelligence_repository import CommunitySummaryProvider


class CommunitySummaryRegistry:
    """Name → community summary provider lookup."""

    def __init__(
        self,
        providers: list[CommunitySummaryProvider],
        *,
        fallback_order: list[str] | None = None,
    ) -> None:
        self._providers = {provider.provider_name: provider for provider in providers}
        order = list(fallback_order or ["openai", "anthropic", "gemini", "deterministic"])
        if "deterministic" in self._providers and "deterministic" not in order:
            order = [*order, "deterministic"]
        self._order = order

    def get(self, name: str) -> CommunitySummaryProvider | None:
        return self._providers.get(name)

    def fallback_order(self) -> list[str]:
        return list(self._order)

    def all(self) -> list[CommunitySummaryProvider]:
        return list(self._providers.values())
