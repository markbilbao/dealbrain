"""Unit tests for the in-memory Knowledge Graph repository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphSnapshot,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.exceptions import KnowledgeGraphValidationError
from app.intelligence.knowledge_graph.memory import (
    InMemoryKnowledgeEdgeRepository,
    InMemoryKnowledgeGraphRepository,
    InMemoryKnowledgeNodeRepository,
)

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def _node(node_id: str, *, canonical_key: str | None = None, **overrides) -> KnowledgeNode:
    defaults = dict(
        node_id=node_id,
        node_type=NodeType.PRODUCT,
        canonical_key=canonical_key or f"product:{node_id}",
        source="fixture",
        source_id=node_id,
        label=f"Label {node_id}",
        confidence=0.9,
        data_status="mock",
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(overrides)
    return KnowledgeNode(**defaults)


def _edge(edge_id: str, from_id: str, to_id: str, **overrides) -> KnowledgeEdge:
    defaults = dict(
        edge_id=edge_id,
        edge_type=EdgeType.SIMILAR_TO,
        from_node_id=from_id,
        to_node_id=to_id,
        confidence=0.8,
        source="fixture",
    )
    defaults.update(overrides)
    return KnowledgeEdge(**defaults)


class TestInMemoryKnowledgeNodeRepository:
    def test_add_and_get(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        node = _node("n1")
        repo.add(node)
        assert repo.get("n1") == node

    def test_add_duplicate_raises(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        repo.add(_node("n1"))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.add(_node("n1"))

    def test_find_by_canonical_key(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        node = _node("n1", canonical_key="product:asus:tuf")
        repo.add(node)
        assert repo.find_by_canonical_key("product:asus:tuf") == node
        assert repo.find_by_canonical_key("missing") is None

    def test_update_moves_canonical_index(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        repo.add(_node("n1", canonical_key="key-a"))
        updated = _node("n1", canonical_key="key-b")
        repo.update(updated)
        assert repo.find_by_canonical_key("key-a") is None
        assert repo.find_by_canonical_key("key-b") == updated

    def test_update_unknown_raises(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        with pytest.raises(KnowledgeGraphValidationError):
            repo.update(_node("missing"))

    def test_list_by_type(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        repo.add(_node("n1", node_type=NodeType.PRODUCT))
        repo.add(_node("n2", node_type=NodeType.BRAND, canonical_key="brand:asus"))
        assert [n.node_id for n in repo.list_by_type(NodeType.PRODUCT)] == ["n1"]
        assert [n.node_id for n in repo.list_by_type(NodeType.BRAND)] == ["n2"]

    def test_remove(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        repo.add(_node("n1"))
        assert repo.remove("n1") is True
        assert repo.remove("n1") is False
        assert repo.get("n1") is None

    def test_clear_and_all(self) -> None:
        repo = InMemoryKnowledgeNodeRepository()
        repo.add(_node("n1"))
        repo.add(_node("n2", canonical_key="product:n2"))
        assert len(repo.all()) == 2
        repo.clear()
        assert repo.all() == []


class TestInMemoryKnowledgeEdgeRepository:
    def test_add_and_get(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        edge = _edge("e1", "a", "b")
        repo.add(edge)
        assert repo.get("e1") == edge

    def test_add_duplicate_raises(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        repo.add(_edge("e1", "a", "b"))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.add(_edge("e1", "a", "b"))

    def test_list_outgoing_incoming(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        repo.add(_edge("e1", "a", "b"))
        repo.add(_edge("e2", "c", "a"))
        assert [e.edge_id for e in repo.list_outgoing("a")] == ["e1"]
        assert [e.edge_id for e in repo.list_incoming("a")] == ["e2"]

    def test_list_by_type(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        repo.add(_edge("e1", "a", "b", edge_type=EdgeType.SIMILAR_TO))
        repo.add(_edge("e2", "a", "c", edge_type=EdgeType.MADE_BY))
        assert [e.edge_id for e in repo.list_by_type(EdgeType.MADE_BY)] == ["e2"]

    def test_update_unknown_raises(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        with pytest.raises(KnowledgeGraphValidationError):
            repo.update(_edge("missing", "a", "b"))

    def test_remove_and_clear(self) -> None:
        repo = InMemoryKnowledgeEdgeRepository()
        repo.add(_edge("e1", "a", "b"))
        assert repo.remove("e1") is True
        assert repo.remove("e1") is False
        repo.add(_edge("e2", "a", "b"))
        repo.clear()
        assert repo.all() == []


class TestCompositeRepositoryReferentialIntegrity:
    def test_add_node_then_edge(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        repo.add_node(_node("b", canonical_key="product:b"))
        edge = repo.add_edge(_edge("e1", "a", "b"))
        assert edge.edge_id == "e1"

    def test_add_edge_missing_from_node_raises(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("b", canonical_key="product:b"))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.add_edge(_edge("e1", "missing", "b"))

    def test_add_edge_missing_to_node_raises(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.add_edge(_edge("e1", "a", "missing"))

    def test_update_edge_missing_nodes_raises(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        repo.add_node(_node("b", canonical_key="product:b"))
        edge = repo.add_edge(_edge("e1", "a", "b"))
        repo.remove_node("b")
        with pytest.raises(KnowledgeGraphValidationError):
            repo.update_edge(edge)

    def test_remove_node_cascades_incident_edges(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        repo.add_node(_node("b", canonical_key="product:b"))
        repo.add_node(_node("c", canonical_key="product:c"))
        repo.add_edge(_edge("e1", "a", "b"))
        repo.add_edge(_edge("e2", "c", "a"))
        assert repo.remove_node("a") is True
        assert repo.get_edge("e1") is None
        assert repo.get_edge("e2") is None
        assert repo.get_node("b") is not None

    def test_remove_missing_node_returns_false(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        assert repo.remove_node("missing") is False

    def test_clear_removes_everything(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        repo.add_node(_node("b", canonical_key="product:b"))
        repo.add_edge(_edge("e1", "a", "b"))
        repo.clear()
        assert repo.nodes.all() == []
        assert repo.edges.all() == []

    def test_add_node_strips_whitespace(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        node = _node("  n1  ", canonical_key="  key  ", label="  Label  ")
        stored = repo.add_node(node)
        assert stored.node_id == "n1"
        assert stored.canonical_key == "key"
        assert stored.label == "Label"


class TestSnapshotExportImport:
    def test_export_snapshot_sorted_and_counted(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("b", canonical_key="product:b"))
        repo.add_node(_node("a"))
        repo.add_edge(_edge("e1", "a", "b"))
        snapshot = repo.export_snapshot(data_status="mock")
        assert isinstance(snapshot, GraphSnapshot)
        assert [n.node_id for n in snapshot.nodes] == ["a", "b"]
        assert snapshot.source_summary["node_count"] == 2
        assert snapshot.source_summary["edge_count"] == 1
        assert snapshot.source_summary["node_types"]["product"] == 2

    def test_export_snapshot_invalid_status_falls_back_to_mock(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        snapshot = repo.export_snapshot(data_status="not-a-real-status")
        assert snapshot.data_status == "mock"

    def test_export_then_import_round_trip(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        repo.add_node(_node("b", canonical_key="product:b"))
        repo.add_edge(_edge("e1", "a", "b"))
        snapshot = repo.export_snapshot()

        target = InMemoryKnowledgeGraphRepository()
        target.add_node(_node("stale", canonical_key="product:stale"))
        imported = target.import_snapshot(snapshot)

        assert isinstance(imported, GraphSnapshot)
        assert target.get_node("stale") is None
        assert target.get_node("a") is not None
        assert target.get_node("b") is not None
        assert target.get_edge("e1") is not None

    def test_import_snapshot_accepts_dict_payload(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        payload = repo.export_snapshot().to_dict()

        target = InMemoryKnowledgeGraphRepository()
        target.import_snapshot(payload)
        assert target.get_node("a") is not None

    def test_import_snapshot_wrong_schema_version_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository(schema_version=1)
        payload = repo.export_snapshot().to_dict()
        payload["schema_version"] = 99
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_missing_nodes_list_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        del payload["nodes"]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_invalid_data_status_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["data_status"] = "not-real"
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_duplicate_node_id_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        payload = repo.export_snapshot().to_dict()
        payload["nodes"].append(dict(payload["nodes"][0]))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_node_missing_node_id_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = [{"node_type": "product", "label": "x"}]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_unsupported_node_type_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = [
            {
                "node_id": "n1",
                "node_type": "not_a_type",
                "canonical_key": "k",
                "source": "s",
                "source_id": "s1",
                "label": "L",
            }
        ]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_edge_with_missing_endpoint_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = [
            {
                "node_id": "n1",
                "node_type": "product",
                "canonical_key": "k",
                "source": "s",
                "source_id": "s1",
                "label": "L",
            }
        ]
        payload["edges"] = [
            {
                "edge_id": "e1",
                "edge_type": "MADE_BY",
                "from_node_id": "n1",
                "to_node_id": "does-not-exist",
            }
        ]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_unsupported_edge_type_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = [
            {
                "node_id": "n1",
                "node_type": "product",
                "canonical_key": "k1",
                "source": "s",
                "source_id": "s1",
                "label": "L1",
            },
            {
                "node_id": "n2",
                "node_type": "brand",
                "canonical_key": "k2",
                "source": "s",
                "source_id": "s2",
                "label": "L2",
            },
        ]
        payload["edges"] = [
            {
                "edge_id": "e1",
                "edge_type": "NOT_A_REAL_EDGE",
                "from_node_id": "n1",
                "to_node_id": "n2",
            }
        ]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_malformed_node_entry_rejected(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = ["not-a-dict"]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_import_snapshot_evidence_ids_must_be_list(self) -> None:
        repo = InMemoryKnowledgeGraphRepository()
        payload = repo.export_snapshot().to_dict()
        payload["nodes"] = [
            {
                "node_id": "n1",
                "node_type": "product",
                "canonical_key": "k1",
                "source": "s",
                "source_id": "s1",
                "label": "L1",
            },
            {
                "node_id": "n2",
                "node_type": "brand",
                "canonical_key": "k2",
                "source": "s",
                "source_id": "s2",
                "label": "L2",
            },
        ]
        payload["edges"] = [
            {
                "edge_id": "e1",
                "edge_type": "MADE_BY",
                "from_node_id": "n1",
                "to_node_id": "n2",
                "evidence_ids": "not-a-list",
            }
        ]
        with pytest.raises(KnowledgeGraphValidationError):
            repo.import_snapshot(payload)

    def test_idempotent_reingestion_via_add_node_dedup_not_required_here(self) -> None:
        # The bare repository (no dedup service) enforces uniqueness by node_id only.
        repo = InMemoryKnowledgeGraphRepository()
        repo.add_node(_node("a"))
        with pytest.raises(KnowledgeGraphValidationError):
            repo.add_node(_node("a"))
