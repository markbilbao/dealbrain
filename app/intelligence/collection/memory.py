"""In-memory CollectionJobRepository for development and tests."""

from __future__ import annotations

from app.domain.entities.collection import CollectionJob, CollectionRun
from app.domain.interfaces.collection_job_repository import CollectionJobRepository


class InMemoryCollectionJobRepository(CollectionJobRepository):
    """Process-local job and run store with deterministic ordering."""

    def __init__(self) -> None:
        self._jobs: dict[str, CollectionJob] = {}
        self._job_order: list[str] = []
        self._runs: dict[str, CollectionRun] = {}
        self._run_order: list[str] = []

    def save_job(self, job: CollectionJob) -> CollectionJob:
        if job.job_id not in self._jobs:
            self._job_order.append(job.job_id)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> CollectionJob | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[CollectionJob]:
        return [self._jobs[job_id] for job_id in self._job_order if job_id in self._jobs]

    def delete_job(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        del self._jobs[job_id]
        self._job_order = [item for item in self._job_order if item != job_id]
        return True

    def save_run(self, run: CollectionRun) -> CollectionRun:
        if run.run_id not in self._runs:
            self._run_order.append(run.run_id)
        self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> CollectionRun | None:
        return self._runs.get(run_id)

    def list_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        ordered = [
            self._runs[run_id] for run_id in reversed(self._run_order) if run_id in self._runs
        ]
        return ordered[: max(0, limit)]

    def clear(self) -> None:
        """Reset all stored jobs and runs (tests)."""
        self._jobs.clear()
        self._job_order.clear()
        self._runs.clear()
        self._run_order.clear()
