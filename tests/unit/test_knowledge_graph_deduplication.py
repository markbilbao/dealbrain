"""Unit tests for Knowledge Graph node/edge deduplication and identity resolution."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.knowledge_graph import EdgeType, KnowledgeEdge, KnowledgeNode, NodeType
from app.intelligence.knowledge_graph.deduplication import (
    EdgeDeduplicationService,
    IdentityResolutionService,
    NodeDeduplicationService,
)
from app.intelligence.knowledge_graph.memory import InMemoryKnowledgeGraphRepository

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _node(node_id: str, canonical_key: str, **overrides) -> KnowledgeNode:
    defaults = dict(
        node_id=node_id,
        node_type=NodeType.PRODUCT,
        canonical_key=canonical_key,
        source="fixture",
        source_id=node_id,
        label=f"Label {node_id}",
        confidence=0.7,
        data_status="mock",
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return KnowledgeNode(**defaults)


class TestNodeDeduplicationService:
    def test_first_upsert_creates(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        dedup = NodeDeduplicationService(repo)
        node, created = dedup.upsert(_node("n1", "product:asus:tuf"))
        assert created is True
        assert repo.get_node("n1") is not None

    def test_second_upsert_same_canonical_key_merges(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        dedup = NodeDeduplicationService(repo)
        dedup.upsert(_node("n1", "product:asus:tuf", confidence=0.7, label="Original"))
        merged, created = dedup.upsert(
            _node("n1-alt-id", "product:asus:tuf", confidence=0.95, label="Better label")
        )
        assert created is False
        assert merged.node_id == "n1"  # keeps original id
        assert merged.confidence == 0.95  # max confidence
        assert merged.label == "Better label"
        assert len(repo.nodes.all()) == 1

    def test_upsert_merges_metadata(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        dedup = NodeDeduplicationService(repo)
        dedup.upsert(_node("n1", "product:x", metadata={"a": 1}))
        merged, _ = dedup.upsert(_node("n1", "product:x", metadata={"b": 2}))
        assert dict(merged.metadata) == {"a": 1, "b": 2}

    def test_idempotent_reingestion_does_not_duplicate(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        dedup = NodeDeduplicationService(repo)
        for _ in range(3):
            dedup.upsert(_node("n1", "product:asus:tuf"))
        assert len(repo.nodes.all()) == 1

    def test_upsert_falls_back_to_node_id_lookup(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        dedup = NodeDeduplicationService(repo)
        dedup.upsert(_node("n1", "product:key-one"))
        # Same node_id but a different canonical key: falls back to node_id match.
        merged, created = dedup.upsert(_node("n1", "product:key-two", label="Updated"))
        assert created is False
        assert merged.label == "Updated"


class TestEdgeDeduplicationService:
    def _seeded_repo(self) -> InMemoryKnowledgeGraphRepository:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a", "product:a"))
        repo.add_node(_node("b", "brand:b", node_type=NodeType.BRAND))
        return repo

    def test_first_upsert_creates_edge(self) -> None:
        repo = self._seeded_repo()
        dedup = EdgeDeduplicationService(repo)
        edge, created = dedup.upsert(
            KnowledgeEdge(
                edge_id="e1", edge_type=EdgeType.MADE_BY, from_node_id="a", to_node_id="b"
            )
        )
        assert created is True
        assert repo.get_edge("e1") is not None

    def test_duplicate_same_direction_merges(self) -> None:
        repo = self._seeded_repo()
        dedup = EdgeDeduplicationService(repo)
        dedup.upsert(
            KnowledgeEdge(
                edge_id="e1",
                edge_type=EdgeType.MADE_BY,
                from_node_id="a",
                to_node_id="b",
                confidence=0.5,
                evidence_ids=("ev1",),
            )
        )
        merged, created = dedup.upsert(
            KnowledgeEdge(
                edge_id="e2",
                edge_type=EdgeType.MADE_BY,
                from_node_id="a",
                to_node_id="b",
                confidence=0.9,
                evidence_ids=("ev2",),
            )
        )
        assert created is False
        assert merged.edge_id == "e1"
        assert merged.confidence == 0.9
        assert set(merged.evidence_ids) == {"ev1", "ev2"}
        assert len(repo.edges.all()) == 1

    def test_symmetric_edge_reverse_direction_merges(self) -> None:
        repo = self._seeded_repo()
        repo.add_node(_node("c", "product:c"))
        dedup = EdgeDeduplicationService(repo)
        dedup.upsert(
            KnowledgeEdge(
                edge_id="e1", edge_type=EdgeType.SIMILAR_TO, from_node_id="a", to_node_id="c"
            )
        )
        merged, created = dedup.upsert(
            KnowledgeEdge(
                edge_id="e2", edge_type=EdgeType.SIMILAR_TO, from_node_id="c", to_node_id="a"
            )
        )
        assert created is False
        assert merged.edge_id == "e1"
        assert len(repo.edges.all()) == 1

    def test_non_symmetric_edge_reverse_direction_is_distinct(self) -> None:
        repo = self._seeded_repo()
        dedup = EdgeDeduplicationService(repo)
        dedup.upsert(
            KnowledgeEdge(
                edge_id="e1", edge_type=EdgeType.MADE_BY, from_node_id="a", to_node_id="b"
            )
        )
        # Reverse direction for a non-symmetric type is a different (invalid endpoint) edge,
        # but dedup logic itself should not treat it as equivalent.
        equivalent = dedup._find_equivalent(  # noqa: SLF001 - internal helper under test
            KnowledgeEdge(
                edge_id="e2", edge_type=EdgeType.MADE_BY, from_node_id="b", to_node_id="a"
            )
        )
        assert equivalent is None

    def test_idempotent_edge_reingestion(self) -> None:
        repo = self._seeded_repo()
        dedup = EdgeDeduplicationService(repo)
        for _ in range(3):
            dedup.upsert(
                KnowledgeEdge(
                    edge_id="e1", edge_type=EdgeType.MADE_BY, from_node_id="a", to_node_id="b"
                )
            )
        assert len(repo.edges.all()) == 1


class TestIdentityResolutionService:
    def test_resolve_product_creates_canonical_node(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        svc = IdentityResolutionService(repo)
        node = svc.resolve_product(
            label="ASUS TUF Gaming A15",
            brand="ASUS",
            source="shopee",
            source_id="shopee-1",
            marketplace="Shopee",
        )
        assert node.node_type == NodeType.PRODUCT
        assert node.metadata["marketplace"] == "Shopee"
        assert node.metadata["brand"] == "ASUS"

    def test_resolve_product_merges_across_marketplaces(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        svc = IdentityResolutionService(repo)
        first = svc.resolve_product(
            label="ASUS TUF Gaming A15",
            brand="ASUS",
            source="shopee",
            source_id="shopee-1",
            marketplace="Shopee",
            confidence=0.9,
        )
        second = svc.resolve_product(
            label="ASUS TUF Gaming A15",
            brand="ASUS",
            source="lazada",
            source_id="lazada-9",
            marketplace="Lazada",
            confidence=0.95,
        )
        assert first.node_id == second.node_id
        assert len(repo.nodes.list_by_type(NodeType.PRODUCT)) == 1
        assert second.confidence == 0.95
