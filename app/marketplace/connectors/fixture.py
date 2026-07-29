"""Fixture marketplace connector — deterministic demo data only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.entities.marketplace_data import (
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorHealthStatus,
    MarketplaceSeller,
    SourceMode,
    SyncCheckpoint,
)
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector
from app.marketplace.fixtures import FIXTURE_OFFERS


class FixtureMarketplaceConnector(MarketplaceDataConnector):
    """Serves canned fixture offers. Never labeled as live."""

    CONNECTOR_ID = "fixture-marketplace"
    SOURCE_MODE = SourceMode.FIXTURE

    def __init__(self, payloads: tuple[Mapping[str, Any], ...] | None = None) -> None:
        self._payloads = tuple(payloads or FIXTURE_OFFERS)

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def name(self) -> str:
        return "Fixture Marketplace Connector"

    @property
    def marketplace(self) -> str:
        return "fixture"

    @property
    def capabilities(self) -> frozenset[ConnectorCapability]:
        return frozenset(
            {
                ConnectorCapability.VALIDATE_CONFIGURATION,
                ConnectorCapability.TEST_CONNECTION,
                ConnectorCapability.FETCH_PRODUCTS,
                ConnectorCapability.FETCH_PRODUCT,
                ConnectorCapability.FETCH_OFFERS,
                ConnectorCapability.FETCH_PRICES,
                ConnectorCapability.FETCH_INVENTORY,
                ConnectorCapability.FETCH_SELLERS,
                ConnectorCapability.REPORT_HEALTH,
            }
        )

    def validate_configuration(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        if config.marketplace not in {"fixture", "demo"}:
            return False, "Fixture connector expects marketplace='fixture'"
        return True, "Fixture configuration valid"

    def test_connection(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        ok, message = self.validate_configuration(config)
        if not ok:
            return ok, message
        return True, "Fixture connector ready (demo data only — not live)"

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
        for raw in self._payloads:
            if str(raw.get("marketplace_product_id")) == product_id:
                return dict(raw)
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
        for raw in self._payloads:
            enriched = {
                **dict(raw),
                "source_mode": SourceMode.FIXTURE.value,
                "marketplace": "fixture",
                "simulated": False,
                "label": "Demo / fixture data — not live marketplace pricing",
            }
            if needle:
                hay = f"{enriched.get('title', '')} {enriched.get('brand', '')}".lower()
                if needle not in hay:
                    continue
            results.append(enriched)
            if len(results) >= limit:
                break
        return results, None

    def fetch_prices(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        del config
        wanted = set(product_ids)
        out: list[Mapping[str, Any]] = []
        for raw in self._payloads:
            pid = str(raw.get("marketplace_product_id"))
            if pid in wanted:
                out.append(
                    {
                        "marketplace_product_id": pid,
                        "sale_price": raw.get("sale_price"),
                        "regular_price": raw.get("regular_price"),
                        "currency": raw.get("currency"),
                        "source_mode": SourceMode.FIXTURE.value,
                    }
                )
        return out

    def fetch_inventory(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        del config
        wanted = set(product_ids)
        out: list[Mapping[str, Any]] = []
        for raw in self._payloads:
            pid = str(raw.get("marketplace_product_id"))
            if pid in wanted:
                out.append(
                    {
                        "marketplace_product_id": pid,
                        "availability": raw.get("availability"),
                        "inventory_quantity": raw.get("inventory_quantity"),
                        "source_mode": SourceMode.FIXTURE.value,
                    }
                )
        return out

    def fetch_sellers(
        self, config: ConnectorConfiguration, seller_ids: Sequence[str]
    ) -> list[MarketplaceSeller]:
        del config
        wanted = set(seller_ids)
        sellers: list[MarketplaceSeller] = []
        seen: set[str] = set()
        for raw in self._payloads:
            sid = str(raw.get("seller_id") or "")
            if sid and sid in wanted and sid not in seen:
                seen.add(sid)
                sellers.append(
                    MarketplaceSeller(
                        seller_id=sid,
                        name=str(raw.get("seller_name") or sid),
                        marketplace="fixture",
                        rating=_as_float(raw.get("seller_rating")),
                        source_mode=SourceMode.FIXTURE,
                    )
                )
        return sellers

    def report_health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=ConnectorHealthStatus.HEALTHY,
            message="Fixture connector healthy (demo data only)",
        )


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
