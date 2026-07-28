"""In-memory PriceHistoryStore for local development and tests."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.domain.entities.price_history import PriceSnapshot
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.intelligence.price_history.statistics import sort_snapshots


def snapshot_uniqueness_key(snapshot: PriceSnapshot) -> tuple[str, str, str, datetime]:
    """Deterministic uniqueness key for duplicate protection."""
    return (
        snapshot.canonical_product_id,
        snapshot.marketplace.lower(),
        snapshot.listing_id,
        snapshot.observed_at,
    )


class InMemoryPriceHistoryStore(PriceHistoryStore):
    """Process-local store — replaceable with the SQLAlchemy adapter."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, PriceSnapshot] = {}
        self._by_key: dict[tuple[str, str, str, datetime], UUID] = {}

    def clear(self) -> None:
        """Remove all snapshots (tests / fixture reloads)."""
        self._by_id.clear()
        self._by_key.clear()

    async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        key = snapshot_uniqueness_key(snapshot)
        existing_id = self._by_key.get(key)
        if existing_id is not None:
            return self._by_id[existing_id]
        self._by_id[snapshot.snapshot_id] = snapshot
        self._by_key[key] = snapshot.snapshot_id
        return snapshot

    async def save_many(self, snapshots: list[PriceSnapshot]) -> list[PriceSnapshot]:
        saved: list[PriceSnapshot] = []
        for snapshot in snapshots:
            saved.append(await self.save(snapshot))
        return saved

    async def get_by_canonical_product(
        self,
        canonical_product_id: str,
    ) -> list[PriceSnapshot]:
        matches = [
            snapshot
            for snapshot in self._by_id.values()
            if snapshot.canonical_product_id == canonical_product_id
        ]
        return sort_snapshots(matches)

    async def get_by_listing(self, listing_id: str) -> list[PriceSnapshot]:
        matches = [
            snapshot for snapshot in self._by_id.values() if snapshot.listing_id == listing_id
        ]
        return sort_snapshots(matches)

    async def get_by_date_range(
        self,
        *,
        canonical_product_id: str | None = None,
        listing_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PriceSnapshot]:
        matches: list[PriceSnapshot] = []
        for snapshot in self._by_id.values():
            if (
                canonical_product_id is not None
                and snapshot.canonical_product_id != canonical_product_id
            ):
                continue
            if listing_id is not None and snapshot.listing_id != listing_id:
                continue
            if start is not None and snapshot.observed_at < start:
                continue
            if end is not None and snapshot.observed_at > end:
                continue
            matches.append(snapshot)
        return sort_snapshots(matches)

    async def get_by_snapshot_id(self, snapshot_id: UUID) -> PriceSnapshot | None:
        return self._by_id.get(snapshot_id)
