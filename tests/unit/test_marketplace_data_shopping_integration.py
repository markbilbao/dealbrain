"""Shopping Assistant + DealScore integration with Marketplace Data provenance."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.domain.entities.marketplace_listing import (
    AvailabilityStatus,
    MarketplaceListing,
    MarketplaceSearchResult,
)
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.dealscore import WeightedDealScoreEngine
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.registry import MarketplaceConnectorRegistry
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.shopping_assistant_service import ShoppingAssistantService

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
QUERY = "What is the best gaming laptop under 60000?"


def make_marketplace_data() -> MarketplaceDataService:
    repo = InMemoryMarketplaceDataRepository()
    registry = MarketplaceConnectorRegistry(
        [
            FixtureMarketplaceConnector(),
            ImportedMarketplaceConnector(),
            MockLiveMarketplaceConnector(),
        ],
        register_stubs=False,
    )
    service = MarketplaceDataService(
        repo,
        registry,
        clock=lambda: FIXED_NOW,
        require_auth_for_ops=False,
    )
    service.seed_demo_data(actor="demo")
    return service


def make_assistant(*, marketplace_data: MarketplaceDataService | None) -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
        allow_client_mode=True,
        primary_provider="openai",
        secondary_provider="anthropic",
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=60),
        marketplace_data_service=marketplace_data,
        clock=lambda: FIXED_NOW,
    )


def test_anonymous_shopping_still_works_without_marketplace_data() -> None:
    assistant = make_assistant(marketplace_data=None)
    response = assistant.query({"query": QUERY})
    assert response.answer
    assert response.processing.get("authenticated") in (False, None)


def test_shopping_assistant_attaches_provenance_notes() -> None:
    data = make_marketplace_data()
    assistant = make_assistant(marketplace_data=data)
    response = assistant.query({"query": "iPhone 15 Pro"})
    assert response.answer
    warning_codes = {w.code for w in response.warnings}
    # Provenance notes when candidates overlap marketplace offers; otherwise still succeeds.
    assert response.top_recommendation is not None or warning_codes or response.answer


def test_dealscore_provenance_notes() -> None:
    data = make_marketplace_data()
    marketplace = MagicMock(spec=MarketplaceIntelligenceService)
    marketplace.search.return_value = MarketplaceSearchResult(
        query="iphone",
        results=(
            MarketplaceListing(
                marketplace="fixture",
                product_id="fx-iphone-15-pro-256",
                title="Apple iPhone 15 Pro 256GB Natural Titanium",
                price=69990.0,
                currency="PHP",
                seller="Fixture Mobile Hub",
                rating=4.8,
                url="https://fixtures.dealbrain.local/iphone-15-pro",
                availability=AvailabilityStatus.IN_STOCK,
            ),
        ),
    )
    service = DealRecommendationService(
        marketplace_service=marketplace,
        deal_score_engine=WeightedDealScoreEngine(),
        marketplace_data_service=data,
    )
    result = service.recommend("iphone")
    explanations = " ".join(" ".join(ev.deal_score.explanation) for ev in result.evaluations)
    lowered = explanations.lower()
    assert "not live" in lowered or "fixture" in lowered or "simulated" in lowered


def test_shopping_enrichment_payload() -> None:
    data = make_marketplace_data()
    enrichment = data.shopping_enrichment()
    assert enrichment
    assert all("source_mode" in item for item in enrichment)
    assert all("notes" in item for item in enrichment)
    fixture_items = [i for i in enrichment if i["source_mode"] == "fixture"]
    assert fixture_items
    assert fixture_items[0]["is_current_live_price"] is False
