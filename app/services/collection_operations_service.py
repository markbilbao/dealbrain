"""Collection Operations — job control, run history, status, health, readiness.

Operational control layer for Sprint 8 marketplace collection. Uses mock
collectors only. No live scraping, LLMs, or background sleeping.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.domain.entities.collection import (
    CollectionJob,
    CollectionOperationalStatus,
    CollectionReadinessCheck,
    CollectionRun,
    CollectionStatus,
    CollectionSubsystemHealth,
    CollectionSubsystemReadiness,
    CollectionTriggerType,
    CollectorAvailability,
)
from app.domain.exceptions import (
    CollectionConcurrentRunError,
    CollectionJobNotFoundError,
    CollectionJobNotRunnableError,
    CollectionRunNotFoundError,
    CollectionValidationError,
)
from app.domain.interfaces.collection_job_repository import (
    CollectionJobRepository,
    CollectionRunRepository,
)
from app.domain.interfaces.collection_scheduler import CollectionScheduler
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.intelligence.collection.ids import make_job_id
from app.intelligence.collection.scheduler import InMemoryCollectionScheduler
from app.services.marketplace_collection_service import MarketplaceCollectionService

MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 60 * 24 * 30  # 30 days
RECENT_FAILURE_WINDOW = timedelta(hours=24)


class CollectionOperationsService:
    """Manage collection jobs, runs, operational status, and readiness."""

    def __init__(
        self,
        *,
        collection_service: MarketplaceCollectionService,
        repository: CollectionJobRepository,
        run_repository: CollectionRunRepository | None = None,
        scheduler: CollectionScheduler,
        collectors: Sequence[MarketplaceCollector],
        price_history_store: PriceHistoryStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._collection = collection_service
        self._repository = repository
        self._run_repository: CollectionRunRepository = run_repository or repository  # type: ignore[assignment]
        self._scheduler = scheduler
        self._collectors = {c.marketplace_name.strip().lower(): c for c in collectors}
        self._price_history_store = price_history_store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._manual_locks: set[str] = set()

    # ------------------------------------------------------------------ jobs
    def create_job(
        self,
        *,
        name: str,
        query: str,
        marketplaces: Sequence[str],
        interval_minutes: int,
        enabled: bool = True,
        scenario: str | None = None,
        next_run_at: datetime | None = None,
        job_id: str | None = None,
    ) -> CollectionJob:
        interval_seconds = self._validate_interval_minutes(interval_minutes)
        markets = self._validate_marketplaces(marketplaces)
        cleaned_query = query.strip()
        if not cleaned_query:
            raise CollectionValidationError("Job query must not be blank.")
        cleaned_name = name.strip()
        if not cleaned_name:
            raise CollectionValidationError("Job name must not be blank.")

        stamp = self._clock()
        resolved_id = job_id or make_job_id(
            query=cleaned_query,
            marketplaces=markets,
            interval_seconds=interval_seconds,
            created_at=stamp,
        )
        job = CollectionJob(
            job_id=resolved_id,
            query=cleaned_query,
            marketplaces=markets,
            interval_seconds=interval_seconds,
            enabled=enabled,
            created_at=stamp,
            next_run_at=next_run_at or stamp,
            scenario=scenario,
            running=False,
            name=cleaned_name,
            paused=False,
            updated_at=stamp,
        )
        saved = self._repository.save_job(job)
        self._scheduler.register_job(saved)
        return saved

    def get_job(self, job_id: str) -> CollectionJob:
        job = self._repository.get_job(job_id)
        if job is None:
            raise CollectionJobNotFoundError(job_id)
        return job

    def list_jobs(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        enabled: bool | None = None,
    ) -> list[CollectionJob]:
        return self._repository.list_jobs_filtered(
            status=status,
            marketplace=marketplace,
            enabled=enabled,
        )

    def update_job(
        self,
        job_id: str,
        *,
        name: str | None = None,
        query: str | None = None,
        marketplaces: Sequence[str] | None = None,
        interval_minutes: int | None = None,
        enabled: bool | None = None,
        scenario: str | None = None,
        next_run_at: datetime | None = None,
    ) -> CollectionJob:
        job = self.get_job(job_id)
        stamp = self._clock()
        updates: dict[str, object] = {"updated_at": stamp}

        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise CollectionValidationError("Job name must not be blank.")
            updates["name"] = cleaned
        if query is not None:
            cleaned = query.strip()
            if not cleaned:
                raise CollectionValidationError("Job query must not be blank.")
            updates["query"] = cleaned
        if marketplaces is not None:
            updates["marketplaces"] = self._validate_marketplaces(marketplaces)
        if interval_minutes is not None:
            updates["interval_seconds"] = self._validate_interval_minutes(interval_minutes)
        if enabled is not None:
            updates["enabled"] = enabled
            if enabled is False:
                updates["paused"] = False
        if scenario is not None:
            updates["scenario"] = scenario
        if next_run_at is not None:
            updates["next_run_at"] = next_run_at

        updated = replace(job, **updates)  # type: ignore[arg-type]
        saved = self._repository.save_job(updated)
        self._scheduler.register_job(saved)
        return saved

    def delete_job(self, job_id: str) -> None:
        self.get_job(job_id)
        # Scheduler remove also deletes from the shared repository.
        if not self._scheduler.remove_job(job_id):
            if not self._repository.delete_job(job_id):
                raise CollectionJobNotFoundError(job_id)

    def pause_job(self, job_id: str) -> CollectionJob:
        job = self.get_job(job_id)
        stamp = self._clock()
        updated = replace(job, paused=True, enabled=True, updated_at=stamp)
        saved = self._repository.save_job(updated)
        self._scheduler.register_job(saved)
        return saved

    def resume_job(self, job_id: str) -> CollectionJob:
        job = self.get_job(job_id)
        stamp = self._clock()
        updated = replace(job, paused=False, enabled=True, updated_at=stamp)
        saved = self._repository.save_job(updated)
        self._scheduler.register_job(saved)
        return saved

    def enable_job(self, job_id: str) -> CollectionJob:
        return self.update_job(job_id, enabled=True)

    def disable_job(self, job_id: str) -> CollectionJob:
        return self.update_job(job_id, enabled=False)

    async def run_job(
        self,
        job_id: str,
        *,
        idempotency_key: str | None = None,
        override: bool = False,
        trigger: CollectionTriggerType = CollectionTriggerType.MANUAL,
    ) -> CollectionRun:
        if idempotency_key:
            existing = self._repository.get_run_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        job = self.get_job(job_id)
        if not override:
            if not job.enabled:
                raise CollectionJobNotRunnableError(job_id, "job is disabled")
            if job.paused:
                raise CollectionJobNotRunnableError(job_id, "job is paused")

        if job.running or job_id in self._manual_locks:
            raise CollectionConcurrentRunError(job_id)

        now = self._clock()
        self._manual_locks.add(job_id)
        locked = replace(job, running=True, updated_at=now)
        self._repository.save_job(locked)

        try:
            run = await self._collection.run_collection(
                query=job.query,
                marketplaces=job.marketplaces,
                observed_at=now,
                scenario=job.scenario,
                job_id=job.job_id,
                trigger=trigger,
                idempotency_key=idempotency_key,
            )
            if idempotency_key:
                self._repository.save_idempotency_key(idempotency_key, run.run_id)

            success = run.status in {
                CollectionStatus.COMPLETED,
                CollectionStatus.PARTIALLY_COMPLETED,
            }
            next_run = now + timedelta(seconds=job.interval_seconds)
            updated = replace(
                job,
                running=False,
                last_run_at=now,
                next_run_at=next_run if trigger == CollectionTriggerType.SCHEDULED else job.next_run_at,
                updated_at=now,
                last_success_at=now if success else job.last_success_at,
                last_failure_at=now if run.status == CollectionStatus.FAILED else job.last_failure_at,
                consecutive_failure_count=(
                    0
                    if success
                    else (
                        job.consecutive_failure_count + 1
                        if run.status == CollectionStatus.FAILED
                        else job.consecutive_failure_count
                    )
                ),
            )
            # Manual runs still advance last_run metadata but keep next_run unless scheduled.
            if trigger == CollectionTriggerType.MANUAL:
                updated = replace(
                    updated,
                    next_run_at=job.next_run_at,
                )
            self._repository.save_job(updated)
            return run
        finally:
            self._manual_locks.discard(job_id)
            existing = self._repository.get_job(job_id)
            if existing is not None and existing.running:
                self._repository.save_job(
                    replace(existing, running=False, updated_at=self._clock())
                )

    async def run_due_jobs(self, *, now: datetime | None = None) -> list[CollectionRun]:
        """Execute all due enabled (non-paused) jobs. Safe for a future worker."""
        runs = await self._scheduler.run_due_jobs(now=now)
        return list(runs)

    # ------------------------------------------------------------------ runs
    def get_run(self, run_id: str) -> CollectionRun:
        run = self._run_repository.get_run(run_id)
        if run is None:
            raise CollectionRunNotFoundError(run_id)
        return run

    def list_runs(self, *, limit: int = 50, failed_only: bool = False) -> list[CollectionRun]:
        if failed_only:
            return self._run_repository.list_failed_runs(limit=limit)
        return self._run_repository.list_runs(limit=limit)

    def list_runs_for_job(self, job_id: str, *, limit: int = 50) -> list[CollectionRun]:
        self.get_job(job_id)
        return self._run_repository.list_runs_for_job(job_id, limit=limit)

    # ---------------------------------------------------------- status / health
    def get_operational_status(self) -> CollectionOperationalStatus:
        now = self._clock()
        jobs = self._repository.list_jobs()
        runs = self._run_repository.list_runs(limit=10_000)

        enabled_jobs = [job for job in jobs if job.enabled and not job.paused]
        paused_jobs = [job for job in jobs if job.paused]
        due_jobs = [
            job
            for job in jobs
            if job.enabled and not job.paused and job.next_run_at <= now and not job.running
        ]
        recent_failures = [
            job
            for job in jobs
            if job.last_failure_at is not None
            and job.last_failure_at >= now - RECENT_FAILURE_WINDOW
            and job.consecutive_failure_count > 0
        ]

        last_success = max(
            (run.completed_at for run in runs if run.completed_at and run.status
             in {CollectionStatus.COMPLETED, CollectionStatus.PARTIALLY_COMPLETED}),
            default=None,
        )
        last_failure = max(
            (run.completed_at for run in runs if run.completed_at and run.status == CollectionStatus.FAILED),
            default=None,
        )
        total_snapshots = sum(run.stored_snapshot_count for run in runs)

        scheduler_status = "callable"
        if isinstance(self._scheduler, InMemoryCollectionScheduler):
            scheduler_status = self._scheduler.status

        availability = tuple(
            CollectorAvailability(
                marketplace=name,
                available=collector.health_check(),
            )
            for name, collector in sorted(self._collectors.items())
        )

        return CollectionOperationalStatus(
            total_jobs=len(jobs),
            enabled_jobs=len(enabled_jobs),
            paused_jobs=len(paused_jobs),
            jobs_currently_due=len(due_jobs),
            jobs_with_recent_failures=len(recent_failures),
            last_successful_collection=last_success,
            last_failed_collection=last_failure,
            total_snapshots_collected=total_snapshots,
            scheduler_status=scheduler_status,
            collector_availability=availability,
        )

    def health(self) -> CollectionSubsystemHealth:
        """Liveness: collection operations subsystem is loaded and callable."""
        try:
            _ = self._scheduler.list_jobs
            _ = self._collection.list_collectors()
            return CollectionSubsystemHealth(
                status="up",
                subsystem="collection-operations",
                running=True,
                detail="Collection operations subsystem is running (mock collectors only).",
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionSubsystemHealth(
                status="down",
                subsystem="collection-operations",
                running=False,
                detail=str(exc),
            )

    def readiness(self) -> CollectionSubsystemReadiness:
        """Readiness probes — local only, no external network calls."""
        checks: list[CollectionReadinessCheck] = []

        try:
            self._repository.list_jobs()
            checks.append(
                CollectionReadinessCheck(
                    name="job_repository",
                    ready=True,
                    detail="Job repository is available.",
                )
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CollectionReadinessCheck(
                    name="job_repository",
                    ready=False,
                    detail=str(exc),
                )
            )

        try:
            self._run_repository.list_runs(limit=1)
            checks.append(
                CollectionReadinessCheck(
                    name="run_repository",
                    ready=True,
                    detail="Run repository is available.",
                )
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CollectionReadinessCheck(
                    name="run_repository",
                    ready=False,
                    detail=str(exc),
                )
            )

        if self._price_history_store is None:
            checks.append(
                CollectionReadinessCheck(
                    name="price_history_store",
                    ready=False,
                    detail="Price history store is not configured.",
                )
            )
        else:
            checks.append(
                CollectionReadinessCheck(
                    name="price_history_store",
                    ready=True,
                    detail="Price history store is available.",
                )
            )

        if self._collectors:
            unavailable = [
                name
                for name, collector in self._collectors.items()
                if not collector.health_check()
            ]
            if unavailable:
                checks.append(
                    CollectionReadinessCheck(
                        name="mock_collectors",
                        ready=False,
                        detail=f"Collectors unavailable: {', '.join(sorted(unavailable))}",
                    )
                )
            else:
                checks.append(
                    CollectionReadinessCheck(
                        name="mock_collectors",
                        ready=True,
                        detail=f"Registered collectors: {', '.join(sorted(self._collectors))}",
                    )
                )
        else:
            checks.append(
                CollectionReadinessCheck(
                    name="mock_collectors",
                    ready=False,
                    detail="No mock collectors registered.",
                )
            )

        try:
            callable(self._scheduler.run_due_jobs)
            checks.append(
                CollectionReadinessCheck(
                    name="scheduler",
                    ready=True,
                    detail="Scheduler run_due_jobs is callable.",
                )
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                CollectionReadinessCheck(
                    name="scheduler",
                    ready=False,
                    detail=str(exc),
                )
            )

        config_ok = True
        config_detail = "Configuration is valid."
        for job in self._repository.list_jobs():
            if job.interval_seconds <= 0:
                config_ok = False
                config_detail = f"Job {job.job_id} has invalid interval_seconds."
                break
            unknown = [m for m in job.marketplaces if m not in self._collectors]
            if unknown:
                config_ok = False
                config_detail = f"Job {job.job_id} references unknown marketplaces: {unknown}"
                break
        checks.append(
            CollectionReadinessCheck(
                name="configuration",
                ready=config_ok,
                detail=config_detail,
            )
        )

        ready = all(check.ready for check in checks)
        return CollectionSubsystemReadiness(
            ready=ready,
            status="ready" if ready else "not_ready",
            checks=tuple(checks),
        )

    # --------------------------------------------------------------- helpers
    def _validate_interval_minutes(self, interval_minutes: int) -> int:
        if not isinstance(interval_minutes, int) or isinstance(interval_minutes, bool):
            raise CollectionValidationError("interval_minutes must be an integer.")
        if interval_minutes < MIN_INTERVAL_MINUTES:
            raise CollectionValidationError(
                f"interval_minutes must be >= {MIN_INTERVAL_MINUTES}."
            )
        if interval_minutes > MAX_INTERVAL_MINUTES:
            raise CollectionValidationError(
                f"interval_minutes must be <= {MAX_INTERVAL_MINUTES}."
            )
        return interval_minutes * 60

    def _validate_marketplaces(self, marketplaces: Sequence[str]) -> tuple[str, ...]:
        markets = tuple(m.strip().lower() for m in marketplaces if m and m.strip())
        if not markets:
            raise CollectionValidationError("At least one marketplace is required.")
        unknown = [m for m in markets if m not in self._collectors]
        if unknown:
            raise CollectionValidationError(f"Unknown marketplaces: {', '.join(unknown)}")
        return markets
