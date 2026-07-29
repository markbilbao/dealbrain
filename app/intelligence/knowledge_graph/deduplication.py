"""Idempotent node and edge deduplication for the Knowledge Graph."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.domain.entities.knowledge_graph import (
    SYMMETRIC_EDGE_TYPES,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.interfaces.knowledge_graph_repository import KnowledgeGraphRepository
from app.intelligence.knowledge_graph.canonicalization import NodeCanonicalizationService
from app.intelligence.knowledge_graph.registry import (
    DEFAULT_RELATIONSHIP_REGISTRY,
    RelationshipRegistry,
)
from app.intelligence.knowledge_graph.validator import sanitize_metadata


class NodeDeduplicationService:
    """Merge nodes by canonical key; repeated ingestion is idempotent."""

    def __init__(
        self,
        repository: KnowledgeGraphRepository,
        *,
        canonicalization: NodeCanonicalizationService | None = None,
    ) -> None:
        self._repo = repository
        self._canonical = canonicalization or NodeCanonicalizationService()

    def upsert(self, node: KnowledgeNode) -> tuple[KnowledgeNode, bool]:
        """Insert or update by canonical key. Returns (node, created)."""
        existing = self._repo.nodes.find_by_canonical_key(node.canonical_key)
        if existing is None:
            existing = self._repo.get_node(node.node_id)

        if existing is None:
            created = self._repo.add_node(node)
            return created, True

        merged_meta = {**dict(existing.metadata), **dict(node.metadata)}
        updated = KnowledgeNode(
            node_id=existing.node_id,
            node_type=existing.node_type,
            canonical_key=existing.canonical_key,
            # Preserve the first-seen identity (source/source_id) so external callers
            # can keep resolving this node by its original ID even after later
            # cross-marketplace mirrors merge into it (see IdentityResolutionService).
            source=existing.source or node.source,
            source_id=existing.source_id or node.source_id,
            label=node.label or existing.label,
            confidence=max(existing.confidence, node.confidence),
            data_status=node.data_status or existing.data_status,
            created_at=existing.created_at,
            updated_at=datetime.now(UTC),
            metadata=sanitize_metadata(merged_meta),
        )
        return self._repo.update_node(updated), False


class EdgeDeduplicationService:
    """Prevent duplicate and reverse-symmetric edges."""

    def __init__(
        self,
        repository: KnowledgeGraphRepository,
        *,
        registry: RelationshipRegistry | None = None,
        canonicalization: NodeCanonicalizationService | None = None,
    ) -> None:
        self._repo = repository
        self._registry = registry or DEFAULT_RELATIONSHIP_REGISTRY
        self._canonical = canonicalization or NodeCanonicalizationService()

    def upsert(self, edge: KnowledgeEdge) -> tuple[KnowledgeEdge, bool]:
        """Insert edge or return existing equivalent. Returns (edge, created)."""
        existing = self._find_equivalent(edge)
        if existing is not None:
            merged_evidence = tuple(dict.fromkeys([*existing.evidence_ids, *edge.evidence_ids]))
            updated = KnowledgeEdge(
                edge_id=existing.edge_id,
                edge_type=existing.edge_type,
                from_node_id=existing.from_node_id,
                to_node_id=existing.to_node_id,
                confidence=max(existing.confidence, edge.confidence),
                source=edge.source or existing.source,
                evidence_ids=merged_evidence,
                created_at=existing.created_at,
                updated_at=datetime.now(UTC),
                metadata=sanitize_metadata({**dict(existing.metadata), **dict(edge.metadata)}),
            )
            return self._repo.update_edge(updated), False
        created = self._repo.add_edge(edge)
        return created, True

    def _find_equivalent(self, edge: KnowledgeEdge) -> KnowledgeEdge | None:
        for candidate in self._repo.edges.list_outgoing(edge.from_node_id):
            if candidate.edge_type == edge.edge_type and candidate.to_node_id == edge.to_node_id:
                return candidate
        if edge.edge_type in SYMMETRIC_EDGE_TYPES or self._registry.is_symmetric(edge.edge_type):
            for candidate in self._repo.edges.list_outgoing(edge.to_node_id):
                if (
                    candidate.edge_type == edge.edge_type
                    and candidate.to_node_id == edge.from_node_id
                ):
                    return candidate
        return self._repo.get_edge(edge.edge_id)


class IdentityResolutionService:
    """Resolve marketplace-specific product identities to canonical nodes."""

    def __init__(
        self,
        repository: KnowledgeGraphRepository,
        *,
        canonicalization: NodeCanonicalizationService | None = None,
        deduplicator: NodeDeduplicationService | None = None,
    ) -> None:
        self._repo = repository
        self._canonical = canonicalization or NodeCanonicalizationService()
        self._dedup = deduplicator or NodeDeduplicationService(
            repository, canonicalization=self._canonical
        )

    def resolve_product(
        self,
        *,
        label: str,
        brand: str | None = None,
        source: str,
        source_id: str,
        marketplace: str | None = None,
        confidence: float = 0.9,
        data_status: str = "mock",
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeNode:
        key = self._canonical.canonical_key(
            NodeType.PRODUCT,
            source=source,
            source_id=source_id,
            label=label,
            brand=brand,
            marketplace=marketplace,
        )
        node_id = self._canonical.deterministic_node_id(NodeType.PRODUCT, key)
        now = datetime.now(UTC)
        node = KnowledgeNode(
            node_id=node_id,
            node_type=NodeType.PRODUCT,
            canonical_key=key,
            source=source,
            source_id=source_id,
            label=label,
            confidence=confidence,
            data_status=data_status,  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            metadata=sanitize_metadata(
                {
                    **(metadata or {}),
                    "marketplace": marketplace,
                    "brand": brand,
                }
            ),
        )
        resolved, _ = self._dedup.upsert(node)
        return resolved
