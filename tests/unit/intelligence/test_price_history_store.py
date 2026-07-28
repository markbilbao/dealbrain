"""Unit tests for InMemoryPriceHistoryStore and SQLAlchemy adapter mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot
from app.infrastructure.database.models.price_snapshot import PriceSnapshotModel
from app.infrastructure.database.repositories.price_history_repository import (
    SQLAlchemyPriceHistoryStore,
    _to_entity,
)
from app.intelligence.price_history import InMemoryPriceHistoryStore


def _snap(
    *,
    product_id: str = "prod-1",
    marketplace: str = "shopee",
    listing_id: str = "1001001",
    observed_at: datetime | None = None,
    total: float = 100.0,
    snapshot_id: UUID | None = None,
) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id=snapshot_id or uuid4(),
        canonical_product_id=product_id,
        marketplace=marketplace,
        listing_id=listing_id,
        seller_name="Seller",
        currency="PHP",
        item_price=total,
        shipping_cost=0.0,
        total_cost=total,
        availability=AvailabilityStatus.IN_STOCK,
        observed_at=observed_at or datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_save_one_snapshot() -> None:
    store = InMemoryPriceHistoryStore()
    snap = _snap()
    saved = await store.save(snap)
    assert saved.snapshot_id == snap.snapshot_id
    history = await store.get_by_canonical_product("prod-1")
    assert len(history) == 1


@pytest.mark.asyncio
async def test_save_multiple_snapshots() -> None:
    store = InMemoryPriceHistoryStore()
    snaps = [
        _snap(observed_at=datetime(2026, 1, 1, tzinfo=UTC), total=1.0),
        _snap(observed_at=datetime(2026, 1, 2, tzinfo=UTC), total=2.0),
        _snap(observed_at=datetime(2026, 1, 3, tzinfo=UTC), total=3.0),
    ]
    saved = await store.save_many(snaps)
    assert len(saved) == 3
    assert len(await store.get_by_canonical_product("prod-1")) == 3


@pytest.mark.asyncio
async def test_duplicate_protection() -> None:
    store = InMemoryPriceHistoryStore()
    first = _snap(snapshot_id=UUID("11111111-1111-4111-8111-111111111111"))
    duplicate = _snap(snapshot_id=UUID("22222222-2222-4222-8222-222222222222"))
    saved_first = await store.save(first)
    saved_dup = await store.save(duplicate)
    assert saved_dup.snapshot_id == saved_first.snapshot_id
    assert len(await store.get_by_canonical_product("prod-1")) == 1


@pytest.mark.asyncio
async def test_identical_timestamps_same_key_deduped() -> None:
    store = InMemoryPriceHistoryStore()
    ts = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    a = _snap(observed_at=ts, total=10.0)
    b = _snap(observed_at=ts, total=99.0)
    await store.save(a)
    saved_b = await store.save(b)
    assert saved_b.total_cost == 10.0
    assert len(await store.get_by_listing("1001001")) == 1


@pytest.mark.asyncio
async def test_listing_and_product_retrieval() -> None:
    store = InMemoryPriceHistoryStore()
    await store.save(
        _snap(product_id="p1", listing_id="L1", observed_at=datetime(2026, 1, 1, tzinfo=UTC))
    )
    await store.save(
        _snap(product_id="p1", listing_id="L2", observed_at=datetime(2026, 1, 2, tzinfo=UTC))
    )
    await store.save(
        _snap(product_id="p2", listing_id="L1", observed_at=datetime(2026, 1, 3, tzinfo=UTC))
    )
    assert len(await store.get_by_canonical_product("p1")) == 2
    assert len(await store.get_by_listing("L1")) == 2


@pytest.mark.asyncio
async def test_date_range_filtering() -> None:
    store = InMemoryPriceHistoryStore()
    await store.save_many(
        [
            _snap(observed_at=datetime(2026, 1, 1, tzinfo=UTC), total=1),
            _snap(observed_at=datetime(2026, 1, 15, tzinfo=UTC), total=2),
            _snap(observed_at=datetime(2026, 2, 1, tzinfo=UTC), total=3),
        ]
    )
    ranged = await store.get_by_date_range(
        canonical_product_id="prod-1",
        start=datetime(2026, 1, 10, tzinfo=UTC),
        end=datetime(2026, 1, 31, tzinfo=UTC),
    )
    assert len(ranged) == 1
    assert ranged[0].total_cost == 2.0


@pytest.mark.asyncio
async def test_deterministic_ordering_from_store() -> None:
    store = InMemoryPriceHistoryStore()
    await store.save(
        _snap(
            marketplace="shopee",
            listing_id="2",
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            total=2,
        )
    )
    await store.save(
        _snap(
            marketplace="lazada",
            listing_id="1",
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            total=1,
        )
    )
    history = await store.get_by_canonical_product("prod-1")
    assert history[0].marketplace == "lazada"
    assert history[1].marketplace == "shopee"


def test_sqlalchemy_model_to_entity_mapping() -> None:
    row = MagicMock(spec=PriceSnapshotModel)
    row.snapshot_id = UUID("aaaaaaaa-0001-4000-8000-000000000001")
    row.canonical_product_id = "prod-1"
    row.marketplace = "shopee"
    row.listing_id = "1001001"
    row.seller_name = "Seller"
    row.currency = "PHP"
    row.item_price = 100.0
    row.shipping_cost = 10.0
    row.total_cost = 110.0
    row.availability = "in_stock"
    row.observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    entity = _to_entity(row)
    assert entity.total_cost == 110.0
    assert entity.availability == AvailabilityStatus.IN_STOCK


@pytest.mark.asyncio
async def test_sqlalchemy_store_save_returns_existing_on_conflict() -> None:
    session = AsyncMock()
    existing = _snap(snapshot_id=UUID("aaaaaaaa-0001-4000-8000-000000000001"))

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=insert_result)
    session.commit = AsyncMock()

    store = SQLAlchemyPriceHistoryStore(session)

    # Patch private lookup used after conflict.
    async def _find(_snapshot: PriceSnapshot) -> PriceSnapshot:
        return existing

    store._find_by_uniqueness_key = _find  # type: ignore[method-assign]
    incoming = _snap(snapshot_id=UUID("bbbbbbbb-0001-4000-8000-000000000002"))
    saved = await store.save(incoming)
    assert saved.snapshot_id == existing.snapshot_id
    session.commit.assert_awaited()
