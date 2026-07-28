"""Deterministic in-memory collection scheduler (no threads / no sleeping)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta

from app.domain.entities.collection import CollectionJob, CollectionRun
from app.domain.interfaces.collection_job_repository import CollectionJobRepository
from app.domain.interfaces.collection_scheduler import CollectionScheduler

RunJobCallback = Callable[[CollectionJob, datetime], Awaitable[CollectionRun]]


class InMemoryCollectionScheduler(CollectionScheduler):
    """Interval scheduler that executes only when ``run_due_jobs`` is called."""

    def __init__(
        self,
        repository: CollectionJobRepository,
        *,
        run_job: RunJobCallback,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._run_job = run_job
        self._clock = clock or (lambda: datetime.now(UTC))
        self._running_jobs: set[str] = set()

    def register_job(self, job: CollectionJob) -> CollectionJob:
        return self._repository.save_job(job)

    def remove_job(self, job_id: str) -> bool:
        self._running_jobs.discard(job_id)
        return self._repository.delete_job(job_id)

    def list_jobs(self) -> list[CollectionJob]:
        return self._repository.list_jobs()

    async def run_due_jobs(
        self,
        *,
        now: datetime | None = None,
    ) -> Sequence[CollectionRun]:
        current = now or self._clock()
        runs: list[CollectionRun] = []

        for job in list(self._repository.list_jobs()):
            if not job.enabled:
                continue
            if job.next_run_at > current:
                continue
            if job.job_id in self._running_jobs or job.running:
                # Concurrency prevention — skip without advancing schedule.
                continue

            self._running_jobs.add(job.job_id)
            locked = CollectionJob(
                job_id=job.job_id,
                query=job.query,
                marketplaces=job.marketplaces,
                interval_seconds=job.interval_seconds,
                enabled=job.enabled,
                created_at=job.created_at,
                next_run_at=job.next_run_at,
                last_run_at=job.last_run_at,
                scenario=job.scenario,
                running=True,
            )
            self._repository.save_job(locked)

            try:
                run = await self._run_job(locked, current)
                runs.append(run)
                next_run = current + timedelta(seconds=job.interval_seconds)
                updated = CollectionJob(
                    job_id=job.job_id,
                    query=job.query,
                    marketplaces=job.marketplaces,
                    interval_seconds=job.interval_seconds,
                    enabled=job.enabled,
                    created_at=job.created_at,
                    next_run_at=next_run,
                    last_run_at=current,
                    scenario=job.scenario,
                    running=False,
                )
                self._repository.save_job(updated)
            finally:
                self._running_jobs.discard(job.job_id)
                existing = self._repository.get_job(job.job_id)
                if existing is not None and existing.running:
                    self._repository.save_job(
                        CollectionJob(
                            job_id=existing.job_id,
                            query=existing.query,
                            marketplaces=existing.marketplaces,
                            interval_seconds=existing.interval_seconds,
                            enabled=existing.enabled,
                            created_at=existing.created_at,
                            next_run_at=existing.next_run_at,
                            last_run_at=existing.last_run_at,
                            scenario=existing.scenario,
                            running=False,
                        )
                    )

        return runs
