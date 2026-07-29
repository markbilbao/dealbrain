"""Registry of AI review providers with configurable fallback order."""

from __future__ import annotations

from app.domain.interfaces.ai_review_provider import AIReviewProvider


class AIProviderRegistry:
    """Lookup and ordered fallback for AIReviewProvider adapters."""

    def __init__(
        self,
        providers: list[AIReviewProvider],
        *,
        fallback_order: list[str] | None = None,
    ) -> None:
        self._providers = {provider.provider_name: provider for provider in providers}
        order = fallback_order or list(self._providers.keys())
        # Ensure deterministic is always last resort.
        if "deterministic" in self._providers and "deterministic" not in order:
            order = [*order, "deterministic"]
        self._fallback_order = order

    def get(self, name: str) -> AIReviewProvider | None:
        return self._providers.get(name)

    def all(self) -> list[AIReviewProvider]:
        return list(self._providers.values())

    def fallback_order(self) -> list[str]:
        return list(self._fallback_order)

    def available_in_order(self, names: list[str] | None = None) -> list[AIReviewProvider]:
        sequence = names or self._fallback_order
        found: list[AIReviewProvider] = []
        for name in sequence:
            provider = self._providers.get(name)
            if provider is not None and provider.is_available():
                found.append(provider)
        return found

    def require_deterministic(self) -> AIReviewProvider:
        provider = self._providers.get("deterministic")
        if provider is None:
            raise RuntimeError("DeterministicReviewProvider is not registered.")
        return provider
