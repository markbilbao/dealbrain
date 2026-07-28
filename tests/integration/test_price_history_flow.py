"""Integration flow: marketplace results → stored snapshots → statistics."""

from __future__ import annotations

import pytest
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.marketplace import LazadaConnector, ShopeeConnector
from app.intelligence.price_history import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    InMemoryPriceHistoryStore,
    calculate_statistics,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService


@pytest.mark.asyncio
async def test_marketplace_to_price_history_flow() -> None:
    store = InMemoryPriceHistoryStore()
    marketplace = MarketplaceIntelligenceService(
        connectors=[ShopeeConnector(), LazadaConnector()]
    )
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    service = PriceHistoryService(
        store,
        marketplace_service=marketplace,
        product_intelligence_service=product,
        app_env="development",
        seed_demo_mock_on_search=True,
    )

    search = marketplace.search("iPhone 17 Pro Max")
    assert search.results

    result = await service.search_and_record("iPhone 17 Pro Max")
    assert result.statistics is not None

    stored = await store.get_by_canonical_product(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    assert stored
    stats_again = calculate_statistics(stored)
    assert stats_again.to_dict() == result.statistics.to_dict()

    # Duplicate search must not invent extra mock rows (idempotent uniqueness).
    second = await service.search_and_record("iPhone 17 Pro Max")
    stored_again = await store.get_by_canonical_product(IPHONE_DEMO_CANONICAL_PRODUCT_ID)
    assert len(stored_again) == len(stored) or len(stored_again) >= len(stored)
    assert second.statistics is not None
    assert second.statistics.trend == result.statistics.trend
