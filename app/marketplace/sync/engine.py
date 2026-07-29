"""Synchronization engine for marketplace connectors."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    ConnectorError,
    ConnectorHealth,
    ConnectorHealthStatus,
    DeadLetterRecord,
    InventorySnapshot,
    MarketplaceOffer,
    MarketplacePriceSnapshot,
    MatchAmbiguityStatus,
    RawMarketplaceRecord,
    SourceMode,
    SyncCheckpoint,
    SyncConflict,
    SyncConflictKind,
    SyncJob,
    SyncJobStatus,
    SyncMode,
    SyncResult,
)
from app.domain.exceptions import (
    MarketplaceDataNotFoundError,
    MarketplaceDataRateLimitError,
    MarketplaceDataValidationError,
)
from app.domain.interfaces.marketplace_data_repository import (
    MarketplaceDataConnector,
    MarketplaceDataRepository,
)
from app.marketplace.normalization.normalizer import MarketplaceRecordNormalizer, content_hash
from app.marketplace.sync.retry import SyncRetryPolicy


class MarketplaceSyncEngine:
    """Full/incremental sync with checkpointing, retries, and conflict reporting."""

    def __init__(
        self,
        repository: MarketplaceDataRepository,
        connectors: dict[str, MarketplaceDataConnector],
        *,
        normalizer: MarketplaceRecordNormalizer | None = None,
        retry_policy: SyncRetryPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        match_threshold: float = 0.85,
    ) -> None:
        self._repo = repository
        self._connectors = connectors
        self._normalizer = normalizer or MarketplaceRecordNormalizer()
        self._retry = retry_policy or SyncRetryPolicy()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._match_threshold = match_threshold
        self._cancel_flags: dict[str, bool] = {}

    def request_cancel(self, job_id: str) -> None:
        self._cancel_flags[job_id] = True

    def run(
        self,
        *,
        job_id: str,
        connector_id: str,
        mode: SyncMode = SyncMode.FULL,
        idempotency_key: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> SyncJob:
        if idempotency_key:
            existing = self._repo.get_sync_job_by_idempotency(idempotency_key)
            if existing is not None:
                return existing

        connector = self._connectors.get(connector_id)
        if connector is None:
            raise MarketplaceDataNotFoundError(connector_id)

        config = self._repo.get_configuration(connector_id)
        if config is None:
            raise MarketplaceDataValidationError(f"Connector {connector_id} is not configured")

        now = self._clock()
        job = SyncJob(
            job_id=job_id,
            connector_id=connector_id,
            mode=mode,
            status=SyncJobStatus.RUNNING,
            created_at=now,
            started_at=now,
            idempotency_key=idempotency_key,
        )
        self._repo.save_sync_job(job)
        self._cancel_flags[job_id] = False

        source_mode = self._source_mode_for(connector)
        checkpoint = None if mode == SyncMode.FULL else self._repo.get_checkpoint(connector_id)

        fetched: list[dict[str, Any]] = []
        errors: list[ConnectorError] = []
        attempt = 0
        new_checkpoint: SyncCheckpoint | None = None
        started = self._clock()

        while True:
            if self._cancel_flags.get(job_id):
                return self._finalize(
                    job,
                    status=SyncJobStatus.CANCELLED,
                    result=SyncResult(records_fetched=len(fetched), checkpoint=None),
                    errors=errors,
                    summary="Sync cancelled",
                )
            attempt += 1
            try:
                rate = connector.report_rate_limit()
                if rate.limited:
                    raise MarketplaceDataRateLimitError(rate.message or "rate_limited")
                page, new_checkpoint = connector.fetch_offers(
                    config, query=query, checkpoint=checkpoint, limit=limit
                )
                fetched.extend(dict(item) for item in page)
                break
            except MarketplaceDataRateLimitError as exc:
                decision = self._retry.decide(attempt=attempt, error_code="rate_limited")
                errors.append(
                    ConnectorError(
                        code="rate_limited",
                        message=str(exc),
                        retryable=decision.should_retry,
                        observed_at=self._clock(),
                        details={"advisory_delay_seconds": decision.delay_seconds},
                    )
                )
                if not decision.should_retry:
                    self._update_health_failure(connector, errors, started)
                    return self._finalize(
                        job,
                        status=SyncJobStatus.FAILED,
                        result=SyncResult(records_fetched=0, records_failed=1),
                        errors=errors,
                        summary="Rate limited",
                    )
            except Exception as exc:  # noqa: BLE001 — connector boundary
                code = "simulated_transient_failure" if "transient" in str(exc) else "fetch_error"
                if "rate_limited" in str(exc):
                    code = "rate_limited"
                decision = self._retry.decide(attempt=attempt, error_code=code)
                errors.append(
                    ConnectorError(
                        code=code,
                        message=str(exc),
                        retryable=decision.should_retry,
                        observed_at=self._clock(),
                        details={"advisory_delay_seconds": decision.delay_seconds},
                    )
                )
                if not decision.should_retry:
                    self._update_health_failure(connector, errors, started)
                    return self._finalize(
                        job,
                        status=SyncJobStatus.FAILED,
                        result=SyncResult(records_fetched=0, records_failed=1),
                        errors=errors,
                        summary=f"Sync failed: {exc}",
                    )

        written = 0
        failed = 0
        duplicates = 0
        conflicts = 0
        dead = 0
        normalized_count = 0
        health = self._repo.get_health(connector_id)
        connector_healthy = health is None or health.status in {
            ConnectorHealthStatus.HEALTHY,
            ConnectorHealthStatus.DEGRADED,
        }

        for raw in fetched:
            if self._cancel_flags.get(job_id):
                return self._finalize(
                    job,
                    status=SyncJobStatus.CANCELLED,
                    result=SyncResult(
                        records_fetched=len(fetched),
                        records_normalized=normalized_count,
                        records_written=written,
                        records_failed=failed,
                        records_duplicate=duplicates,
                        conflicts=conflicts,
                        dead_lettered=dead,
                        checkpoint=new_checkpoint.cursor if new_checkpoint else None,
                    ),
                    errors=errors,
                    summary="Sync cancelled during processing",
                )
            try:
                digest = content_hash(raw)
                existing = self._repo.find_offer_by_content_hash(digest)
                if existing is not None:
                    duplicates += 1
                    continue

                ingested = self._clock()
                raw_id = f"raw:{job_id}:{digest[:16]}"
                self._repo.save_raw_record(
                    RawMarketplaceRecord(
                        record_id=raw_id,
                        source_mode=source_mode,
                        source_id=connector.marketplace,
                        marketplace=str(raw.get("marketplace") or connector.marketplace),
                        payload=dict(raw),
                        ingested_at=ingested,
                        connector_id=connector_id,
                        content_hash=digest,
                    )
                )
                offer = self._normalizer.normalize(
                    raw,
                    source_mode=source_mode,
                    source_id=connector.marketplace,
                    connector_id=connector_id,
                    raw_record_id=raw_id,
                    ingested_at=ingested,
                    now=ingested,
                    connector_healthy=connector_healthy,
                    freshness_thresholds=(
                        config.freshness_fresh_hours,
                        config.freshness_aging_hours,
                        config.freshness_stale_hours,
                    ),
                    simulated=bool(raw.get("simulated"))
                    or connector.marketplace == "simulated_live",
                )
                normalized_count += 1
                offer = self._apply_matching(offer, job_id)
                if offer.match_ambiguity in {
                    MatchAmbiguityStatus.AMBIGUOUS,
                    MatchAmbiguityStatus.CONFLICT,
                }:
                    conflicts += 1
                self._persist_offer(offer, ingested)
                written += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                dead += 1
                self._repo.save_dead_letter(
                    DeadLetterRecord(
                        record_id=f"dlq:{job_id}:{failed}",
                        sync_job_id=job_id,
                        reason=str(exc),
                        payload=dict(raw),
                        created_at=self._clock(),
                        retryable=False,
                    )
                )
                errors.append(
                    ConnectorError(
                        code="normalize_or_write_failed",
                        message=str(exc),
                        retryable=False,
                        observed_at=self._clock(),
                    )
                )

        if new_checkpoint is not None:
            self._repo.save_checkpoint(new_checkpoint)

        latency_ms = (self._clock() - started).total_seconds() * 1000.0
        status = SyncJobStatus.COMPLETED
        if failed and written:
            status = SyncJobStatus.PARTIALLY_COMPLETED
        elif failed and not written:
            status = SyncJobStatus.FAILED

        self._repo.save_health(
            ConnectorHealth(
                connector_id=connector_id,
                status=(
                    ConnectorHealthStatus.HEALTHY
                    if status == SyncJobStatus.COMPLETED
                    else (
                        ConnectorHealthStatus.DEGRADED
                        if status == SyncJobStatus.PARTIALLY_COMPLETED
                        else ConnectorHealthStatus.UNAVAILABLE
                    )
                ),
                last_attempted_sync=started,
                last_successful_sync=self._clock() if written else None,
                records_processed=written,
                records_failed=failed,
                latency_ms=latency_ms,
                rate_limit=connector.report_rate_limit(),
                recent_errors=tuple(errors[-5:]),
                checkpoint=new_checkpoint.cursor if new_checkpoint else None,
                consecutive_failures=0
                if written
                else (health.consecutive_failures + 1 if health else 1),
                message=connector.report_health().message,
            )
        )

        return self._finalize(
            job,
            status=status,
            result=SyncResult(
                records_fetched=len(fetched),
                records_normalized=normalized_count,
                records_written=written,
                records_failed=failed,
                records_duplicate=duplicates,
                conflicts=conflicts,
                dead_lettered=dead,
                checkpoint=new_checkpoint.cursor if new_checkpoint else None,
            ),
            errors=errors,
            summary=(
                f"{mode.value} sync wrote {written}/{len(fetched)} "
                f"(failed={failed}, duplicates={duplicates}, conflicts={conflicts})"
            ),
        )

    def _apply_matching(self, offer: MarketplaceOffer, job_id: str) -> MarketplaceOffer:
        decision = self._repo.match_product(
            brand=offer.brand,
            model=offer.model,
            title=offer.title,
            sku=offer.sku,
            upc=None,
            marketplace_product_id=offer.marketplace_product_id,
            marketplace=offer.marketplace,
        )
        if decision.ambiguity == MatchAmbiguityStatus.AMBIGUOUS:
            self._repo.save_sync_conflict(
                SyncConflict(
                    conflict_id=f"conflict:{job_id}:{offer.offer_id}",
                    sync_job_id=job_id,
                    kind=SyncConflictKind.AMBIGUOUS_MATCH,
                    message="Ambiguous product match — review required",
                    offer_id=offer.offer_id,
                    confidence=decision.confidence,
                    reasons=decision.reasons,
                    created_at=self._clock(),
                    payload={"candidates": list(decision.candidate_ids)},
                )
            )
        elif decision.ambiguity == MatchAmbiguityStatus.MATCHED and (
            decision.confidence < self._match_threshold
        ):
            self._repo.save_sync_conflict(
                SyncConflict(
                    conflict_id=f"conflict:{job_id}:{offer.offer_id}",
                    sync_job_id=job_id,
                    kind=SyncConflictKind.LOW_CONFIDENCE_MATCH,
                    message="Match confidence below safe threshold",
                    offer_id=offer.offer_id,
                    product_id=decision.matched_product_id,
                    confidence=decision.confidence,
                    reasons=decision.reasons,
                    created_at=self._clock(),
                )
            )
            decision = type(decision)(
                matched_product_id=None,
                confidence=decision.confidence,
                reasons=decision.reasons + ("held for review",),
                ambiguity=MatchAmbiguityStatus.CONFLICT,
                candidate_ids=decision.candidate_ids,
            )

        return MarketplaceOffer(
            offer_id=offer.offer_id,
            product_id=decision.matched_product_id or offer.product_id,
            marketplace=offer.marketplace,
            marketplace_product_id=offer.marketplace_product_id,
            title=offer.title,
            currency=offer.currency,
            regular_price=offer.regular_price,
            sale_price=offer.sale_price,
            shipping_cost=offer.shipping_cost,
            total_price=offer.total_price,
            availability=offer.availability,
            inventory_quantity=offer.inventory_quantity,
            seller=offer.seller,
            marketplace_url=offer.marketplace_url,
            image_url=offer.image_url,
            condition=offer.condition,
            warranty=offer.warranty,
            brand=offer.brand,
            model=offer.model,
            category=offer.category,
            sku=offer.sku,
            source_mode=offer.source_mode,
            provenance=offer.provenance,
            freshness=offer.freshness,
            confidence=offer.confidence,
            matched_canonical_product_id=decision.matched_product_id,
            match_confidence=decision.confidence,
            match_reasons=decision.reasons,
            match_ambiguity=decision.ambiguity,
            observed_at=offer.observed_at,
            raw_record_id=offer.raw_record_id,
            simulated=offer.simulated,
        )

    def _persist_offer(self, offer: MarketplaceOffer, ingested: datetime) -> None:
        self._repo.save_offer(offer)
        item_price = (
            offer.sale_price if offer.sale_price is not None else (offer.regular_price or 0.0)
        )
        self._repo.save_price_snapshot(
            MarketplacePriceSnapshot(
                snapshot_id=f"price:{offer.offer_id}:{ingested.isoformat()}",
                product_id=offer.product_id,
                offer_id=offer.offer_id,
                marketplace=offer.marketplace,
                currency=offer.currency,
                item_price=float(item_price),
                shipping_cost=offer.shipping_cost,
                total_price=offer.total_price,
                availability=offer.availability,
                observed_at=offer.observed_at or ingested,
                source_timestamp=offer.provenance.source_timestamp if offer.provenance else None,
                ingested_at=ingested,
                source_mode=offer.source_mode,
                seller_name=offer.seller.name if offer.seller else None,
                provenance=offer.provenance,
            )
        )
        self._repo.save_inventory_snapshot(
            InventorySnapshot(
                snapshot_id=f"inv:{offer.offer_id}:{ingested.isoformat()}",
                product_id=offer.product_id,
                offer_id=offer.offer_id,
                marketplace=offer.marketplace,
                availability=offer.availability,
                quantity=offer.inventory_quantity,
                observed_at=offer.observed_at or ingested,
                source_timestamp=offer.provenance.source_timestamp if offer.provenance else None,
                ingested_at=ingested,
                source_mode=offer.source_mode,
                seller_name=offer.seller.name if offer.seller else None,
                provenance=offer.provenance,
            )
        )

    def _finalize(
        self,
        job: SyncJob,
        *,
        status: SyncJobStatus,
        result: SyncResult,
        errors: list[ConnectorError],
        summary: str,
    ) -> SyncJob:
        updated = SyncJob(
            job_id=job.job_id,
            connector_id=job.connector_id,
            mode=job.mode,
            status=status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=self._clock(),
            result=result,
            cancel_requested=self._cancel_flags.get(job.job_id, False),
            idempotency_key=job.idempotency_key,
            errors=tuple(errors),
            summary=summary,
        )
        return self._repo.save_sync_job(updated)

    def _update_health_failure(
        self,
        connector: MarketplaceDataConnector,
        errors: list[ConnectorError],
        started: datetime,
    ) -> None:
        prior = self._repo.get_health(connector.connector_id)
        self._repo.save_health(
            ConnectorHealth(
                connector_id=connector.connector_id,
                status=ConnectorHealthStatus.UNAVAILABLE,
                last_attempted_sync=started,
                last_successful_sync=prior.last_successful_sync if prior else None,
                records_failed=1,
                rate_limit=connector.report_rate_limit(),
                recent_errors=tuple(errors[-5:]),
                consecutive_failures=(prior.consecutive_failures + 1) if prior else 1,
                message=str(errors[-1].message if errors else "sync failed"),
            )
        )

    @staticmethod
    def _source_mode_for(connector: MarketplaceDataConnector) -> SourceMode:
        marketplace = connector.marketplace
        if marketplace == "fixture":
            return SourceMode.FIXTURE
        if marketplace == "imported":
            return SourceMode.IMPORTED
        # simulated_live intentionally uses LIVE mode with simulated=True labeling
        return SourceMode.LIVE
