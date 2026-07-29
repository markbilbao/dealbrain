"""Future official marketplace connector stubs.

These stubs document the extension path for real marketplace integrations.
They do **not** perform HTTP calls, store credentials, or claim connectivity.
"""

from __future__ import annotations

from app.domain.entities.marketplace_data import (
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealth,
    ConnectorHealthStatus,
)
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector

_BASE_CAPABILITIES = frozenset(
    {
        ConnectorCapability.VALIDATE_CONFIGURATION,
        ConnectorCapability.TEST_CONNECTION,
        ConnectorCapability.REPORT_HEALTH,
    }
)


class FutureOfficialConnectorStub(MarketplaceDataConnector):
    """Unconfigured stub for a future official marketplace connector."""

    def __init__(
        self,
        *,
        connector_id: str,
        name: str,
        marketplace: str,
        description: str,
    ) -> None:
        self._connector_id = connector_id
        self._name = name
        self._marketplace = marketplace
        self._description = description

    @property
    def connector_id(self) -> str:
        return self._connector_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def marketplace(self) -> str:
        return self._marketplace

    @property
    def description(self) -> str:
        return self._description

    @property
    def capabilities(self) -> frozenset[ConnectorCapability]:
        return _BASE_CAPABILITIES

    def validate_configuration(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        del config
        return False, (
            f"{self._name} is not implemented. Official API integration required "
            "before live connectivity can be enabled."
        )

    def test_connection(self, config: ConnectorConfiguration) -> tuple[bool, str]:
        return self.validate_configuration(config)

    def report_health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=ConnectorHealthStatus.UNCONFIGURED,
            message=self._description,
        )


def future_connector_stubs() -> tuple[FutureOfficialConnectorStub, ...]:
    """Documented stubs for marketplaces without official integrations yet."""
    return (
        FutureOfficialConnectorStub(
            connector_id="future-shopee-official",
            name="Shopee Official Connector (Future)",
            marketplace="shopee",
            description=(
                "Stub only — no unofficial scraping. Requires official Shopee Open Platform "
                "credentials and a dedicated adapter implementation."
            ),
        ),
        FutureOfficialConnectorStub(
            connector_id="future-lazada-official",
            name="Lazada Official Connector (Future)",
            marketplace="lazada",
            description=(
                "Stub only — no unofficial scraping. Requires official Lazada Open Platform "
                "credentials and a dedicated adapter implementation."
            ),
        ),
        FutureOfficialConnectorStub(
            connector_id="future-amazon-official",
            name="Amazon Official Connector (Future)",
            marketplace="amazon",
            description=(
                "Stub only. Requires Amazon SP-API (or approved partner API) integration."
            ),
        ),
        FutureOfficialConnectorStub(
            connector_id="future-tiktok-shop-official",
            name="TikTok Shop Official Connector (Future)",
            marketplace="tiktok_shop",
            description="Stub only. Requires official TikTok Shop Partner API integration.",
        ),
        FutureOfficialConnectorStub(
            connector_id="future-ebay-official",
            name="eBay Official Connector (Future)",
            marketplace="ebay",
            description="Stub only. Requires official eBay Browse/Sell API integration.",
        ),
    )
