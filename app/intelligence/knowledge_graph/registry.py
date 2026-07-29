"""Knowledge Graph relationship and node-type registry.

Centralizes supported types so edge-type strings are not scattered.
Future edge types can be registered without modifying traversal code.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.knowledge_graph import SYMMETRIC_EDGE_TYPES, EdgeType, NodeType
from app.domain.exceptions import KnowledgeGraphValidationError


@dataclass(frozen=True, slots=True)
class EdgeTypeSpec:
    """Metadata for a registered relationship type."""

    edge_type: EdgeType
    description: str
    symmetric: bool = False
    allowed_from: frozenset[NodeType] | None = None
    allowed_to: frozenset[NodeType] | None = None
    weight: float = 1.0


_DEFAULT_SPECS: dict[EdgeType, EdgeTypeSpec] = {
    EdgeType.SOLD_BY: EdgeTypeSpec(
        EdgeType.SOLD_BY,
        "Product is sold by a seller",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.SELLER}),
    ),
    EdgeType.OFFERED_ON: EdgeTypeSpec(
        EdgeType.OFFERED_ON,
        "Product is offered on a marketplace",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.MARKETPLACE}),
    ),
    EdgeType.HAS_PRICE: EdgeTypeSpec(
        EdgeType.HAS_PRICE,
        "Product has a price observation",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRICE_OBSERVATION}),
    ),
    EdgeType.HAS_PRICE_HISTORY: EdgeTypeSpec(
        EdgeType.HAS_PRICE_HISTORY,
        "Product has price history",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRICE_HISTORY}),
    ),
    EdgeType.HAS_REVIEW: EdgeTypeSpec(
        EdgeType.HAS_REVIEW,
        "Product has a review",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.REVIEW}),
    ),
    EdgeType.DISCUSSED_IN: EdgeTypeSpec(
        EdgeType.DISCUSSED_IN,
        "Product is discussed in community evidence",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.COMMUNITY_EVIDENCE, NodeType.TOPIC}),
    ),
    EdgeType.HAS_COMMUNITY_EVIDENCE: EdgeTypeSpec(
        EdgeType.HAS_COMMUNITY_EVIDENCE,
        "Product has community evidence",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.COMMUNITY_EVIDENCE}),
    ),
    EdgeType.HAS_AI_SUMMARY: EdgeTypeSpec(
        EdgeType.HAS_AI_SUMMARY,
        "Product has an AI summary",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.AI_SUMMARY}),
        weight=0.85,
    ),
    EdgeType.MADE_BY: EdgeTypeSpec(
        EdgeType.MADE_BY,
        "Product is made by a brand",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.BRAND}),
    ),
    EdgeType.BELONGS_TO_CATEGORY: EdgeTypeSpec(
        EdgeType.BELONGS_TO_CATEGORY,
        "Product belongs to a category",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.CATEGORY}),
    ),
    EdgeType.HAS_TOPIC: EdgeTypeSpec(
        EdgeType.HAS_TOPIC,
        "Entity has a discussion or review topic",
        allowed_from=frozenset({NodeType.PRODUCT, NodeType.REVIEW, NodeType.COMMUNITY_EVIDENCE}),
        allowed_to=frozenset({NodeType.TOPIC}),
    ),
    EdgeType.SIMILAR_TO: EdgeTypeSpec(
        EdgeType.SIMILAR_TO,
        "Products are similar",
        symmetric=True,
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRODUCT}),
        weight=0.9,
    ),
    EdgeType.COMPARES_WITH: EdgeTypeSpec(
        EdgeType.COMPARES_WITH,
        "Products are compared",
        symmetric=True,
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRODUCT}),
        weight=0.9,
    ),
    EdgeType.ACCESSORY_OF: EdgeTypeSpec(
        EdgeType.ACCESSORY_OF,
        "Accessory belongs to a product",
        allowed_from=frozenset({NodeType.ACCESSORY, NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRODUCT}),
    ),
    EdgeType.RECOMMENDED_WITH: EdgeTypeSpec(
        EdgeType.RECOMMENDED_WITH,
        "Product is recommended with another",
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRODUCT}),
        weight=0.85,
    ),
    EdgeType.COMPATIBLE_WITH: EdgeTypeSpec(
        EdgeType.COMPATIBLE_WITH,
        "Entities are compatible",
        symmetric=True,
        allowed_from=frozenset({NodeType.PRODUCT, NodeType.ACCESSORY, NodeType.COMPATIBILITY}),
        allowed_to=frozenset({NodeType.PRODUCT, NodeType.ACCESSORY, NodeType.COMPATIBILITY}),
        weight=0.9,
    ),
    EdgeType.HAS_WARNING: EdgeTypeSpec(
        EdgeType.HAS_WARNING,
        "Entity has a warning evidence node",
        allowed_from=frozenset({NodeType.PRODUCT, NodeType.SELLER}),
        allowed_to=frozenset({NodeType.EVIDENCE}),
        weight=0.95,
    ),
    EdgeType.HAS_EVIDENCE: EdgeTypeSpec(
        EdgeType.HAS_EVIDENCE,
        "Entity is backed by evidence",
        allowed_from=frozenset(set(NodeType)),
        allowed_to=frozenset({NodeType.EVIDENCE, NodeType.COMMUNITY_EVIDENCE, NodeType.REVIEW}),
    ),
    EdgeType.SUPPORTED_BY: EdgeTypeSpec(
        EdgeType.SUPPORTED_BY,
        "Claim or summary is supported by evidence",
        allowed_from=frozenset({NodeType.AI_SUMMARY, NodeType.TOPIC, NodeType.EVIDENCE}),
        allowed_to=frozenset(
            {
                NodeType.EVIDENCE,
                NodeType.COMMUNITY_EVIDENCE,
                NodeType.REVIEW,
                NodeType.PRICE_OBSERVATION,
            }
        ),
        weight=0.95,
    ),
    EdgeType.CONTRADICTS: EdgeTypeSpec(
        EdgeType.CONTRADICTS,
        "Evidence contradicts another claim or evidence",
        allowed_from=frozenset(
            {
                NodeType.EVIDENCE,
                NodeType.COMMUNITY_EVIDENCE,
                NodeType.REVIEW,
                NodeType.AI_SUMMARY,
            }
        ),
        allowed_to=frozenset(
            {
                NodeType.EVIDENCE,
                NodeType.COMMUNITY_EVIDENCE,
                NodeType.REVIEW,
                NodeType.AI_SUMMARY,
                NodeType.TOPIC,
            }
        ),
        weight=0.9,
    ),
    EdgeType.ALTERNATIVE_TO: EdgeTypeSpec(
        EdgeType.ALTERNATIVE_TO,
        "Product is an alternative to another",
        symmetric=True,
        allowed_from=frozenset({NodeType.PRODUCT}),
        allowed_to=frozenset({NodeType.PRODUCT}),
        weight=0.9,
    ),
}


class RelationshipRegistry:
    """Mutable registry of edge-type specifications."""

    def __init__(self, specs: dict[EdgeType, EdgeTypeSpec] | None = None) -> None:
        self._specs: dict[EdgeType, EdgeTypeSpec] = dict(specs or _DEFAULT_SPECS)

    def register(self, spec: EdgeTypeSpec, *, overwrite: bool = False) -> None:
        if spec.edge_type in self._specs and not overwrite:
            raise KnowledgeGraphValidationError(
                f"Edge type already registered: {spec.edge_type.value}"
            )
        self._specs[spec.edge_type] = spec

    def get(self, edge_type: EdgeType | str) -> EdgeTypeSpec:
        resolved = self.resolve_edge_type(edge_type)
        return self._specs[resolved]

    def is_registered(self, edge_type: EdgeType | str) -> bool:
        try:
            self.resolve_edge_type(edge_type)
            return True
        except KnowledgeGraphValidationError:
            return False

    def resolve_edge_type(self, edge_type: EdgeType | str) -> EdgeType:
        if isinstance(edge_type, EdgeType):
            if edge_type not in self._specs:
                raise KnowledgeGraphValidationError(f"Unsupported edge type: {edge_type.value}")
            return edge_type
        raw = str(edge_type).strip().upper()
        try:
            resolved = EdgeType(raw)
        except ValueError as exc:
            raise KnowledgeGraphValidationError(f"Unsupported edge type: {edge_type}") from exc
        if resolved not in self._specs:
            raise KnowledgeGraphValidationError(f"Unsupported edge type: {edge_type}")
        return resolved

    def resolve_node_type(self, node_type: NodeType | str) -> NodeType:
        if isinstance(node_type, NodeType):
            return node_type
        raw = str(node_type).strip().lower()
        try:
            return NodeType(raw)
        except ValueError as exc:
            raise KnowledgeGraphValidationError(f"Unsupported node type: {node_type}") from exc

    def is_symmetric(self, edge_type: EdgeType | str) -> bool:
        resolved = self.resolve_edge_type(edge_type)
        spec = self._specs[resolved]
        return spec.symmetric or resolved in SYMMETRIC_EDGE_TYPES

    def weight(self, edge_type: EdgeType | str) -> float:
        return self.get(edge_type).weight

    def validate_endpoints(
        self,
        edge_type: EdgeType | str,
        from_type: NodeType,
        to_type: NodeType,
    ) -> None:
        spec = self.get(edge_type)
        if spec.allowed_from is not None and from_type not in spec.allowed_from:
            raise KnowledgeGraphValidationError(
                f"Edge {spec.edge_type.value} cannot start from node type {from_type.value}."
            )
        if spec.allowed_to is not None and to_type not in spec.allowed_to:
            raise KnowledgeGraphValidationError(
                f"Edge {spec.edge_type.value} cannot end at node type {to_type.value}."
            )

    def all_edge_types(self) -> list[EdgeType]:
        return list(self._specs.keys())

    def all_node_types(self) -> list[NodeType]:
        return list(NodeType)


DEFAULT_RELATIONSHIP_REGISTRY = RelationshipRegistry()
