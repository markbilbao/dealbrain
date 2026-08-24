"""Sprint 31 research provider registry: uniqueness, isolation, fail-closed catalog."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.domain.entities.research_execution import (
    CapabilityCertification,
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)

ROOT = Path(__file__).resolve().parents[2]


def _provider(provider_id: str, *, test_fixture: bool = True) -> StaticResearchProvider:
    capability = ResearchCapability.CURRENT_PRICING
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=provider_id,
            provider_type="test" if test_fixture else "merchant",
            supported_markets=("PH",),
            supported_capabilities=(capability,),
            supported_sources=("amazon",),
            certification_status="registered",
            certification_version="v1",
            test_fixture=test_fixture,
            capability_certifications=(
                CapabilityCertification(
                    capability=capability,
                    markets=("PH",),
                    sources=("amazon",),
                    policy="unknown",
                    certification_version="v1",
                ),
            ),
        )
    )


def test_production_registry_is_empty_and_refuses_test_fixtures() -> None:
    registry = production_research_provider_registry()
    assert registry.list_providers() == ()
    assert registry.certified_providers() == ()
    with pytest.raises(ValueError, match="test providers"):
        registry.register(_provider("test-amazon-ph"))


def test_duplicate_provider_ids_are_rejected() -> None:
    first = _provider("test-dup")
    registry = research_provider_registry_for_tests([first])
    with pytest.raises(ValueError, match="duplicate provider_id"):
        registry.register(_provider("test-dup"))


def test_registry_listing_is_deterministic() -> None:
    registry = research_provider_registry_for_tests(
        [_provider("test-b"), _provider("test-a")]
    )
    assert [item.provider_id for item in registry.list_providers()] == ["test-b", "test-a"]
    again = research_provider_registry_for_tests(
        [_provider("test-b"), _provider("test-a")]
    )
    assert again.fingerprint() == registry.fingerprint()


def test_production_registry_module_does_not_import_test_or_network_clients() -> None:
    sources = [
        (ROOT / "app/research/registry.py").read_text(encoding="utf-8"),
        (ROOT / "app/research/providers.py").read_text(encoding="utf-8"),
        (ROOT / "app/research/__init__.py").read_text(encoding="utf-8"),
    ]
    for source in sources:
        assert "import requests" not in source
        assert "import httpx" not in source
        assert "from httpx" not in source
        assert "urllib.request" not in source
        assert "aiohttp" not in source
        assert "FixtureMarketplaceConnector" not in source
        assert "MockLiveMarketplaceConnector" not in source
        assert "web_search" not in source
    production = (ROOT / "app/research/registry.py").read_text(encoding="utf-8")
    assert "allow_test_providers=False" in production
    assert "Product Foundation" in production or "test providers are never registered" in production
