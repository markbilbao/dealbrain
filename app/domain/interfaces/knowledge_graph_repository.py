"""Knowledge Graph repository ports (storage-neutral).

In-memory implementations satisfy v1. Persistent graph databases can be
swapped in later without changing domain or service contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphSnapshot,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)


class KnowledgeNodeRepository(ABC):
    """Port for knowledge node persistence."""

    @abstractmethod
    def add(self, node: KnowledgeNode) -> KnowledgeNode:
        """Insert a node. Raises on duplicate ID."""

    @abstractmethod
    def update(self, node: KnowledgeNode) -> KnowledgeNode:
        """Replace an existing node by ID."""

    @abstractmethod
    def get(self, node_id: str) -> KnowledgeNode | None:
        """Fetch a node by ID."""

    @abstractmethod
    def find_by_canonical_key(self, canonical_key: str) -> KnowledgeNode | None:
        """Fetch the first node matching a canonical key."""

    @abstractmethod
    def list_by_type(self, node_type: NodeType) -> list[KnowledgeNode]:
        """List all nodes of a given type."""

    @abstractmethod
    def remove(self, node_id: str) -> bool:
        """Remove a node by ID. Returns True if removed."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all nodes."""

    @abstractmethod
    def all(self) -> list[KnowledgeNode]:
        """Return all nodes."""


class KnowledgeEdgeRepository(ABC):
    """Port for knowledge edge persistence."""

    @abstractmethod
    def add(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Insert an edge. Raises on duplicate ID."""

    @abstractmethod
    def update(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Replace an existing edge by ID."""

    @abstractmethod
    def get(self, edge_id: str) -> KnowledgeEdge | None:
        """Fetch an edge by ID."""

    @abstractmethod
    def list_outgoing(self, node_id: str) -> list[KnowledgeEdge]:
        """List edges leaving a node."""

    @abstractmethod
    def list_incoming(self, node_id: str) -> list[KnowledgeEdge]:
        """List edges entering a node."""

    @abstractmethod
    def list_by_type(self, edge_type: EdgeType) -> list[KnowledgeEdge]:
        """List edges of a given relationship type."""

    @abstractmethod
    def remove(self, edge_id: str) -> bool:
        """Remove an edge by ID. Returns True if removed."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all edges."""

    @abstractmethod
    def all(self) -> list[KnowledgeEdge]:
        """Return all edges."""


class KnowledgeGraphRepository(ABC):
    """Composite graph repository with referential integrity."""

    @property
    @abstractmethod
    def nodes(self) -> KnowledgeNodeRepository:
        """Node repository."""

    @property
    @abstractmethod
    def edges(self) -> KnowledgeEdgeRepository:
        """Edge repository."""

    @abstractmethod
    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Add a node."""

    @abstractmethod
    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Add an edge; both endpoints must exist."""

    @abstractmethod
    def update_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Update a node."""

    @abstractmethod
    def update_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Update an edge; endpoints must exist."""

    @abstractmethod
    def get_node(self, node_id: str) -> KnowledgeNode | None:
        """Get a node."""

    @abstractmethod
    def get_edge(self, edge_id: str) -> KnowledgeEdge | None:
        """Get an edge."""

    @abstractmethod
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its incident edges."""

    @abstractmethod
    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge."""

    @abstractmethod
    def clear(self) -> None:
        """Clear the entire fixture graph."""


class GraphSnapshotRepository(ABC):
    """Port for exporting and importing deterministic graph snapshots."""

    @abstractmethod
    def export_snapshot(self, *, data_status: str = "mock") -> GraphSnapshot:
        """Export the current graph as a snapshot."""

    @abstractmethod
    def import_snapshot(self, snapshot: GraphSnapshot | dict) -> GraphSnapshot:
        """Validate and import a snapshot, replacing current graph contents."""
