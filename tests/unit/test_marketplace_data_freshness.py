"""Unit tests for Sprint 18 marketplace data freshness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.entities.marketplace_data import FreshnessStatus, SourceMode
from app.marketplace.freshness.rules import evaluate_freshness

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def test_fixture_never_current_live() -> None:
    result = evaluate_freshness(
        source_mode=SourceMode.FIXTURE,
        observed_at=FIXED_NOW,
        source_timestamp=FIXED_NOW,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=True,
    )
    assert result.status == FreshnessStatus.UNKNOWN
    assert result.is_current_live_price is False
    assert result.warning is not None
    assert "not current live" in result.warning.lower() or "fixture" in result.warning.lower()


def test_imported_aging_and_stale() -> None:
    aging = evaluate_freshness(
        source_mode=SourceMode.IMPORTED,
        observed_at=FIXED_NOW - timedelta(hours=10),
        source_timestamp=None,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
    )
    assert aging.status == FreshnessStatus.AGING
    assert aging.is_current_live_price is False
    assert aging.warning is not None
    assert "not live" in aging.warning.lower()

    stale = evaluate_freshness(
        source_mode=SourceMode.IMPORTED,
        observed_at=FIXED_NOW - timedelta(hours=48),
        source_timestamp=None,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
    )
    assert stale.status == FreshnessStatus.STALE


def test_live_fresh_aging_stale() -> None:
    fresh = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=FIXED_NOW - timedelta(hours=1),
        source_timestamp=FIXED_NOW - timedelta(hours=1),
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=True,
        simulated=False,
    )
    assert fresh.status == FreshnessStatus.FRESH
    assert fresh.is_current_live_price is True

    aging = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=FIXED_NOW - timedelta(hours=12),
        source_timestamp=None,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=True,
    )
    assert aging.status == FreshnessStatus.AGING
    assert aging.warning is not None

    stale = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=FIXED_NOW - timedelta(hours=40),
        source_timestamp=None,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=True,
    )
    assert stale.status == FreshnessStatus.STALE
    assert "stale" in (stale.warning or "").lower()


def test_simulated_live_not_current_live_price() -> None:
    result = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=FIXED_NOW - timedelta(minutes=30),
        source_timestamp=FIXED_NOW - timedelta(minutes=30),
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=True,
        simulated=True,
    )
    assert result.status == FreshnessStatus.FRESH
    assert result.is_current_live_price is False
    assert result.warning is not None
    assert "SIMULATED LIVE" in result.warning


def test_unhealthy_connector_warning() -> None:
    result = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=FIXED_NOW - timedelta(hours=1),
        source_timestamp=None,
        ingested_at=FIXED_NOW,
        now=FIXED_NOW,
        connector_healthy=False,
        simulated=False,
    )
    assert result.is_current_live_price is False
    assert result.warning is not None
    assert "unhealthy" in result.warning.lower()


def test_unknown_without_timestamps() -> None:
    result = evaluate_freshness(
        source_mode=SourceMode.LIVE,
        observed_at=None,
        source_timestamp=None,
        ingested_at=None,
        now=FIXED_NOW,
    )
    assert result.status == FreshnessStatus.UNKNOWN
