"""Unit tests for the Knowledge Graph engine: creation, traversal, and paths."""

from __future__ import annotations

import pytest
from app.domain.entities.knowledge_graph import EdgeType, GraphLimits, NodeType
from app.domain.exceptions import (
    KnowledgeGraphNotFoundError,
    KnowledgeGraphValidationError,
)
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository


def make_engine(**limit_overrides) -> KnowledgeGraphEngine:
    repo = InMemoryKnowledgeGraphRepository()
    limits = GraphLimits(
        max_depth=limit_overrides.get("max_depth", 3),
        max_nodes=limit_overrides.get("max_nodes", 100),
        max_edges=limit_overrides.get("max_edges", 200),
        max_paths=limit_overrides.get("max_paths", 20),
        min_confidence=limit_overrides.get("min_confidence", 0.0),
    )
    return KnowledgeGraphEngine(repo, limits=limits)


class TestNodeCreation:
    def test_create_node_basic(self) -> None:
        engine = make_engine()
        node = engine.create_node(
            node_type=NodeType.PRODUCT,
            source="fixture",
            source_id="p1",
            label="ASUS TUF A15",
            brand="ASUS",
        )
        assert node.node_type == NodeType.PRODUCT
        assert node.canonical_key == "product:asus:asus-tuf-a15"

    def test_create_node_accepts_string_type(self) -> None:
        engine = make_engine()
        node = engine.create_node(
            node_type="brand", source="fixture", source_id="asus", label="ASUS"
        )
        assert node.node_type == NodeType.BRAND

    def test_create_node_unsupported_type_rejected(self) -> None:
        engine = make_engine()
        with pytest.raises(KnowledgeGraphValidationError):
            engine.create_node(node_type="not_a_type", source="fixture", source_id="x", label="x")

    def test_create_node_is_idempotent(self) -> None:
        engine = make_engine()
        first = engine.create_node(
            node_type=NodeType.PRODUCT, source="shopee", source_id="p1", label="X", brand="ASUS"
        )
        second = engine.create_node(
            node_type=NodeType.PRODUCT, source="lazada", source_id="p2", label="X", brand="ASUS"
        )
        assert first.node_id == second.node_id
        assert len(engine.repository.nodes.all()) == 1

    def test_create_node_clamps_confidence(self) -> None:
        engine = make_engine()
        with pytest.raises(KnowledgeGraphValidationError):
            engine.create_node(
                node_type=NodeType.PRODUCT,
                source="fixture",
                source_id="p1",
                label="X",
                confidence=1.5,
            )


class TestEdgeCreation:
    def _two_nodes(self, engine: KnowledgeGraphEngine):
        product = engine.create_node(
            node_type=NodeType.PRODUCT, source="fixture", source_id="p1", label="X", brand="ASUS"
        )
        brand = engine.create_node(
            node_type=NodeType.BRAND, source="fixture", source_id="asus", label="ASUS"
        )
        return product, brand

    def test_create_edge_basic(self) -> None:
        engine = make_engine()
        product, brand = self._two_nodes(engine)
        edge = engine.create_edge(
            edge_type=EdgeType.MADE_BY, from_node_id=product.node_id, to_node_id=brand.node_id
        )
        assert edge.edge_type == EdgeType.MADE_BY
        assert edge.from_node_id == product.node_id

    def test_create_edge_missing_node_rejected(self) -> None:
        engine = make_engine()
        product, _ = self._two_nodes(engine)
        with pytest.raises(KnowledgeGraphValidationError):
            engine.create_edge(
                edge_type=EdgeType.MADE_BY,
                from_node_id=product.node_id,
                to_node_id="does-not-exist",
            )

    def test_create_edge_invalid_relationship_rejected(self) -> None:
        """A SOLD_BY edge must go product -> seller, not brand -> product."""
        engine = make_engine()
        product, brand = self._two_nodes(engine)
        with pytest.raises(KnowledgeGraphValidationError):
            engine.create_edge(
                edge_type=EdgeType.SOLD_BY, from_node_id=brand.node_id, to_node_id=product.node_id
            )

    def test_create_edge_unsupported_type_rejected(self) -> None:
        engine = make_engine()
        product, brand = self._two_nodes(engine)
        with pytest.raises(KnowledgeGraphValidationError):
            engine.create_edge(
                edge_type="NOT_A_REAL_EDGE", from_node_id=product.node_id, to_node_id=brand.node_id
            )

    def test_create_edge_is_idempotent(self) -> None:
        engine = make_engine()
        product, brand = self._two_nodes(engine)
        first = engine.create_edge(
            edge_type=EdgeType.MADE_BY, from_node_id=product.node_id, to_node_id=brand.node_id
        )
        second = engine.create_edge(
            edge_type=EdgeType.MADE_BY, from_node_id=product.node_id, to_node_id=brand.node_id
        )
        assert first.edge_id == second.edge_id
        assert len(engine.repository.edges.all()) == 1


