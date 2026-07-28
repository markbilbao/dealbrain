"""Unit tests for CollectionOperationsService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.entities.collection import CollectionStatus, CollectionTriggerType
from app.domain.exceptions import (
    CollectionConcurrentRunError,
    CollectionJobNotRunnableError,
    CollectionRunImmutableError,
    CollectionValidationError,
)
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
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

FIXED_NOW = datetime(2026, 7, 28, 21, 0, tzinfo=UTC)


def _build_ops(
    *,
    now: datetime = FIXED_NOW,
    collectors: list[MarketplaceCollector] | None = None,
) -> tuple[CollectionOperationsService, InMemoryCollectionJobRepository]:
    repo = InMemoryCollectionJobRepository()
    store = InMemoryPriceHistoryStore()
    price = PriceHistoryService(store, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    resolved = collectors or [
        MockShopeeCollector(clock=lambda: now),
        MockLazadaCollector(clock=lambda: now),
    ]
    collection = MarketplaceCollectionService(
        resolved,
        price_history_service=price,
        product_intelligence_service=product,
        repository=repo,
        clock=lambda: now,
    )
    scheduler = InMemoryCollectionScheduler(
        repo, run_job=collection.run_job, clock=lambda: now
    )
    ops = CollectionOperationsService(
        collection_service=collection,
        repository=repo,
        run_repository=repo,
        scheduler=scheduler,
        collectors=resolved,
        price_history_store=store,
        clock=lambda: now,
    )
    return ops, repo


@pytest.mark.asyncio
async def test_create_update_delete_pause_resume() -> None:
    ops, _ = _build_ops()
    job = ops.create_job(
        name="Watch iPhone",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=30,
        job_id="ops-job-1",
    )
    assert job.status.value == "active"
    assert job.interval_minutes == 30
    assert job.name == "Watch iPhone"

    updated = ops.update_job("ops-job-1", interval_minutes=15, enabled=True)
    assert updated.interval_minutes == 15

    paused = ops.pause_job("ops-job-1")
    assert paused.status.value == "paused"
    resumed = ops.resume_job("ops-job-1")
    assert resumed.status.value == "active"

    ops.delete_job("ops-job-1")
    assert ops.list_jobs() == []


@pytest.mark.asyncio
async def test_manual_trigger_and_due_execution() -> None:
    ops, _ = _build_ops()
    job = ops.create_job(
        name="Due job",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        interval_minutes=60,
        next_run_at=FIXED_NOW - timedelta(minutes=1),
        job_id="due-job",
    )
    run = await ops.run_job(job.job_id)
    assert run.trigger == CollectionTriggerType.MANUAL
    assert run.job_id == "due-job"
    assert run.status in {
        CollectionStatus.COMPLETED,
        CollectionStatus.PARTIALLY_COMPLETED,
    }

    # Make due again and execute via run-due.
    ops.update_job("due-job", next_run_at=FIXED_NOW - timedelta(seconds=1))
    due_runs = await ops.run_due_jobs(now=FIXED_NOW)
    assert len(due_runs) == 1
    assert due_runs[0].trigger == CollectionTriggerType.SCHEDULED


@pytest.mark.asyncio
async def test_disabled_and_paused_protection() -> None:
    ops, _ = _build_ops()
    ops.create_job(
        name="Protected",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=10,
        job_id="prot-1",
    )
    ops.disable_job("prot-1")
    with pytest.raises(CollectionJobNotRunnableError, match="disabled"):
        await ops.run_job("prot-1")

    ops.enable_job("prot-1")
    ops.pause_job("prot-1")
    with pytest.raises(CollectionJobNotRunnableError, match="paused"):
        await ops.run_job("prot-1")

    # Override allows execution.
    run = await ops.run_job("prot-1", override=True)
    assert run.job_id == "prot-1"


@pytest.mark.asyncio
async def test_concurrent_run_protection() -> None:
    ops, repo = _build_ops()
    ops.create_job(
        name="Once",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="once-1",
    )
    # Simulate an in-flight lock.
    ops._manual_locks.add("once-1")  # noqa: SLF001
    with pytest.raises(CollectionConcurrentRunError):
        await ops.run_job("once-1")
    ops._manual_locks.discard("once-1")  # noqa: SLF001

    job = repo.get_job("once-1")
    assert job is not None
    from dataclasses import replace

    repo.save_job(replace(job, running=True))
    with pytest.raises(CollectionConcurrentRunError):
        await ops.run_job("once-1")


@pytest.mark.asyncio
async def test_idempotency_key_returns_original_run() -> None:
    ops, _ = _build_ops()
    ops.create_job(
        name="Idem",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="idem-1",
    )
    first = await ops.run_job("idem-1", idempotency_key="key-abc")
    second = await ops.run_job("idem-1", idempotency_key="key-abc")
    assert first.run_id == second.run_id
    assert second.idempotency_key == "key-abc"


@pytest.mark.asyncio
async def test_retry_metadata_exposed_without_sleeping() -> None:
    from app.domain.entities.collection import CollectionTarget
    from app.intelligence.collection.retry import RetryableCollectionError

    class Flaky(MarketplaceCollector):
        @property
        def marketplace_name(self) -> str:
            return "shopee"

        def health_check(self) -> bool:
            return True

        def collect(self, target: CollectionTarget):
            raise RetryableCollectionError("timeout", "timed out")

    ops, _ = _build_ops(collectors=[Flaky()])
    ops.create_job(
        name="Retry",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="retry-1",
    )
    run = await ops.run_job("retry-1")
    assert run.status == CollectionStatus.FAILED
    assert run.retry is not None
    assert run.retry.attempt >= 1
    assert run.retry.max_attempts >= 1
    assert run.retry.final_failure_reason is not None
    assert any("timeout" in item for item in run.error_summaries)


@pytest.mark.asyncio
async def test_run_history_queries_and_immutability() -> None:
    ops, repo = _build_ops()
    ops.create_job(
        name="History",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="hist-1",
    )
    run = await ops.run_job("hist-1")
    assert ops.get_run(run.run_id).run_id == run.run_id
    assert ops.list_runs_for_job("hist-1")
    assert ops.list_runs(limit=10)

    from dataclasses import replace

    mutated = replace(run, skipped_count=run.skipped_count + 99)
    with pytest.raises(CollectionRunImmutableError):
        repo.save_run(mutated)


@pytest.mark.asyncio
async def test_operational_status_health_readiness() -> None:
    ops, _ = _build_ops()
    ops.create_job(
        name="Status",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee", "lazada"],
        interval_minutes=5,
        next_run_at=FIXED_NOW - timedelta(minutes=1),
        job_id="status-1",
    )
    await ops.run_job("status-1")
    status = ops.get_operational_status()
    assert status.total_jobs == 1
    assert status.enabled_jobs == 1
    assert status.total_snapshots_collected >= 1
    assert {c.marketplace for c in status.collector_availability} == {"shopee", "lazada"}

    health = ops.health()
    assert health.running is True
    assert health.status == "up"

    readiness = ops.readiness()
    assert readiness.ready is True
    names = {check.name for check in readiness.checks}
    assert names >= {
        "job_repository",
        "run_repository",
        "price_history_store",
        "mock_collectors",
        "scheduler",
        "configuration",
    }


@pytest.mark.asyncio
async def test_invalid_interval_and_marketplace_rejected() -> None:
    ops, _ = _build_ops()
    with pytest.raises(CollectionValidationError, match="interval_minutes"):
        ops.create_job(
            name="Bad",
            query="iPhone",
            marketplaces=["shopee"],
            interval_minutes=0,
        )
    with pytest.raises(CollectionValidationError, match="Unknown marketplaces"):
        ops.create_job(
            name="Bad",
            query="iPhone",
            marketplaces=["amazon"],
            interval_minutes=10,
        )


@pytest.mark.asyncio
async def test_deterministic_repeated_execution() -> None:
    ops_a, _ = _build_ops()
    ops_b, _ = _build_ops()
    job_a = ops_a.create_job(
        name="Det",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="det-1",
    )
    job_b = ops_b.create_job(
        name="Det",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="det-1",
    )
    assert job_a.job_id == job_b.job_id
    run_a = await ops_a.run_job("det-1", idempotency_key="same")
    run_b = await ops_b.run_job("det-1", idempotency_key="same")
    assert run_a.run_id == run_b.run_id
    assert run_a.stored_snapshot_count == run_b.stored_snapshot_count


@pytest.mark.asyncio
async def test_paused_jobs_skipped_by_run_due() -> None:
    ops, _ = _build_ops()
    ops.create_job(
        name="Paused due",
        query="iPhone 17 Pro Max",
        marketplaces=["shopee"],
        interval_minutes=5,
        next_run_at=FIXED_NOW - timedelta(minutes=1),
        job_id="paused-due",
    )
    ops.pause_job("paused-due")
    runs = await ops.run_due_jobs(now=FIXED_NOW)
    assert runs == []


@pytest.mark.asyncio
async def test_filter_jobs_by_status_marketplace_enabled() -> None:
    ops, _ = _build_ops()
    ops.create_job(
        name="A",
        query="iPhone",
        marketplaces=["shopee"],
        interval_minutes=5,
        job_id="f1",
    )
    ops.create_job(
        name="B",
        query="iPhone",
        marketplaces=["lazada"],
        interval_minutes=5,
        enabled=False,
        job_id="f2",
    )
    ops.pause_job("f1")
    assert len(ops.list_jobs(status="paused")) == 1
    assert len(ops.list_jobs(marketplace="lazada")) == 1
    assert len(ops.list_jobs(enabled=False)) == 1
