"""MarketplaceCollector port — pluggable collection adapters.

Implementations gather listings for a CollectionTarget and return normalized
CollectedListing objects. Live HTTP is not required; mock adapters are valid.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.collection import CollectionResult, CollectionTarget


class MarketplaceCollector(ABC):
    """Abstract contract for collecting listings from one marketplace."""

    @property
    @abstractmethod
    def marketplace_name(self) -> str:
        """Stable marketplace identifier (e.g. ``shopee``, ``lazada``)."""

    @abstractmethod
    def collect(self, target: CollectionTarget) -> CollectionResult:
        """Collect listings for ``target`` and return a normalized result.

        Callers inject run identifiers and timestamps via target context or
        constructor dependencies — collectors must not invent random UUIDs.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return ``True`` when the collector is ready to accept work."""
