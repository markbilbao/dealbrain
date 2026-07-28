"""SQLAlchemy adapter for the PriceHistoryStore port."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.infrastructure.database.models.price_snapshot import PriceSnapshotModel
from app.intelligence.price_history.memory import snapshot_uniqueness_key
from app.intelligence.price_history.statistics import sort_snapshots


def _to_entity(row: PriceSnapshotModel) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id=row.snapshot_id,
        canonical_product_id=row.canonical_product_id,
        marketplace=row.marketplace,
        listing_id=row.listing_id,
        seller_name=row.seller_name,
        currency=row.currency,
        item_price=row.item_price,
        shipping_cost=row.shipping_cost,
        total_cost=row.total_cost,
        availability=AvailabilityStatus(row.availability),
        observed_at=row.observed_at,
    )


class SQLAlchemyPriceHistoryStore(PriceHistoryStore):
    """PostgreSQL-backed price snapshot store with uniqueness protection."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        stmt = (
            insert(PriceSnapshotModel)
            .values(
                snapshot_id=snapshot.snapshot_id,
                canonical_product_id=snapshot.canonical_product_id,
                marketplace=snapshot.marketplace,
                listing_id=snapshot.listing_id,
                seller_name=snapshot.seller_name,
                currency=snapshot.currency,
                item_price=snapshot.item_price,
                shipping_cost=snapshot.shipping_cost,
                total_cost=snapshot.total_cost,
                availability=snapshot.availability.value,
                observed_at=snapshot.observed_at,
            )
            .on_conflict_do_nothing(
                constraint="uq_price_snapshot_observation",
            )
            .returning(PriceSnapshotModel.snapshot_id)
        )
        result = await self._session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        await self._session.commit()

        if inserted_id is not None:
            row = await self._session.get(PriceSnapshotModel, inserted_id)
            assert row is not None
            return _to_entity(row)

        existing = await self._find_by_uniqueness_key(snapshot)
        assert existing is not None
        return existing

    async def save_many(self, snapshots: list[PriceSnapshot]) -> list[PriceSnapshot]:
        saved: list[PriceSnapshot] = []
        for snapshot in snapshots:
            saved.append(await self.save(snapshot))
        return saved

    async def get_by_canonical_product(
        self,
        canonical_product_id: str,
    ) -> list[PriceSnapshot]:
        result = await self._session.execute(
            select(PriceSnapshotModel)
            .where(PriceSnapshotModel.canonical_product_id == canonical_product_id)
            .order_by(
                PriceSnapshotModel.observed_at.asc(),
                PriceSnapshotModel.marketplace.asc(),
                PriceSnapshotModel.listing_id.asc(),
                PriceSnapshotModel.snapshot_id.asc(),
            )
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def get_by_listing(self, listing_id: str) -> list[PriceSnapshot]:
        result = await self._session.execute(
            select(PriceSnapshotModel)
            .where(PriceSnapshotModel.listing_id == listing_id)
            .order_by(
                PriceSnapshotModel.observed_at.asc(),
                PriceSnapshotModel.marketplace.asc(),
                PriceSnapshotModel.listing_id.asc(),
                PriceSnapshotModel.snapshot_id.asc(),
            )
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def get_by_date_range(
        self,
        *,
        canonical_product_id: str | None = None,
        listing_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PriceSnapshot]:
        stmt = select(PriceSnapshotModel)
        if canonical_product_id is not None:
            stmt = stmt.where(
                PriceSnapshotModel.canonical_product_id == canonical_product_id
            )
        if listing_id is not None:
            stmt = stmt.where(PriceSnapshotModel.listing_id == listing_id)
        if start is not None:
            stmt = stmt.where(PriceSnapshotModel.observed_at >= start)
        if end is not None:
            stmt = stmt.where(PriceSnapshotModel.observed_at <= end)
        stmt = stmt.order_by(
            PriceSnapshotModel.observed_at.asc(),
            PriceSnapshotModel.marketplace.asc(),
            PriceSnapshotModel.listing_id.asc(),
            PriceSnapshotModel.snapshot_id.asc(),
        )
        result = await self._session.execute(stmt)
        return sort_snapshots([_to_entity(row) for row in result.scalars().all()])

    async def get_by_snapshot_id(self, snapshot_id: UUID) -> PriceSnapshot | None:
        row = await self._session.get(PriceSnapshotModel, snapshot_id)
        return _to_entity(row) if row else None

    async def _find_by_uniqueness_key(self, snapshot: PriceSnapshot) -> PriceSnapshot | None:
        _canonical, marketplace, listing_id, observed_at = snapshot_uniqueness_key(snapshot)
        result = await self._session.execute(
            select(PriceSnapshotModel).where(
                PriceSnapshotModel.canonical_product_id == snapshot.canonical_product_id,
                PriceSnapshotModel.marketplace == marketplace,
                PriceSnapshotModel.listing_id == listing_id,
                PriceSnapshotModel.observed_at == observed_at,
            )
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None
