"""Unit tests for Knowledge Graph domain entities and value objects."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest
from app.domain.entities.knowledge_graph import (
    SYMMETRIC_EDGE_TYPES,
    EdgeType,
    GraphExplanation,
    GraphLimits,
    GraphPath,
    GraphSnapshot,
    GraphSubgraph,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _node(**overrides) -> KnowledgeNode:
    defaults = dict(
        node_id="kg:product:abc123",
        node_type=NodeType.PRODUCT,
        canonical_key="product:asus:tuf-a15",
        source="fixture",
        source_id="sa-laptop-tuf-a15",
        label="ASUS TUF Gaming A15",
        confidence=0.95,
        data_status="mock",
        created_at=NOW,
        updated_at=NOW,
        metadata={"deal_score": 88.0},
    )
    defaults.update(overrides)
    return KnowledgeNode(**defaults)


def _edge(**overrides) -> KnowledgeEdge:
    defaults = dict(
        edge_id="kg:edge:def456",
        edge_type=EdgeType.MADE_BY,
        from_node_id="kg:product:abc123",
        to_node_id="kg:brand:asus",
        confidence=0.99,
        source="fixture",
        evidence_ids=("kg:evidence:1",),
        created_at=NOW,
        updated_at=NOW,
        metadata={"note": "seeded"},
    )
    defaults.update(overrides)
    return KnowledgeEdge(**defaults)


class TestNodeTypes:
    def test_all_expected_node_types_present(self) -> None:
        expected = {
            "product",
            "seller",
            "review",
            "community_evidence",
            "price_observation",
            "price_history",
            "marketplace",
            "brand",
            "category",
            "topic",
            "evidence",
            "ai_summary",
            "video",
            "accessory",
            "compatibility",
        }
        actual = {item.value for item in NodeType}
        assert actual == expected

    def test_node_type_is_str_enum(self) -> None:
        assert NodeType.PRODUCT == "product"
        assert str(NodeType.PRODUCT.value) == "product"


class TestEdgeTypes:
    def test_all_expected_edge_types_present(self) -> None:
        expected = {
            "SOLD_BY",
            "OFFERED_ON",
            "HAS_PRICE",
            "HAS_PRICE_HISTORY",
            "HAS_REVIEW",
            "DISCUSSED_IN",
            "HAS_COMMUNITY_EVIDENCE",
            "HAS_AI_SUMMARY",
            "MADE_BY",
            "BELONGS_TO_CATEGORY",
            "HAS_TOPIC",
            "SIMILAR_TO",
            "COMPARES_WITH",
            "ACCESSORY_OF",
            "RECOMMENDED_WITH",
            "COMPATIBLE_WITH",
            "HAS_WARNING",
            "HAS_EVIDENCE",
            "SUPPORTED_BY",
            "CONTRADICTS",
            "ALTERNATIVE_TO",
        }
        actual = {item.value for item in EdgeType}
        assert actual == expected

    def test_symmetric_edge_types(self) -> None:
        assert {
            EdgeType.SIMILAR_TO,
            EdgeType.COMPARES_WITH,
            EdgeType.COMPATIBLE_WITH,
            EdgeType.ALTERNATIVE_TO,
        } == SYMMETRIC_EDGE_TYPES


class TestKnowledgeNode:
    def test_is_frozen(self) -> None:
        node = _node()
        assert dataclasses.is_dataclass(node)
        with pytest.raises(dataclasses.FrozenInstanceError):
            node.label = "changed"  # type: ignore[misc]

    def test_metadata_is_read_only_mapping(self) -> None:
        node = _node(metadata={"a": 1})
        with pytest.raises(TypeError):
            node.metadata["a"] = 2  # type: ignore[index]

    def test_defaults(self) -> None:
        node = KnowledgeNode(
            node_id="kg:x:1",
            node_type=NodeType.TOPIC,
            canonical_key="topic:battery",
            source="fixture",
            source_id="battery",
            label="Battery",
        )
        assert node.confidence == 1.0
        assert node.data_status == "mock"
        assert node.created_at is None
        assert node.updated_at is None
        assert dict(node.metadata) == {}

    def test_to_dict_shape(self) -> None:
        node = _node()
        payload = node.to_dict()
        assert payload["node_id"] == node.node_id
        assert payload["node_type"] == "product"
        assert payload["confidence"] == 0.95
        assert payload["data_status"] == "mock"
        assert payload["created_at"] == NOW.isoformat()
        assert payload["updated_at"] == NOW.isoformat()
        assert payload["metadata"] == {"deal_score": 88.0}
        assert isinstance(payload["metadata"], dict)

    def test_to_dict_rounds_confidence(self) -> None:
        node = _node(confidence=0.123456789)
        assert node.to_dict()["confidence"] == 0.1235

    def test_to_dict_handles_missing_timestamps(self) -> None:
        node = _node(created_at=None, updated_at=None)
        payload = node.to_dict()
        assert payload["created_at"] is None
        assert payload["updated_at"] is None


class TestKnowledgeEdge:
    def test_is_frozen(self) -> None:
        edge = _edge()
        with pytest.raises(dataclasses.FrozenInstanceError):
            edge.confidence = 0.1  # type: ignore[misc]

    def test_evidence_ids_normalized_to_tuple(self) -> None:
        edge = _edge(evidence_ids=["a", "b", "a"])
        assert edge.evidence_ids == ("a", "b", "a")
        assert isinstance(edge.evidence_ids, tuple)

    def test_defaults(self) -> None:
        edge = KnowledgeEdge(
            edge_id="kg:edge:1",
            edge_type=EdgeType.SOLD_BY,
            from_node_id="a",
            to_node_id="b",
        )
        assert edge.confidence == 1.0
        assert edge.source == "knowledge_graph"
        assert edge.evidence_ids == ()

    def test_to_dict_shape(self) -> None:
        edge = _edge()
        payload = edge.to_dict()
        assert payload["edge_id"] == edge.edge_id
        assert payload["edge_type"] == "MADE_BY"
        assert payload["from_node_id"] == "kg:product:abc123"
        assert payload["to_node_id"] == "kg:brand:asus"
        assert payload["evidence_ids"] == ["kg:evidence:1"]
        assert isinstance(payload["evidence_ids"], list)
        assert payload["metadata"] == {"note": "seeded"}


class TestGraphPath:
    def test_to_dict(self) -> None:
        path = GraphPath(
            node_ids=("a", "b", "c"),
            edge_ids=("e1", "e2"),
            confidence=0.734567,
            confidence_band="medium",
            evidence_ids=("ev1",),
        )
        payload = path.to_dict()
        assert payload["node_ids"] == ["a", "b", "c"]
        assert payload["edge_ids"] == ["e1", "e2"]
        assert payload["confidence"] == 0.7346
        assert payload["confidence_band"] == "medium"
        assert payload["evidence_ids"] == ["ev1"]

    def test_defaults_no_evidence(self) -> None:
        path = GraphPath(node_ids=("a",), edge_ids=(), confidence=1.0, confidence_band="high")
        assert path.evidence_ids == ()


class TestGraphLimits:
    def test_defaults_match_spec(self) -> None:
        limits = GraphLimits()
        assert limits.max_depth == 3
        assert limits.max_nodes == 100
        assert limits.max_edges == 200
        assert limits.max_paths == 20
        assert limits.min_confidence == 0.0

    def test_to_dict(self) -> None:
        limits = GraphLimits(
            max_depth=2, max_nodes=10, max_edges=20, max_paths=5, min_confidence=0.5
        )
        assert limits.to_dict() == {
            "max_depth": 2,
            "max_nodes": 10,
            "max_edges": 20,
            "max_paths": 5,
            "min_confidence": 0.5,
        }


class TestGraphSubgraph:
    def test_defaults(self) -> None:
        subgraph = GraphSubgraph(root_node=None, nodes=(), edges=())
        assert subgraph.evidence_paths == ()
        assert subgraph.warnings == ()
        assert subgraph.data_status == "mock"
        assert subgraph.truncated is False
        assert isinstance(subgraph.limits, GraphLimits)
        assert subgraph.contradictions == ()
        assert dict(subgraph.summary) == {}

    def test_to_dict_with_root_and_nodes(self) -> None:
        node = _node()
        edge = _edge()
        subgraph = GraphSubgraph(
            root_node=node,
            nodes=(node,),
            edges=(edge,),
            warnings=("truncated",),
            truncated=True,
            summary={"node_counts": {"product": 1}},
        )
        payload = subgraph.to_dict()
        assert payload["root_node"]["node_id"] == node.node_id
        assert len(payload["nodes"]) == 1
        assert len(payload["edges"]) == 1
        assert payload["warnings"] == ["truncated"]
        assert payload["truncated"] is True
        assert payload["summary"] == {"node_counts": {"product": 1}}

    def test_to_dict_root_none(self) -> None:
        subgraph = GraphSubgraph(root_node=None, nodes=(), edges=())
        assert subgraph.to_dict()["root_node"] is None

    def test_summary_is_read_only_mapping(self) -> None:
        subgraph = GraphSubgraph(root_node=None, nodes=(), edges=(), summary={"a": 1})
        with pytest.raises(TypeError):
            subgraph.summary["a"] = 2  # type: ignore[index]


class TestGraphExplanation:
    def test_to_dict_unsupported(self) -> None:
        explanation = GraphExplanation(
            claim="A relates to B",
            supported=False,
            confidence=0.0,
            confidence_band="low",
        )
        payload = explanation.to_dict()
        assert payload["supported"] is False
        assert payload["confidence"] == 0.0
        assert payload["paths"] == []
        assert payload["contradictions"] == []

    def test_to_dict_supported_with_paths(self) -> None:
        path = GraphPath(
            node_ids=("a", "b"), edge_ids=("e1",), confidence=0.9, confidence_band="high"
        )
        explanation = GraphExplanation(
            claim="A relates to B",
            supported=True,
            confidence=0.9,
            confidence_band="high",
            paths=(path,),
            limitations=("Traversal does not prove causation.",),
        )
        payload = explanation.to_dict()
        assert payload["supported"] is True
        assert len(payload["paths"]) == 1
        assert "Traversal does not prove causation." in payload["limitations"]


class TestGraphSnapshot:
    def test_to_dict_shape(self) -> None:
        node = _node()
        edge = _edge()
        snapshot = GraphSnapshot(
            schema_version=1,
            nodes=(node,),
            edges=(edge,),
            created_at=NOW,
            data_status="mock",
            source_summary={"node_count": 1, "edge_count": 1},
        )
        payload = snapshot.to_dict()
        assert payload["schema_version"] == 1
        assert payload["created_at"] == NOW.isoformat()
        assert payload["data_status"] == "mock"
        assert payload["source_summary"] == {"node_count": 1, "edge_count": 1}
        assert len(payload["nodes"]) == 1
        assert len(payload["edges"]) == 1

    def test_source_summary_is_read_only(self) -> None:
        snapshot = GraphSnapshot(
            schema_version=1,
            nodes=(),
            edges=(),
            created_at=NOW,
            data_status="mock",
            source_summary={"a": 1},
        )
        with pytest.raises(TypeError):
            snapshot.source_summary["a"] = 2  # type: ignore[index]
