"""Knowledge Graph API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphLimitsPayload(BaseModel):
    max_depth: int = 3
    max_nodes: int = 100
    max_edges: int = 200
    max_paths: int = 20
    min_confidence: float = 0.0


class KnowledgeNodePayload(BaseModel):
    node_id: str
    node_type: str
    canonical_key: str
    source: str
    source_id: str
    label: str
    confidence: float = 1.0
    data_status: str = "mock"
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgePayload(BaseModel):
    edge_id: str
    edge_type: str
    from_node_id: str
    to_node_id: str
    confidence: float = 1.0
    source: str = "knowledge_graph"
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphPathPayload(BaseModel):
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_band: str = "low"
    evidence_ids: list[str] = Field(default_factory=list)


class GraphSubgraphResponse(BaseModel):
    root_node: KnowledgeNodePayload | None = None
    nodes: list[KnowledgeNodePayload] = Field(default_factory=list)
    edges: list[KnowledgeEdgePayload] = Field(default_factory=list)
    evidence_paths: list[GraphPathPayload] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_status: str = "mock"
    truncated: bool = False
    limits: GraphLimitsPayload = Field(default_factory=GraphLimitsPayload)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class GraphPathResponse(BaseModel):
    from_node_id: str
    to_node_id: str
    paths: list[GraphPathPayload] = Field(default_factory=list)
    truncated: bool = False
    limits: GraphLimitsPayload = Field(default_factory=GraphLimitsPayload)
    data_status: str = "mock"


class GraphExplanationResponse(BaseModel):
    claim: str
    supported: bool
    confidence: float
    confidence_band: str
    paths: list[GraphPathPayload] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class GraphRelationshipsResponse(BaseModel):
    node: KnowledgeNodePayload
    outgoing: list[KnowledgeEdgePayload] = Field(default_factory=list)
    incoming: list[KnowledgeEdgePayload] = Field(default_factory=list)
    data_status: str = "mock"


class GraphEvidenceResponse(BaseModel):
    node_id: str
    root: KnowledgeNodePayload | None = None
    evidence_nodes: list[KnowledgeNodePayload] = Field(default_factory=list)
    evidence_edges: list[KnowledgeEdgePayload] = Field(default_factory=list)
    stale: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_status: str = "mock"


class GraphMetaResponse(BaseModel):
    enabled: bool = True
    demo_product_id: str
    demo_product_name: str
    data_status: str = "mock"
    external_graph_database: bool = False
    limits: GraphLimitsPayload = Field(default_factory=GraphLimitsPayload)
    node_types: list[str] = Field(default_factory=list)
    edge_types: list[str] = Field(default_factory=list)
    confidence_method: str = "minimum_edge_confidence"
