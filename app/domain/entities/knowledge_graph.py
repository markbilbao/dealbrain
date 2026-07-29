"""Knowledge Graph domain entities and value objects.

Provider-neutral, storage-neutral graph model for connecting DealBrain
evidence across products, sellers, reviews, community, prices, and more.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Literal

DataStatus = Literal["mock", "imported", "live"]
ConfidenceBand = Literal["high", "medium", "low"]


class NodeType(StrEnum):
    """Supported knowledge graph node types."""

    PRODUCT = "product"
    SELLER = "seller"
    REVIEW = "review"
    COMMUNITY_EVIDENCE = "community_evidence"
    PRICE_OBSERVATION = "price_observation"
    PRICE_HISTORY = "price_history"
    MARKETPLACE = "marketplace"
    BRAND = "brand"
    CATEGORY = "category"
    TOPIC = "topic"
    EVIDENCE = "evidence"
    AI_SUMMARY = "ai_summary"
    VIDEO = "video"
    ACCESSORY = "accessory"
    COMPATIBILITY = "compatibility"


class EdgeType(StrEnum):
    """Supported knowledge graph relationship types."""

    SOLD_BY = "SOLD_BY"
    OFFERED_ON = "OFFERED_ON"
    HAS_PRICE = "HAS_PRICE"
    HAS_PRICE_HISTORY = "HAS_PRICE_HISTORY"
    HAS_REVIEW = "HAS_REVIEW"
    DISCUSSED_IN = "DISCUSSED_IN"
    HAS_COMMUNITY_EVIDENCE = "HAS_COMMUNITY_EVIDENCE"
    HAS_AI_SUMMARY = "HAS_AI_SUMMARY"
    MADE_BY = "MADE_BY"
    BELONGS_TO_CATEGORY = "BELONGS_TO_CATEGORY"
    HAS_TOPIC = "HAS_TOPIC"
    SIMILAR_TO = "SIMILAR_TO"
    COMPARES_WITH = "COMPARES_WITH"
    ACCESSORY_OF = "ACCESSORY_OF"
    RECOMMENDED_WITH = "RECOMMENDED_WITH"
    COMPATIBLE_WITH = "COMPATIBLE_WITH"
    HAS_WARNING = "HAS_WARNING"
    HAS_EVIDENCE = "HAS_EVIDENCE"
    SUPPORTED_BY = "SUPPORTED_BY"
    CONTRADICTS = "CONTRADICTS"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"


# Symmetric edge types: reverse duplicates are rejected unless explicitly allowed.
SYMMETRIC_EDGE_TYPES: frozenset[EdgeType] = frozenset(
    {
        EdgeType.SIMILAR_TO,
        EdgeType.COMPARES_WITH,
        EdgeType.COMPATIBLE_WITH,
        EdgeType.ALTERNATIVE_TO,
    }
)


@dataclass(frozen=True, slots=True)
class KnowledgeNode:
    """Normalized knowledge graph node."""

    node_id: str
    node_type: NodeType
    canonical_key: str
    source: str
    source_id: str
    label: str
    confidence: float = 1.0
    data_status: DataStatus = "mock"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "canonical_key": self.canonical_key,
            "source": self.source,
            "source_id": self.source_id,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "data_status": self.data_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class KnowledgeEdge:
    """Normalized knowledge graph edge with evidence tracing."""

    edge_id: str
    edge_type: EdgeType
    from_node_id: str
    to_node_id: str
    confidence: float = 1.0
    source: str = "knowledge_graph"
    evidence_ids: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "evidence_ids", tuple(self.evidence_ids))

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "edge_type": self.edge_type.value,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "evidence_ids": list(self.evidence_ids),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class GraphPath:
    """Ordered path through the knowledge graph."""

    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    confidence: float
    confidence_band: ConfidenceBand
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_ids": list(self.node_ids),
            "edge_ids": list(self.edge_ids),
            "confidence": round(self.confidence, 4),
            "confidence_band": self.confidence_band,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class GraphLimits:
    """Server-enforced traversal and output bounds."""

    max_depth: int = 3
    max_nodes: int = 100
    max_edges: int = 200
    max_paths: int = 20
    min_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
            "max_edges": self.max_edges,
            "max_paths": self.max_paths,
            "min_confidence": self.min_confidence,
        }


@dataclass(frozen=True, slots=True)
class GraphSubgraph:
    """Bounded subgraph response with evidence paths and warnings."""

    root_node: KnowledgeNode | None
    nodes: tuple[KnowledgeNode, ...]
    edges: tuple[KnowledgeEdge, ...]
    evidence_paths: tuple[GraphPath, ...] = ()
    warnings: tuple[str, ...] = ()
    data_status: DataStatus = "mock"
    truncated: bool = False
    limits: GraphLimits = field(default_factory=GraphLimits)
    contradictions: tuple[dict[str, Any], ...] = ()
    summary: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", MappingProxyType(dict(self.summary)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_node": self.root_node.to_dict() if self.root_node else None,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "evidence_paths": [path.to_dict() for path in self.evidence_paths],
            "warnings": list(self.warnings),
            "data_status": self.data_status,
            "truncated": self.truncated,
            "limits": self.limits.to_dict(),
            "contradictions": list(self.contradictions),
            "summary": dict(self.summary),
        }


@dataclass(frozen=True, slots=True)
class GraphExplanation:
    """Evidence-grounded explanation of a graph claim."""

    claim: str
    supported: bool
    confidence: float
    confidence_band: ConfidenceBand
    paths: tuple[GraphPath, ...] = ()
    contradictions: tuple[dict[str, Any], ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "supported": self.supported,
            "confidence": round(self.confidence, 4),
            "confidence_band": self.confidence_band,
            "paths": [path.to_dict() for path in self.paths],
            "contradictions": list(self.contradictions),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    """Deterministic exportable graph snapshot for tests and demos."""

    schema_version: int
    nodes: tuple[KnowledgeNode, ...]
    edges: tuple[KnowledgeEdge, ...]
    created_at: datetime
    data_status: DataStatus
    source_summary: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_summary", MappingProxyType(dict(self.source_summary)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "created_at": self.created_at.isoformat(),
            "data_status": self.data_status,
            "source_summary": dict(self.source_summary),
        }
