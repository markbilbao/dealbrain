"""Research provider port — certified execution contract.

Sprint 31 owns capability declaration, certification metadata, and routing.
Sprint 38 owns live execution. This port must not perform HTTP.
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
        """Return eligibility for one capability/market/source triple."""

    def execute(self, step: ResearchProviderStep) -> None:
        """Reserved for Sprint 38. Sprint 31 implementations must not execute."""
