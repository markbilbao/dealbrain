"""Mock live marketplace connector — simulated live data for tests/demo only.

SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.marketplace_data import (
    SIMULATED_LIVE_LABEL,
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorHealthStatus,
    ConnectorRateLimit,
    SourceMode,
    SyncCheckpoint,
)
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector
from app.marketplace.fixtures import SIMULATED_LIVE_OFFERS


class MockLiveMarketplaceConnector(MarketplaceDataConnector):
    """Deterministic simulated-live connector for tests and demos.

    Declares source mode ``live`` only in the simulated sense. Responses always
    include the simulated-live label. This is **not** a real Shopee, Lazada,
    Amazon, TikTok Shop, eBay, or other marketplace integration.
    """

    CONNECTOR_ID = "mock-live-marketplace"
    SOURCE_MODE = SourceMode.LIVE

    def __init__(
        self,
        payloads: tuple[Mapping[str, Any], ...] | None = None,
        *,
        rate_limited: bool = False,
        fail_next: int = 0,
    ) -> None:
        self._payloads = tuple(payloads or SIMULATED_LIVE_OFFERS)
        self._rate_limited = rate_limited
        self._fail_next = fail_next
        self._fetch_count = 0

    @property
    def connector_id(self) -> str:
        return self.CONNECTOR_ID

    @property
    def name(self) -> str:
        return "Mock Live Marketplace Connector (Simulated)"

    @property
    def marketplace(self) -> str:
        return "simulated_live"

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
                ConnectorCapability.CONTINUE_FROM_CHECKPOINT,
                ConnectorCapability.REPORT_RATE_LIMIT,
                ConnectorCapability.REPORT_HEALTH,
            }
        )

    def validate_configuration(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        if config.marketplace not in {"simulated_live", "mock_live", "live_sim"}:
            return False, "Mock live connector expects marketplace='simulated_live'"
        if config.base_url and not str(config.base_url).startswith("https://simulated."):
            return False, "Mock live connector only accepts simulated.dealbrain.local base URLs"
        return True, f"Simulated live configuration valid — {SIMULATED_LIVE_LABEL}"

    def test_connection(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        ok, message = self.validate_configuration(config)
        if not ok:
            return ok, message
        if self._rate_limited:
            return False, "Simulated rate limit active"
        return True, SIMULATED_LIVE_LABEL

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
        self._maybe_fail()
        for raw in self._payloads:
            if str(raw.get("marketplace_product_id")) == product_id:
                return self._enrich(raw)
        return None

    def fetch_offers(
        self,
        config: ConnectorConfiguration,
        *,
        query: str | None = None,
        checkpoint: SyncCheckpoint | None = None,
        limit: int = 50,
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        del config
        self._maybe_fail()
        if self._rate_limited:
            raise RuntimeError("rate_limited")

        start = 0
        if checkpoint and checkpoint.cursor.isdigit():
            start = int(checkpoint.cursor)

        needle = (query or "").strip().lower()
        sliced = list(self._payloads[start : start + limit])
        results: list[Mapping[str, Any]] = []
        for raw in sliced:
            enriched = self._enrich(raw)
            if needle:
                hay = f"{enriched.get('title', '')} {enriched.get('brand', '')}".lower()
                if needle not in hay:
                    continue
            results.append(enriched)

        next_cursor = start + len(sliced)
        new_checkpoint = None
        if next_cursor < len(self._payloads):
            new_checkpoint = SyncCheckpoint(
                connector_id=self.connector_id,
                cursor=str(next_cursor),
                updated_at=datetime.now(UTC),
                metadata={"simulated": True},
            )
        self._fetch_count += 1
        return results, new_checkpoint

    def continue_from_checkpoint(
        self, config: ConnectorConfiguration, checkpoint: SyncCheckpoint
    ) -> tuple[list[Mapping[str, Any]], SyncCheckpoint | None]:
        return self.fetch_offers(config, checkpoint=checkpoint)

    def fetch_prices(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        del config
        self._maybe_fail()
        wanted = set(product_ids)
        out: list[Mapping[str, Any]] = []
        for raw in self._payloads:
            pid = str(raw.get("marketplace_product_id"))
            if pid in wanted:
                out.append(
                    {
                        **self._enrich(raw),
                        "sale_price": raw.get("sale_price"),
                        "regular_price": raw.get("regular_price"),
                    }
                )
        return out

    def fetch_inventory(
        self, config: ConnectorConfiguration, product_ids: Sequence[str]
    ) -> list[Mapping[str, Any]]:
        del config
        self._maybe_fail()
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
                        "source_mode": SourceMode.LIVE.value,
                        "simulated": True,
                        "label": SIMULATED_LIVE_LABEL,
                    }
                )
        return out

    def report_rate_limit(self) -> ConnectorRateLimit:
        if self._rate_limited:
            return ConnectorRateLimit(
                limited=True,
                remaining=0,
                retry_after_seconds=30.0,
                message="Simulated rate limit",
            )
        return ConnectorRateLimit(limited=False, remaining=100)

    def report_health(self) -> ConnectorHealth:
        status = (
            ConnectorHealthStatus.DEGRADED if self._rate_limited else ConnectorHealthStatus.HEALTHY
        )
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=status,
            records_processed=self._fetch_count,
            rate_limit=self.report_rate_limit(),
            message=SIMULATED_LIVE_LABEL,
        )

    def set_rate_limited(self, limited: bool) -> None:
        self._rate_limited = limited

    def _enrich(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return {
            **dict(raw),
            "source_mode": SourceMode.LIVE.value,
            "marketplace": "simulated_live",
            "simulated": True,
            "label": SIMULATED_LIVE_LABEL,
        }

    def _maybe_fail(self) -> None:
        if self._fail_next > 0:
            self._fail_next -= 1
            raise RuntimeError("simulated_transient_failure")
