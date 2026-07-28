"""Unit tests for PriceHistoryService and development mock fixture guards."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.entities.price_history import PriceTrend
from app.domain.exceptions import PriceHistoryValidationError
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    InMemoryPriceHistoryStore,
    build_iphone_demo_mock_snapshots,
    load_iphone_demo_mock_history,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService, snapshot_from_payload
from app.services.product_intelligence_service import ProductIntelligenceService


def _service(store: InMemoryPriceHistoryStore | None = None) -> PriceHistoryService:
    memory = store or InMemoryPriceHistoryStore()
    marketplace = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()]
    )
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    return PriceHistoryService(
        memory,
        marketplace_service=marketplace,
        product_intelligence_service=product,
        app_env="development",
        seed_demo_mock_on_search=True,
    )


@pytest.mark.asyncio
async def test_record_listing_snapshot() -> None:
    service = _service()
    listing = MarketplaceListing(
        marketplace="Shopee",
        product_id="1001001",
        title="Apple iPhone 17 Pro Max 256GB Black Titanium",
        price=74_999.0,
        currency="php",
        seller="Apple Authorized PH",
        rating=4.9,
        url="https://example.com",
        availability=AvailabilityStatus.IN_STOCK,
    )
    snap = await service.record_listing_snapshot(
        listing,
        canonical_product_id=IPHONE_DEMO_CANONICAL_PRODUCT_ID,
        observed_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
    )
    assert snap.marketplace == "shopee"
    assert snap.currency == "PHP"
    assert snap.total_cost == 74_999.0
    history = await service.get_product_history(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    assert history.statistics is not None
    assert history.statistics.observation_count == 1
    assert history.statistics.trend == PriceTrend.INSUFFICIENT_DATA


@pytest.mark.asyncio
async def test_mock_fixture_never_loads_in_production() -> None:
    store = InMemoryPriceHistoryStore()
    with pytest.raises(PriceHistoryValidationError, match="never load in production"):
        await load_iphone_demo_mock_history(store, app_env="production")
    assert await store.get_by_canonical_product(IPHONE_DEMO_CANONICAL_PRODUCT_ID) == []


@pytest.mark.asyncio
async def test_mock_fixture_loads_in_development() -> None:
    store = InMemoryPriceHistoryStore()
    saved = await load_iphone_demo_mock_history(store, app_env="development")
    assert len(saved) == len(build_iphone_demo_mock_snapshots())
    history = await store.get_by_canonical_product(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    assert len(history) == len(saved)


@pytest.mark.asyncio
async def test_search_and_record_integration_flow() -> None:
    service = _service()
    result = await service.search_and_record("iPhone 17 Pro Max")
    assert result.currency == "PHP"
    assert result.statistics is not None
    assert result.statistics.observation_count >= 3
    assert result.history
    assert result.marketplace_summaries
    assert result.canonical_product_id == IPHONE_DEMO_CANONICAL_PRODUCT_ID
    assert result.is_mock_history is True
    # No prediction language in serialised payload.
    payload = result.to_dict()
    blob = str(payload).lower()
    assert "forecast" not in blob
    assert "will rise" not in blob
    assert "will fall" not in blob
    assert "buy next week" not in blob


@pytest.mark.asyncio
async def test_product_and_listing_history_endpoints_logic() -> None:
    store = InMemoryPriceHistoryStore()
    service = PriceHistoryService(store, app_env="development")
    await load_iphone_demo_mock_history(store, app_env="development")
    product = await service.get_product_history(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    listing = await service.get_listing_history("1001001")
    assert product.statistics is not None
    assert listing.statistics is not None
    assert listing.statistics.observation_count < product.statistics.observation_count


@pytest.mark.asyncio
async def test_date_range_via_service() -> None:
    store = InMemoryPriceHistoryStore()
    service = PriceHistoryService(store)
    await load_iphone_demo_mock_history(store, app_env="development")
    ranged = await service.get_history_in_range(
        canonical_product_id=IPHONE_DEMO_CANONICAL_PRODUCT_ID,
        start=datetime(2026, 6, 1, tzinfo=UTC),
        end=datetime(2026, 6, 30, tzinfo=UTC),
    )
    assert ranged.statistics is not None
    assert all(
        datetime(2026, 6, 1, tzinfo=UTC)
        <= s.observed_at
        <= datetime(2026, 6, 30, 23, 59, tzinfo=UTC)
        for s in ranged.snapshots
    )


def test_snapshot_from_payload_rejects_bad_availability() -> None:
    with pytest.raises(PriceHistoryValidationError, match="Unsupported availability"):
        snapshot_from_payload(
            canonical_product_id="p",
            marketplace="shopee",
            listing_id="1",
            currency="PHP",
            item_price=1.0,
            shipping_cost=0.0,
            availability="not-a-status",
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_seed_skipped_when_production_even_if_flag_true() -> None:
    store = InMemoryPriceHistoryStore()
    marketplace = MarketplaceIntelligenceService(connectors=[ShopeeConnector()])
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    service = PriceHistoryService(
        store,
        marketplace_service=marketplace,
        product_intelligence_service=product,
        app_env="production",
        seed_demo_mock_on_search=True,
    )
    await service.search_and_record("iPhone 17 Pro Max")
    seeded = await store.get_by_canonical_product(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    # Current observations may be recorded, but mock fixture timestamps must not appear.
    mock_ids = {s.snapshot_id for s in build_iphone_demo_mock_snapshots()}
    assert not any(s.snapshot_id in mock_ids for s in seeded)
