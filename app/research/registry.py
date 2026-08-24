"""Server-authoritative technical research provider registry.

Deterministic, browser-immutable, and empty of production providers.
Answers what implementations exist and what they can technically do.
Certification is a separate catalog authority. Routing preference is a
separate trusted policy catalog.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.research_execution import ResearchProviderDescriptor
from app.research.digest import stable_sha256
from app.research.providers import StaticResearchProvider


class ResearchProviderRegistry:
    """Catalog of research provider implementations.

    Duplicate ``provider_id`` values are rejected. Production construction
    (``allow_test_providers=False``) refuses test fixtures. Registration is
    not certification.
    """

    def __init__(
        self,
        providers: Sequence[StaticResearchProvider] | None = None,
        *,
        allow_test_providers: bool = False,
    ) -> None:
        self._allow_test_providers = allow_test_providers
        self._providers: dict[str, StaticResearchProvider] = {}
        self._order: list[str] = []
        for provider in providers or ():
            self.register(provider)

    @property
    def allows_test_providers(self) -> bool:
        return self._allow_test_providers

    def register(self, provider: StaticResearchProvider) -> StaticResearchProvider:
        descriptor = provider.descriptor
        if descriptor.test_fixture and not self._allow_test_providers:
            raise ValueError("test providers cannot be registered in the production registry")
        if descriptor.provider_id in self._providers:
            raise ValueError(f"duplicate provider_id: {descriptor.provider_id}")
        self._order.append(descriptor.provider_id)
        self._providers[descriptor.provider_id] = provider
        return provider

    def get(self, provider_id: str) -> StaticResearchProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> tuple[StaticResearchProvider, ...]:
        return tuple(self._providers[provider_id] for provider_id in self._order)

    def list_descriptors(self) -> tuple[ResearchProviderDescriptor, ...]:
        return tuple(provider.descriptor for provider in self.list_providers())

    def fingerprint(self) -> str:
        """Deterministic technical catalog identity for plan digests."""

        payload = [
            {
                "provider_id": descriptor.provider_id,
                "supported_markets": list(descriptor.supported_markets),
                "supported_capabilities": [
                    item.value for item in descriptor.supported_capabilities
                ],
                "supported_sources": list(descriptor.supported_sources),
            }
            for descriptor in self.list_descriptors()
        ]
        return stable_sha256({"kind": "research_provider_registry_v1", "providers": payload})


def production_research_provider_registry() -> ResearchProviderRegistry:
    """Fail-closed production catalog. No certified providers yet.

    Sprints 32–36 own populating certified merchant/market evidence.
    Product Foundation fixtures and test providers are never registered.
    """

    return ResearchProviderRegistry(allow_test_providers=False)


def research_provider_registry_for_tests(
    providers: Sequence[StaticResearchProvider],
) -> ResearchProviderRegistry:
    """Explicit test catalog. Callers must pass fixtures; nothing is implicit."""

    return ResearchProviderRegistry(providers, allow_test_providers=True)
