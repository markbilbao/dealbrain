"""Metadata sanitization and entity validation for the Knowledge Graph."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.entities.knowledge_graph import (
    EdgeType,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.exceptions import KnowledgeGraphValidationError
from app.intelligence.knowledge_graph.registry import (
    DEFAULT_RELATIONSHIP_REGISTRY,
    RelationshipRegistry,
)

_FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "authorization",
        "private_key",
        "prompt",
        "system_prompt",
        "hidden_prompt",
    }
)
_MAX_METADATA_KEYS = 40
_MAX_METADATA_DEPTH = 3
_MAX_STRING_LEN = 2000


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip secrets and bound untrusted metadata size/depth."""
    if not metadata:
        return {}
    return _sanitize_value(dict(metadata), depth=0)  # type: ignore[return-value]


def _sanitize_value(value: Any, *, depth: int) -> Any:
    if depth > _MAX_METADATA_DEPTH:
        return "[truncated]"
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= _MAX_METADATA_KEYS:
                cleaned["_truncated"] = True
                break
            key_str = str(key)[:128]
            if key_str.lower().replace("-", "_") in _FORBIDDEN_METADATA_KEYS:
                continue
            cleaned[key_str] = _sanitize_value(item, depth=depth + 1)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item, depth=depth + 1) for item in list(value)[:50]]
    if isinstance(value, str):
        return value[:_MAX_STRING_LEN]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING_LEN]


def clamp_confidence(value: float | int | None, *, default: float = 1.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise KnowledgeGraphValidationError("confidence must be a number.") from exc
    if number < 0.0 or number > 1.0:
        raise KnowledgeGraphValidationError("confidence must be between 0.0 and 1.0.")
    return round(number, 6)


class KnowledgeGraphValidator:
    """Validate nodes and edges before persistence."""

    def __init__(self, registry: RelationshipRegistry | None = None) -> None:
        self._registry = registry or DEFAULT_RELATIONSHIP_REGISTRY

    def validate_node(self, node: KnowledgeNode) -> KnowledgeNode:
        if not node.node_id or not str(node.node_id).strip():
            raise KnowledgeGraphValidationError("node_id must not be blank.")
        if not node.canonical_key or not str(node.canonical_key).strip():
            raise KnowledgeGraphValidationError("canonical_key must not be blank.")
        if not node.source or not str(node.source).strip():
            raise KnowledgeGraphValidationError("source must not be blank.")
        if not node.source_id or not str(node.source_id).strip():
            raise KnowledgeGraphValidationError("source_id must not be blank.")
        if not node.label or not str(node.label).strip():
            raise KnowledgeGraphValidationError("label must not be blank.")
        if not isinstance(node.node_type, NodeType):
            raise KnowledgeGraphValidationError("node_type is unsupported.")
        clamp_confidence(node.confidence)
        if node.data_status not in {"mock", "imported", "live"}:
            raise KnowledgeGraphValidationError(f"Unsupported data_status: {node.data_status}")
        return node

    def validate_edge(
        self,
        edge: KnowledgeEdge,
        *,
        from_type: NodeType | None = None,
        to_type: NodeType | None = None,
    ) -> KnowledgeEdge:
        if not edge.edge_id or not str(edge.edge_id).strip():
            raise KnowledgeGraphValidationError("edge_id must not be blank.")
        if not edge.from_node_id or not edge.to_node_id:
            raise KnowledgeGraphValidationError("edge endpoints must not be blank.")
        if edge.from_node_id == edge.to_node_id:
            raise KnowledgeGraphValidationError("self-loops are not allowed.")
        if not isinstance(edge.edge_type, EdgeType):
            raise KnowledgeGraphValidationError("edge_type is unsupported.")
        if not self._registry.is_registered(edge.edge_type):
            raise KnowledgeGraphValidationError(f"Unsupported edge type: {edge.edge_type.value}")
        clamp_confidence(edge.confidence)
        if not edge.source or not str(edge.source).strip():
            raise KnowledgeGraphValidationError("edge source must not be blank.")
        if from_type is not None and to_type is not None:
            self._registry.validate_endpoints(edge.edge_type, from_type, to_type)
        return edge

    def parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise KnowledgeGraphValidationError(f"Invalid datetime: {value}") from exc
