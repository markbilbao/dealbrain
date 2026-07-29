"""Limited structured Knowledge Graph queries (no free-form query language)."""

from __future__ import annotations

from typing import Any

from app.domain.entities.knowledge_graph import EdgeType, NodeType
from app.domain.exceptions import KnowledgeGraphValidationError
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.product_graph import ProductKnowledgeGraphService


class GraphQueryService:
    """Deterministic structured queries over the knowledge graph."""

    def __init__(
        self,
        engine: KnowledgeGraphEngine,
        *,
        product_graph: ProductKnowledgeGraphService | None = None,
    ) -> None:
        self._engine = engine
        self._products = product_graph or ProductKnowledgeGraphService(engine)

    def find_sellers(self, product_id: str) -> list[dict[str, Any]]:
        return self._neighbors_of_type(product_id, EdgeType.SOLD_BY, NodeType.SELLER)

    def find_reviews(self, product_id: str) -> list[dict[str, Any]]:
        return self._neighbors_of_type(product_id, EdgeType.HAS_REVIEW, NodeType.REVIEW)

    def find_community_evidence(self, product_id: str) -> list[dict[str, Any]]:
        return self._neighbors_of_type(
            product_id,
            EdgeType.HAS_COMMUNITY_EVIDENCE,
            NodeType.COMMUNITY_EVIDENCE,
        )

    def find_products_sharing_brand(self, product_id: str) -> list[dict[str, Any]]:
        return self._products_via(product_id, EdgeType.MADE_BY, NodeType.BRAND)

    def find_products_sharing_category(self, product_id: str) -> list[dict[str, Any]]:
        return self._products_via(product_id, EdgeType.BELONGS_TO_CATEGORY, NodeType.CATEGORY)

    def find_similar_products(self, product_id: str) -> list[dict[str, Any]]:
        return self._neighbors_of_type(product_id, EdgeType.SIMILAR_TO, NodeType.PRODUCT)

    def find_evidence_for_topic(self, topic_label: str) -> list[dict[str, Any]]:
        cleaned = (topic_label or "").strip().lower()
        if not cleaned:
            raise KnowledgeGraphValidationError("topic must not be blank.")
        results: list[dict[str, Any]] = []
        for topic in self._engine.repository.nodes.list_by_type(NodeType.TOPIC):
            if topic.label.lower() != cleaned and topic.source_id.lower() != cleaned:
                continue
            for edge in self._engine.repository.edges.list_incoming(topic.node_id):
                source = self._engine.repository.get_node(edge.from_node_id)
                if source is not None:
                    results.append(source.to_dict())
        return results

    def find_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        max_depth: int | None = None,
        edge_types: list[str] | None = None,
        min_confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        paths = self._engine.find_paths(
            from_node_id,
            to_node_id,
            max_depth=max_depth,
            edge_types=edge_types,
            min_confidence=min_confidence,
        )
        return [path.to_dict() for path in paths]

    def explain_recommendation(
        self,
        from_product_id: str,
        to_product_id: str,
    ) -> dict[str, Any]:
        from_id = self._products.resolve_product_node_id(from_product_id)
        to_id = self._products.resolve_product_node_id(to_product_id)
        explanation = self._engine.explain_connection(
            from_id,
            to_id,
            claim=f"Recommendation relationship between {from_product_id} and {to_product_id}",
            edge_types=[
                EdgeType.SIMILAR_TO.value,
                EdgeType.ALTERNATIVE_TO.value,
                EdgeType.RECOMMENDED_WITH.value,
                EdgeType.COMPARES_WITH.value,
                EdgeType.MADE_BY.value,
                EdgeType.BELONGS_TO_CATEGORY.value,
            ],
        )
        return explanation.to_dict()

    def _neighbors_of_type(
        self,
        product_id: str,
        edge_type: EdgeType,
        node_type: NodeType,
    ) -> list[dict[str, Any]]:
        node_id = self._products.resolve_product_node_id(product_id)
        subgraph = self._engine.neighbors(
            node_id,
            direction="outgoing",
            edge_types=[edge_type.value],
        )
        return [
            node.to_dict()
            for node in subgraph.nodes
            if node.node_type == node_type and node.node_id != node_id
        ]

    def _products_via(
        self,
        product_id: str,
        edge_type: EdgeType,
        hub_type: NodeType,
    ) -> list[dict[str, Any]]:
        node_id = self._products.resolve_product_node_id(product_id)
        hubs = self._neighbors_of_type(product_id, edge_type, hub_type)
        related: dict[str, dict[str, Any]] = {}
        for hub in hubs:
            for edge in self._engine.repository.edges.list_incoming(hub["node_id"]):
                if edge.edge_type != edge_type:
                    continue
                other = self._engine.repository.get_node(edge.from_node_id)
                if other is None or other.node_id == node_id:
                    continue
                if other.node_type == NodeType.PRODUCT:
                    related[other.node_id] = other.to_dict()
        return list(related.values())
