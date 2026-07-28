"""Deterministic in-memory collection scheduler (no threads / no sleeping)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace
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
        self._status = "idle"

    @property
    def status(self) -> str:
        if self._running_jobs:
            return "running"
        return self._status

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
        self._status = "running"

        try:
            for job in list(self._repository.list_jobs()):
                if not job.enabled or job.paused:
                    continue
                if job.next_run_at > current:
                    continue
                if job.job_id in self._running_jobs or job.running:
                    # Concurrency prevention — skip without advancing schedule.
                    continue

                self._running_jobs.add(job.job_id)
                locked = replace(job, running=True, updated_at=current)
                self._repository.save_job(locked)

                try:
                    run = await self._run_job(locked, current)
                    runs.append(run)
                    next_run = current + timedelta(seconds=job.interval_seconds)
                    success = run.status.value in {"completed", "partially_completed"}
                    updated = replace(
                        job,
                        next_run_at=next_run,
                        last_run_at=current,
                        running=False,
                        updated_at=current,
                        last_success_at=current if success else job.last_success_at,
                        last_failure_at=(
                            current if run.status.value == "failed" else job.last_failure_at
                        ),
                        consecutive_failure_count=(
                            0
                            if success
                            else job.consecutive_failure_count
                            + (1 if run.status.value == "failed" else 0)
                        ),
                    )
                    self._repository.save_job(updated)
                finally:
                    self._running_jobs.discard(job.job_id)
                    existing = self._repository.get_job(job.job_id)
                    if existing is not None and existing.running:
                        self._repository.save_job(
                            replace(existing, running=False, updated_at=current)
                        )
        finally:
            self._status = "idle"

        return runs
