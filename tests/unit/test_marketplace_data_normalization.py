"""Unit tests for Sprint 18 marketplace data normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.marketplace_data import (
    SIMULATED_LIVE_LABEL,
    FreshnessStatus,
    SourceMode,
)
from app.marketplace.normalization.normalizer import MarketplaceRecordNormalizer, content_hash

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def base_raw(**overrides: object) -> dict:
    payload = {
        "marketplace_product_id": "p-1",
        "title": "Normalized Widget",
        "brand": "Acme",
        "model": "W1",
        "currency": "PHP",
        "regular_price": 1000,
        "sale_price": 900,
        "shipping_cost": 50,
        "availability": "in_stock",
        "inventory_quantity": 5,
        "seller_id": "s-1",
        "seller_name": "Seller One",
        "observed_at": "2026-07-29T10:00:00+00:00",
        "marketplace": "fixture",
    }
    payload.update(overrides)
    return payload


def test_normalize_computes_total_and_provenance() -> None:
    normalizer = MarketplaceRecordNormalizer()
    offer = normalizer.normalize(
        base_raw(),
        source_mode=SourceMode.FIXTURE,
        source_id="fixture",
        connector_id="fixture-marketplace",
        raw_record_id="raw-1",
        now=FIXED_NOW,
    )
    assert offer.total_price == 950.0
    assert offer.source_mode == SourceMode.FIXTURE
    assert offer.provenance is not None
    assert offer.provenance.source_mode == SourceMode.FIXTURE
    assert offer.provenance.raw_record_id == "raw-1"
    assert offer.freshness is not None
    assert offer.freshness.status == FreshnessStatus.UNKNOWN
    assert offer.freshness.is_current_live_price is False
    assert offer.simulated is False


def test_raw_content_hash_stable() -> None:
    a = content_hash(base_raw())
    b = content_hash(base_raw())
    assert a == b
    assert a != content_hash(base_raw(title="Other"))


def test_never_promote_fixture_to_live() -> None:
    normalizer = MarketplaceRecordNormalizer()
    offer = normalizer.normalize(
        base_raw(source_mode="live", simulated=True),
        source_mode=SourceMode.FIXTURE,
        source_id="fixture",
        now=FIXED_NOW,
    )
    assert offer.source_mode == SourceMode.FIXTURE
    assert offer.simulated is False
    assert offer.freshness is not None
    assert offer.freshness.is_current_live_price is False


def test_never_promote_imported_to_live() -> None:
    normalizer = MarketplaceRecordNormalizer()
    offer = normalizer.normalize(
        base_raw(marketplace="imported", source_mode="live"),
        source_mode=SourceMode.IMPORTED,
        source_id="imported",
        import_batch_id="batch-1",
        now=FIXED_NOW,
    )
    assert offer.source_mode == SourceMode.IMPORTED
    assert offer.simulated is False
    assert offer.provenance is not None
    assert offer.provenance.import_batch_id == "batch-1"
    assert offer.to_dict()["label"] != SIMULATED_LIVE_LABEL


def test_simulated_live_keeps_label() -> None:
    normalizer = MarketplaceRecordNormalizer()
    offer = normalizer.normalize(
        base_raw(
            marketplace="simulated_live",
            source_mode="live",
            simulated=True,
            observed_at="2026-07-29T11:30:00+00:00",
        ),
        source_mode=SourceMode.LIVE,
        source_id="simulated_live",
        connector_id="mock-live-marketplace",
        now=FIXED_NOW,
        simulated=True,
        connector_healthy=True,
    )
    assert offer.source_mode == SourceMode.LIVE
    assert offer.simulated is True
    assert offer.to_dict()["label"] == SIMULATED_LIVE_LABEL
    assert offer.freshness is not None
    assert offer.freshness.is_current_live_price is False


def test_missing_required_fields_raise() -> None:
    normalizer = MarketplaceRecordNormalizer()
    with pytest.raises(ValueError):
        normalizer.normalize(
            {"title": "No id"},
            source_mode=SourceMode.FIXTURE,
            source_id="fixture",
            now=FIXED_NOW,
        )
    with pytest.raises(ValueError):
        normalizer.normalize(
            {"marketplace_product_id": "x", "title": "No price"},
            source_mode=SourceMode.FIXTURE,
            source_id="fixture",
            now=FIXED_NOW,
        )
