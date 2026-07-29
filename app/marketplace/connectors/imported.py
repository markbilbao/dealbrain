"""Imported marketplace connector — serves previously imported records."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.domain.entities.marketplace_data import (
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorHealthStatus,
    MarketplaceOffer,
    SourceMode,
    SyncCheckpoint,
)
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector


class ImportedMarketplaceConnector(MarketplaceDataConnector):
    """Reads offers previously stored from CSV/JSON imports.

    Never labeled as live — source mode is always ``imported``.
    """

    CONNECTOR_ID = "imported-marketplace"
    SOURCE_MODE = SourceMode.IMPORTED

    def __init__(
        self,
        offer_provider: Callable[[], Sequence[MarketplaceOffer]] | None = None,
    ) -> None:
        self._offer_provider = offer_provider or (lambda: ())

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def name(self) -> str:
        return "Imported Marketplace Connector"

    @property
    def marketplace(self) -> str:
        return "imported"

    @property
    def capabilities(self) -> frozenset[ConnectorCapability]:
        return frozenset(
            {
                ConnectorCapability.VALIDATE_CONFIGURATION,
                ConnectorCapability.TEST_CONNECTION,
                ConnectorCapability.FETCH_PRODUCTS,
                ConnectorCapability.FETCH_PRODUCT,
                ConnectorCapability.FETCH_OFFERS,
                ConnectorCapability.REPORT_HEALTH,
            }
        )

    def validate_configuration(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        if config.marketplace not in {"imported", "import"}:
            return False, "Imported connector expects marketplace='imported'"
        return True, "Imported configuration valid"

    def test_connection(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        ok, message = self.validate_configuration(config)
        if not ok:
            return ok, message
        count = len(self._imported_offers())
        return True, f"Imported connector ready ({count} imported offers — not live)"

    def fetch_products(
        self,
        config: ConnectorConfiguration,
        *,
        query: str | None = None,
        checkpoint: SyncCheckpoint | None = None,
        limit: int = 50,
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        return self.fetch_offers(config, query=query, checkpoint=checkpoint, limit=limit)

    def fetch_product(
        self, config: ConnectorConfiguration, product_id: str
    ) -> Mapping[str, Any] | None:
        del config
        for offer in self._imported_offers():
            if offer.marketplace_product_id == product_id or offer.offer_id == product_id:
                return offer.to_dict()
        return None

    def fetch_offers(
        self,
        config: ConnectorConfiguration,
        *,
        query: str | None = None,
        checkpoint: SyncCheckpoint | None = None,
        limit: int = 50,
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        del config, checkpoint
        needle = (query or "").strip().lower()
        results: list[Mapping[str, Any]] = []
        for offer in self._imported_offers():
            if offer.source_mode != SourceMode.IMPORTED:
                continue
            payload = offer.to_dict()
            payload["source_mode"] = SourceMode.IMPORTED.value
            payload["label"] = "Imported data — not live marketplace pricing"
            if needle:
                hay = f"{offer.title} {offer.brand or ''}".lower()
                if needle not in hay:
                    continue
            results.append(payload)
            if len(results) >= limit:
                break
        return results, None

    def report_health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=ConnectorHealthStatus.HEALTHY,
            records_processed=len(self._imported_offers()),
            message="Imported connector healthy (file imports only — not live)",
        )

    def _imported_offers(self) -> list[MarketplaceOffer]:
        return [o for o in self._offer_provider() if o.source_mode == SourceMode.IMPORTED]
