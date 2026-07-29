"""End-to-end Knowledge Graph flow (in-memory, no external graph database)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.knowledge_graph import EdgeType, GraphLimits, NodeType
from app.infrastructure.ai.shopping_providers import DeterministicShoppingProviderAdapter
from app.intelligence.knowledge_graph.aggregator import KnowledgeGraphAggregator
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository
from app.intelligence.shopping_assistant.memory import InMemoryConversationRepository
from app.intelligence.shopping_assistant.orchestrator import (
    ShoppingAssistantOrchestrator,
    ShoppingExplanationRegistry,
)
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.shopping_assistant_service import ShoppingAssistantService


def _graph_service(**kwargs) -> KnowledgeGraphService:
    repo = InMemoryKnowledgeGraphRepository()
    engine = KnowledgeGraphEngine(
        repo, limits=GraphLimits(max_depth=3, max_nodes=200, max_edges=400, max_paths=20)
    )
    return KnowledgeGraphService(engine, **kwargs)


def _shopping_assistant(*, knowledge_graph_service=None) -> ShoppingAssistantService:
    registry = ShoppingExplanationRegistry([DeterministicShoppingProviderAdapter()])
    orchestrator = ShoppingAssistantOrchestrator(
        registry,
        ai_enabled=False,
        configured_mode="economy",
    )
    return ShoppingAssistantService(
        orchestrator=orchestrator,
        conversation_repository=InMemoryConversationRepository(ttl_seconds=600),
        knowledge_graph_service=knowledge_graph_service,
        clock=lambda: datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )


def test_end_to_end_demo_to_product_graph_to_evidence() -> None:
    service = _graph_service()
    demo = service.demo()
    assert demo.root_node.label == DEMO_PRODUCT_LABEL

    product = service.product_graph(DEMO_PRODUCT_ID)
    assert product.root_node.node_id == demo.root_node.node_id
    assert product.summary["brands"]

    evidence = service.evidence(product.root_node.node_id)
    assert evidence["evidence_nodes"]
    assert "contradictions" in evidence


def test_end_to_end_path_confidence_and_explanation() -> None:
    service = _graph_service()
    demo = service.demo()
    made_by = [e for e in demo.edges if e.edge_type == EdgeType.MADE_BY]
    assert made_by

    path_payload = service.find_paths(demo.root_node.node_id, made_by[0].to_node_id)
    assert path_payload["paths"]
    best_path = path_payload["paths"][0]
    assert best_path["confidence"] == made_by[0].confidence
    assert best_path["confidence_band"] in {"high", "medium", "low"}

    explanation = service.explain(
        from_node_id=demo.root_node.node_id, to_node_id=made_by[0].to_node_id
    )
    assert explanation.supported is True
    assert explanation.limitations


def test_end_to_end_multi_source_product_merge() -> None:
    """The demo laptop's cross-marketplace mirror (same brand+label) collapses onto
    the same canonical product node instead of creating a duplicate."""
    service = _graph_service()
    service.ensure_seeded()
    product_graph = service.product_graph(DEMO_PRODUCT_ID, max_depth=2)
    marketplaces = {n.label for n in product_graph.nodes if n.node_type == NodeType.MARKETPLACE}
    assert "Lazada" in marketplaces or "Shopee" in marketplaces
    demo_products = [
        n
        for n in product_graph.nodes
        if n.node_type == NodeType.PRODUCT and n.label == DEMO_PRODUCT_LABEL
    ]
    assert len(demo_products) == 1
    assert demo_products[0].node_id == product_graph.root_node.node_id


def test_end_to_end_contradiction_detection() -> None:
    """A seeded CONTRADICTS edge between community evidence and a review is
    discoverable via the evidence endpoint for the evidence node itself."""
    service = _graph_service()
    service.ensure_seeded()
    contradicting_edges = service._engine.repository.edges.list_by_type(EdgeType.CONTRADICTS)  # noqa: SLF001
    assert contradicting_edges
    left_node_id = contradicting_edges[0].from_node_id
    payload = service.evidence(left_node_id)
    assert payload["contradictions"]


def test_end_to_end_snapshot_round_trip_preserves_traversal() -> None:
    source = _graph_service()
    source.ensure_seeded()
    demo_before = source.demo()
    snapshot = source.export_snapshot()

    target = _graph_service()
    target.import_snapshot(snapshot)
    demo_after = target.demo()

    assert demo_after.root_node.node_id == demo_before.root_node.node_id
    assert len(demo_after.nodes) == len(demo_before.nodes)

    paths_before = source.find_paths(
        demo_before.root_node.node_id,
        [e for e in demo_before.edges if e.edge_type == EdgeType.MADE_BY][0].to_node_id,
    )
    paths_after = target.find_paths(
        demo_after.root_node.node_id,
        [e for e in demo_after.edges if e.edge_type == EdgeType.MADE_BY][0].to_node_id,
    )
    assert paths_before["paths"][0]["confidence"] == paths_after["paths"][0]["confidence"]


def test_end_to_end_shopping_assistant_uses_graph_evidence() -> None:
    graph = _graph_service()
    assistant = _shopping_assistant(knowledge_graph_service=graph)
    response = assistant.query({"query": "What is the best gaming laptop under 60000?"})
    assert response.processing["knowledge_graph_integrated"] is True
    graph_evidence = [item for item in response.evidence if item.source_id == "knowledge_graph"]
    assert graph_evidence
    assert not any(w.code == "graph_unavailable" for w in response.warnings)


def test_end_to_end_shopping_assistant_without_graph_degrades_gracefully() -> None:
    assistant = _shopping_assistant(knowledge_graph_service=None)
    response = assistant.query({"query": "What is the best gaming laptop under 60000?"})
    assert response.answer
    assert response.processing["knowledge_graph_integrated"] is False
    assert any(w.code == "graph_unavailable" for w in response.warnings)


def test_end_to_end_ai_summary_never_cites_itself() -> None:
    service = _graph_service()
    service.ensure_seeded()
    product = service.product_graph(DEMO_PRODUCT_ID, max_depth=2)
    summaries = [n for n in product.nodes if n.node_type == NodeType.AI_SUMMARY]
    assert summaries
    summary = summaries[0]
    relationships = service.relationships(summary.node_id)
    for edge in relationships["outgoing"]:
        if edge["edge_type"] == "SUPPORTED_BY":
            assert edge["to_node_id"] != summary.node_id


def test_end_to_end_aggregator_and_engine_share_deterministic_ids() -> None:
    """Two independently seeded graphs from the same fixtures produce identical
    canonical node IDs for the demo product (determinism, not randomness)."""
    repo_a = InMemoryKnowledgeGraphRepository()
    engine_a = KnowledgeGraphEngine(repo_a, limits=GraphLimits(max_nodes=500, max_edges=1000))
    result_a = KnowledgeGraphAggregator(engine_a).seed_from_fixtures()

    repo_b = InMemoryKnowledgeGraphRepository()
    engine_b = KnowledgeGraphEngine(repo_b, limits=GraphLimits(max_nodes=500, max_edges=1000))
    result_b = KnowledgeGraphAggregator(engine_b).seed_from_fixtures()

    assert result_a["product_nodes"][DEMO_PRODUCT_ID] == result_b["product_nodes"][DEMO_PRODUCT_ID]
    assert result_a["node_count"] == result_b["node_count"]
    assert result_a["edge_count"] == result_b["edge_count"]


def test_end_to_end_no_secrets_across_full_flow() -> None:
    graph = _graph_service()
    demo = graph.demo()
    evidence = graph.evidence(demo.root_node.node_id)
    meta = graph.meta()
    blob = f"{demo.to_dict()}{evidence}{meta}".lower()
    assert "api_key" not in blob
    assert "system_prompt" not in blob
    assert "password" not in blob