class TestGetNode:
    def test_get_node_missing_raises(self) -> None:
        engine = make_engine()
        with pytest.raises(KnowledgeGraphNotFoundError):
            engine.get_node("missing")


class _GraphFixture:
    """Small deterministic graph: product -[MADE_BY]-> brand,
    product -[BELONGS_TO_CATEGORY]-> category, product -[SIMILAR_TO]-> product2,
    product2 -[SIMILAR_TO]-> product3 (cycle back to product via SIMILAR_TO)."""

    def __init__(self, engine: KnowledgeGraphEngine) -> None:
        self.engine = engine
        self.product = engine.create_node(
            node_type=NodeType.PRODUCT,
            source="fixture",
            source_id="p1",
            label="Laptop One",
            brand="ASUS",
        )
        self.brand = engine.create_node(
            node_type=NodeType.BRAND, source="fixture", source_id="asus", label="ASUS"
        )
        self.category = engine.create_node(
            node_type=NodeType.CATEGORY,
            source="fixture",
            source_id="laptop",
            label="Laptop",
            category="laptop",
        )
        self.product2 = engine.create_node(
            node_type=NodeType.PRODUCT,
            source="fixture",
            source_id="p2",
            label="Laptop Two",
            brand="Acer",
        )
        self.product3 = engine.create_node(
            node_type=NodeType.PRODUCT,
            source="fixture",
            source_id="p3",
            label="Laptop Three",
            brand="Lenovo",
        )
        self.review = engine.create_node(
            node_type=NodeType.REVIEW, source="reviews", source_id="rev1", label="Great review"
        )
        engine.create_edge(
            edge_type=EdgeType.MADE_BY,
            from_node_id=self.product.node_id,
            to_node_id=self.brand.node_id,
        )
        engine.create_edge(
            edge_type=EdgeType.BELONGS_TO_CATEGORY,
            from_node_id=self.product.node_id,
            to_node_id=self.category.node_id,
        )
        engine.create_edge(
            edge_type=EdgeType.SIMILAR_TO,
            from_node_id=self.product.node_id,
            to_node_id=self.product2.node_id,
            confidence=0.8,
        )
        engine.create_edge(
            edge_type=EdgeType.SIMILAR_TO,
            from_node_id=self.product2.node_id,
            to_node_id=self.product3.node_id,
            confidence=0.6,
        )
        # Cycle: product3 back to product.
        engine.create_edge(
            edge_type=EdgeType.SIMILAR_TO,
            from_node_id=self.product3.node_id,
            to_node_id=self.product.node_id,
            confidence=0.5,
        )
        # Two hops from product, and NOT reachable via the SIMILAR_TO cycle shortcut.
        engine.create_edge(
            edge_type=EdgeType.HAS_REVIEW,
            from_node_id=self.product2.node_id,
            to_node_id=self.review.node_id,
        )


