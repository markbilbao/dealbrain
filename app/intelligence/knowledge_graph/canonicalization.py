"""Deterministic node canonicalization for the Knowledge Graph."""

from __future__ import annotations

import hashlib
import re

from app.domain.entities.knowledge_graph import NodeType

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_token(value: str) -> str:
    text = (value or "").strip().lower()
    text = _WHITESPACE_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub("-", text)
    return text.strip("-")


class NodeCanonicalizationService:
    """Build stable canonical keys without AI."""

    def canonical_key(
        self,
        node_type: NodeType | str,
        *,
        source: str | None = None,
        source_id: str | None = None,
        label: str | None = None,
        marketplace: str | None = None,
        brand: str | None = None,
        category: str | None = None,
    ) -> str:
        type_name = node_type.value if isinstance(node_type, NodeType) else str(node_type).lower()
        if type_name == NodeType.PRODUCT.value:
            # Prefer identity across marketplaces when brand+label available.
            brand_token = normalize_token(brand or "")
            label_token = normalize_token(label or "")
            if brand_token and label_token:
                return f"product:{brand_token}:{label_token}"
            if source and source_id:
                return f"product:{normalize_token(source)}:{normalize_token(source_id)}"
            return f"product:{label_token or 'unknown'}"

        if type_name == NodeType.SELLER.value:
            market = normalize_token(marketplace or source or "unknown")
            seller = normalize_token(label or source_id or "unknown")
            return f"seller:{market}:{seller}"

        if type_name == NodeType.MARKETPLACE.value:
            return f"marketplace:{normalize_token(label or source_id or 'unknown')}"

        if type_name == NodeType.BRAND.value:
            return f"brand:{normalize_token(label or source_id or 'unknown')}"

        if type_name == NodeType.CATEGORY.value:
            return f"category:{normalize_token(category or label or source_id or 'unknown')}"

        if type_name == NodeType.TOPIC.value:
            return f"topic:{normalize_token(label or source_id or 'unknown')}"

        if type_name in {
            NodeType.REVIEW.value,
            NodeType.COMMUNITY_EVIDENCE.value,
            NodeType.EVIDENCE.value,
            NodeType.AI_SUMMARY.value,
            NodeType.PRICE_OBSERVATION.value,
            NodeType.PRICE_HISTORY.value,
            NodeType.VIDEO.value,
            NodeType.ACCESSORY.value,
            NodeType.COMPATIBILITY.value,
        }:
            src = normalize_token(source or "unknown")
            sid = normalize_token(source_id or label or "unknown")
            return f"{type_name}:{src}:{sid}"

        return f"{type_name}:{normalize_token(source_id or label or 'unknown')}"

    def deterministic_node_id(
        self,
        node_type: NodeType | str,
        canonical_key: str,
        *,
        prefix: str = "kg",
    ) -> str:
        type_name = node_type.value if isinstance(node_type, NodeType) else str(node_type).lower()
        digest = hashlib.sha256(f"{type_name}|{canonical_key}".encode()).hexdigest()[:16]
        return f"{prefix}:{type_name}:{digest}"

    def deterministic_edge_id(
        self,
        edge_type: str,
        from_node_id: str,
        to_node_id: str,
        *,
        prefix: str = "kg",
    ) -> str:
        digest = hashlib.sha256(f"{edge_type}|{from_node_id}|{to_node_id}".encode()).hexdigest()[
            :16
        ]
        return f"{prefix}:edge:{digest}"
