"""Unit tests for the Knowledge Graph fixture aggregator."""

from __future__ import annotations

from app.domain.entities.knowledge_graph import EdgeType, GraphLimits, NodeType
from app.intelligence.knowledge_graph.aggregator import KnowledgeGraphAggregator
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository


def make_engine() -> KnowledgeGraphEngine:
    repo = InMemoryKnowledgeGraphRepository()
    return KnowledgeGraphEngine(
        repo, limits=GraphLimits(max_depth=3, max_nodes=1000, max_edges=2000, max_paths=20)
    )


class TestSeedFromFixtures:
    def test_seed_creates_nodes_and_edges(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        assert result["node_count"] > 0
        assert result["edge_count"] > 0
        assert result["data_status"] == "mock"
        assert result["warnings"]

    def test_seed_is_idempotent_when_repeated(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        first = aggregator.seed_from_fixtures()
        second = aggregator.seed_from_fixtures()
        assert first["node_count"] == second["node_count"]
        assert first["edge_count"] == second["edge_count"]

    def test_seed_without_clear_does_not_duplicate(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        aggregator.seed_from_fixtures(clear=True)
        node_count_before = len(engine.repository.nodes.all())
        aggregator.seed_from_fixtures(clear=False)
        assert len(engine.repository.nodes.all()) == node_count_before

    def test_demo_product_node_created(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        aggregator.seed_from_fixtures()
        products = engine.repository.nodes.list_by_type(NodeType.PRODUCT)
        labels = {p.label for p in products}
        assert DEMO_PRODUCT_LABEL in labels

    def test_multi_source_merging_shopee_lazada_same_brand_label(self) -> None:
        """The demo laptop and its Lazada mirror share brand+label and must
        collapse onto the same canonical product node."""
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        products = engine.repository.nodes.list_by_type(NodeType.PRODUCT)
        matching = [p for p in products if p.label == DEMO_PRODUCT_LABEL]
        assert len(matching) == 1
        node_id = result["product_nodes"][DEMO_PRODUCT_ID]
        assert matching[0].node_id == node_id

    def test_brand_and_category_edges_created(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        node_id = result["product_nodes"][DEMO_PRODUCT_ID]
        made_by = [
            e
            for e in engine.repository.edges.list_outgoing(node_id)
            if e.edge_type == EdgeType.MADE_BY
        ]
        belongs = [
            e
            for e in engine.repository.edges.list_outgoing(node_id)
            if e.edge_type == EdgeType.BELONGS_TO_CATEGORY
        ]
        assert made_by
        assert belongs

    def test_ai_summary_is_supported_by_underlying_evidence_not_itself(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        node_id = result["product_nodes"][DEMO_PRODUCT_ID]
        summary_edges = [
            e
            for e in engine.repository.edges.list_outgoing(node_id)
            if e.edge_type == EdgeType.HAS_AI_SUMMARY
        ]
        assert summary_edges
        summary_node_id = summary_edges[0].to_node_id
        summary_node = engine.repository.get_node(summary_node_id)
        assert summary_node.node_type == NodeType.AI_SUMMARY

        supported_by_edges = engine.repository.edges.list_outgoing(summary_node_id)
        assert supported_by_edges
        for edge in supported_by_edges:
            assert edge.edge_type == EdgeType.SUPPORTED_BY
            assert edge.to_node_id != summary_node_id
            backing = engine.repository.get_node(edge.to_node_id)
            assert backing.node_type == NodeType.EVIDENCE

    def test_similar_and_alternative_edges_created_for_pairs(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        aggregator.seed_from_fixtures()
        similar_edges = engine.repository.edges.list_by_type(EdgeType.SIMILAR_TO)
        alternative_edges = engine.repository.edges.list_by_type(EdgeType.ALTERNATIVE_TO)
        assert similar_edges
        assert alternative_edges

    def test_contradiction_seeded_for_demo_product(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        aggregator.seed_from_fixtures()
        contradictions = engine.repository.edges.list_by_type(EdgeType.CONTRADICTS)
        assert contradictions
        edge = contradictions[0]
        assert edge.evidence_ids

    def test_community_evidence_deduplicated_despite_duplicate_fixture_source_id(self) -> None:
        """fixtures.py intentionally includes a duplicate community_evidence source_id;
        canonicalization + dedup must collapse it to one node."""
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        aggregator.seed_from_fixtures()
        community_nodes = engine.repository.nodes.list_by_type(NodeType.COMMUNITY_EVIDENCE)
        thread_nodes = [n for n in community_nodes if n.source_id == "reddit-tuf-thread-1"]
        assert len(thread_nodes) == 1

    def test_community_adapter_extends_evidence(self) -> None:
        class _StubAdapter:
            def evidence_for(self, product_ids):
                return [
                    {
                        "product_id": DEMO_PRODUCT_ID,
                        "source": "stub_adapter",
                        "source_id": "stub-1",
                        "label": "Stub community evidence",
                        "topic": "value",
                        "confidence": 0.6,
                        "data_status": "mock",
                    }
                ]

        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine, community_adapter=_StubAdapter())
        aggregator.seed_from_fixtures()
        community_nodes = engine.repository.nodes.list_by_type(NodeType.COMMUNITY_EVIDENCE)
        assert any(n.source == "stub_adapter" for n in community_nodes)

    def test_warnings_mention_fixture_and_no_guarantee(self) -> None:
        engine = make_engine()
        aggregator = KnowledgeGraphAggregator(engine)
        result = aggregator.seed_from_fixtures()
        blob = " ".join(result["warnings"]).lower()
        assert "fixture" in blob
        assert "not" in blob
