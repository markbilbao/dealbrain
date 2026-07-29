"""Knowledge Graph engine: bounded traversal, path finding, and mutations."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphExplanation,
    GraphLimits,
    GraphPath,
    GraphSubgraph,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.exceptions import (
    KnowledgeGraphNotFoundError,
    KnowledgeGraphValidationError,
)
from app.domain.interfaces.knowledge_graph_repository import KnowledgeGraphRepository
from app.intelligence.knowledge_graph.canonicalization import NodeCanonicalizationService
from app.intelligence.knowledge_graph.confidence import confidence_band, path_confidence
from app.intelligence.knowledge_graph.deduplication import (
    EdgeDeduplicationService,
    NodeDeduplicationService,
)
from app.intelligence.knowledge_graph.registry import (
    DEFAULT_RELATIONSHIP_REGISTRY,
    RelationshipRegistry,
)
from app.intelligence.knowledge_graph.validator import (
    KnowledgeGraphValidator,
    clamp_confidence,
    sanitize_metadata,
)


class KnowledgeGraphEngine:
    """Core graph operations with deterministic bounded BFS traversal."""

    def __init__(
        self,
        repository: KnowledgeGraphRepository,
        *,
        registry: RelationshipRegistry | None = None,
        limits: GraphLimits | None = None,
        canonicalization: NodeCanonicalizationService | None = None,
    ) -> None:
        self._repo = repository
        self._registry = registry or DEFAULT_RELATIONSHIP_REGISTRY
        self._limits = limits or GraphLimits()
        self._canonical = canonicalization or NodeCanonicalizationService()
        self._validator = KnowledgeGraphValidator(self._registry)
        self._node_dedup = NodeDeduplicationService(repository, canonicalization=self._canonical)
        self._edge_dedup = EdgeDeduplicationService(
            repository, registry=self._registry, canonicalization=self._canonical
        )

    @property
    def repository(self) -> KnowledgeGraphRepository:
        return self._repo

    @property
    def limits(self) -> GraphLimits:
        return self._limits

    def effective_limits(
        self,
        *,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        max_edges: int | None = None,
        max_paths: int | None = None,
        min_confidence: float | None = None,
    ) -> GraphLimits:
        """Clamp client-requested limits to server ceilings."""
        return GraphLimits(
            max_depth=min(max_depth or self._limits.max_depth, self._limits.max_depth),
            max_nodes=min(max_nodes or self._limits.max_nodes, self._limits.max_nodes),
            max_edges=min(max_edges or self._limits.max_edges, self._limits.max_edges),
            max_paths=min(max_paths or self._limits.max_paths, self._limits.max_paths),
            min_confidence=max(
                min_confidence if min_confidence is not None else self._limits.min_confidence,
                self._limits.min_confidence,
            ),
        )

    def create_node(
        self,
        *,
        node_type: NodeType | str,
        source: str,
        source_id: str,
        label: str,
        confidence: float = 1.0,
        data_status: str = "mock",
        metadata: dict[str, Any] | None = None,
        node_id: str | None = None,
        canonical_key: str | None = None,
        brand: str | None = None,
        marketplace: str | None = None,
        category: str | None = None,
    ) -> KnowledgeNode:
        resolved_type = self._registry.resolve_node_type(node_type)
        key = canonical_key or self._canonical.canonical_key(
            resolved_type,
            source=source,
            source_id=source_id,
            label=label,
            brand=brand,
            marketplace=marketplace,
            category=category,
        )
        nid = node_id or self._canonical.deterministic_node_id(resolved_type, key)
        now = datetime.now(UTC)
        node = KnowledgeNode(
            node_id=nid,
            node_type=resolved_type,
            canonical_key=key,
            source=source,
            source_id=source_id,
            label=label,
            confidence=clamp_confidence(confidence),
            data_status=data_status,  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            metadata=sanitize_metadata(metadata or {}),
        )
        created, _ = self._node_dedup.upsert(node)
        return created

    def create_edge(
        self,
        *,
        edge_type: EdgeType | str,
        from_node_id: str,
        to_node_id: str,
        confidence: float = 1.0,
        source: str = "knowledge_graph",
        evidence_ids: Iterable[str] | None = None,
        metadata: dict[str, Any] | None = None,
        edge_id: str | None = None,
    ) -> KnowledgeEdge:
        resolved_type = self._registry.resolve_edge_type(edge_type)
        from_node = self._repo.get_node(from_node_id)
        to_node = self._repo.get_node(to_node_id)
        if from_node is None or to_node is None:
            raise KnowledgeGraphValidationError(
                "Cannot create edge: one or both nodes are missing."
            )
        self._registry.validate_endpoints(resolved_type, from_node.node_type, to_node.node_type)
        eid = edge_id or self._canonical.deterministic_edge_id(
            resolved_type.value, from_node_id, to_node_id
        )
        now = datetime.now(UTC)
        edge = KnowledgeEdge(
            edge_id=eid,
            edge_type=resolved_type,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            confidence=clamp_confidence(confidence),
            source=source,
            evidence_ids=tuple(evidence_ids or ()),
            created_at=now,
            updated_at=now,
            metadata=sanitize_metadata(metadata or {}),
        )
        created, _ = self._edge_dedup.upsert(edge)
        return created

    def get_node(self, node_id: str) -> KnowledgeNode:
        node = self._repo.get_node(node_id)
        if node is None:
            raise KnowledgeGraphNotFoundError(node_id)
        return node

    def neighbors(
        self,
        node_id: str,
        *,
        direction: str = "both",
        edge_types: Iterable[str] | None = None,
        min_confidence: float | None = None,
        max_nodes: int | None = None,
    ) -> GraphSubgraph:
        root = self.get_node(node_id)
        limits = self.effective_limits(max_nodes=max_nodes, min_confidence=min_confidence)
        allowed = self._resolve_edge_filter(edge_types)
        edges: list[KnowledgeEdge] = []
        if direction in {"outgoing", "both"}:
            edges.extend(self._repo.edges.list_outgoing(node_id))
        if direction in {"incoming", "both"}:
            edges.extend(self._repo.edges.list_incoming(node_id))

        filtered: list[KnowledgeEdge] = []
        seen_edge_ids: set[str] = set()
        for edge in edges:
            if edge.edge_id in seen_edge_ids:
                continue
            if allowed is not None and edge.edge_type not in allowed:
                continue
            if edge.confidence < limits.min_confidence:
                continue
            seen_edge_ids.add(edge.edge_id)
            filtered.append(edge)

        truncated = False
        if len(filtered) > limits.max_edges:
            filtered = filtered[: limits.max_edges]
            truncated = True

        nodes = {root.node_id: root}
        for edge in filtered:
            for nid in (edge.from_node_id, edge.to_node_id):
                if nid not in nodes:
                    neighbor = self._repo.get_node(nid)
                    if neighbor is not None:
                        nodes[nid] = neighbor
                if len(nodes) >= limits.max_nodes:
                    truncated = True
                    break
            if truncated and len(nodes) >= limits.max_nodes:
                break

        return GraphSubgraph(
            root_node=root,
            nodes=tuple(nodes.values()),
            edges=tuple(filtered),
            warnings=("Neighbor listing truncated by server limits.",) if truncated else (),
            data_status=root.data_status,
            truncated=truncated,
            limits=limits,
        )

    def traverse(
        self,
        root_node_id: str,
        *,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        max_edges: int | None = None,
        edge_types: Iterable[str] | None = None,
        node_types: Iterable[str] | None = None,
        min_confidence: float | None = None,
    ) -> GraphSubgraph:
        root = self.get_node(root_node_id)
        limits = self.effective_limits(
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
            min_confidence=min_confidence,
        )
        allowed_edges = self._resolve_edge_filter(edge_types)
        allowed_nodes = self._resolve_node_filter(node_types)

        nodes: dict[str, KnowledgeNode] = {root.node_id: root}
        edges: dict[str, KnowledgeEdge] = {}
        truncated = False
        queue: deque[tuple[str, int]] = deque([(root.node_id, 0)])
        visited: set[str] = {root.node_id}

        while queue:
            current_id, depth = queue.popleft()
            if depth >= limits.max_depth:
                continue
            incident = [
                *self._repo.edges.list_outgoing(current_id),
                *self._repo.edges.list_incoming(current_id),
            ]
            for edge in incident:
                if edge.edge_id in edges:
                    continue
                if allowed_edges is not None and edge.edge_type not in allowed_edges:
                    continue
                if edge.confidence < limits.min_confidence:
                    continue
                if len(edges) >= limits.max_edges:
                    truncated = True
                    break
                edges[edge.edge_id] = edge
                next_id = edge.to_node_id if edge.from_node_id == current_id else edge.from_node_id
                if next_id in visited:
                    continue
                neighbor = self._repo.get_node(next_id)
                if neighbor is None:
                    continue
                if allowed_nodes is not None and neighbor.node_type not in allowed_nodes:
                    continue
                if len(nodes) >= limits.max_nodes:
                    truncated = True
                    continue
                nodes[next_id] = neighbor
                visited.add(next_id)
                queue.append((next_id, depth + 1))
            if truncated and len(nodes) >= limits.max_nodes and len(edges) >= limits.max_edges:
                break

        warnings: list[str] = []
        if truncated:
            warnings.append("Traversal truncated by server limits.")
        return GraphSubgraph(
            root_node=root,
            nodes=tuple(nodes.values()),
            edges=tuple(edges.values()),
            warnings=tuple(warnings),
            data_status=root.data_status,
            truncated=truncated,
            limits=limits,
            summary=self._summarize(nodes.values(), edges.values()),
        )

    def find_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        max_depth: int | None = None,
        max_paths: int | None = None,
        edge_types: Iterable[str] | None = None,
        min_confidence: float | None = None,
    ) -> list[GraphPath]:
        self.get_node(from_node_id)
        self.get_node(to_node_id)
        limits = self.effective_limits(
            max_depth=max_depth,
            max_paths=max_paths,
            min_confidence=min_confidence,
        )
        allowed_edges = self._resolve_edge_filter(edge_types)

        paths: list[GraphPath] = []
        queue: deque[tuple[str, list[str], list[str], set[str]]] = deque(
            [(from_node_id, [from_node_id], [], {from_node_id})]
        )

        while queue and len(paths) < limits.max_paths:
            current, node_path, edge_path, visited = queue.popleft()
            if len(node_path) - 1 > limits.max_depth:
                continue
            if current == to_node_id and edge_path:
                edges = [self._repo.get_edge(eid) for eid in edge_path]
                concrete = [edge for edge in edges if edge is not None]
                score = path_confidence(concrete)
                if score < limits.min_confidence:
                    continue
                evidence: list[str] = []
                for edge in concrete:
                    evidence.extend(edge.evidence_ids)
                paths.append(
                    GraphPath(
                        node_ids=tuple(node_path),
                        edge_ids=tuple(edge_path),
                        confidence=score,
                        confidence_band=confidence_band(score),
                        evidence_ids=tuple(dict.fromkeys(evidence)),
                    )
                )
                continue
            if len(node_path) - 1 >= limits.max_depth:
                continue
            for edge in [
                *self._repo.edges.list_outgoing(current),
                *self._repo.edges.list_incoming(current),
            ]:
                if allowed_edges is not None and edge.edge_type not in allowed_edges:
                    continue
                if edge.confidence < limits.min_confidence:
                    continue
                next_id = edge.to_node_id if edge.from_node_id == current else edge.from_node_id
                if next_id in visited:
                    continue
                queue.append(
                    (
                        next_id,
                        [*node_path, next_id],
                        [*edge_path, edge.edge_id],
                        visited | {next_id},
                    )
                )

        paths.sort(key=lambda item: (-item.confidence, len(item.edge_ids), item.edge_ids))
        return paths[: limits.max_paths]

    def shortest_evidence_path(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        max_depth: int | None = None,
        edge_types: Iterable[str] | None = None,
        min_confidence: float | None = None,
    ) -> GraphPath | None:
        paths = self.find_paths(
            from_node_id,
            to_node_id,
            max_depth=max_depth,
            max_paths=1,
            edge_types=edge_types,
            min_confidence=min_confidence,
        )
        return paths[0] if paths else None

    def explain_connection(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        claim: str | None = None,
        max_depth: int | None = None,
        max_paths: int | None = None,
        edge_types: Iterable[str] | None = None,
        min_confidence: float | None = None,
    ) -> GraphExplanation:
        from_node = self.get_node(from_node_id)
        to_node = self.get_node(to_node_id)
        paths = self.find_paths(
            from_node_id,
            to_node_id,
            max_depth=max_depth,
            max_paths=max_paths,
            edge_types=edge_types,
            min_confidence=min_confidence,
        )
        claim_text = claim or f"{from_node.label} is connected to {to_node.label}"
        limitations = [
            "Graph relationships are only as reliable as their source evidence.",
            "Traversal does not prove causation.",
            "Most current data is fixture, mock, or imported.",
        ]
        if not paths:
            return GraphExplanation(
                claim=claim_text,
                supported=False,
                confidence=0.0,
                confidence_band="low",
                paths=(),
                contradictions=(),
                limitations=tuple(limitations),
            )
        best = paths[0]
        contradictions = self._collect_contradictions(from_node_id, to_node_id)
        return GraphExplanation(
            claim=claim_text,
            supported=True,
            confidence=best.confidence,
            confidence_band=best.confidence_band,
            paths=tuple(paths),
            contradictions=tuple(contradictions),
            limitations=tuple(limitations),
        )

    def _collect_contradictions(self, from_node_id: str, to_node_id: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for node_id in (from_node_id, to_node_id):
            for edge in self._repo.edges.list_outgoing(node_id):
                if edge.edge_type == EdgeType.CONTRADICTS:
                    found.append(
                        {
                            "edge_id": edge.edge_id,
                            "from_node_id": edge.from_node_id,
                            "to_node_id": edge.to_node_id,
                            "confidence": edge.confidence,
                            "evidence_ids": list(edge.evidence_ids),
                        }
                    )
        return found

    def _resolve_edge_filter(self, edge_types: Iterable[str] | None) -> set[EdgeType] | None:
        if edge_types is None:
            return None
        resolved = {self._registry.resolve_edge_type(item) for item in edge_types}
        return resolved

    def _resolve_node_filter(self, node_types: Iterable[str] | None) -> set[NodeType] | None:
        if node_types is None:
            return None
        return {self._registry.resolve_node_type(item) for item in node_types}

    @staticmethod
    def _summarize(
        nodes: Iterable[KnowledgeNode], edges: Iterable[KnowledgeEdge]
    ) -> dict[str, Any]:
        node_counts: dict[str, int] = {}
        for node in nodes:
            node_counts[node.node_type.value] = node_counts.get(node.node_type.value, 0) + 1
        edge_counts: dict[str, int] = {}
        for edge in edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1
        return {"node_counts": node_counts, "edge_counts": edge_counts}
