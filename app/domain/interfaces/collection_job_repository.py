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
        """Persist a completed (or partial) collection run."""

    @abstractmethod
    def get_run(self, run_id: str) -> CollectionRun | None:
        """Return a run by id, or ``None``."""

    @abstractmethod
    def list_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        """Return recent runs, newest first."""
