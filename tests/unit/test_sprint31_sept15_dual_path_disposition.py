"""September 15 dual-path disposition: prove family boundaries stay separate.

This is architecture-boundary evidence for the recorded 2026-09-05 review.
It does not unify connectors, implement live research, or change Sprint 32/37.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.dependencies import get_marketplace_collectors, get_marketplace_connectors
from app.domain.entities.research_execution import ResearchCapability, ResearchProviderDescriptor
from app.domain.interfaces.marketplace_collector import MarketplaceCollector
from app.domain.interfaces.marketplace_connector import MarketplaceConnector
from app.domain.interfaces.marketplace_data_repository import MarketplaceDataConnector
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.shopee import MockShopeeCollector
from app.intelligence.marketplace.lazada.connector import LazadaConnector
from app.intelligence.marketplace.shopee.connector import ShopeeConnector
from app.market.context import compose_market_context
from app.market.coverage import assess_shopping_coverage
from app.market.support import production_certified_shopping_markets
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.registry import MarketplaceConnectorRegistry
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.philippines_certification_evidence import philippines_merchant_provider_ids
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.research.routing import production_research_provider_routing_policy_catalog
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.research_execution import execute_research_plan

ROOT = Path(__file__).resolve().parents[2]


def _test_provider(provider_id: str) -> StaticResearchProvider:
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=provider_id,
            provider_type="test",
            supported_markets=("PH",),
            supported_capabilities=(ResearchCapability.CURRENT_PRICING,),
            supported_sources=("amazon",),
            test_fixture=True,
        )
    )


def test_four_connector_ports_remain_distinct_types() -> None:
    assert MarketplaceConnector is not MarketplaceDataConnector
    assert MarketplaceConnector is not MarketplaceCollector
    assert MarketplaceDataConnector is not MarketplaceCollector


def test_sprint4_search_connectors_are_not_sync_or_research_ports() -> None:
    for connector in (ShopeeConnector(), LazadaConnector()):
        assert isinstance(connector, MarketplaceConnector)
        assert not isinstance(connector, MarketplaceDataConnector)
        assert not isinstance(connector, MarketplaceCollector)
        assert hasattr(connector, "marketplace_name")
        assert not hasattr(connector, "connector_id")
        assert not hasattr(connector, "provider_id")


def test_sprint18_sync_connectors_are_not_search_or_collector_ports() -> None:
    for connector in (
        FixtureMarketplaceConnector(),
        ImportedMarketplaceConnector(),
        MockLiveMarketplaceConnector(),
    ):
        assert isinstance(connector, MarketplaceDataConnector)
        assert not isinstance(connector, MarketplaceConnector)
        assert not isinstance(connector, MarketplaceCollector)
        assert connector.connector_id
        assert not hasattr(connector, "marketplace_name")


def test_sprint8_collectors_remain_a_separate_historical_family() -> None:
    for collector in (MockShopeeCollector(), MockLazadaCollector()):
        assert isinstance(collector, MarketplaceCollector)
        assert not isinstance(collector, MarketplaceConnector)
        assert not isinstance(collector, MarketplaceDataConnector)
        assert collector.marketplace_name in {"shopee", "lazada"}
        assert not hasattr(collector, "connector_id")
        assert not hasattr(collector, "provider_id")


def test_sprint4_and_sprint8_di_lists_stay_family_local() -> None:
    search = get_marketplace_connectors()
    collectors = get_marketplace_collectors()
    assert [type(item).__name__ for item in search] == ["ShopeeConnector", "LazadaConnector"]
    assert [type(item).__name__ for item in collectors] == [
        "MockShopeeCollector",
        "MockLazadaCollector",
    ]
    assert all(isinstance(item, MarketplaceConnector) for item in search)
    assert all(isinstance(item, MarketplaceCollector) for item in collectors)


def test_sprint8_reuses_sprint4_normalize_listing_only() -> None:
    shopee_source = (ROOT / "app/intelligence/collection/shopee.py").read_text(encoding="utf-8")
    lazada_source = (ROOT / "app/intelligence/collection/lazada.py").read_text(encoding="utf-8")
    assert "normalize_listing" in shopee_source
    assert "normalize_listing" in lazada_source
    assert ".search(" not in shopee_source
    assert ".search(" not in lazada_source
    assert "MarketplaceConnectorRegistry" not in shopee_source
    assert "ResearchProvider" not in shopee_source


def test_family_ports_do_not_import_each_other() -> None:
    ports = (
        ROOT / "app/domain/interfaces/marketplace_connector.py",
        ROOT / "app/domain/interfaces/marketplace_data_repository.py",
        ROOT / "app/domain/interfaces/marketplace_collector.py",
        ROOT / "app/domain/interfaces/research_provider.py",
    )
    texts = [path.read_text(encoding="utf-8") for path in ports]
    assert "marketplace_data_repository" not in texts[0]
    assert "marketplace_collector" not in texts[0]
    assert "research_provider" not in texts[0]
    assert "marketplace_connector" not in texts[1]
    assert "marketplace_collector" not in texts[1]
    assert "research_provider" not in texts[1]
    assert "marketplace_connector" not in texts[2]
    assert "marketplace_data_repository" not in texts[2]
    assert "research_provider" not in texts[2]
    assert "MarketplaceConnector" not in texts[3]
    assert "MarketplaceDataConnector" not in texts[3]
    assert "MarketplaceCollector" not in texts[3]


def test_sprint18_duplicate_connector_id_still_overwrites() -> None:
    first = ImportedMarketplaceConnector(lambda: ())
    second = ImportedMarketplaceConnector(lambda: ())
    registry = MarketplaceConnectorRegistry([first], register_stubs=False)
    assert registry.get(ImportedMarketplaceConnector.CONNECTOR_ID) is first
    registry.register(second)
    assert registry.get(ImportedMarketplaceConnector.CONNECTOR_ID) is second
    assert registry.list_connectors() == [second]


def test_sprint18_imported_connector_rewire_uses_register_overwrite() -> None:
    original = ImportedMarketplaceConnector()
    registry = MarketplaceConnectorRegistry([original], register_stubs=False)
    MarketplaceDataService(
        InMemoryMarketplaceDataRepository(),
        registry,
        require_auth_for_ops=False,
    )
    replacement = registry.get(ImportedMarketplaceConnector.CONNECTOR_ID)
    assert replacement is not original
    assert isinstance(replacement, ImportedMarketplaceConnector)


def test_sprint31_still_rejects_duplicate_provider_id() -> None:
    registry = research_provider_registry_for_tests([_test_provider("test-dup")])
    with pytest.raises(ValueError, match="duplicate provider_id"):
        registry.register(_test_provider("test-dup"))


def test_production_research_and_market_catalogs_remain_empty() -> None:
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    assert production_certified_shopping_markets().to_tuple() == ()


def test_philippines_documentary_ids_are_not_production_providers() -> None:
    registry = production_research_provider_registry()
    documentary_ids = philippines_merchant_provider_ids()
    assert documentary_ids == (
        "ph-shopee",
        "ph-lazada",
        "ph-tiktok-shop",
        "ph-amazon",
        "ph-temu",
    )
    for provider_id in documentary_ids:
        assert registry.get(provider_id) is None


def test_sprint31_execution_remains_unimplemented() -> None:
    provider = _test_provider("test-no-execute")
    with pytest.raises(NotImplementedError, match="cannot execute research"):
        provider.execute(None)  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError, match="not implemented"):
        execute_research_plan(None)  # type: ignore[arg-type]


def test_no_shared_merchant_identity_mapping_module_exists() -> None:
    absent = (
        ROOT / "app/identity/merchant_mapping.py",
        ROOT / "app/research/merchant_identity.py",
        ROOT / "app/marketplace/identity_mapping.py",
        ROOT / "app/market/connector_identity.py",
    )
    for path in absent:
        assert path.exists() is False


def test_market_context_is_not_connector_owned() -> None:
    payload = compose_market_context(trusted_market=None).to_dict()
    assert "connector_id" not in payload
    assert "provider_id" not in payload
    assert "marketplace_name" not in payload
    assert payload["shopping_market_certified"] is False
    market_root = ROOT / "app/market"
    for path in market_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "MarketplaceConnector" not in text
        assert "MarketplaceDataConnector" not in text
        assert "MarketplaceCollector" not in text


def test_affiliate_availability_cannot_certify_or_invoke_connectors() -> None:
    coverage = assess_shopping_coverage(affiliate_available=True)
    assert coverage.certified is False
    assert coverage.coverage_available is False
    assert coverage.connector_invocation_eligible is False


def test_di_keeps_four_family_factories_separate() -> None:
    deps = (ROOT / "app/core/dependencies.py").read_text(encoding="utf-8")
    assert "def get_marketplace_connectors()" in deps
    assert "ShopeeConnector(), LazadaConnector()" in deps
    assert "def get_marketplace_connector_registry()" in deps
    assert "FixtureMarketplaceConnector()" in deps
    assert "def get_marketplace_collectors()" in deps
    assert "MockShopeeCollector(), MockLazadaCollector()" in deps
    registry = (ROOT / "app/research/registry.py").read_text(encoding="utf-8")
    assert "class ResearchProviderRegistry" in registry
    assert "production_research_provider_registry" in registry
