"""Unit tests for the in-memory collection scheduler."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.entities.collection import (
    CollectionJob,
    CollectionRun,
    CollectionStatus,
)
from app.intelligence.collection.memory import InMemoryCollectionJobRepository
from app.intelligence.collection.scheduler import InMemoryCollectionScheduler

FIXED_NOW = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_scheduler_due_and_not_due() -> None:
    repo = InMemoryCollectionJobRepository()
    executed: list[str] = []

    async def run_job(job: CollectionJob, now: datetime) -> CollectionRun:
        executed.append(job.job_id)
        return CollectionRun(
            run_id=f"run-{job.job_id}",
            query=job.query,
            marketplaces=job.marketplaces,
            status=CollectionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            job_id=job.job_id,
        )

    scheduler = InMemoryCollectionScheduler(repo, run_job=run_job, clock=lambda: FIXED_NOW)
    due = CollectionJob(
        job_id="due-1",
        query="iPhone",
        marketplaces=("shopee",),
        interval_seconds=3600,
        enabled=True,
        created_at=FIXED_NOW - timedelta(hours=2),
        next_run_at=FIXED_NOW - timedelta(minutes=1),
    )
    future = CollectionJob(
        job_id="future-1",
        query="iPhone",
        marketplaces=("lazada",),
        interval_seconds=3600,
        enabled=True,
        created_at=FIXED_NOW,
        next_run_at=FIXED_NOW + timedelta(hours=1),
    )
    scheduler.register_job(due)
    scheduler.register_job(future)

    runs = await scheduler.run_due_jobs(now=FIXED_NOW)
    assert len(runs) == 1
    assert executed == ["due-1"]
    updated = repo.get_job("due-1")
    assert updated is not None
    assert updated.last_run_at == FIXED_NOW
    assert updated.next_run_at == FIXED_NOW + timedelta(seconds=3600)
    assert updated.running is False


@pytest.mark.asyncio
async def test_scheduler_concurrency_prevention() -> None:
    repo = InMemoryCollectionJobRepository()
    calls = {"count": 0}

    async def run_job(job: CollectionJob, now: datetime) -> CollectionRun:
        calls["count"] += 1
        # Simulate concurrent re-entry while this job is marked running.
        nested = await scheduler.run_due_jobs(now=now)
        assert nested == []
        return CollectionRun(
            run_id=f"run-{job.job_id}",
            query=job.query,
            marketplaces=job.marketplaces,
            status=CollectionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            job_id=job.job_id,
        )

    scheduler = InMemoryCollectionScheduler(repo, run_job=run_job, clock=lambda: FIXED_NOW)
    job = CollectionJob(
        job_id="once",
        query="iPhone",
        marketplaces=("shopee",),
        interval_seconds=60,
        enabled=True,
        created_at=FIXED_NOW,
        next_run_at=FIXED_NOW,
    )
    scheduler.register_job(job)
    runs = await scheduler.run_due_jobs(now=FIXED_NOW)
    assert len(runs) == 1
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_scheduler_remove_and_list() -> None:
    repo = InMemoryCollectionJobRepository()

    async def run_job(job: CollectionJob, now: datetime) -> CollectionRun:
        return CollectionRun(
            run_id="x",
            query=job.query,
            marketplaces=job.marketplaces,
            status=CollectionStatus.COMPLETED,
            started_at=now,
            completed_at=now,
        )

    scheduler = InMemoryCollectionScheduler(repo, run_job=run_job)
    job = CollectionJob(
        job_id="j1",
        query="q",
        marketplaces=("shopee",),
        interval_seconds=10,
        enabled=True,
        created_at=FIXED_NOW,
        next_run_at=FIXED_NOW,
    )
    scheduler.register_job(job)
    assert len(scheduler.list_jobs()) == 1
    assert scheduler.remove_job("j1") is True
    assert scheduler.list_jobs() == []
