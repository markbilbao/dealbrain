"""In-memory MarketplaceDataRepository for Sprint 18 demos and tests."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.marketplace_data import (
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorRun,
    DeadLetterRecord,
    ImportBatch,
    ImportRecord,
    InventorySnapshot,
    MarketplaceOffer,
    MarketplacePriceSnapshot,
    MarketplaceSource,
    ProductMatchDecision,
    RawMarketplaceRecord,
    SyncCheckpoint,
    SyncConflict,
    SyncJob,
)
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataRepository
from app.marketplace.fixtures import CATALOG_PRODUCTS
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher


class InMemoryMarketplaceDataRepository(MarketplaceDataRepository):
    """Dict-backed marketplace data store with deterministic catalog matching."""

    def __init__(self) -> None:
        self._sources: dict[str, MarketplaceSource] = {}
        self._configurations: dict[str, ConnectorConfiguration] = {}
        self._raw_records: dict[str, RawMarketplaceRecord] = {}
        self._offers: dict[str, MarketplaceOffer] = {}
        self._content_hash_to_offer_id: dict[str, str] = {}
        self._raw_content_hashes: dict[str, str] = {}
        self._price_snapshots: dict[str, list[MarketplacePriceSnapshot]] = {}
        self._inventory_snapshots: dict[str, list[InventorySnapshot]] = {}
        self._import_batches: dict[str, ImportBatch] = {}
        self._import_batch_idempotency: dict[str, str] = {}
        self._import_records: dict[str, list[ImportRecord]] = {}
        self._sync_jobs: dict[str, SyncJob] = {}
        self._sync_job_idempotency: dict[str, str] = {}
        self._sync_conflicts: dict[str, list[SyncConflict]] = {}
        self._checkpoints: dict[str, SyncCheckpoint] = {}
        self._health: dict[str, ConnectorHealth] = {}
        self._dead_letters: dict[str, list[DeadLetterRecord]] = {}
        self._connector_runs: dict[str, ConnectorRun] = {}
        self._matcher = MarketplaceProductMatcher()
        self._seed_catalog()

    def _seed_catalog(self) -> None:
        for row in CATALOG_PRODUCTS:
            aliases = row.get("aliases") or ()
            self._matcher.register(
                CatalogEntry(
                    product_id=str(row["product_id"]),
                    brand=row.get("brand"),
                    model=row.get("model"),
                    title=str(row["title"]),
                    sku=row.get("sku"),
                    upc=row.get("upc"),
                    ean=row.get("ean"),
                    gtin=row.get("gtin"),
                    aliases=tuple(str(a) for a in aliases),
                )
            )

    def remember_content_hash(self, content_hash: str, offer_id: str) -> None:
        """Index a content hash to an offer for duplicate detection."""
        digest = content_hash.strip()
        if digest:
            self._content_hash_to_offer_id[digest] = offer_id

    def save_source(self, source: MarketplaceSource) -> MarketplaceSource:
        self._sources[source.source_id] = source
        return source

    def list_sources(self) -> list[MarketplaceSource]:
        return list(self._sources.values())

    def get_source(self, source_id: str) -> MarketplaceSource | None:
        return self._sources.get(source_id)

    def save_configuration(self, config: ConnectorConfiguration) -> ConnectorConfiguration:
        self._configurations[config.connector_id] = config
        return config

    def get_configuration(self, connector_id: str) -> ConnectorConfiguration | None:
        return self._configurations.get(connector_id)

    def save_raw_record(self, record: RawMarketplaceRecord) -> RawMarketplaceRecord:
        self._raw_records[record.record_id] = record
        if record.content_hash:
            self._raw_content_hashes[record.content_hash] = record.record_id
        return record

    def get_raw_record(self, record_id: str) -> RawMarketplaceRecord | None:
        return self._raw_records.get(record_id)

    def save_offer(self, offer: MarketplaceOffer) -> MarketplaceOffer:
        self._offers[offer.offer_id] = offer
        if offer.raw_record_id:
            raw = self._raw_records.get(offer.raw_record_id)
            if raw is not None and raw.content_hash:
                self.remember_content_hash(raw.content_hash, offer.offer_id)
        return offer

    def get_offer(self, offer_id: str) -> MarketplaceOffer | None:
        return self._offers.get(offer_id)

    def list_offers(
        self,
        *,
        source_mode: str | None = None,
        marketplace: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[MarketplaceOffer]:
        results: list[MarketplaceOffer] = []
        mode_key = source_mode.strip().lower() if source_mode else None
        market_key = marketplace.strip().lower() if marketplace else None
        product_key = product_id.strip() if product_id else None
        for offer in self._offers.values():
            if mode_key is not None and offer.source_mode.value != mode_key:
                continue
            if market_key is not None and offer.marketplace.lower() != market_key:
                continue
            if product_key is not None and offer.product_id != product_key:
                continue
            results.append(offer)
            if len(results) >= max(0, limit):
                break
        return results

    def find_offer_by_content_hash(self, content_hash: str) -> MarketplaceOffer | None:
        digest = content_hash.strip()
        if not digest:
            return None
        offer_id = self._content_hash_to_offer_id.get(digest)
        if offer_id is None:
            return None
        return self._offers.get(offer_id)

    def save_price_snapshot(self, snapshot: MarketplacePriceSnapshot) -> MarketplacePriceSnapshot:
        bucket = self._price_snapshots.setdefault(snapshot.product_id, [])
        bucket.append(snapshot)
        return snapshot

    def list_price_history(self, product_id: str) -> list[MarketplacePriceSnapshot]:
        snapshots = list(self._price_snapshots.get(product_id, ()))
        snapshots.sort(key=lambda item: item.observed_at)
        return snapshots

    def save_inventory_snapshot(self, snapshot: InventorySnapshot) -> InventorySnapshot:
        bucket = self._inventory_snapshots.setdefault(snapshot.product_id, [])
        bucket.append(snapshot)
        return snapshot

    def list_inventory_history(self, product_id: str) -> list[InventorySnapshot]:
        snapshots = list(self._inventory_snapshots.get(product_id, ()))
        snapshots.sort(key=lambda item: item.observed_at)
        return snapshots

    def save_import_batch(self, batch: ImportBatch) -> ImportBatch:
        self._import_batches[batch.batch_id] = batch
        if batch.idempotency_key:
            self._import_batch_idempotency[batch.idempotency_key] = batch.batch_id
        return batch

    def get_import_batch(self, batch_id: str) -> ImportBatch | None:
        return self._import_batches.get(batch_id)

    def get_import_batch_by_idempotency(self, key: str) -> ImportBatch | None:
        cleaned = key.strip()
        if not cleaned:
            return None
        batch_id = self._import_batch_idempotency.get(cleaned)
        if batch_id is None:
            return None
        return self._import_batches.get(batch_id)

    def save_import_record(self, batch_id: str, record: ImportRecord) -> ImportRecord:
        bucket = self._import_records.setdefault(batch_id, [])
        bucket.append(record)
        return record

    def list_import_errors(self, batch_id: str) -> list[ImportRecord]:
        return [r for r in self._import_records.get(batch_id, ()) if r.status == "rejected"]

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        self._sync_jobs[job.job_id] = job
        if job.idempotency_key:
            self._sync_job_idempotency[job.idempotency_key] = job.job_id
        return job

    def get_sync_job(self, job_id: str) -> SyncJob | None:
        return self._sync_jobs.get(job_id)

    def get_sync_job_by_idempotency(self, key: str) -> SyncJob | None:
        cleaned = key.strip()
        if not cleaned:
            return None
        job_id = self._sync_job_idempotency.get(cleaned)
        if job_id is None:
            return None
        return self._sync_jobs.get(job_id)

    def save_sync_conflict(self, conflict: SyncConflict) -> SyncConflict:
        bucket = self._sync_conflicts.setdefault(conflict.sync_job_id, [])
        bucket.append(conflict)
        return conflict

    def list_sync_conflicts(self, sync_job_id: str) -> list[SyncConflict]:
        return list(self._sync_conflicts.get(sync_job_id, ()))

    def save_checkpoint(self, checkpoint: SyncCheckpoint) -> SyncCheckpoint:
        self._checkpoints[checkpoint.connector_id] = checkpoint
        return checkpoint

    def get_checkpoint(self, connector_id: str) -> SyncCheckpoint | None:
        return self._checkpoints.get(connector_id)

    def save_health(self, health: ConnectorHealth) -> ConnectorHealth:
        self._health[health.connector_id] = health
        return health

    def get_health(self, connector_id: str) -> ConnectorHealth | None:
        return self._health.get(connector_id)

    def save_dead_letter(self, record: DeadLetterRecord) -> DeadLetterRecord:
        bucket = self._dead_letters.setdefault(record.sync_job_id, [])
        bucket.append(record)
        return record

    def list_dead_letters(self, sync_job_id: str) -> list[DeadLetterRecord]:
        return list(self._dead_letters.get(sync_job_id, ()))

    def save_connector_run(self, run: ConnectorRun) -> ConnectorRun:
        self._connector_runs[run.run_id] = run
        return run

    def register_catalog_product(
        self,
        *,
        product_id: str,
        brand: str | None,
        model: str | None,
        title: str,
        sku: str | None = None,
        upc: str | None = None,
        aliases: Sequence[str] = (),
    ) -> None:
        self._matcher.register(
            CatalogEntry(
                product_id=product_id,
                brand=brand,
                model=model,
                title=title,
                sku=sku,
                upc=upc,
                aliases=tuple(aliases),
            )
        )

    def match_product(
        self,
        *,
        brand: str | None,
        model: str | None,
        title: str,
        sku: str | None = None,
        upc: str | None = None,
        ean: str | None = None,
        gtin: str | None = None,
        marketplace_product_id: str | None = None,
        marketplace: str | None = None,
    ) -> ProductMatchDecision:
        return self._matcher.match(
            brand=brand,
            model=model,
            title=title,
            sku=sku,
            upc=upc,
            ean=ean,
            gtin=gtin,
            marketplace_product_id=marketplace_product_id,
            marketplace=marketplace,
        )

    def clear(self) -> None:
        """Reset all stored data and re-seed the fixture catalog (tests)."""
        self._sources.clear()
        self._configurations.clear()
        self._raw_records.clear()
        self._offers.clear()
        self._content_hash_to_offer_id.clear()
        self._raw_content_hashes.clear()
        self._price_snapshots.clear()
        self._inventory_snapshots.clear()
        self._import_batches.clear()
        self._import_batch_idempotency.clear()
        self._import_records.clear()
        self._sync_jobs.clear()
        self._sync_job_idempotency.clear()
        self._sync_conflicts.clear()
        self._checkpoints.clear()
        self._health.clear()
        self._dead_letters.clear()
        self._connector_runs.clear()
        self._matcher = MarketplaceProductMatcher()
        self._seed_catalog()
