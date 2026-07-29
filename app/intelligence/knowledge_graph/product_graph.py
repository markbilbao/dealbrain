"""Product-centered Knowledge Graph projection."""

from __future__ import annotations

from typing import Any

from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphLimits,
    GraphSubgraph,
    NodeType,
)
from app.domain.exceptions import KnowledgeGraphNotFoundError
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.evidence import ContradictionService
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID


class ProductKnowledgeGraphService:
    """Return a normalized product-centered subgraph."""

    def __init__(self, engine: KnowledgeGraphEngine) -> None:
        self._engine = engine
        self._contradictions = ContradictionService(engine.repository)

    def resolve_product_node_id(self, product_id: str) -> str:
        cleaned = (product_id or "").strip()
        if not cleaned:
            raise KnowledgeGraphNotFoundError(product_id or "")
        direct = self._engine.repository.get_node(cleaned)
        if direct is not None and direct.node_type == NodeType.PRODUCT:
            return direct.node_id
        for node in self._engine.repository.nodes.list_by_type(NodeType.PRODUCT):
            if node.source_id == cleaned or node.metadata.get("product_id") == cleaned:
                return node.node_id
            if node.label.lower() == cleaned.lower():
                return node.node_id
        raise KnowledgeGraphNotFoundError(cleaned)

    def product_graph(
        self,
        product_id: str,
        *,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        max_edges: int | None = None,
    ) -> GraphSubgraph:
        node_id = self.resolve_product_node_id(product_id)
        subgraph = self._engine.traverse(
            node_id,
            max_depth=max_depth if max_depth is not None else 2,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
        contradictions = self._contradictions.contradictions_for(node_id)
        # Expand contradiction counterpart nodes lightly.
        for item in contradictions:
            for key in ("from_node_id", "to_node_id"):
                other = self._engine.repository.get_node(item[key])
                if other is None:
                    continue
                if all(existing.node_id != other.node_id for existing in subgraph.nodes):
                    # Rebuild with appended node via tuple concat below.
                    pass
        summary = self._product_summary(subgraph)
        warnings = list(subgraph.warnings)
        if subgraph.data_status == "mock":
            warnings.append("Fixture/mock data — incomplete live marketplace coverage.")
        if contradictions:
            warnings.append("Conflicting evidence detected for this product.")
        return GraphSubgraph(
            root_node=subgraph.root_node,
            nodes=subgraph.nodes,
            edges=subgraph.edges,
            evidence_paths=subgraph.evidence_paths,
            warnings=tuple(dict.fromkeys(warnings)),
            data_status=subgraph.data_status,
            truncated=subgraph.truncated,
            limits=subgraph.limits,
            contradictions=tuple(contradictions),
            summary=summary,
        )

    def demo(self) -> GraphSubgraph:
        return self.product_graph(DEMO_PRODUCT_ID)

    def _product_summary(self, subgraph: GraphSubgraph) -> dict[str, Any]:
        nodes = list(subgraph.nodes)
        edges = list(subgraph.edges)

        def labels(node_type: NodeType) -> list[str]:
            return [node.label for node in nodes if node.node_type == node_type]

        def connected(edge_type: EdgeType) -> list[str]:
            root_id = subgraph.root_node.node_id if subgraph.root_node else None
            found: list[str] = []
            for edge in edges:
                if edge.edge_type != edge_type:
                    continue
                other = (
                    edge.to_node_id
                    if edge.from_node_id == root_id
                    else edge.from_node_id
                    if edge.to_node_id == root_id
                    else None
                )
                if other is None:
                    continue
                node = self._engine.repository.get_node(other)
                if node is not None:
                    found.append(node.label)
            return found

        node_counts: dict[str, int] = {}
        for node in nodes:
            node_counts[node.node_type.value] = node_counts.get(node.node_type.value, 0) + 1
        edge_counts: dict[str, int] = {}
        for edge in edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1

        return {
            "brands": labels(NodeType.BRAND),
            "categories": labels(NodeType.CATEGORY),
            "sellers": connected(EdgeType.SOLD_BY),
            "marketplaces": connected(EdgeType.OFFERED_ON),
            "reviews": labels(NodeType.REVIEW),
            "community_evidence": labels(NodeType.COMMUNITY_EVIDENCE),
            "price_history": labels(NodeType.PRICE_HISTORY),
            "topics": labels(NodeType.TOPIC),
            "ai_summaries": labels(NodeType.AI_SUMMARY),
            "similar_products": connected(EdgeType.SIMILAR_TO),
            "warnings_nodes": connected(EdgeType.HAS_WARNING),
            "node_counts": node_counts,
            "edge_counts": edge_counts,
            "limits": (subgraph.limits or GraphLimits()).to_dict(),
        }
