"""Marketplace Intelligence application service.

Aggregates results from multiple :class:`MarketplaceConnector` adapters into a
single normalized search response. Connectors are injected — adding Amazon,
eBay, Facebook Marketplace, or Carousell only requires registering a new
adapter.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.marketplace_listing import (
    MarketplaceListing,
    MarketplaceSearchResult,
)
from app.domain.interfaces.marketplace_connector import MarketplaceConnector


class MarketplaceIntelligenceService:
    """Use-case orchestration for multi-marketplace search and lookup."""

    def __init__(self, connectors: Sequence[MarketplaceConnector]) -> None:
        self._connectors = list(connectors)

    @property
    def connectors(self) -> tuple[MarketplaceConnector, ...]:
        """Registered marketplace connectors."""
        return tuple(self._connectors)

    def search(self, query: str) -> MarketplaceSearchResult:
        """Search all connectors and aggregate normalized listings."""
        cleaned = query.strip()
        if not cleaned:
            return MarketplaceSearchResult(query=cleaned, results=())

        aggregated: list[MarketplaceListing] = []
        for connector in self._connectors:
            aggregated.extend(connector.search(cleaned))

        return MarketplaceSearchResult(query=cleaned, results=tuple(aggregated))
