"""Marketplace connector registry — capability and source-mode metadata."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.marketplace_data import MarketplaceConnectorInfo, SourceMode
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.connectors.stubs import FutureOfficialConnectorStub, future_connector_stubs


class MarketplaceConnectorRegistry:
    """Register and describe marketplace data connectors.

    Future official stubs may be registered (disabled / unofficial) but are
    omitted from ``list_infos`` unless ``include_stubs=True``.
    """

    def __init__(
        self,
        connectors: Sequence[MarketplaceDataConnector] | None = None,
        *,
        register_stubs: bool = True,
    ) -> None:
        self._connectors: dict[str, MarketplaceDataConnector] = {}
        self._order: list[str] = []
        self._stub_ids: set[str] = set()
        for connector in connectors or ():
            self.register(connector)
        if register_stubs:
            for stub in future_connector_stubs():
                self.register(stub)

    def register(self, connector: MarketplaceDataConnector) -> MarketplaceDataConnector:
        connector_id = connector.connector_id
        if connector_id not in self._connectors:
            self._order.append(connector_id)
        self._connectors[connector_id] = connector
        if isinstance(connector, FutureOfficialConnectorStub):
            self._stub_ids.add(connector_id)
        return connector

    def get(self, connector_id: str) -> MarketplaceDataConnector | None:
        return self._connectors.get(connector_id)

    def list_connectors(self) -> list[MarketplaceDataConnector]:
        return [
            self._connectors[connector_id]
            for connector_id in self._order
            if connector_id in self._connectors
        ]

    def list_infos(self, *, include_stubs: bool = False) -> list[MarketplaceConnectorInfo]:
        infos: list[MarketplaceConnectorInfo] = []
        for connector in self.list_connectors():
            if connector.connector_id in self._stub_ids and not include_stubs:
                continue
            infos.append(self.connector_info(connector))
        return infos

    def connector_info(self, connector: MarketplaceDataConnector) -> MarketplaceConnectorInfo:
        capabilities = tuple(sorted(connector.capabilities, key=lambda item: item.value))

        if isinstance(connector, FutureOfficialConnectorStub):
            return MarketplaceConnectorInfo(
                connector_id=connector.connector_id,
                name=connector.name,
                marketplace=connector.marketplace,
                source_mode=SourceMode.LIVE,
                capabilities=capabilities,
                simulated=False,
                enabled=False,
                description=connector.description,
                official=False,
            )

        if isinstance(connector, MockLiveMarketplaceConnector):
            return MarketplaceConnectorInfo(
                connector_id=connector.connector_id,
                name=connector.name,
                marketplace=connector.marketplace,
                source_mode=SourceMode.LIVE,
                capabilities=capabilities,
                simulated=True,
                enabled=True,
                description="SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION",
                official=False,
            )

        if isinstance(connector, FixtureMarketplaceConnector):
            return MarketplaceConnectorInfo(
                connector_id=connector.connector_id,
                name=connector.name,
                marketplace=connector.marketplace,
                source_mode=SourceMode.FIXTURE,
                capabilities=capabilities,
                simulated=False,
                enabled=True,
                description="Demo / fixture data — not live marketplace pricing",
                official=False,
            )

        if isinstance(connector, ImportedMarketplaceConnector):
            return MarketplaceConnectorInfo(
                connector_id=connector.connector_id,
                name=connector.name,
                marketplace=connector.marketplace,
                source_mode=SourceMode.IMPORTED,
                capabilities=capabilities,
                simulated=False,
                enabled=True,
                description="Imported data — not live marketplace pricing",
                official=False,
            )

        source_mode = getattr(type(connector), "SOURCE_MODE", SourceMode.FIXTURE)
        if not isinstance(source_mode, SourceMode):
            source_mode = SourceMode.FIXTURE
        description = str(getattr(connector, "description", "") or "")
        return MarketplaceConnectorInfo(
            connector_id=connector.connector_id,
            name=connector.name,
            marketplace=connector.marketplace,
            source_mode=source_mode,
            capabilities=capabilities,
            simulated=False,
            enabled=True,
            description=description,
            official=False,
        )
