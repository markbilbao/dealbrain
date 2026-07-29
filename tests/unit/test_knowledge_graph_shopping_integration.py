"""Unit tests for Knowledge Graph <-> Shopping Assistant integration."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.knowledge_graph import GraphLimits
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.knowledge_graph.aggregator import KnowledgeGraphAggregator
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.shopping_assistant_service import ShoppingAssistantService


def make_graph_service(**kwargs) -> KnowledgeGraphService:
    repo = InMemoryKnowledgeGraphRepository()
    engine = KnowledgeGraphEngine(
        repo, limits=GraphLimits(max_depth=3, max_nodes=100, max_edges=200, max_paths=20)
    )
    return KnowledgeGraphService(engine, **kwargs)


def make_assistant(*, knowledge_graph_service=None) -> ShoppingAssistantService:
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
        knowledge_graph_service=knowledge_graph_service,
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


class TestGraphAvailableIntegration:
    def test_response_includes_graph_evidence_when_available(self) -> None:
        graph = make_graph_service()
        assistant = make_assistant(knowledge_graph_service=graph)
        result = assistant.query({"query": "What is the best gaming laptop under 60000?"})
        assert result.processing["knowledge_graph_integrated"] is True
        graph_evidence = [item for item in result.evidence if item.source_id == "knowledge_graph"]
        assert graph_evidence

    def test_no_graph_unavailable_warning_when_service_present(self) -> None:
        graph = make_graph_service()
        assistant = make_assistant(knowledge_graph_service=graph)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        assert not any(w.code == "graph_unavailable" for w in result.warnings)

    def test_graph_evidence_types_restricted_to_allowed_set(self) -> None:
        graph = make_graph_service()
        assistant = make_assistant(knowledge_graph_service=graph)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        allowed_types = {
            "graph_path",
            "related_product",
            "cross_source_support",
            "contradiction",
            "compatibility",
            "community_topic",
        }
        graph_evidence = [item for item in result.evidence if item.source_id == "knowledge_graph"]
        for item in graph_evidence:
            assert item.type in allowed_types


class TestGraphUnavailableFallback:
    def test_none_collaborator_produces_warning(self) -> None:
        assistant = make_assistant(knowledge_graph_service=None)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        assert any(w.code == "graph_unavailable" for w in result.warnings)
        assert result.processing["knowledge_graph_integrated"] is False

    def test_none_collaborator_still_returns_valid_response(self) -> None:
        assistant = make_assistant(knowledge_graph_service=None)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        assert result.answer
        assert result.top_recommendation is not None

    def test_raising_collaborator_degrades_gracefully(self) -> None:
        class _ExplodingGraphService:
            def shopping_assistant_evidence(self, product_ids):
                raise RuntimeError("graph backend exploded")

        assistant = make_assistant(knowledge_graph_service=_ExplodingGraphService())
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        assert result.answer
        graph_evidence = [item for item in result.evidence if item.source_id == "knowledge_graph"]
        assert graph_evidence == []

    def test_disabled_knowledge_graph_service_falls_back(self) -> None:
        graph = make_graph_service(enabled=False)
        assistant = make_assistant(knowledge_graph_service=graph)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        # shopping_assistant_evidence() itself returns [] when disabled, never raises.
        graph_evidence = [item for item in result.evidence if item.source_id == "knowledge_graph"]
        assert graph_evidence == []


class TestNoSecretsInIntegratedResponse:
    def test_no_secrets_leak_through_graph_evidence(self) -> None:
        graph = make_graph_service()
        assistant = make_assistant(knowledge_graph_service=graph)
        result = assistant.query({"query": "Best gaming laptop under 60000"})
        blob = str(result.to_dict()).lower()
        assert "api_key" not in blob
        assert "secret" not in blob or "secrets_included" in blob


class TestKnowledgeGraphAggregatorSharesDemoProduct:
    def test_demo_product_matches_shopping_catalog(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        engine = KnowledgeGraphEngine(repo, limits=GraphLimits())
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        assert DEMO_PRODUCT_ID in result["product_nodes"]
