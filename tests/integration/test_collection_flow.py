"""Integration: mock collector → collection service → Price History snapshots."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.collection import CollectionStatus
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.memory import InMemoryCollectionJobRepository
from app.intelligence.collection.scheduler import InMemoryCollectionScheduler
from app.intelligence.collection.shopee import MockShopeeCollector
from app.intelligence.price_history import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    InMemoryPriceHistoryStore,
)
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService

FIXED_NOW = datetime(2026, 7, 28, 18, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_mock_collector_to_price_history_snapshot() -> None:
    store = InMemoryPriceHistoryStore()
    repo = InMemoryCollectionJobRepository()
    price = PriceHistoryService(store, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    service = MarketplaceCollectionService(
        [
            MockShopeeCollector(clock=lambda: FIXED_NOW),
            MockLazadaCollector(clock=lambda: FIXED_NOW),
        ],
        price_history_service=price,
        product_intelligence_service=product,
        repository=repo,
        clock=lambda: FIXED_NOW,
    )

    run = await service.run_collection(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        observed_at=FIXED_NOW,
    )
    assert run.status in {CollectionStatus.COMPLETED, CollectionStatus.PARTIALLY_COMPLETED}
    assert run.stored_snapshot_count >= 1

    shopee_snaps = await store.get_by_listing("1001001")
    lazada_snaps = await store.get_by_listing("2002001")
    assert shopee_snaps
    assert lazada_snaps
    assert shopee_snaps[0].marketplace == "shopee"
    assert lazada_snaps[0].marketplace == "lazada"
    assert shopee_snaps[0].currency == "PHP"
    assert lazada_snaps[0].currency == "PHP"
    assert shopee_snaps[0].observed_at == FIXED_NOW
    assert shopee_snaps[0].total_cost == round(
        shopee_snaps[0].item_price + shopee_snaps[0].shipping_cost, 2
    )
    # iPhone demo identity maps onto the fixed canonical product id.
    assert any(
        snap.canonical_product_id == IPHONE_DEMO_CANONICAL_PRODUCT_ID
        for snap in [*shopee_snaps, *lazada_snaps]
    )

    # Scheduled job path also stores snapshots.
    job = service.create_job(
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_seconds=300,
        created_at=FIXED_NOW,
        next_run_at=FIXED_NOW,
        job_id="integration-job",
    )
    scheduler = InMemoryCollectionScheduler(
        repo, run_job=service.run_job, clock=lambda: FIXED_NOW
    )
    scheduler.register_job(job)
    due_runs = await scheduler.run_due_jobs(now=FIXED_NOW)
    assert len(due_runs) == 1
    assert due_runs[0].job_id == "integration-job"
    assert due_runs[0].stored_snapshot_count >= 1
