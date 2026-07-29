"""Unit tests for Sprint 18 marketplace data connectors."""

from __future__ import annotations

from app.domain.entities.marketplace_data import (
    SIMULATED_LIVE_LABEL,
    ConnectorCapability,
    ConnectorConfiguration,
    ConnectorHealthStatus,
    SourceMode,
)
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.connectors.stubs import future_connector_stubs
from app.marketplace.registry import MarketplaceConnectorRegistry


def test_fixture_connector_mode_capabilities_and_label() -> None:
    connector = FixtureMarketplaceConnector()
    assert connector.SOURCE_MODE == SourceMode.FIXTURE
    assert connector.connector_id == "fixture-marketplace"
    assert ConnectorCapability.FETCH_OFFERS in connector.capabilities
    assert ConnectorCapability.CONTINUE_FROM_CHECKPOINT not in connector.capabilities

    config = ConnectorConfiguration(connector_id=connector.connector_id, marketplace="fixture")
    ok, message = connector.validate_configuration(config)
    assert ok is True
    ok, message = connector.test_connection(config)
    assert ok is True
    assert "not live" in message.lower()

    offers, checkpoint = connector.fetch_offers(config, limit=10)
    assert len(offers) >= 1
    assert checkpoint is None
    assert all(o["source_mode"] == SourceMode.FIXTURE.value for o in offers)
    assert all(o.get("simulated") is False for o in offers)


def test_fixture_rejects_wrong_marketplace_config() -> None:
    connector = FixtureMarketplaceConnector()
    config = ConnectorConfiguration(connector_id=connector.connector_id, marketplace="shopee")
    ok, message = connector.validate_configuration(config)
    assert ok is False
    assert "fixture" in message.lower()


def test_imported_connector_mode_and_label() -> None:
    connector = ImportedMarketplaceConnector()
    assert connector.SOURCE_MODE == SourceMode.IMPORTED
    config = ConnectorConfiguration(connector_id=connector.connector_id, marketplace="imported")
    ok, message = connector.test_connection(config)
    assert ok is True
    assert "not live" in message.lower()
    offers, _ = connector.fetch_offers(config)
    assert offers == []
    health = connector.report_health()
    assert health.status == ConnectorHealthStatus.HEALTHY
    assert "not live" in health.message.lower()


def test_mock_live_is_simulated_not_real() -> None:
    connector = MockLiveMarketplaceConnector()
    assert connector.SOURCE_MODE == SourceMode.LIVE
    assert connector.marketplace == "simulated_live"
    assert ConnectorCapability.CONTINUE_FROM_CHECKPOINT in connector.capabilities
    assert ConnectorCapability.REPORT_RATE_LIMIT in connector.capabilities

    config = ConnectorConfiguration(
        connector_id=connector.connector_id,
        marketplace="simulated_live",
        base_url="https://simulated.dealbrain.local",
    )
    ok, message = connector.test_connection(config)
    assert ok is True
    assert message == SIMULATED_LIVE_LABEL

    offers, _ = connector.fetch_offers(config, limit=5)
    assert offers
    assert all(o["simulated"] is True for o in offers)
    assert all(o["label"] == SIMULATED_LIVE_LABEL for o in offers)
    assert all(o["source_mode"] == SourceMode.LIVE.value for o in offers)

    health = connector.report_health()
    assert SIMULATED_LIVE_LABEL in health.message


def test_mock_live_config_validation() -> None:
    connector = MockLiveMarketplaceConnector()
    bad_market = ConnectorConfiguration(connector_id=connector.connector_id, marketplace="shopee")
    ok, _ = connector.validate_configuration(bad_market)
    assert ok is False

    bad_url = ConnectorConfiguration(
        connector_id=connector.connector_id,
        marketplace="simulated_live",
        base_url="https://api.shopee.com",
    )
    ok, message = connector.validate_configuration(bad_url)
    assert ok is False
    assert "simulated" in message.lower()


def test_registry_labels_and_stubs() -> None:
    registry = MarketplaceConnectorRegistry(
        [
            FixtureMarketplaceConnector(),
            ImportedMarketplaceConnector(),
            MockLiveMarketplaceConnector(),
        ],
        register_stubs=True,
    )
    infos = {info.connector_id: info for info in registry.list_infos(include_stubs=True)}
    assert infos["fixture-marketplace"].source_mode == SourceMode.FIXTURE
    assert infos["imported-marketplace"].source_mode == SourceMode.IMPORTED
    mock = infos["mock-live-marketplace"]
    assert mock.source_mode == SourceMode.LIVE
    assert mock.simulated is True
    assert mock.to_dict()["label"] == SIMULATED_LIVE_LABEL

    stubs = future_connector_stubs()
    assert {s.marketplace for s in stubs} >= {
        "shopee",
        "lazada",
        "amazon",
        "tiktok_shop",
        "ebay",
    }
    for stub in stubs:
        ok, message = stub.validate_configuration(
            ConnectorConfiguration(connector_id=stub.connector_id, marketplace=stub.marketplace)
        )
        assert ok is False
        assert "not implemented" in message.lower() or "official" in message.lower()
        assert stub.report_health().status == ConnectorHealthStatus.UNCONFIGURED
        assert infos[stub.connector_id].enabled is False
