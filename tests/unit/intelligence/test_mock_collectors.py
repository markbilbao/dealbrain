"""Unit tests for mock marketplace collectors and deterministic ids."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.collection import CollectionStatus, CollectionTarget
from app.intelligence.collection.ids import make_collection_run_id
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.shopee import MockShopeeCollector

FIXED_NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def _clock() -> datetime:
    return FIXED_NOW


def test_identical_inputs_produce_identical_collection_results() -> None:
    shopee = MockShopeeCollector(clock=_clock)
    target = CollectionTarget(query="iPhone 17 Pro Max", scenario="success")
    first = shopee.collect(target)
    second = shopee.collect(target)
    assert first.to_dict() == second.to_dict()
    assert first.status == CollectionStatus.COMPLETED
    assert first.successful_listing_count >= 1


def test_make_collection_run_id_is_deterministic() -> None:
    a = make_collection_run_id(
        query="iPhone",
        marketplaces=("shopee", "lazada"),
        observed_at=FIXED_NOW,
    )
    b = make_collection_run_id(
        query="iPhone",
        marketplaces=("lazada", "shopee"),
        observed_at=FIXED_NOW,
    )
    assert a == b
    assert a.startswith("colrun_")


def test_empty_scenario() -> None:
    collector = MockLazadaCollector(clock=_clock)
    result = collector.collect(CollectionTarget(query="iPhone", scenario="empty"))
    assert result.successful_listing_count == 0
    assert result.status == CollectionStatus.COMPLETED


def test_total_failure_scenario() -> None:
    collector = MockShopeeCollector(clock=_clock)
    result = collector.collect(CollectionTarget(query="iPhone", scenario="total_failure"))
    assert result.status == CollectionStatus.FAILED
    assert result.errors
    assert result.errors[0].code == "total_failure"
    assert result.errors[0].retryable is False


def test_partial_failure_scenario() -> None:
    collector = MockShopeeCollector(clock=_clock)
    result = collector.collect(
        CollectionTarget(query="iPhone 17 Pro Max", scenario="partial_failure")
    )
    assert result.status == CollectionStatus.PARTIALLY_COMPLETED
    assert result.successful_listing_count >= 1
    assert result.failed_listing_count >= 1


def test_unavailable_scenario() -> None:
    collector = MockShopeeCollector(clock=_clock)
    result = collector.collect(CollectionTarget(query="Galaxy", scenario="unavailable"))
    assert result.listings
    assert result.listings[0].listing.availability.value == "out_of_stock"


def test_malformed_scenario() -> None:
    collector = MockLazadaCollector(clock=_clock)
    result = collector.collect(CollectionTarget(query="iPhone", scenario="malformed"))
    assert any(error.code == "malformed_listing" for error in result.errors)


def test_duplicate_scenario() -> None:
    collector = MockShopeeCollector(clock=_clock)
    result = collector.collect(
        CollectionTarget(query="iPhone 17 Pro Max", scenario="duplicate")
    )
    assert result.successful_listing_count == 2
    assert result.listings[0].is_duplicate is False
    assert result.listings[1].is_duplicate is True


def test_health_check() -> None:
    assert MockShopeeCollector().health_check() is True
    assert MockLazadaCollector().health_check() is True
