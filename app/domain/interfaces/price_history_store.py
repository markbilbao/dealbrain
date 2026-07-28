"""Persistence port for timestamped marketplace price snapshots."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities.price_history import PriceSnapshot


class PriceHistoryStore(ABC):
    """Abstract store for price snapshots.

    Implementations must enforce uniqueness on
    ``(canonical_product_id, marketplace, listing_id, observed_at)``.
    """

    @abstractmethod
    async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        """Persist a snapshot. Return existing row when the uniqueness key matches."""

    @abstractmethod
    async def save_many(self, snapshots: list[PriceSnapshot]) -> list[PriceSnapshot]:
        """Persist multiple snapshots with the same duplicate-protection rule."""

    @abstractmethod
    async def get_by_canonical_product(
        self,
        canonical_product_id: str,
    ) -> list[PriceSnapshot]:
        """Return all snapshots for a canonical product, ordered by observed_at ASC."""

    @abstractmethod
    async def get_by_listing(self, listing_id: str) -> list[PriceSnapshot]:
        """Return all snapshots for a marketplace listing_id, ordered by observed_at ASC."""

    @abstractmethod
    async def get_by_date_range(
        self,
        *,
        canonical_product_id: str | None = None,
        listing_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PriceSnapshot]:
        """Return snapshots filtered by optional product/listing and date range.

        Inclusive on both ends when ``start`` / ``end`` are provided.
        Ordered by observed_at ASC, then marketplace, listing_id, snapshot_id.
        """

    @abstractmethod
    async def get_by_snapshot_id(self, snapshot_id: UUID) -> PriceSnapshot | None:
        """Return a single snapshot by id, or None."""
