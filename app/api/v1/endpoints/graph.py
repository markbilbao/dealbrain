"""Knowledge Graph API endpoints.

Bounded, evidence-first graph queries. No external graph database.
Client traversal parameters are clamped to server limits.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.mappers.knowledge_graph import (
    to_evidence_response,
    to_explanation_response,
    to_node_payload,
    to_path_response,
    to_relationships_response,
    to_subgraph_response,
)
from app.core.dependencies import get_knowledge_graph_service
from app.domain.exceptions import (
    KnowledgeGraphNotFoundError,
    KnowledgeGraphValidationError,
)
from app.schemas.knowledge_graph import (
    GraphEvidenceResponse,
    GraphExplanationResponse,
    GraphMetaResponse,
    GraphPathResponse,
    GraphRelationshipsResponse,
    GraphSubgraphResponse,
    KnowledgeNodePayload,
)
from app.services.knowledge_graph_service import KnowledgeGraphService

router = APIRouter(prefix="/graph")


def _map_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KnowledgeGraphValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    if isinstance(exc, KnowledgeGraphNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Knowledge graph failed to process the request.",
    )


def _parse_edge_types(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


@router.get(
    "/demo",
    response_model=GraphSubgraphResponse,
    summary="Knowledge Graph demo product subgraph",
)
async def graph_demo(
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphSubgraphResponse:
    try:
        subgraph = service.demo()
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_subgraph_response(subgraph)


@router.get(
    "/meta",
    response_model=GraphMetaResponse,
    summary="Knowledge Graph metadata and limits",
)
async def graph_meta(
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphMetaResponse:
    return GraphMetaResponse(**service.meta())


@router.get(
    "/product/{product_id}",
    response_model=GraphSubgraphResponse,
    summary="Product-centered knowledge graph",
)
async def graph_product(
    product_id: str,
    max_depth: int | None = Query(default=None, ge=1, le=10),
    max_nodes: int | None = Query(default=None, ge=1, le=1000),
    max_edges: int | None = Query(default=None, ge=1, le=2000),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphSubgraphResponse:
    try:
        subgraph = service.product_graph(
            product_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        raise _map_error(exc) from exc
    return to_subgraph_response(subgraph)


@router.get(
    "/node/{node_id}",
    response_model=KnowledgeNodePayload,
    summary="Fetch a knowledge graph node",
)
async def graph_node(
    node_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> KnowledgeNodePayload:
    try:
        node = service.get_node(node_id)
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_node_payload(node)


@router.get(
    "/node/{node_id}/neighbors",
    response_model=GraphSubgraphResponse,
    summary="Direct neighbors of a node",
)
async def graph_neighbors(
    node_id: str,
    direction: str = Query(default="both"),
    edge_types: str | None = Query(default=None),
    minimum_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    max_nodes: int | None = Query(default=None, ge=1, le=1000),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphSubgraphResponse:
    try:
        subgraph = service.neighbors(
            node_id,
            direction=direction,
            edge_types=_parse_edge_types(edge_types),
            min_confidence=minimum_confidence,
            max_nodes=max_nodes,
        )
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_subgraph_response(subgraph)


@router.get(
    "/node/{node_id}/relationships",
    response_model=GraphRelationshipsResponse,
    summary="Incoming and outgoing relationships for a node",
)
async def graph_relationships(
    node_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphRelationshipsResponse:
    try:
        payload = service.relationships(node_id)
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_relationships_response(payload)


@router.get(
    "/path",
    response_model=GraphPathResponse,
    summary="Find evidence paths between two nodes",
)
async def graph_path(
    from_node_id: str = Query(...),
    to_node_id: str = Query(...),
    max_depth: int | None = Query(default=None, ge=1, le=10),
    edge_types: str | None = Query(default=None),
    minimum_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphPathResponse:
    try:
        payload = service.find_paths(
            from_node_id,
            to_node_id,
            max_depth=max_depth,
            edge_types=_parse_edge_types(edge_types),
            min_confidence=minimum_confidence,
        )
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_path_response(payload)


@router.get(
    "/evidence/{node_id}",
    response_model=GraphEvidenceResponse,
    summary="Evidence linked to a knowledge graph node",
)
async def graph_evidence(
    node_id: str,
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphEvidenceResponse:
    try:
        payload = service.evidence(node_id)
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_evidence_response(payload)


@router.get(
    "/explain",
    response_model=GraphExplanationResponse,
    summary="Explain why two nodes or products are connected",
)
async def graph_explain(
    from_node_id: str | None = Query(default=None),
    to_node_id: str | None = Query(default=None),
    from_product_id: str | None = Query(default=None),
    to_product_id: str | None = Query(default=None),
    claim: str | None = Query(default=None),
    max_depth: int | None = Query(default=None, ge=1, le=10),
    service: KnowledgeGraphService = Depends(get_knowledge_graph_service),
) -> GraphExplanationResponse:
    try:
        explanation = service.explain(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            from_product_id=from_product_id,
            to_product_id=to_product_id,
            claim=claim,
            max_depth=max_depth,
        )
    except (KnowledgeGraphValidationError, KnowledgeGraphNotFoundError) as exc:
        raise _map_error(exc) from exc
    return to_explanation_response(explanation)
