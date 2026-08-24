"""Research provider port — certified execution contract.

Sprint 31 owns technical capability declaration and routing against
separate trusted certification and routing-policy catalogs. Sprint 38
owns live execution. This port must not perform HTTP.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.research_execution import (
    ProviderEligibility,
    ResearchCapability,
    ResearchProviderDescriptor,
    ResearchProviderStep,
)


class ResearchProvider(Protocol):
    """Provider-neutral research execution contract."""

    @property
    def descriptor(self) -> ResearchProviderDescriptor:
        """Server-known metadata. Must not include secrets."""

    def supports(
        self,
        capability: ResearchCapability,
        market: str | None,
        source: str | None,
    ) -> ProviderEligibility:
        """Return technical support for one capability/market/source triple.

        Technical support is not production certification or routing preference.
        """

    def execute(self, step: ResearchProviderStep) -> None:
        """Reserved for Sprint 38. Sprint 31 implementations must not execute."""
