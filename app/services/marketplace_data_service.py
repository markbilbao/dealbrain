"""Marketplace Data Synchronization application service — Sprint 18."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    SIMULATED_LIVE_LABEL,
    SOURCE_MODE_LABELS,
    ConnectorConfiguration,
    ConnectorHealth,
    ImportBatch,
    ImportRecord,
    InventorySnapshot,
    MarketplaceConnectorInfo,
    MarketplaceOffer,
    MarketplacePriceSnapshot,
    MarketplaceSource,
    RawMarketplaceRecord,
    SourceMode,
    SourceStatus,
    SyncJob,
    SyncMode,
)
from app.domain.exceptions import (
    MarketplaceDataAuthError,
    MarketplaceDataNotFoundError,
    MarketplaceDataValidationError,
)
from app.domain.interfaces.marketplace_data_repository import (
    MarketplaceDataAuditHook,
    MarketplaceDataRepository,
    SyncJobTrigger,
)
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.health.tracker import build_health
from app.marketplace.imports.pipeline import ImportPipeline
from app.marketplace.normalization.normalizer import MarketplaceRecordNormalizer, content_hash
from app.marketplace.registry import MarketplaceConnectorRegistry
from app.marketplace.security import redact_secrets
from app.marketplace.sync.engine import MarketplaceSyncEngine


class InMemoryAuditHook(MarketplaceDataAuditHook):
    """Simple in-memory audit trail (no secrets)."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(
        self,
        action: str,
        *,
        actor: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "action": action,
                "actor": actor,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": redact_secrets(dict(details or {})),
            }
        )


