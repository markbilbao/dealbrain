"""Marketplace Collection application service.

Orchestrates mock collectors, isolates per-marketplace failures, records
Price History snapshots for valid listings, and returns explainable summaries.
No live marketplace HTTP, LLMs, or background threads.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.domain.entities.collection import (
    CollectionFailure,
    CollectionJob,
    CollectionResult,
    CollectionRun,
    CollectionStatus,
    CollectionTarget,
)
from app.domain.entities.marketplace_listing import MarketplaceListing
from app.domain.exceptions import (
    CollectionJobNotFoundError,
    CollectionValidationError,
    UnsupportedProductError,
)
from app.domain.interfaces.collection_job_repository import CollectionJobRepository
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.marketplace_rate_limiter import MarketplaceRateLimiter
from app.intelligence.collection.ids import make_collection_run_id, make_job_id
from app.intelligence.collection.retry import CollectionRetryPolicy, RetryableCollectionError
from app.intelligence.collection.validation import is_valid_listing, validate_listing
from app.intelligence.price_history.mock_fixture import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    IPHONE_DEMO_IDENTITY_KEY,
)
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService

logger = get_logger(__name__)


class MarketplaceCollectionService:
    """Use-case orchestration for scheduled and manual marketplace collection."""

    def __init__(
        self,
        collectors: Sequence[MarketplaceCollector],
        *,
        price_history_service: PriceHistoryService,
        product_intelligence_service: ProductIntelligenceService | None = None,
        repository: CollectionJobRepository,
        rate_limiter: MarketplaceRateLimiter | None = None,
        retry_policy: CollectionRetryPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        snapshot_id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._collectors = {c.marketplace_name.strip().lower(): c for c in collectors}
        self._price_history = price_history_service
        self._product_intelligence = product_intelligence_service
        self._repository = repository
        self._rate_limiter = rate_limiter
        self._retry_policy = retry_policy or CollectionRetryPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._snapshot_id_factory = snapshot_id_factory

    @property
    def collectors(self) -> tuple[MarketplaceCollector, ...]:
        return tuple(self._collectors.values())

    def list_collectors(self) -> list[str]:
        return sorted(self._collectors)

    async def run_collection(
        self,
        *,
        query: str,
        marketplaces: Sequence[str] | None = None,
        observed_at: datetime | None = None,
        scenario: str | None = None,
        job_id: str | None = None,
        run_id: str | None = None,
    ) -> CollectionRun:
        """Run one or more collectors and forward valid listings to Price History."""
        cleaned = query.strip()
        if not cleaned:
            raise CollectionValidationError("Collection query must not be blank.")

        selected = self._select_collectors(marketplaces)
        if not selected:
            raise CollectionValidationError("No collectors matched the selected marketplaces.")

        started_at = self._clock()
        observation_time = observed_at or started_at
        marketplace_names = tuple(collector.marketplace_name for collector in selected)
        resolved_run_id = run_id or make_collection_run_id(
            query=cleaned,
            marketplaces=marketplace_names,
            observed_at=observation_time,
            suffix=job_id or "",
        )

        results: list[CollectionResult] = []
        warnings: list[str] = []
        stored_snapshot_count = 0
        skipped_count = 0
        failure_count = 0
        seen_listing_keys: set[tuple[str, str]] = set()

        for collector in selected:
            market = collector.marketplace_name
            if self._rate_limiter is not None:
                decision = self._rate_limiter.allow(market, now=started_at)
                if not decision.allowed:
                    failure_count += 1
                    results.append(
                        CollectionResult(
                            run_id=f"{resolved_run_id}:{market}",
                            marketplace=market,
                            query=cleaned,
                            target_id=None,
                            started_at=started_at,
                            completed_at=self._clock(),
                            listing_count=0,
                            successful_listing_count=0,
                            failed_listing_count=1,
                            listings=(),
                            errors=(
                                CollectionFailure(
                                    marketplace=market,
                                    code="rate_limited",
                                    message=(
                                        f"Rate limited; retry after "
                                        f"{decision.retry_after_seconds}s"
                                    ),
                                    retryable=True,
                                ),
                            ),
                            status=CollectionStatus.FAILED,
                            warnings=("Rate limiter rejected marketplace request",),
                        )
                    )
                    warnings.append(f"{market}: rate limited")
                    continue

            result = self._collect_with_retry(
                collector,
                CollectionTarget(
                    query=cleaned,
                    marketplace=market,
                    scenario=scenario,
                ),
                parent_run_id=resolved_run_id,
            )
            results.append(result)

            if result.status == CollectionStatus.FAILED:
                failure_count += result.failed_listing_count or 1
            else:
                failure_count += result.failed_listing_count

            for collected in result.listings:
                listing = collected.listing
                key = (listing.marketplace.strip().lower(), listing.product_id)
                if collected.is_duplicate or key in seen_listing_keys:
                    skipped_count += 1
                    warnings.append(
                        f"Skipped duplicate listing {listing.marketplace}:{listing.product_id}"
                    )
                    seen_listing_keys.add(key)
                    continue
                seen_listing_keys.add(key)

                if not is_valid_listing(listing):
                    skipped_count += 1
                    reasons = ", ".join(validate_listing(listing))
                    warnings.append(
                        f"Skipped malformed listing {listing.marketplace}:{listing.product_id}"
                        f" ({reasons})"
                    )
                    continue

                snapshot_id = (
                    self._snapshot_id_factory() if self._snapshot_id_factory is not None else None
                )
                stored = await self._store_listing_snapshot(
                    listing,
                    observed_at=observation_time,
                    snapshot_id=snapshot_id,
                )
                if stored:
                    stored_snapshot_count += 1
                else:
                    skipped_count += 1
                    warnings.append(
                        f"Skipped listing without resolvable product identity: "
                        f"{listing.marketplace}:{listing.product_id}"
                    )

            warnings.extend(result.warnings)

        completed_at = self._clock()
        status = self._aggregate_status(results)
        run = CollectionRun(
            run_id=resolved_run_id,
            query=cleaned,
            marketplaces=marketplace_names,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            results=tuple(results),
            stored_snapshot_count=stored_snapshot_count,
            skipped_count=skipped_count,
            failure_count=failure_count,
            warnings=tuple(dict.fromkeys(warnings)),
            observed_at=observation_time,
            job_id=job_id,
        )
        self._repository.save_run(run)
        self._log_summary(run)
        return run

    def create_job(
        self,
        *,
        query: str,
        marketplaces: Sequence[str],
        interval_seconds: int,
        enabled: bool = True,
        scenario: str | None = None,
        job_id: str | None = None,
        created_at: datetime | None = None,
        next_run_at: datetime | None = None,
    ) -> CollectionJob:
        cleaned = query.strip()
        if not cleaned:
            raise CollectionValidationError("Job query must not be blank.")
        if interval_seconds <= 0:
            raise CollectionValidationError("interval_seconds must be positive.")

        markets = tuple(m.strip().lower() for m in marketplaces if m.strip())
        if not markets:
            raise CollectionValidationError("At least one marketplace is required.")
        unknown = [m for m in markets if m not in self._collectors]
        if unknown:
            raise CollectionValidationError(
                f"Unknown marketplaces: {', '.join(unknown)}"
            )

        stamp = created_at or self._clock()
        resolved_id = job_id or make_job_id(
            query=cleaned,
            marketplaces=markets,
            interval_seconds=interval_seconds,
            created_at=stamp,
        )
        job = CollectionJob(
            job_id=resolved_id,
            query=cleaned,
            marketplaces=markets,
            interval_seconds=interval_seconds,
            enabled=enabled,
            created_at=stamp,
            next_run_at=next_run_at or stamp,
            scenario=scenario,
            running=False,
        )
        return self._repository.save_job(job)

    def list_jobs(self) -> list[CollectionJob]:
        return self._repository.list_jobs()

    def delete_job(self, job_id: str) -> None:
        if not self._repository.delete_job(job_id):
            raise CollectionJobNotFoundError(job_id)

    def get_run(self, run_id: str) -> CollectionRun:
        run = self._repository.get_run(run_id)
        if run is None:
            from app.domain.exceptions import CollectionRunNotFoundError

            raise CollectionRunNotFoundError(run_id)
        return run

    def list_runs(self, *, limit: int = 50) -> list[CollectionRun]:
        return self._repository.list_runs(limit=limit)

    async def run_job(self, job: CollectionJob, now: datetime) -> CollectionRun:
        """Execute a single scheduled job (used by the scheduler callback)."""
        return await self.run_collection(
            query=job.query,
            marketplaces=job.marketplaces,
            observed_at=now,
            scenario=job.scenario,
            job_id=job.job_id,
        )

    def _select_collectors(
        self, marketplaces: Sequence[str] | None
    ) -> list[MarketplaceCollector]:
        if not marketplaces:
            return [self._collectors[name] for name in sorted(self._collectors)]
        selected: list[MarketplaceCollector] = []
        for name in marketplaces:
            key = name.strip().lower()
            collector = self._collectors.get(key)
            if collector is not None:
                selected.append(collector)
        return selected

    def _collect_with_retry(
        self,
        collector: MarketplaceCollector,
        target: CollectionTarget,
        *,
        parent_run_id: str,
    ) -> CollectionResult:
        """Invoke a collector with deterministic retry decisions (no sleeping)."""
        attempt = 0
        last_error: Exception | None = None
        retry_warnings: list[str] = []

        while True:
            attempt += 1
            try:
                if not collector.health_check():
                    raise RetryableCollectionError(
                        "temporary_unavailable",
                        f"{collector.marketplace_name} collector health check failed",
                    )
                result = collector.collect(target)
                # Ensure result run_id nests under the parent run for explainability.
                if not result.run_id.startswith(parent_run_id):
                    result = CollectionResult(
                        run_id=f"{parent_run_id}:{collector.marketplace_name}",
                        marketplace=result.marketplace,
                        query=result.query,
                        target_id=result.target_id,
                        started_at=result.started_at,
                        completed_at=result.completed_at,
                        listing_count=result.listing_count,
                        successful_listing_count=result.successful_listing_count,
                        failed_listing_count=result.failed_listing_count,
                        listings=result.listings,
                        errors=result.errors,
                        status=result.status,
                        warnings=tuple([*result.warnings, *retry_warnings]),
                    )
                elif retry_warnings:
                    result = CollectionResult(
                        run_id=result.run_id,
                        marketplace=result.marketplace,
                        query=result.query,
                        target_id=result.target_id,
                        started_at=result.started_at,
                        completed_at=result.completed_at,
                        listing_count=result.listing_count,
                        successful_listing_count=result.successful_listing_count,
                        failed_listing_count=result.failed_listing_count,
                        listings=result.listings,
                        errors=result.errors,
                        status=result.status,
                        warnings=tuple([*result.warnings, *retry_warnings]),
                    )
                return result
            except RetryableCollectionError as exc:
                last_error = exc
                decision = self._retry_policy.decide(attempt=attempt, error_code=exc.code)
                if not decision.should_retry:
                    break
                retry_warnings.append(
                    f"Retry scheduled for {collector.marketplace_name} "
                    f"(attempt {attempt}, delay {decision.delay_seconds}s) — not sleeping"
                )
                # Deterministic: continue immediately without sleeping.
                continue
            except Exception as exc:  # noqa: BLE001 — isolate collector crashes
                last_error = exc
                decision = self._retry_policy.decide(
                    attempt=attempt, error_code="temporary_unavailable"
                )
                if decision.should_retry and isinstance(exc, RetryableCollectionError):
                    continue
                # Non-retryable unexpected failures become isolated marketplace failures.
                break

        now = self._clock()
        message = str(last_error) if last_error else "Unknown collector failure"
        code = getattr(last_error, "code", "total_failure")
        return CollectionResult(
            run_id=f"{parent_run_id}:{collector.marketplace_name}",
            marketplace=collector.marketplace_name,
            query=target.query,
            target_id=target.target_id,
            started_at=now,
            completed_at=now,
            listing_count=0,
            successful_listing_count=0,
            failed_listing_count=1,
            listings=(),
            errors=(
                CollectionFailure(
                    marketplace=collector.marketplace_name,
                    code=str(code),
                    message=message,
                    retryable=self._retry_policy.is_retryable_code(str(code)),
                ),
            ),
            status=CollectionStatus.FAILED,
            warnings=tuple(retry_warnings),
        )

    async def _store_listing_snapshot(
        self,
        listing: MarketplaceListing,
        *,
        observed_at: datetime,
        snapshot_id: UUID | None,
    ) -> bool:
        canonical_id = await self._resolve_canonical_product_id(listing)
        if canonical_id is None:
            # Fall back to a deterministic synthetic id so valid listings still
            # contribute Price History observations when identity cannot resolve.
            canonical_id = (
                f"collected:{listing.marketplace.strip().lower()}:{listing.product_id}"
            )

        before = await self._price_history.record_listing_snapshot(
            listing,
            canonical_product_id=canonical_id,
            observed_at=observed_at,
            snapshot_id=snapshot_id,
        )
        return before is not None

    async def _resolve_canonical_product_id(self, listing: MarketplaceListing) -> str | None:
        if self._product_intelligence is None:
            return None
        try:
            parsed = await self._product_intelligence.parse_listing(listing.title)
        except UnsupportedProductError:
            return None
        if parsed.product.identity_key == IPHONE_DEMO_IDENTITY_KEY:
            return IPHONE_DEMO_CANONICAL_PRODUCT_ID
        return str(parsed.product.id)

    @staticmethod
    def _aggregate_status(results: Sequence[CollectionResult]) -> CollectionStatus:
        if not results:
            return CollectionStatus.FAILED
        statuses = {result.status for result in results}
        if statuses == {CollectionStatus.COMPLETED}:
            return CollectionStatus.COMPLETED
        if statuses == {CollectionStatus.FAILED}:
            return CollectionStatus.FAILED
        if CollectionStatus.FAILED in statuses or CollectionStatus.PARTIALLY_COMPLETED in statuses:
            return CollectionStatus.PARTIALLY_COMPLETED
        if CollectionStatus.CANCELLED in statuses:
            return CollectionStatus.CANCELLED
        return CollectionStatus.COMPLETED

    def _log_summary(self, run: CollectionRun) -> None:
        summary = run.to_summary_dict()
        logger.info(
            "marketplace_collection_summary",
            extra={"collection_summary": summary},
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("collection_summary_detail=%s", summary)