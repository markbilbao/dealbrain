"""Map Knowledge Graph domain objects to API schemas."""

from __future__ import annotations

from typing import Any

from app.domain.entities.knowledge_graph import (
    GraphExplanation,
    GraphSubgraph,
    KnowledgeEdge,
    KnowledgeNode,
)
from app.schemas.knowledge_graph import (
    GraphEvidenceResponse,
    GraphExplanationResponse,
    GraphLimitsPayload,
    GraphPathPayload,
    GraphPathResponse,
    GraphRelationshipsResponse,
    GraphSubgraphResponse,
    KnowledgeEdgePayload,
    KnowledgeNodePayload,
)


def to_node_payload(node: KnowledgeNode | dict[str, Any]) -> KnowledgeNodePayload:
    data = node.to_dict() if isinstance(node, KnowledgeNode) else dict(node)
    return KnowledgeNodePayload(**data)


def to_edge_payload(edge: KnowledgeEdge | dict[str, Any]) -> KnowledgeEdgePayload:
    data = edge.to_dict() if isinstance(edge, KnowledgeEdge) else dict(edge)
    return KnowledgeEdgePayload(**data)


def to_subgraph_response(subgraph: GraphSubgraph) -> GraphSubgraphResponse:
    payload = subgraph.to_dict()
    return GraphSubgraphResponse(
        root_node=to_node_payload(payload["root_node"]) if payload.get("root_node") else None,
        nodes=[to_node_payload(item) for item in payload.get("nodes") or []],
        edges=[to_edge_payload(item) for item in payload.get("edges") or []],
        evidence_paths=[GraphPathPayload(**item) for item in payload.get("evidence_paths") or []],
        warnings=list(payload.get("warnings") or []),
        data_status=payload.get("data_status") or "mock",
        truncated=bool(payload.get("truncated")),
        limits=GraphLimitsPayload(**(payload.get("limits") or {})),
        contradictions=list(payload.get("contradictions") or []),
        summary=dict(payload.get("summary") or {}),
    )


def to_path_response(payload: dict[str, Any]) -> GraphPathResponse:
    return GraphPathResponse(
        from_node_id=payload["from_node_id"],
        to_node_id=payload["to_node_id"],
        paths=[GraphPathPayload(**item) for item in payload.get("paths") or []],
        truncated=bool(payload.get("truncated")),
        limits=GraphLimitsPayload(**(payload.get("limits") or {})),
        data_status=payload.get("data_status") or "mock",
    )


def to_explanation_response(explanation: GraphExplanation) -> GraphExplanationResponse:
    payload = explanation.to_dict()
    return GraphExplanationResponse(
        claim=payload["claim"],
        supported=payload["supported"],
        confidence=payload["confidence"],
        confidence_band=payload["confidence_band"],
        paths=[GraphPathPayload(**item) for item in payload.get("paths") or []],
        contradictions=list(payload.get("contradictions") or []),
        limitations=list(payload.get("limitations") or []),
    )


def to_relationships_response(payload: dict[str, Any]) -> GraphRelationshipsResponse:
    return GraphRelationshipsResponse(
        node=to_node_payload(payload["node"]),
        outgoing=[to_edge_payload(item) for item in payload.get("outgoing") or []],
        incoming=[to_edge_payload(item) for item in payload.get("incoming") or []],
        data_status=payload.get("data_status") or "mock",
    )


def to_evidence_response(payload: dict[str, Any]) -> GraphEvidenceResponse:
    root = payload.get("root")
    return GraphEvidenceResponse(
        node_id=payload["node_id"],
        root=to_node_payload(root) if root else None,
        evidence_nodes=[to_node_payload(item) for item in payload.get("evidence_nodes") or []],
        evidence_edges=[to_edge_payload(item) for item in payload.get("evidence_edges") or []],
        stale=list(payload.get("stale") or []),
        contradictions=list(payload.get("contradictions") or []),
        warnings=list(payload.get("warnings") or []),
        data_status=payload.get("data_status") or "mock",
    )