class TestNeighbors:
    def test_neighbors_both_directions(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.neighbors(fx.product.node_id)
        node_ids = {n.node_id for n in subgraph.nodes}
        assert fx.brand.node_id in node_ids
        assert fx.category.node_id in node_ids
        assert fx.product2.node_id in node_ids

    def test_neighbors_outgoing_only(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.neighbors(fx.product2.node_id, direction="outgoing")
        node_ids = {n.node_id for n in subgraph.nodes}
        assert fx.product3.node_id in node_ids
        assert fx.product.node_id not in node_ids

    def test_neighbors_filters_by_edge_type(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.neighbors(fx.product.node_id, edge_types=["MADE_BY"])
        edge_types = {e.edge_type for e in subgraph.edges}
        assert edge_types == {EdgeType.MADE_BY}

    def test_neighbors_filters_by_min_confidence(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.neighbors(fx.product2.node_id, min_confidence=0.7)
        for edge in subgraph.edges:
            assert edge.confidence >= 0.7

    def test_neighbors_missing_root_raises(self) -> None:
        engine = make_engine()
        with pytest.raises(KnowledgeGraphNotFoundError):
            engine.neighbors("missing")

    def test_neighbors_truncated_when_over_max_nodes(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.neighbors(fx.product.node_id, max_nodes=1)
        assert subgraph.truncated is True
        assert subgraph.warnings


class TestTraverse:
    def test_traverse_bounded_depth(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=1)
        node_ids = {n.node_id for n in subgraph.nodes}
        assert fx.brand.node_id in node_ids
        assert fx.product2.node_id in node_ids
        # review is two hops away (product -> product2 -> review); no shortcut exists.
        assert fx.review.node_id not in node_ids

    def test_traverse_multi_hop(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=3)
        node_ids = {n.node_id for n in subgraph.nodes}
        assert fx.review.node_id in node_ids

    def test_traverse_handles_cycles_without_infinite_loop(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=10)
        # Should terminate and each node should appear only once.
        node_ids = [n.node_id for n in subgraph.nodes]
        assert len(node_ids) == len(set(node_ids))

    def test_traverse_filters_by_node_type(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=2, node_types=["brand"])
        node_types = {n.node_type for n in subgraph.nodes}
        assert node_types.issubset({NodeType.PRODUCT, NodeType.BRAND})
        assert fx.category.node_id not in {n.node_id for n in subgraph.nodes}

    def test_traverse_truncated_when_over_max_edges(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=3, max_edges=1)
        assert subgraph.truncated is True

    def test_traverse_missing_root_raises(self) -> None:
        engine = make_engine()
        with pytest.raises(KnowledgeGraphNotFoundError):
            engine.traverse("missing")

    def test_traverse_summary_counts(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        subgraph = engine.traverse(fx.product.node_id, max_depth=3)
        assert subgraph.summary["node_counts"]["product"] >= 1
        assert subgraph.summary["edge_counts"].get("MADE_BY") == 1


class TestFindPaths:
    def test_find_direct_path(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        paths = engine.find_paths(fx.product.node_id, fx.brand.node_id)
        assert len(paths) == 1
        assert paths[0].node_ids == (fx.product.node_id, fx.brand.node_id)

    def test_find_multi_hop_path(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        paths = engine.find_paths(fx.product.node_id, fx.product3.node_id, max_depth=3)
        assert paths
        assert paths[0].node_ids[-1] == fx.product3.node_id

    def test_find_paths_respects_cycle_and_terminates(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        # There's a cycle product -> product2 -> product3 -> product; ensure this terminates
        # quickly and returns a path rather than looping forever.
        paths = engine.find_paths(fx.product.node_id, fx.product2.node_id, max_depth=5)
        assert isinstance(paths, list)
        assert paths

    def test_path_confidence_is_minimum_edge_confidence(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        paths = engine.find_paths(fx.product.node_id, fx.product3.node_id, max_depth=3)
        best = paths[0]
        assert best.confidence == pytest.approx(0.6)  # min(0.8, 0.6) along product->p2->p3
        assert best.confidence_band == "medium"

    def test_find_paths_no_path_returns_empty(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        isolated = engine.create_node(
            node_type=NodeType.TOPIC, source="fixture", source_id="isolated", label="Isolated Topic"
        )
        paths = engine.find_paths(fx.product.node_id, isolated.node_id)
        assert paths == []

    def test_find_paths_missing_node_raises(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        with pytest.raises(KnowledgeGraphNotFoundError):
            engine.find_paths(fx.product.node_id, "missing")

    def test_find_paths_respects_max_paths_limit(self) -> None:
        engine = make_engine(max_paths=1)
        fx = _GraphFixture(engine)
        paths = engine.find_paths(fx.product.node_id, fx.product3.node_id, max_depth=3)
        assert len(paths) <= 1

    def test_find_paths_filters_by_min_confidence(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        paths = engine.find_paths(
            fx.product.node_id, fx.product3.node_id, max_depth=3, min_confidence=0.9
        )
        assert paths == []

    def test_shortest_evidence_path_returns_single_best(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        path = engine.shortest_evidence_path(fx.product.node_id, fx.brand.node_id)
        assert path is not None
        assert path.node_ids == (fx.product.node_id, fx.brand.node_id)

    def test_shortest_evidence_path_none_when_unreachable(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        isolated = engine.create_node(
            node_type=NodeType.TOPIC, source="fixture", source_id="isolated2", label="Isolated"
        )
        assert engine.shortest_evidence_path(fx.product.node_id, isolated.node_id) is None


class TestExplainConnection:
    def test_explain_supported(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        explanation = engine.explain_connection(fx.product.node_id, fx.brand.node_id)
        assert explanation.supported is True
        assert explanation.confidence > 0
        assert explanation.limitations

    def test_explain_unsupported_when_no_path(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        isolated = engine.create_node(
            node_type=NodeType.TOPIC, source="fixture", source_id="isolated3", label="Isolated"
        )
        explanation = engine.explain_connection(fx.product.node_id, isolated.node_id)
        assert explanation.supported is False
        assert explanation.confidence == 0.0
        assert explanation.confidence_band == "low"

    def test_explain_uses_custom_claim(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        explanation = engine.explain_connection(
            fx.product.node_id, fx.brand.node_id, claim="Custom claim text"
        )
        assert explanation.claim == "Custom claim text"

    def test_explain_default_claim_mentions_labels(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        explanation = engine.explain_connection(fx.product.node_id, fx.brand.node_id)
        assert fx.product.label in explanation.claim
        assert fx.brand.label in explanation.claim

    def test_explain_collects_contradictions(self) -> None:
        engine = make_engine()
        fx = _GraphFixture(engine)
        evidence_a = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="ev-a", label="Claim A"
        )
        evidence_b = engine.create_node(
            node_type=NodeType.EVIDENCE, source="fixture", source_id="ev-b", label="Claim B"
        )
        engine.create_edge(
            edge_type=EdgeType.CONTRADICTS,
            from_node_id=evidence_a.node_id,
            to_node_id=evidence_b.node_id,
        )
        engine.create_edge(
            edge_type=EdgeType.HAS_EVIDENCE,
            from_node_id=fx.product.node_id,
            to_node_id=evidence_a.node_id,
        )
        explanation = engine.explain_connection(fx.product.node_id, evidence_a.node_id)
        assert explanation.contradictions


class TestEffectiveLimits:
    def test_client_cannot_widen_server_ceiling(self) -> None:
        engine = make_engine(
            max_depth=2, max_nodes=10, max_edges=10, max_paths=5, min_confidence=0.2
        )
        limits = engine.effective_limits(max_depth=100, max_nodes=1000, min_confidence=0.0)
        assert limits.max_depth == 2
        assert limits.max_nodes == 10
        assert limits.min_confidence == 0.2

    def test_client_can_narrow_within_ceiling(self) -> None:
        engine = make_engine(max_depth=5, max_nodes=100)
        limits = engine.effective_limits(max_depth=1, max_nodes=5)
        assert limits.max_depth == 1
        assert limits.max_nodes == 5
