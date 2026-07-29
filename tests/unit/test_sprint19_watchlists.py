"""Unit tests for Sprint 19 watchlist extensions (ExtendedWatchlistService).

Covers ownership, lifecycle (pause/resume/archive), default watchlists,
idempotent item adds, target price validation, history, and preferred
sellers. Mirrors the fixture-building patterns in
``tests/unit/test_watchlist_service.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.watchlist import ItemKind, WatchlistStatus
from app.domain.exceptions import (
    WatchlistItemNotFoundError,
    WatchlistOwnershipError,
    WatchlistValidationError,
)
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.services.price_history_service import PriceHistoryService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.watchlists.memory import InMemoryWatchlistStore
from app.watchlists.security import WatchlistAuditLogger

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _build_service() -> tuple[ExtendedWatchlistService, InMemoryWatchlistStore]:
    store = InMemoryWatchlistStore()
    price = PriceHistoryService(InMemoryPriceHistoryStore(), app_env="development")
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"id-{counter['n']}"

    service = ExtendedWatchlistService(
        store,
        price_history_service=price,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        audit_logger=WatchlistAuditLogger(clock=lambda: FIXED_NOW, id_factory=next_id),
    )
    return service, store


# --------------------------------------------------------------------- creation


def test_create_watchlist_with_owner() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    assert wl.owner_id == "user-1"
    assert wl.status == WatchlistStatus.ACTIVE
    assert wl.is_default is False


def test_create_multiple_watchlists_per_owner() -> None:
    service, _ = _build_service()
    wl1 = service.create_watchlist(name="Phones", owner_id="user-1")
    wl2 = service.create_watchlist(name="Laptops", owner_id="user-1")
    listed = service.list_watchlists(owner_id="user-1")
    assert {w.watchlist_id for w in listed} == {wl1.watchlist_id, wl2.watchlist_id}


def test_default_watchlist_is_unique_per_owner() -> None:
    service, _ = _build_service()
    first = service.create_watchlist(name="Phones", owner_id="user-1", is_default=True)
    second = service.create_watchlist(name="Laptops", owner_id="user-1", is_default=True)

    refreshed_first = service.get_watchlist(first.watchlist_id)
    assert refreshed_first.is_default is False
    assert service.get_watchlist(second.watchlist_id).is_default is True


def test_default_watchlist_scoped_per_owner() -> None:
    """Two different owners may each have their own default watchlist."""
    service, _ = _build_service()
    a = service.create_watchlist(name="A", owner_id="user-a", is_default=True)
    b = service.create_watchlist(name="B", owner_id="user-b", is_default=True)
    assert service.get_watchlist(a.watchlist_id).is_default is True
    assert service.get_watchlist(b.watchlist_id).is_default is True


# --------------------------------------------------------------------- ownership


def test_require_owner_allows_owner() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    assert service.require_owner(wl.watchlist_id, "user-1").watchlist_id == wl.watchlist_id


def test_require_owner_rejects_other_user() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    with pytest.raises(WatchlistOwnershipError):
        service.require_owner(wl.watchlist_id, "user-2")


def test_require_owner_allows_any_caller_for_unowned_watchlist() -> None:
    """Sprint 10 fixtures with owner_id=None remain accessible to anyone."""
    service, _ = _build_service()
    wl = service.create_watchlist(name="Legacy")
    assert service.require_owner(wl.watchlist_id, "anyone").watchlist_id == wl.watchlist_id


# --------------------------------------------------------------------- items


@pytest.mark.asyncio
async def test_add_and_remove_product() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_item_idempotent(
        wl.watchlist_id, canonical_product_id="prod-1", product_label="Phone 1"
    )
    assert item.canonical_product_id == "prod-1"
    assert item.item_kind == ItemKind.PRODUCT

    service.delete_item(item.item_id)
    with pytest.raises(WatchlistItemNotFoundError):
        service.get_item(item.item_id)


@pytest.mark.asyncio
async def test_add_item_idempotent_returns_existing_on_duplicate() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    first = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")
    second = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")
    assert first.item_id == second.item_id
    assert len(service.list_items(wl.watchlist_id)) == 1


@pytest.mark.asyncio
async def test_add_item_idempotent_can_raise_when_disabled() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")
    with pytest.raises(WatchlistValidationError):
        await service.add_item_idempotent(
            wl.watchlist_id, canonical_product_id="prod-1", return_existing=False
        )


@pytest.mark.asyncio
async def test_target_price_validation() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    with pytest.raises(WatchlistValidationError):
        await service.add_item_idempotent(
            wl.watchlist_id, canonical_product_id="prod-1", target_price=-5.0
        )


@pytest.mark.asyncio
async def test_add_offer_tracks_marketplace_offer() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_offer(
        wl.watchlist_id, marketplace_offer_id="offer-99", product_label="Great Deal"
    )
    assert item.item_kind == ItemKind.OFFER
    assert item.marketplace_offer_id == "offer-99"


# --------------------------------------------------------------------- lifecycle


def test_pause_resume_watchlist() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    paused = service.pause_watchlist(wl.watchlist_id, actor_id="user-1")
    assert paused.status == WatchlistStatus.PAUSED
    assert paused.enabled is False
    assert paused.paused_at is not None

    resumed = service.resume_watchlist(wl.watchlist_id, actor_id="user-1")
    assert resumed.status == WatchlistStatus.ACTIVE
    assert resumed.enabled is True
    assert resumed.paused_at is None


def test_archive_watchlist_is_terminal_and_disabled() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    archived = service.archive_watchlist(wl.watchlist_id, actor_id="user-1")
    assert archived.status == WatchlistStatus.ARCHIVED
    assert archived.enabled is False
    assert archived.archived_at is not None
    # Archived watchlists are excluded from enabled-only listings used by
    # alert evaluation scans.
    active_only = [w.watchlist_id for w in service.list_watchlists(enabled=True)]
    assert archived.watchlist_id not in active_only


# --------------------------------------------------------------------- history


@pytest.mark.asyncio
async def test_watchlist_history_records_lifecycle_events() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")
    service.pause_watchlist(wl.watchlist_id)
    service.resume_watchlist(wl.watchlist_id)
    service.archive_watchlist(wl.watchlist_id)

    history = service.get_history(wl.watchlist_id, limit=50)
    event_types = [entry.event_type for entry in history]
    assert "watchlist_created" in event_types
    assert "item_added" in event_types
    assert "watchlist_paused" in event_types
    assert "watchlist_resumed" in event_types
    assert "watchlist_archived" in event_types
    # Newest first.
    assert history[0].event_type == "watchlist_archived"
    assert any(entry.item_id == item.item_id for entry in history)


# --------------------------------------------------------------------- preferred sellers


def test_set_watchlist_preferred_sellers_dedupes_and_strips() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    updated = service.set_watchlist_preferred_sellers(
        wl.watchlist_id, sellers=[" Shopee Official ", "Lazada Mall", "Shopee Official", ""]
    )
    assert updated.preferred_sellers == ("Shopee Official", "Lazada Mall")


@pytest.mark.asyncio
async def test_set_item_preferred_sellers_and_marketplaces() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")

    updated = service.set_item_preferred_sellers(item.item_id, sellers=["Seller A"])
    assert updated.preferred_sellers == ("Seller A",)

    updated = service.set_item_preferred_marketplaces(item.item_id, marketplaces=["shopee"])
    assert updated.preferred_marketplaces == ("shopee",)


@pytest.mark.asyncio
async def test_item_monitoring_pause_and_resume() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")

    paused = service.pause_item_monitoring(item.item_id)
    assert paused.monitoring_paused is True

    resumed = service.resume_item_monitoring(item.item_id)
    assert resumed.monitoring_paused is False


@pytest.mark.asyncio
async def test_item_notes_can_be_set_and_cleared() -> None:
    service, _ = _build_service()
    wl = service.create_watchlist(name="Phones", owner_id="user-1")
    item = await service.add_item_idempotent(wl.watchlist_id, canonical_product_id="prod-1")

    updated = service.set_item_notes(item.item_id, notes="  Waiting for a sale  ")
    assert updated.notes == "Waiting for a sale"

    cleared = service.set_item_notes(item.item_id, notes=None)
    assert cleared.notes is None


# --------------------------------------------------------------------- filters


def test_list_watchlists_filters_by_status() -> None:
    service, _ = _build_service()
    active = service.create_watchlist(name="Active", owner_id="user-1")
    to_archive = service.create_watchlist(name="ToArchive", owner_id="user-1")
    service.archive_watchlist(to_archive.watchlist_id)

    archived_only = service.list_watchlists(owner_id="user-1", status="archived")
    assert [w.watchlist_id for w in archived_only] == [to_archive.watchlist_id]

    active_only = service.list_watchlists(owner_id="user-1", status="active")
    assert [w.watchlist_id for w in active_only] == [active.watchlist_id]
