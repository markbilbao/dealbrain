"""CollectionScheduler port — deterministic due-job execution.

Implementations must not start background threads. Work executes only when
``run_due_jobs`` is invoked. Clocks are injected for determinism.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from app.domain.entities.collection import CollectionJob, CollectionRun


class CollectionScheduler(ABC):
    """Abstract scheduler for marketplace collection jobs."""

    @abstractmethod
    def register_job(self, job: CollectionJob) -> CollectionJob:
        """Register or replace a scheduled job."""

    @abstractmethod
    def remove_job(self, job_id: str) -> bool:
        """Unregister a job. Returns ``True`` when removed."""

    @abstractmethod
    def list_jobs(self) -> list[CollectionJob]:
        """Return registered jobs."""

    @abstractmethod
    async def run_due_jobs(
        self,
        *,
        now: datetime | None = None,
    ) -> Sequence[CollectionRun]:
        """Execute enabled jobs whose ``next_run_at`` is at or before ``now``.

        Concurrent re-entry for the same job must be prevented. No sleeping
        or background workers are allowed.
        """