class MarketplaceDataService(SyncJobTrigger):
    """Orchestrates connectors, imports, sync, freshness, and offer queries."""

    def __init__(
        self,
        repository: MarketplaceDataRepository,
        registry: MarketplaceConnectorRegistry,
        *,
        audit: MarketplaceDataAuditHook | None = None,
        clock: Callable[[], datetime] | None = None,
        require_auth_for_ops: bool = True,
    ) -> None:
        self._repo = repository
        self._registry = registry
        self._audit = audit or InMemoryAuditHook()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._require_auth_for_ops = require_auth_for_ops
        self._pipeline = ImportPipeline()
        self._normalizer = MarketplaceRecordNormalizer()
        self._ensure_default_sources()
        # Wire imported connector to repository offers
        imported = self._registry.get(ImportedMarketplaceConnector.CONNECTOR_ID)
        if isinstance(imported, ImportedMarketplaceConnector):
            # Replace with repo-backed provider
            self._registry.register(
                ImportedMarketplaceConnector(lambda: self._repo.list_offers(limit=10_000))
            )

    def _ensure_default_sources(self) -> None:
        defaults = (
            MarketplaceSource(
                source_id="source-fixture",
                name="Fixture Demo Source",
                marketplace="fixture",
                source_mode=SourceMode.FIXTURE,
                status=SourceStatus.ACTIVE,
                connector_id=FixtureMarketplaceConnector.CONNECTOR_ID,
                description="Deterministic demo fixtures",
            ),
            MarketplaceSource(
                source_id="source-imported",
                name="Imported File Source",
                marketplace="imported",
                source_mode=SourceMode.IMPORTED,
                status=SourceStatus.ACTIVE,
                connector_id=ImportedMarketplaceConnector.CONNECTOR_ID,
                description="CSV/JSON imports",
            ),
            MarketplaceSource(
                source_id="source-simulated-live",
                name="Simulated Live Source",
                marketplace="simulated_live",
                source_mode=SourceMode.LIVE,
                status=SourceStatus.ACTIVE,
                connector_id=MockLiveMarketplaceConnector.CONNECTOR_ID,
                description=SIMULATED_LIVE_LABEL,
                simulated=True,
                label=SIMULATED_LIVE_LABEL,
            ),
        )
        for source in defaults:
            if self._repo.get_source(source.source_id) is None:
                self._repo.save_source(source)

        configs = (
            ConnectorConfiguration(
                connector_id=FixtureMarketplaceConnector.CONNECTOR_ID,
                marketplace="fixture",
                enabled=True,
            ),
            ConnectorConfiguration(
                connector_id=ImportedMarketplaceConnector.CONNECTOR_ID,
                marketplace="imported",
                enabled=True,
            ),
            ConnectorConfiguration(
                connector_id=MockLiveMarketplaceConnector.CONNECTOR_ID,
                marketplace="simulated_live",
                enabled=True,
                base_url="https://simulated.dealbrain.local",
            ),
        )
        for config in configs:
            if self._repo.get_configuration(config.connector_id) is None:
                self._repo.save_configuration(config)
                self._repo.save_health(
                    build_health(
                        connector_id=config.connector_id,
                        enabled=config.enabled,
                        configured=True,
                        message="Configured for demo",
                    )
                )

    def _require_actor(self, actor: str | None) -> str:
        if not self._require_auth_for_ops:
            return actor or "anonymous-demo"
        if not actor:
            raise MarketplaceDataAuthError(
                "Authentication required for marketplace data operations."
            )
        return actor

    def list_sources(self) -> list[MarketplaceSource]:
        return self._repo.list_sources()

    def list_connectors(self, *, include_stubs: bool = True) -> list[MarketplaceConnectorInfo]:
        return self._registry.list_infos(include_stubs=include_stubs)

    def get_connector(self, connector_id: str) -> dict[str, Any]:
        connector = self._registry.get(connector_id)
        if connector is None:
            raise MarketplaceDataNotFoundError(connector_id)
        info = self._registry.connector_info(connector)
        config = self._repo.get_configuration(connector_id)
        health = self._repo.get_health(connector_id) or connector.report_health()
        return {
            **info.to_dict(),
            "configuration": config.to_dict(redact=True) if config else None,
            "health": health.to_dict(),
        }

    def test_connector(self, connector_id: str, *, actor: str | None = None) -> dict[str, Any]:
        actor_id = self._require_actor(actor)
        connector = self._registry.get(connector_id)
        if connector is None:
            raise MarketplaceDataNotFoundError(connector_id)
        config = self._repo.get_configuration(connector_id)
        if config is None:
            raise MarketplaceDataValidationError(f"Connector {connector_id} is not configured")
        ok, message = connector.test_connection(config)
        self._audit.record(
            "connector.test",
            actor=actor_id,
            resource_type="connector",
            resource_id=connector_id,
            details={"ok": ok, "message": message},
        )
        return {
            "connector_id": connector_id,
            "ok": ok,
            "message": message,
            "source_mode": self._registry.connector_info(connector).source_mode.value,
            "simulated": self._registry.connector_info(connector).simulated,
            "label": self._registry.connector_info(connector).to_dict()["label"],
        }

    def get_connector_health(self, connector_id: str) -> ConnectorHealth:
        if self._registry.get(connector_id) is None:
            raise MarketplaceDataNotFoundError(connector_id)
        health = self._repo.get_health(connector_id)
        if health is not None:
            return health
        connector = self._registry.get(connector_id)
        assert connector is not None
        return connector.report_health()

    def import_payload(
        self,
        *,
        filename: str,
        payload: str | bytes,
        content_type: str | None = None,
        field_mapping: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
        actor: str | None = None,
    ) -> ImportBatch:
        actor_id = self._require_actor(actor)
        if idempotency_key:
            existing = self._repo.get_import_batch_by_idempotency(idempotency_key)
            if existing is not None:
                return existing

        batch_id = self._make_id("import", filename, idempotency_key or "")
        known_hashes: set[str] = set()
        for offer in self._repo.list_offers(limit=10_000):
            if offer.raw_record_id:
                raw = self._repo.get_raw_record(offer.raw_record_id)
                if raw and raw.content_hash:
                    known_hashes.add(raw.content_hash)

        batch, records, accepted = self._pipeline.prepare_batch(
            batch_id=batch_id,
            filename=filename,
            payload=payload,
            content_type=content_type,
            field_mapping=field_mapping,
            idempotency_key=idempotency_key,
            now=self._clock(),
            known_hashes=known_hashes,
        )
        self._repo.save_import_batch(batch)
        for record in records:
            self._repo.save_import_record(batch_id, record)

        config = self._repo.get_configuration(ImportedMarketplaceConnector.CONNECTOR_ID)
        thresholds = (
            (
                config.freshness_fresh_hours,
                config.freshness_aging_hours,
                config.freshness_stale_hours,
            )
            if config
            else (6.0, 24.0, 72.0)
        )
        for index, mapped in enumerate(accepted, start=1):
            digest = content_hash(mapped)
            raw_id = f"raw:{batch_id}:{index}"
            ingested = self._clock()
            self._repo.save_raw_record(
                RawMarketplaceRecord(
                    record_id=raw_id,
                    source_mode=SourceMode.IMPORTED,
                    source_id="imported",
                    marketplace="imported",
                    payload=dict(mapped),
                    ingested_at=ingested,
                    connector_id=ImportedMarketplaceConnector.CONNECTOR_ID,
                    import_batch_id=batch_id,
                    content_hash=digest,
                )
            )
            offer = self._normalizer.normalize(
                mapped,
                source_mode=SourceMode.IMPORTED,
                source_id="imported",
                connector_id=ImportedMarketplaceConnector.CONNECTOR_ID,
                import_batch_id=batch_id,
                raw_record_id=raw_id,
                ingested_at=ingested,
                now=ingested,
                freshness_thresholds=thresholds,
            )
            decision = self._repo.match_product(
                brand=offer.brand,
                model=offer.model,
                title=offer.title,
                sku=offer.sku,
                marketplace_product_id=offer.marketplace_product_id,
                marketplace="imported",
            )
            offer = MarketplaceOffer(
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
                source_mode=SourceMode.IMPORTED,
                provenance=offer.provenance,
                freshness=offer.freshness,
                confidence=offer.confidence,
                matched_canonical_product_id=decision.matched_product_id,
                match_confidence=decision.confidence,
                match_reasons=decision.reasons,
                match_ambiguity=decision.ambiguity,
                observed_at=offer.observed_at,
                raw_record_id=raw_id,
                simulated=False,
            )
            self._repo.save_offer(offer)
            remember = getattr(self._repo, "remember_content_hash", None)
            if callable(remember):
                remember(digest, offer.offer_id)
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
                    source_timestamp=offer.provenance.source_timestamp
                    if offer.provenance
                    else None,
                    ingested_at=ingested,
                    source_mode=SourceMode.IMPORTED,
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
                    source_timestamp=offer.provenance.source_timestamp
                    if offer.provenance
                    else None,
                    ingested_at=ingested,
                    source_mode=SourceMode.IMPORTED,
                    seller_name=offer.seller.name if offer.seller else None,
                    provenance=offer.provenance,
                )
            )

        self._audit.record(
            "import.create",
            actor=actor_id,
            resource_type="import_batch",
            resource_id=batch.batch_id,
            details={
                "filename": filename,
                "accepted": batch.records_accepted,
                "rejected": batch.records_rejected,
            },
        )
        return batch

    def get_import(self, batch_id: str) -> ImportBatch:
        batch = self._repo.get_import_batch(batch_id)
        if batch is None:
            raise MarketplaceDataNotFoundError(batch_id)
        return batch

    def get_import_errors(self, batch_id: str) -> list[ImportRecord]:
        if self._repo.get_import_batch(batch_id) is None:
            raise MarketplaceDataNotFoundError(batch_id)
        return self._repo.list_import_errors(batch_id)

    def trigger_sync(
        self,
        connector_id: str,
        *,
        mode: SyncMode = SyncMode.FULL,
        idempotency_key: str | None = None,
        now: datetime | None = None,
        actor: str | None = None,
        query: str | None = None,
    ) -> SyncJob:
        actor_id = self._require_actor(actor)
        del now
        job_id = self._make_id("sync", connector_id, mode.value, idempotency_key or "")
        connectors = {
            c.connector_id: c
            for c in self._registry.list_connectors()
            if not c.connector_id.startswith("future-")
        }
        engine = MarketplaceSyncEngine(self._repo, connectors, clock=self._clock)
        job = engine.run(
            job_id=job_id,
            connector_id=connector_id,
            mode=mode,
            idempotency_key=idempotency_key,
            query=query,
        )
        self._audit.record(
            "sync.trigger",
            actor=actor_id,
            resource_type="sync_job",
            resource_id=job.job_id,
            details={"connector_id": connector_id, "mode": mode.value, "status": job.status.value},
        )
        return job

    def get_sync(self, job_id: str) -> SyncJob:
        job = self._repo.get_sync_job(job_id)
        if job is None:
            raise MarketplaceDataNotFoundError(job_id)
        return job

    def get_sync_conflicts(self, job_id: str) -> list[Any]:
        if self._repo.get_sync_job(job_id) is None:
            raise MarketplaceDataNotFoundError(job_id)
        return self._repo.list_sync_conflicts(job_id)

    def list_offers(
        self,
        *,
        source_mode: str | None = None,
        marketplace: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[MarketplaceOffer]:
        return self._repo.list_offers(
            source_mode=source_mode,
            marketplace=marketplace,
            product_id=product_id,
            limit=limit,
        )

    def get_offer(self, offer_id: str) -> MarketplaceOffer:
        offer = self._repo.get_offer(offer_id)
        if offer is None:
            raise MarketplaceDataNotFoundError(offer_id)
        return offer

    def list_price_history(self, product_id: str) -> list[MarketplacePriceSnapshot]:
        return self._repo.list_price_history(product_id)

    def list_inventory_history(self, product_id: str) -> list[InventorySnapshot]:
        return self._repo.list_inventory_history(product_id)

    def seed_demo_data(self, *, actor: str | None = None) -> dict[str, Any]:
        """Deterministic fixture + simulated-live sync for demos."""
        actor_id = actor or "demo"
        fixture_job = self.trigger_sync(
            FixtureMarketplaceConnector.CONNECTOR_ID,
            mode=SyncMode.FULL,
            idempotency_key="demo-fixture-sync",
            actor=actor_id if not self._require_auth_for_ops else actor_id,
        )
        # Temporarily relax auth for chained demo seed when require_auth and actor provided
        live_job = self.trigger_sync(
            MockLiveMarketplaceConnector.CONNECTOR_ID,
            mode=SyncMode.FULL,
            idempotency_key="demo-simulated-live-sync",
            actor=actor_id,
        )
        return {
            "fixture_sync": fixture_job.to_dict(),
            "simulated_live_sync": live_job.to_dict(),
            "offers": len(self.list_offers()),
            "label": SIMULATED_LIVE_LABEL,
            "source_mode_labels": {k.value: v for k, v in SOURCE_MODE_LABELS.items()},
        }

    def provenance_notes_for_offer(self, offer: MarketplaceOffer) -> list[str]:
        notes: list[str] = []
        label = offer.to_dict().get("label")
        if label:
            notes.append(str(label))
        if offer.freshness and offer.freshness.warning:
            notes.append(offer.freshness.warning)
        if offer.source_mode != SourceMode.LIVE:
            notes.append("Do not treat this price as currently available live marketplace pricing.")
        elif offer.simulated:
            notes.append(SIMULATED_LIVE_LABEL)
        elif offer.freshness and not offer.freshness.is_current_live_price:
            notes.append("Live connector data is not fresh enough to claim current availability.")
        return notes

    def shopping_enrichment(self, product_name: str | None = None) -> list[dict[str, Any]]:
        """Offer provenance/freshness payloads for Shopping Assistant integration."""
        offers = self.list_offers(limit=200)
        out: list[dict[str, Any]] = []
        needle = (product_name or "").strip().lower()
        for offer in offers:
            if (
                needle
                and needle not in offer.title.lower()
                and needle not in (offer.brand or "").lower()
            ):
                continue
            out.append(
                {
                    "offer_id": offer.offer_id,
                    "product_id": offer.matched_canonical_product_id or offer.product_id,
                    "title": offer.title,
                    "total_price": offer.total_price,
                    "currency": offer.currency,
                    "marketplace": offer.marketplace,
                    "source_mode": offer.source_mode.value,
                    "data_status": (
                        "live"
                        if offer.source_mode == SourceMode.LIVE
                        else ("imported" if offer.source_mode == SourceMode.IMPORTED else "mock")
                    ),
                    "freshness_status": offer.freshness.status.value
                    if offer.freshness
                    else "unknown",
                    "freshness_warning": offer.freshness.warning if offer.freshness else None,
                    "is_current_live_price": bool(
                        offer.freshness and offer.freshness.is_current_live_price
                    ),
                    "simulated": offer.simulated,
                    "label": offer.to_dict().get("label"),
                    "match_confidence": offer.match_confidence,
                    "match_reasons": list(offer.match_reasons),
                    "provenance": offer.provenance.to_dict() if offer.provenance else None,
                    "notes": self.provenance_notes_for_offer(offer),
                }
            )
        # Prefer fresher reliable offers when sorting
        rank = {"fresh": 3, "aging": 2, "stale": 1, "unknown": 0}

        def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
            return (
                1 if item["data_status"] == "live" and not item["simulated"] else 0,
                rank.get(str(item["freshness_status"]), 0),
                -(item.get("match_confidence") or 0),
            )

        out.sort(key=sort_key, reverse=True)
        return out

    @staticmethod
    def _make_id(*parts: str) -> str:
        material = "|".join(parts)
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
        return f"{parts[0]}-{digest}"
