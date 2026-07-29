"""Marketplace Data Synchronization ports — Sprint 18."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorRateLimit,
    ConnectorRun,
    DeadLetterRecord,
    ImportBatch,
    ImportRecord,
    InventorySnapshot,
    MarketplaceOffer,
    MarketplacePriceSnapshot,
    MarketplaceSeller,
    MarketplaceSource,
    ProductMatchDecision,
    RawMarketplaceRecord,
    SyncCheckpoint,
    SyncConflict,
    SyncJob,
    SyncMode,
)


class MarketplaceDataConnector(ABC):
    """Provider-neutral marketplace connector for data synchronization.

    Distinct from Sprint 4 ``MarketplaceConnector`` (search/normalize listings).
    Implementations declare capabilities and must never fabricate live status.
    """

    @property
    @abstractmethod
    def connector_id(self) -> str:
        """Stable connector identifier."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable connector name."""

    @property
    @abstractmethod
    def marketplace(self) -> str:
        """Marketplace key (e.g. ``fixture``, ``imported``, ``simulated_live``)."""

    @property
    @abstractmethod
    def capabilities(self) -> frozenset[ConnectorCapability]:
        """Declared supported capabilities."""

    @abstractmethod
    def validate_configuration(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        """Validate non-secret configuration. Returns (ok, message)."""

    @abstractmethod
    def test_connection(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        """Test connectivity without claiming real marketplace access unless true."""

    def fetch_products(
        self,
        config: ConnectorConfiguration,
        *,
        query: str | None = None,
        checkpoint: SyncCheckpoint | None = None,
        limit: int = 50,
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        raise NotImplementedError("fetch_products not supported by this connector")

    def fetch_product(
        self, config: ConnectorConfiguration, product_id: str
    ) -> Mapping[str, Any] | None:
        raise NotImplementedError("fetch_product not supported by this connector")

    def fetch_offers(
        self,
        config: ConnectorConfiguration,
        *,
        query: str | None = None,
        checkpoint: SyncCheckpoint | None = None,
        limit: int = 50,
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        raise NotImplementedError("fetch_offers not supported by this connector")

    def fetch_prices(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        raise NotImplementedError("fetch_prices not supported by this connector")

    def fetch_inventory(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        raise NotImplementedError("fetch_inventory not supported by this connector")

    def fetch_sellers(
        self, config: ConnectorConfiguration, seller_ids: Sequence[str]
    ) -> list[MarketplaceSeller]:
        raise NotImplementedError("fetch_sellers not supported by this connector")

    def fetch_reviews(
        self, config: ConnectorConfiguration, product_id: str
    ) -> list[Mapping[str, Any]]:
        raise NotImplementedError("fetch_reviews not supported by this connector")

    def continue_from_checkpoint(
        self, config: ConnectorConfiguration, checkpoint: SyncCheckpoint
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        raise NotImplementedError("continue_from_checkpoint not supported by this connector")

    def report_rate_limit(self) -> ConnectorRateLimit:
        return ConnectorRateLimit(limited=False)

    def report_health(self) -> ConnectorHealth:
        from app.domain.entities.marketplace_data import ConnectorHealthStatus

        return ConnectorHealth(
            connector_id=self.connector_id,
            status=ConnectorHealthStatus.UNCONFIGURED,
        )


class MarketplaceDataRepository(ABC):
    """Persistence port for marketplace data synchronization (in-memory for Sprint 18)."""

    @abstractmethod
    def save_source(self, source: MarketplaceSource) -> MarketplaceSource: ...

    @abstractmethod
    def list_sources(self) -> list[MarketplaceSource]: ...

    @abstractmethod
    def get_source(self, source_id: str) -> MarketplaceSource | None: ...

    @abstractmethod
    def save_configuration(self, config: ConnectorConfiguration) -> ConnectorConfiguration: ...

    @abstractmethod
    def get_configuration(self, connector_id: str) -> ConnectorConfiguration | None: ...

    @abstractmethod
    def save_raw_record(self, record: RawMarketplaceRecord) -> RawMarketplaceRecord: ...

    @abstractmethod
    def get_raw_record(self, record_id: str) -> RawMarketplaceRecord | None: ...

    @abstractmethod
    def save_offer(self, offer: MarketplaceOffer) -> MarketplaceOffer: ...

    @abstractmethod
    def get_offer(self, offer_id: str) -> MarketplaceOffer | None: ...

    @abstractmethod
    def list_offers(
        self,
        *,
        source_mode: str | None = None,
        marketplace: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[MarketplaceOffer]: ...

    @abstractmethod
    def find_offer_by_content_hash(self, content_hash: str) -> MarketplaceOffer | None: ...

    @abstractmethod
    def save_price_snapshot(
        self, snapshot: MarketplacePriceSnapshot
    ) -> MarketplacePriceSnapshot: ...

    @abstractmethod
    def list_price_history(self, product_id: str) -> list[MarketplacePriceSnapshot]: ...

    @abstractmethod
    def save_inventory_snapshot(self, snapshot: InventorySnapshot) -> InventorySnapshot: ...

    @abstractmethod
    def list_inventory_history(self, product_id: str) -> list[InventorySnapshot]: ...

    @abstractmethod
    def save_import_batch(self, batch: ImportBatch) -> ImportBatch: ...

    @abstractmethod
    def get_import_batch(self, batch_id: str) -> ImportBatch | None: ...

    @abstractmethod
    def get_import_batch_by_idempotency(self, key: str) -> ImportBatch | None: ...

    @abstractmethod
    def save_import_record(self, batch_id: str, record: ImportRecord) -> ImportRecord: ...

    @abstractmethod
    def list_import_errors(self, batch_id: str) -> list[ImportRecord]: ...

    @abstractmethod
    def save_sync_job(self, job: SyncJob) -> SyncJob: ...

    @abstractmethod
    def get_sync_job(self, job_id: str) -> SyncJob | None: ...

    @abstractmethod
    def get_sync_job_by_idempotency(self, key: str) -> SyncJob | None: ...

    @abstractmethod
    def save_sync_conflict(self, conflict: SyncConflict) -> SyncConflict: ...

    @abstractmethod
    def list_sync_conflicts(self, sync_job_id: str) -> list[SyncConflict]: ...

    @abstractmethod
    def save_checkpoint(self, checkpoint: SyncCheckpoint) -> SyncCheckpoint: ...

    @abstractmethod
    def get_checkpoint(self, connector_id: str) -> SyncCheckpoint | None: ...

    @abstractmethod
    def save_health(self, health: ConnectorHealth) -> ConnectorHealth: ...

    @abstractmethod
    def get_health(self, connector_id: str) -> ConnectorHealth | None: ...

    @abstractmethod
    def save_dead_letter(self, record: DeadLetterRecord) -> DeadLetterRecord: ...

    @abstractmethod
    def list_dead_letters(self, sync_job_id: str) -> list[DeadLetterRecord]: ...

    @abstractmethod
    def save_connector_run(self, run: ConnectorRun) -> ConnectorRun: ...

    @abstractmethod
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
    ) -> None: ...

    @abstractmethod
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
    ) -> ProductMatchDecision: ...

    @abstractmethod
    def clear(self) -> None: ...


class SyncJobTrigger(ABC):
    """Scheduler-neutral job trigger — Sprint 19 / infra may invoke later."""

    @abstractmethod
    def trigger_sync(
        self,
        connector_id: str,
        *,
        mode: SyncMode = SyncMode.FULL,
        idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> SyncJob: ...


class MarketplaceDataAuditHook(ABC):
    """Audit hook for configuration and operational actions."""

    @abstractmethod
    def record(
        self,
        action: str,
        *,
        actor: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None: ...
