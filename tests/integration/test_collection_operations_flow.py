"""Integration flow for Collection Operations control plane."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.services.collection_operations_service import CollectionOperationsService
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService

FIXED_NOW = datetime(2026, 7, 28, 22, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_operations_job_to_price_history_and_status() -> None:
    repo = InMemoryCollectionJobRepository()
    store = InMemoryPriceHistoryStore()
    price = PriceHistoryService(store, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    collectors = [
        MockShopeeCollector(clock=lambda: FIXED_NOW),
        MockLazadaCollector(clock=lambda: FIXED_NOW),
    ]
    collection = MarketplaceCollectionService(
        collectors,
        price_history_service=price,
        product_intelligence_service=product,
        repository=repo,
        clock=lambda: FIXED_NOW,
    )
    scheduler = InMemoryCollectionScheduler(
        repo, run_job=collection.run_job, clock=lambda: FIXED_NOW
    )
    ops = CollectionOperationsService(
        collection_service=collection,
        repository=repo,
        run_repository=repo,
        scheduler=scheduler,
        collectors=collectors,
        price_history_store=store,
        clock=lambda: FIXED_NOW,
    )

    job = ops.create_job(
        name="Integration watch",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        interval_minutes=60,
        next_run_at=FIXED_NOW - timedelta(minutes=5),
        job_id="ops-integration-1",
    )
    assert job.status.value == "active"

    run = await ops.run_job(job.job_id, idempotency_key="integration-1")
    assert run.status in {
        CollectionStatus.COMPLETED,
        CollectionStatus.PARTIALLY_COMPLETED,
    }
    assert run.stored_snapshot_count >= 1
    assert run.trigger.value == "manual"

    # Idempotent replay.
    again = await ops.run_job(job.job_id, idempotency_key="integration-1")
    assert again.run_id == run.run_id

    ops.pause_job(job.job_id)
    due_while_paused = await ops.run_due_jobs(now=FIXED_NOW)
    assert due_while_paused == []

    ops.resume_job(job.job_id)
    ops.update_job(job.job_id, next_run_at=FIXED_NOW - timedelta(seconds=1))
    due = await ops.run_due_jobs(now=FIXED_NOW)
    assert len(due) == 1
    assert due[0].trigger.value == "scheduled"

    status = ops.get_operational_status()
    assert status.total_jobs == 1
    assert status.total_snapshots_collected >= 1
    assert ops.health().running is True
    assert ops.readiness().ready is True

    history = ops.list_runs_for_job(job.job_id)
    assert len(history) >= 2
