"""Unit tests for deterministic price statistics and trend classification."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.domain.entities.marketplace_listing import AvailabilityStatus
from app.domain.entities.price_history import PriceSnapshot, PriceTrend
from app.domain.exceptions import PriceHistoryValidationError
from app.intelligence.price_history import (
    FALLING_MOCK_SNAPSHOTS,
    RISING_MOCK_SNAPSHOTS,
    STABLE_MOCK_SNAPSHOTS,
    build_iphone_demo_mock_snapshots,
    build_marketplace_summaries,
    calculate_statistics,
    classify_trend,
    sort_snapshots,
)


def _snap(
    *,
    total: float,
    observed_at: datetime,
    currency: str = "PHP",
    marketplace: str = "shopee",
    listing_id: str = "1",
    availability: AvailabilityStatus = AvailabilityStatus.IN_STOCK,
) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id=uuid4(),
        canonical_product_id="prod-1",
        marketplace=marketplace,
        listing_id=listing_id,
        seller_name="Seller",
        currency=currency,
        item_price=total,
        shipping_cost=0.0,
        total_cost=total,
        availability=availability,
        observed_at=observed_at,
    )


def test_insufficient_data_under_three_observations() -> None:
    snaps = [
        _snap(total=100.0, observed_at=datetime(2026, 1, 1, tzinfo=UTC)),
        _snap(total=110.0, observed_at=datetime(2026, 1, 2, tzinfo=UTC)),
    ]
    assert classify_trend(snaps) == PriceTrend.INSUFFICIENT_DATA
    stats = calculate_statistics(snaps)
    assert stats.trend == PriceTrend.INSUFFICIENT_DATA
    assert stats.observation_count == 2


def test_rising_trend_from_mock_segment() -> None:
    assert classify_trend(RISING_MOCK_SNAPSHOTS) == PriceTrend.RISING


def test_falling_trend_from_mock_segment() -> None:
    assert classify_trend(FALLING_MOCK_SNAPSHOTS) == PriceTrend.FALLING


def test_stable_trend_from_mock_segment() -> None:
    assert classify_trend(STABLE_MOCK_SNAPSHOTS) == PriceTrend.STABLE


def test_current_lowest_highest_average_median_and_changes() -> None:
    snaps = [
        _snap(total=100.0, observed_at=datetime(2026, 1, 1, tzinfo=UTC)),
        _snap(total=200.0, observed_at=datetime(2026, 1, 2, tzinfo=UTC)),
        _snap(total=300.0, observed_at=datetime(2026, 1, 3, tzinfo=UTC)),
        _snap(total=400.0, observed_at=datetime(2026, 1, 4, tzinfo=UTC)),
    ]
    stats = calculate_statistics(snaps)
    assert stats.current_total_cost == 400.0
    assert stats.lowest_recorded_total_cost == 100.0
    assert stats.highest_recorded_total_cost == 400.0
    assert stats.average_total_cost == 250.0
    assert stats.median_total_cost == 250.0
    assert stats.absolute_change == 300.0
    assert stats.percentage_change == 300.0
    assert stats.first_observed == datetime(2026, 1, 1, tzinfo=UTC)
    assert stats.last_observed == datetime(2026, 1, 4, tzinfo=UTC)


def test_median_odd_and_even() -> None:
    odd = [
        _snap(total=10.0, observed_at=datetime(2026, 1, 1, tzinfo=UTC)),
        _snap(total=20.0, observed_at=datetime(2026, 1, 2, tzinfo=UTC)),
        _snap(total=30.0, observed_at=datetime(2026, 1, 3, tzinfo=UTC)),
    ]
    even = odd + [_snap(total=40.0, observed_at=datetime(2026, 1, 4, tzinfo=UTC))]
    assert calculate_statistics(odd).median_total_cost == 20.0
    assert calculate_statistics(even).median_total_cost == 25.0


def test_mixed_currencies_rejected() -> None:
    snaps = [
        _snap(total=100.0, observed_at=datetime(2026, 1, 1, tzinfo=UTC), currency="PHP"),
        _snap(total=2.0, observed_at=datetime(2026, 1, 2, tzinfo=UTC), currency="USD"),
    ]
    with pytest.raises(PriceHistoryValidationError, match="different currencies"):
        calculate_statistics(snaps)


def test_deterministic_ordering() -> None:
    a = _snap(
        total=1.0,
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        marketplace="lazada",
        listing_id="b",
    )
    b = _snap(
        total=2.0,
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        marketplace="lazada",
        listing_id="a",
    )
    c = _snap(
        total=3.0,
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        marketplace="shopee",
        listing_id="a",
    )
    ordered = sort_snapshots([a, c, b])
    assert [s.marketplace for s in ordered] == ["lazada", "lazada", "shopee"]
    assert [s.listing_id for s in ordered] == ["a", "b", "a"]


def test_repeated_calculations_identical() -> None:
    snaps = list(build_iphone_demo_mock_snapshots())
    first = calculate_statistics(snaps).to_dict()
    second = calculate_statistics(snaps).to_dict()
    assert first == second


def test_marketplace_summaries() -> None:
    snaps = list(build_iphone_demo_mock_snapshots())
    summaries = build_marketplace_summaries(snaps)
    names = {s.marketplace for s in summaries}
    assert names == {"lazada", "shopee"}
    for summary in summaries:
        assert summary.observation_count > 0
        assert summary.lowest_recorded_total_cost > 0
        assert summary.latest_total_cost > 0
        assert summary.average_total_cost > 0


def test_unavailable_listings_still_counted() -> None:
    snaps = [
        _snap(
            total=100.0,
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            availability=AvailabilityStatus.OUT_OF_STOCK,
        ),
        _snap(total=110.0, observed_at=datetime(2026, 1, 2, tzinfo=UTC)),
        _snap(total=120.0, observed_at=datetime(2026, 1, 3, tzinfo=UTC)),
    ]
    stats = calculate_statistics(snaps)
    assert stats.observation_count == 3
    assert stats.lowest_recorded_total_cost == 100.0


def test_no_fabricated_history_in_fixture_wording() -> None:
    snaps = build_iphone_demo_mock_snapshots()
    assert len(snaps) >= 3
    for snap in snaps:
        assert "DEVELOPMENT_MOCK_PRICE_HISTORY" in (snap.seller_name or "")
        assert snap.observed_at.year == 2026
