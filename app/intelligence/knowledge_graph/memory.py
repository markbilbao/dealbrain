"""In-memory Knowledge Graph repositories.

Satisfies repository ports without an external graph database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphSnapshot,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.exceptions import KnowledgeGraphValidationError
from app.domain.interfaces.knowledge_graph_repository import (
    GraphSnapshotRepository,
    KnowledgeEdgeRepository,
    KnowledgeGraphRepository,
    KnowledgeNodeRepository,
)
from app.intelligence.knowledge_graph.validator import (
    KnowledgeGraphValidator,
    clamp_confidence,
    sanitize_metadata,
)


class InMemoryKnowledgeNodeRepository(KnowledgeNodeRepository):
    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._by_canonical: dict[str, str] = {}

    def add(self, node: KnowledgeNode) -> KnowledgeNode:
        if node.node_id in self._nodes:
            raise KnowledgeGraphValidationError(f"Duplicate node_id: {node.node_id}")
        self._nodes[node.node_id] = node
        self._by_canonical[node.canonical_key] = node.node_id
        return node

    def update(self, node: KnowledgeNode) -> KnowledgeNode:
        existing = self._nodes.get(node.node_id)
        if existing is None:
            raise KnowledgeGraphValidationError(f"Unknown node_id: {node.node_id}")
        if existing.canonical_key != node.canonical_key:
            self._by_canonical.pop(existing.canonical_key, None)
        self._nodes[node.node_id] = node
        self._by_canonical[node.canonical_key] = node.node_id
        return node

    def get(self, node_id: str) -> KnowledgeNode | None:
        return self._nodes.get(node_id)

    def find_by_canonical_key(self, canonical_key: str) -> KnowledgeNode | None:
        node_id = self._by_canonical.get(canonical_key)
        if node_id is None:
            return None
        return self._nodes.get(node_id)

    def list_by_type(self, node_type: NodeType) -> list[KnowledgeNode]:
        return [node for node in self._nodes.values() if node.node_type == node_type]

    def remove(self, node_id: str) -> bool:
        node = self._nodes.pop(node_id, None)
        if node is None:
            return False
        if self._by_canonical.get(node.canonical_key) == node_id:
            self._by_canonical.pop(node.canonical_key, None)
        return True

    def clear(self) -> None:
        self._nodes.clear()
        self._by_canonical.clear()

    def all(self) -> list[KnowledgeNode]:
        return list(self._nodes.values())


class InMemoryKnowledgeEdgeRepository(KnowledgeEdgeRepository):
    def __init__(self) -> None:
        self._edges: dict[str, KnowledgeEdge] = {}

    def add(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        if edge.edge_id in self._edges:
            raise KnowledgeGraphValidationError(f"Duplicate edge_id: {edge.edge_id}")
        self._edges[edge.edge_id] = edge
        return edge

    def update(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        if edge.edge_id not in self._edges:
            raise KnowledgeGraphValidationError(f"Unknown edge_id: {edge.edge_id}")
        self._edges[edge.edge_id] = edge
        return edge

    def get(self, edge_id: str) -> KnowledgeEdge | None:
        return self._edges.get(edge_id)

    def list_outgoing(self, node_id: str) -> list[KnowledgeEdge]:
        return [edge for edge in self._edges.values() if edge.from_node_id == node_id]

    def list_incoming(self, node_id: str) -> list[KnowledgeEdge]:
        return [edge for edge in self._edges.values() if edge.to_node_id == node_id]

    def list_by_type(self, edge_type: EdgeType) -> list[KnowledgeEdge]:
        return [edge for edge in self._edges.values() if edge.edge_type == edge_type]

    def remove(self, edge_id: str) -> bool:
        return self._edges.pop(edge_id, None) is not None

    def clear(self) -> None:
        self._edges.clear()

    def all(self) -> list[KnowledgeEdge]:
        return list(self._edges.values())


class InMemoryKnowledgeGraphRepository(KnowledgeGraphRepository, GraphSnapshotRepository):
    """Composite in-memory graph with referential integrity and snapshots."""

    def __init__(
        self,
        *,
        schema_version: int = 1,
        validator: KnowledgeGraphValidator | None = None,
    ) -> None:
        self._node_repo = InMemoryKnowledgeNodeRepository()
        self._edge_repo = InMemoryKnowledgeEdgeRepository()
        self._schema_version = schema_version
        self._validator = validator or KnowledgeGraphValidator()

    @property
    def nodes(self) -> KnowledgeNodeRepository:
        return self._node_repo

    @property
    def edges(self) -> KnowledgeEdgeRepository:
        return self._edge_repo

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        cleaned = KnowledgeNode(
            node_id=node.node_id.strip(),
            node_type=node.node_type,
            canonical_key=node.canonical_key.strip(),
            source=node.source.strip(),
            source_id=str(node.source_id).strip(),
            label=node.label.strip(),
            confidence=clamp_confidence(node.confidence),
            data_status=node.data_status,
            created_at=node.created_at,
            updated_at=node.updated_at,
            metadata=sanitize_metadata(dict(node.metadata)),
        )
        self._validator.validate_node(cleaned)
        return self._node_repo.add(cleaned)

    def update_node(self, node: KnowledgeNode) -> KnowledgeNode:
        cleaned = KnowledgeNode(
            node_id=node.node_id.strip(),
            node_type=node.node_type,
            canonical_key=node.canonical_key.strip(),
            source=node.source.strip(),
            source_id=str(node.source_id).strip(),
            label=node.label.strip(),
            confidence=clamp_confidence(node.confidence),
            data_status=node.data_status,
            created_at=node.created_at,
            updated_at=node.updated_at or datetime.now(UTC),
            metadata=sanitize_metadata(dict(node.metadata)),
        )
        self._validator.validate_node(cleaned)
        return self._node_repo.update(cleaned)

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        from_node = self._node_repo.get(edge.from_node_id)
        to_node = self._node_repo.get(edge.to_node_id)
        if from_node is None or to_node is None:
            raise KnowledgeGraphValidationError(
                "Edges cannot reference missing nodes "
                f"(from={edge.from_node_id}, to={edge.to_node_id})."
            )
        cleaned = KnowledgeEdge(
            edge_id=edge.edge_id.strip(),
            edge_type=edge.edge_type,
            from_node_id=edge.from_node_id.strip(),
            to_node_id=edge.to_node_id.strip(),
            confidence=clamp_confidence(edge.confidence),
            source=edge.source.strip(),
            evidence_ids=tuple(str(item) for item in edge.evidence_ids),
            created_at=edge.created_at,
            updated_at=edge.updated_at,
            metadata=sanitize_metadata(dict(edge.metadata)),
        )
        self._validator.validate_edge(
            cleaned,
            from_type=from_node.node_type,
            to_type=to_node.node_type,
        )
        return self._edge_repo.add(cleaned)

    def update_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        from_node = self._node_repo.get(edge.from_node_id)
        to_node = self._node_repo.get(edge.to_node_id)
        if from_node is None or to_node is None:
            raise KnowledgeGraphValidationError("Edges cannot reference missing nodes.")
        cleaned = KnowledgeEdge(
            edge_id=edge.edge_id.strip(),
            edge_type=edge.edge_type,
            from_node_id=edge.from_node_id.strip(),
            to_node_id=edge.to_node_id.strip(),
            confidence=clamp_confidence(edge.confidence),
            source=edge.source.strip(),
            evidence_ids=tuple(str(item) for item in edge.evidence_ids),
            created_at=edge.created_at,
            updated_at=edge.updated_at or datetime.now(UTC),
            metadata=sanitize_metadata(dict(edge.metadata)),
        )
        self._validator.validate_edge(
            cleaned,
            from_type=from_node.node_type,
            to_type=to_node.node_type,
        )
        return self._edge_repo.update(cleaned)

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        return self._node_repo.get(node_id)

    def get_edge(self, edge_id: str) -> KnowledgeEdge | None:
        return self._edge_repo.get(edge_id)

    def remove_node(self, node_id: str) -> bool:
        if not self._node_repo.get(node_id):
            return False
        for edge in list(self._edge_repo.all()):
            if edge.from_node_id == node_id or edge.to_node_id == node_id:
                self._edge_repo.remove(edge.edge_id)
        return self._node_repo.remove(node_id)

    def remove_edge(self, edge_id: str) -> bool:
        return self._edge_repo.remove(edge_id)

    def clear(self) -> None:
        self._edge_repo.clear()
        self._node_repo.clear()

    def export_snapshot(self, *, data_status: str = "mock") -> GraphSnapshot:
        nodes = tuple(sorted(self._node_repo.all(), key=lambda item: item.node_id))
        edges = tuple(sorted(self._edge_repo.all(), key=lambda item: item.edge_id))
        status = data_status if data_status in {"mock", "imported", "live"} else "mock"
        type_counts: dict[str, int] = {}
        for node in nodes:
            type_counts[node.node_type.value] = type_counts.get(node.node_type.value, 0) + 1
        edge_counts: dict[str, int] = {}
        for edge in edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1
        return GraphSnapshot(
            schema_version=self._schema_version,
            nodes=nodes,
            edges=edges,
            created_at=datetime.now(UTC),
            data_status=status,  # type: ignore[arg-type]
            source_summary={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_types": type_counts,
                "edge_types": edge_counts,
            },
        )

    def import_snapshot(self, snapshot: GraphSnapshot | dict[str, Any]) -> GraphSnapshot:
        payload = snapshot.to_dict() if isinstance(snapshot, GraphSnapshot) else dict(snapshot)
        version = payload.get("schema_version")
        if version != self._schema_version:
            raise KnowledgeGraphValidationError(f"Unknown snapshot schema version: {version}")
        nodes_raw = payload.get("nodes")
        edges_raw = payload.get("edges")
        if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
            raise KnowledgeGraphValidationError("Snapshot must include nodes and edges lists.")
        data_status = payload.get("data_status", "mock")
        if data_status not in {"mock", "imported", "live"}:
            raise KnowledgeGraphValidationError(f"Invalid data_status: {data_status}")

        parsed_nodes: list[KnowledgeNode] = []
        seen_node_ids: set[str] = set()
        for raw in nodes_raw:
            if not isinstance(raw, dict):
                raise KnowledgeGraphValidationError("Malformed node in snapshot.")
            node_id = str(raw.get("node_id") or "").strip()
            if not node_id:
                raise KnowledgeGraphValidationError("Snapshot node missing node_id.")
            if node_id in seen_node_ids:
                raise KnowledgeGraphValidationError(f"Duplicate node_id in snapshot: {node_id}")
            seen_node_ids.add(node_id)
            try:
                node_type = NodeType(str(raw.get("node_type") or "").strip().lower())
            except ValueError as exc:
                raise KnowledgeGraphValidationError(
                    f"Unsupported node type in snapshot: {raw.get('node_type')}"
                ) from exc
            parsed_nodes.append(
                KnowledgeNode(
                    node_id=node_id,
                    node_type=node_type,
                    canonical_key=str(raw.get("canonical_key") or "").strip(),
                    source=str(raw.get("source") or "").strip(),
                    source_id=str(raw.get("source_id") or "").strip(),
                    label=str(raw.get("label") or "").strip(),
                    confidence=clamp_confidence(raw.get("confidence", 1.0)),
                    data_status=raw.get("data_status") or data_status,  # type: ignore[arg-type]
                    created_at=self._validator.parse_datetime(raw.get("created_at")),
                    updated_at=self._validator.parse_datetime(raw.get("updated_at")),
                    metadata=sanitize_metadata(dict(raw.get("metadata") or {})),
                )
            )

        parsed_edges: list[KnowledgeEdge] = []
        seen_edge_ids: set[str] = set()
        node_ids = {node.node_id for node in parsed_nodes}
        for raw in edges_raw:
            if not isinstance(raw, dict):
                raise KnowledgeGraphValidationError("Malformed edge in snapshot.")
            edge_id = str(raw.get("edge_id") or "").strip()
            if not edge_id:
                raise KnowledgeGraphValidationError("Snapshot edge missing edge_id.")
            if edge_id in seen_edge_ids:
                raise KnowledgeGraphValidationError(f"Duplicate edge_id in snapshot: {edge_id}")
            seen_edge_ids.add(edge_id)
            from_id = str(raw.get("from_node_id") or "").strip()
            to_id = str(raw.get("to_node_id") or "").strip()
            if from_id not in node_ids or to_id not in node_ids:
                raise KnowledgeGraphValidationError(
                    f"Invalid edge endpoints in snapshot: {edge_id}"
                )
            try:
                edge_type = EdgeType(str(raw.get("edge_type") or "").strip().upper())
            except ValueError as exc:
                raise KnowledgeGraphValidationError(
                    f"Unsupported edge type in snapshot: {raw.get('edge_type')}"
                ) from exc
            evidence_ids = raw.get("evidence_ids") or []
            if not isinstance(evidence_ids, list):
                raise KnowledgeGraphValidationError("evidence_ids must be a list.")
            parsed_edges.append(
                KnowledgeEdge(
                    edge_id=edge_id,
                    edge_type=edge_type,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    confidence=clamp_confidence(raw.get("confidence", 1.0)),
                    source=str(raw.get("source") or "snapshot").strip(),
                    evidence_ids=tuple(str(item) for item in evidence_ids),
                    created_at=self._validator.parse_datetime(raw.get("created_at")),
                    updated_at=self._validator.parse_datetime(raw.get("updated_at")),
                    metadata=sanitize_metadata(dict(raw.get("metadata") or {})),
                )
            )

        self.clear()
        for node in parsed_nodes:
            self.add_node(node)
        for edge in parsed_edges:
            self.add_edge(edge)
        created_at = self._validator.parse_datetime(payload.get("created_at")) or datetime.now(UTC)
        return GraphSnapshot(
            schema_version=self._schema_version,
            nodes=tuple(parsed_nodes),
            edges=tuple(parsed_edges),
            created_at=created_at,
            data_status=data_status,  # type: ignore[arg-type]
            source_summary=dict(payload.get("source_summary") or {}),
        )
