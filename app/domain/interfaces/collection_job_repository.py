"""CollectionJobRepository port — persistence for jobs and runs."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.collection import CollectionJob, CollectionRun


class CollectionJobRepository(ABC):
    """Abstract persistence for scheduled jobs and historical collection runs."""

    @abstractmethod
    def save_job(self, job: CollectionJob) -> CollectionJob:
        """Insert or replace a collection job."""

    @abstractmethod
    def get_job(self, job_id: str) -> CollectionJob | None:
        """Return a job by id, or ``None``."""

    @abstractmethod
    def list_jobs(self) -> list[CollectionJob]:
        """Return all registered jobs in stable insertion order."""

    @abstractmethod
    def delete_job(self, job_id: str) -> bool:
        """Remove a job. Returns ``True`` when a job was deleted."""

    @abstractmethod
    def save_run(self, run: CollectionRun) -> CollectionRun:
        """Persist a collection run.

        Completed runs are immutable — replacing a terminal run raises.
        """

    @abstractmethod
    def get_run(self, run_id: str) -> CollectionRun | None:
        """Return a run by id, or ``None``."""

    @abstractmethod
    def list_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent runs, newest first."""

    def list_jobs_filtered(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        enabled: bool | None = None,
    ) -> list[CollectionJob]:
        """Return jobs filtered by operational status, marketplace, and enabled."""
        jobs = self.list_jobs()
        if enabled is not None:
            jobs = [job for job in jobs if job.enabled is enabled]
        if marketplace is not None:
            market = marketplace.strip().lower()
            jobs = [
                job
                for job in jobs
                if market in {item.strip().lower() for item in job.marketplaces}
            ]
        if status is not None:
            wanted = status.strip().lower()
            jobs = [job for job in jobs if job.status.value == wanted]
        return jobs

    def list_runs_for_job(self, job_id: str, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent runs for one job, newest first."""
        matched = [run for run in self.list_runs(limit=10_000) if run.job_id == job_id]
        return matched[: max(0, limit)]

    def list_failed_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent failed runs, newest first."""
        from app.domain.entities.collection import CollectionStatus

        matched = [
            run for run in self.list_runs(limit=10_000) if run.status == CollectionStatus.FAILED
        ]
        return matched[: max(0, limit)]

    def get_run_by_idempotency_key(self, key: str) -> CollectionRun | None:
        """Return a previously recorded run for an idempotency key."""
        raise NotImplementedError

    def save_idempotency_key(self, key: str, run_id: str) -> None:
        """Associate an idempotency key with a run id."""
        raise NotImplementedError


class CollectionRunRepository(ABC):
    """Narrow port used by readiness checks and run-history queries."""

    @abstractmethod
    def save_run(self, run: CollectionRun) -> CollectionRun:
        """Persist a collection run."""

    @abstractmethod
    def get_run(self, run_id: str) -> CollectionRun | None:
        """Return a run by id, or ``None``."""

    @abstractmethod
    def list_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent runs, newest first."""

    @abstractmethod
    def list_runs_for_job(self, job_id: str, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent runs for one job."""

    @abstractmethod
    def list_failed_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent failed runs."""
