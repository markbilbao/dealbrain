"""SQLAlchemy MarketplaceDataRepository — Sprint 23."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

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
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import (
    MARKETPLACE_DATA_STORES,
    MD_CATALOG,
    MD_CHECKPOINTS,
    MD_CONFIGURATIONS,
    MD_CONNECTOR_RUNS,
    MD_CONTENT_HASH,
    MD_DEAD_LETTERS,
    MD_HEALTH,
    MD_IMPORT_BATCHES,
    MD_IMPORT_RECORDS,
    MD_INVENTORY_SNAPSHOTS,
    MD_OFFERS,
    MD_PRICE_SNAPSHOTS,
    MD_RAW_RECORDS,
    MD_SOURCES,
    MD_SYNC_CONFLICTS,
    MD_SYNC_JOBS,
)
from app.marketplace.fixtures import CATALOG_PRODUCTS
from app.marketplace.matching.matcher import CatalogEntry, MarketplaceProductMatcher


@dataclass(frozen=True, slots=True)
class _ContentHashRef:
    offer_id: str


class SqlAlchemyMarketplaceDataRepository(MarketplaceDataRepository, SessionBound):
    """Operational-entity backed marketplace data store with deterministic matching."""

    def __init__(self, session_factory=None, session=None) -> None:
        super().__init__(session_factory=session_factory, session=session)
        self._matcher = MarketplaceProductMatcher()
        self._seed_catalog()
        self._load_catalog_from_db()

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

    def _load_catalog_from_db(self) -> None:
        with self._ops() as ops:
            entries = ops.list(MD_CATALOG, CatalogEntry)
        for entry in entries:
            self._matcher.register(entry)

    def remember_content_hash(self, content_hash: str, offer_id: str) -> None:
        digest = content_hash.strip()
        if not digest:
            return
        with self._ops() as ops:
            ops.upsert(
                MD_CONTENT_HASH,
                digest,
                _ContentHashRef(offer_id=offer_id),
                secondary_key=digest,
            )

    def save_source(self, source: MarketplaceSource) -> MarketplaceSource:
        with self._ops() as ops:
            return ops.upsert(MD_SOURCES, source.source_id, source)

    def list_sources(self) -> list[MarketplaceSource]:
        with self._ops() as ops:
            return ops.list(MD_SOURCES, MarketplaceSource)

    def get_source(self, source_id: str) -> MarketplaceSource | None:
        with self._ops() as ops:
            return ops.get(MD_SOURCES, source_id, MarketplaceSource)

    def save_configuration(self, config: ConnectorConfiguration) -> ConnectorConfiguration:
        with self._ops() as ops:
            return ops.upsert(MD_CONFIGURATIONS, config.connector_id, config)

    def get_configuration(self, connector_id: str) -> ConnectorConfiguration | None:
        with self._ops() as ops:
            return ops.get(MD_CONFIGURATIONS, connector_id, ConnectorConfiguration)

    def save_raw_record(self, record: RawMarketplaceRecord) -> RawMarketplaceRecord:
        with self._ops() as ops:
            return ops.upsert(MD_RAW_RECORDS, record.record_id, record)

    def get_raw_record(self, record_id: str) -> RawMarketplaceRecord | None:
        with self._ops() as ops:
            return ops.get(MD_RAW_RECORDS, record_id, RawMarketplaceRecord)

    def save_offer(self, offer: MarketplaceOffer) -> MarketplaceOffer:
        with self._ops() as ops:
            saved = ops.upsert(MD_OFFERS, offer.offer_id, offer)
            if offer.raw_record_id:
                raw = ops.get(MD_RAW_RECORDS, offer.raw_record_id, RawMarketplaceRecord)
                if raw is not None and raw.content_hash:
                    digest = raw.content_hash.strip()
                    if digest:
                        ops.upsert(
                            MD_CONTENT_HASH,
                            digest,
                            _ContentHashRef(offer_id=offer.offer_id),
                            secondary_key=digest,
                        )
            return saved

    def get_offer(self, offer_id: str) -> MarketplaceOffer | None:
        with self._ops() as ops:
            return ops.get(MD_OFFERS, offer_id, MarketplaceOffer)

    def list_offers(
        self,
        *,
        source_mode: str | None = None,
        marketplace: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[MarketplaceOffer]:
        mode_key = source_mode.strip().lower() if source_mode else None
        market_key = marketplace.strip().lower() if marketplace else None
        product_key = product_id.strip() if product_id else None

        def _matches(offer: MarketplaceOffer) -> bool:
            if mode_key is not None and offer.source_mode.value != mode_key:
                return False
            if market_key is not None and offer.marketplace.lower() != market_key:
                return False
            if product_key is not None and offer.product_id != product_key:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                MD_OFFERS,
                MarketplaceOffer,
                limit=limit,
                predicate=_matches,
            )

    def find_offer_by_content_hash(self, content_hash: str) -> MarketplaceOffer | None:
        digest = content_hash.strip()
        if not digest:
            return None
        with self._ops() as ops:
            ref = ops.get(MD_CONTENT_HASH, digest, _ContentHashRef)
            if ref is None:
                ref = ops.get_by_secondary(MD_CONTENT_HASH, digest, _ContentHashRef)
            if ref is None:
                return None
            return ops.get(MD_OFFERS, ref.offer_id, MarketplaceOffer)

    def save_price_snapshot(self, snapshot: MarketplacePriceSnapshot) -> MarketplacePriceSnapshot:
        with self._ops() as ops:
            return ops.upsert(
                MD_PRICE_SNAPSHOTS,
                snapshot.snapshot_id,
                snapshot,
                owner_id=snapshot.product_id,
            )

    def list_price_history(self, product_id: str) -> list[MarketplacePriceSnapshot]:
        with self._ops() as ops:
            snapshots = ops.list(
                MD_PRICE_SNAPSHOTS,
                MarketplacePriceSnapshot,
                owner_id=product_id,
            )
        snapshots.sort(key=lambda item: item.observed_at)
        return snapshots

    def save_inventory_snapshot(self, snapshot: InventorySnapshot) -> InventorySnapshot:
        with self._ops() as ops:
            return ops.upsert(
                MD_INVENTORY_SNAPSHOTS,
                snapshot.snapshot_id,
                snapshot,
                owner_id=snapshot.product_id,
            )

    def list_inventory_history(self, product_id: str) -> list[InventorySnapshot]:
        with self._ops() as ops:
            snapshots = ops.list(
                MD_INVENTORY_SNAPSHOTS,
                InventorySnapshot,
                owner_id=product_id,
            )
        snapshots.sort(key=lambda item: item.observed_at)
        return snapshots

    def save_import_batch(self, batch: ImportBatch) -> ImportBatch:
        with self._ops() as ops:
            secondary = batch.idempotency_key.strip() if batch.idempotency_key else None
            if secondary == "":
                secondary = None
            return ops.upsert(
                MD_IMPORT_BATCHES,
                batch.batch_id,
                batch,
                secondary_key=secondary,
            )

    def get_import_batch(self, batch_id: str) -> ImportBatch | None:
        with self._ops() as ops:
            return ops.get(MD_IMPORT_BATCHES, batch_id, ImportBatch)

    def get_import_batch_by_idempotency(self, key: str) -> ImportBatch | None:
        cleaned = key.strip()
        if not cleaned:
            return None
        with self._ops() as ops:
            return ops.get_by_secondary(MD_IMPORT_BATCHES, cleaned, ImportBatch)

    def save_import_record(self, batch_id: str, record: ImportRecord) -> ImportRecord:
        with self._ops() as ops:
            return ops.upsert(
                MD_IMPORT_RECORDS,
                record.record_id,
                record,
                owner_id=batch_id,
            )

    def list_import_errors(self, batch_id: str) -> list[ImportRecord]:
        with self._ops() as ops:
            records = ops.list(MD_IMPORT_RECORDS, ImportRecord, owner_id=batch_id)
        return [r for r in records if r.status == "rejected"]

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        with self._ops() as ops:
            secondary = job.idempotency_key.strip() if job.idempotency_key else None
            if secondary == "":
                secondary = None
            return ops.upsert(
                MD_SYNC_JOBS,
                job.job_id,
                job,
                secondary_key=secondary,
            )

    def get_sync_job(self, job_id: str) -> SyncJob | None:
        with self._ops() as ops:
            return ops.get(MD_SYNC_JOBS, job_id, SyncJob)

    def get_sync_job_by_idempotency(self, key: str) -> SyncJob | None:
        cleaned = key.strip()
        if not cleaned:
            return None
        with self._ops() as ops:
            return ops.get_by_secondary(MD_SYNC_JOBS, cleaned, SyncJob)

    def save_sync_conflict(self, conflict: SyncConflict) -> SyncConflict:
        with self._ops() as ops:
            return ops.upsert(
                MD_SYNC_CONFLICTS,
                conflict.conflict_id,
                conflict,
                owner_id=conflict.sync_job_id,
            )

    def list_sync_conflicts(self, sync_job_id: str) -> list[SyncConflict]:
        with self._ops() as ops:
            return ops.list(MD_SYNC_CONFLICTS, SyncConflict, owner_id=sync_job_id)

    def save_checkpoint(self, checkpoint: SyncCheckpoint) -> SyncCheckpoint:
        with self._ops() as ops:
            return ops.upsert(MD_CHECKPOINTS, checkpoint.connector_id, checkpoint)

    def get_checkpoint(self, connector_id: str) -> SyncCheckpoint | None:
        with self._ops() as ops:
            return ops.get(MD_CHECKPOINTS, connector_id, SyncCheckpoint)

    def save_health(self, health: ConnectorHealth) -> ConnectorHealth:
        with self._ops() as ops:
            return ops.upsert(MD_HEALTH, health.connector_id, health)

    def get_health(self, connector_id: str) -> ConnectorHealth | None:
        with self._ops() as ops:
            return ops.get(MD_HEALTH, connector_id, ConnectorHealth)

    def save_dead_letter(self, record: DeadLetterRecord) -> DeadLetterRecord:
        with self._ops() as ops:
            return ops.upsert(
                MD_DEAD_LETTERS,
                record.record_id,
                record,
                owner_id=record.sync_job_id,
            )

    def list_dead_letters(self, sync_job_id: str) -> list[DeadLetterRecord]:
        with self._ops() as ops:
            return ops.list(MD_DEAD_LETTERS, DeadLetterRecord, owner_id=sync_job_id)

    def save_connector_run(self, run: ConnectorRun) -> ConnectorRun:
        with self._ops() as ops:
            return ops.upsert(MD_CONNECTOR_RUNS, run.run_id, run)

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
        entry = CatalogEntry(
            product_id=product_id,
            brand=brand,
            model=model,
            title=title,
            sku=sku,
            upc=upc,
            aliases=tuple(aliases),
        )
        self._matcher.register(entry)
        with self._ops() as ops:
            ops.upsert(MD_CATALOG, product_id, entry)

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
        with self._ops() as ops:
            ops.clear_stores(MARKETPLACE_DATA_STORES)
        self._matcher = MarketplaceProductMatcher()
        self._seed_catalog()
