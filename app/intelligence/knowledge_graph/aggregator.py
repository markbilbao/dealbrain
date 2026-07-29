"""Aggregate provider-neutral module data into a Knowledge Graph."""

from __future__ import annotations

from typing import Any

from app.domain.entities.knowledge_graph import EdgeType, NodeType
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.fixtures import build_fixture_records


class KnowledgeGraphAggregator:
    """Build a product-centered graph from available fixture / adapter data."""

    def __init__(
        self,
        engine: KnowledgeGraphEngine,
        *,
        community_adapter: Any | None = None,
    ) -> None:
        self._engine = engine
        self._community = community_adapter

    def seed_from_fixtures(self, *, clear: bool = True) -> dict[str, Any]:
        if clear:
            self._engine.repository.clear()
        records = build_fixture_records()
        product_nodes: dict[str, str] = {}

        for product in records["products"]:
            product_node = self._engine.create_node(
                node_type=NodeType.PRODUCT,
                source=str(product.get("marketplace") or "fixture"),
                source_id=str(product["product_id"]),
                label=str(product["label"]),
                brand=product.get("brand"),
                marketplace=product.get("marketplace"),
                category=product.get("category"),
                confidence=0.95,
                data_status=product.get("data_status") or "mock",
                metadata={
                    "product_id": product["product_id"],
                    "deal_score": product.get("deal_score"),
                    "rating": product.get("rating"),
                    "review_count": product.get("review_count"),
                    "known_price": product.get("known_price"),
                    "currency": product.get("currency"),
                },
            )
            # Keep first product_id mapping; cross-marketplace mirrors share the node.
            product_nodes.setdefault(str(product["product_id"]), product_node.node_id)
            # Also map by canonical for demo product aliases.
            product_nodes[product_node.node_id] = product_node.node_id

            if product.get("brand"):
                brand = self._engine.create_node(
                    node_type=NodeType.BRAND,
                    source="fixture",
                    source_id=str(product["brand"]),
                    label=str(product["brand"]),
                    confidence=0.99,
                    data_status="mock",
                )
                self._engine.create_edge(
                    edge_type=EdgeType.MADE_BY,
                    from_node_id=product_node.node_id,
                    to_node_id=brand.node_id,
                    confidence=0.99,
                    source="fixture",
                    evidence_ids=(f"brand:{product['brand']}",),
                )

            if product.get("category"):
                category = self._engine.create_node(
                    node_type=NodeType.CATEGORY,
                    source="fixture",
                    source_id=str(product["category"]),
                    label=str(product["category"]),
                    category=str(product["category"]),
                    confidence=0.99,
                    data_status="mock",
                )
                self._engine.create_edge(
                    edge_type=EdgeType.BELONGS_TO_CATEGORY,
                    from_node_id=product_node.node_id,
                    to_node_id=category.node_id,
                    confidence=0.99,
                    source="fixture",
                )

            if product.get("marketplace"):
                marketplace = self._engine.create_node(
                    node_type=NodeType.MARKETPLACE,
                    source="fixture",
                    source_id=str(product["marketplace"]),
                    label=str(product["marketplace"]),
                    confidence=0.99,
                    data_status="mock",
                )
                self._engine.create_edge(
                    edge_type=EdgeType.OFFERED_ON,
                    from_node_id=product_node.node_id,
                    to_node_id=marketplace.node_id,
                    confidence=0.95,
                    source="fixture",
                    metadata={"known_price": product.get("known_price")},
                )

            if product.get("seller_name"):
                seller = self._engine.create_node(
                    node_type=NodeType.SELLER,
                    source="fixture",
                    source_id=str(product["seller_name"]),
                    label=str(product["seller_name"]),
                    marketplace=product.get("marketplace"),
                    confidence=float(product.get("seller_trust_score") or 0.8),
                    data_status="mock",
                    metadata={"trust_score": product.get("seller_trust_score")},
                )
                self._engine.create_edge(
                    edge_type=EdgeType.SOLD_BY,
                    from_node_id=product_node.node_id,
                    to_node_id=seller.node_id,
                    confidence=float(product.get("seller_trust_score") or 0.8),
                    source="fixture",
                )

            if product.get("known_price") is not None:
                price = self._engine.create_node(
                    node_type=NodeType.PRICE_OBSERVATION,
                    source=str(product.get("marketplace") or "fixture"),
                    source_id=f"{product['product_id']}:price",
                    label=f"{product.get('currency', 'PHP')} {product['known_price']}",
                    confidence=0.9,
                    data_status=product.get("data_status") or "mock",
                    metadata={
                        "amount": product.get("known_price"),
                        "currency": product.get("currency"),
                    },
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_PRICE,
                    from_node_id=product_node.node_id,
                    to_node_id=price.node_id,
                    confidence=0.9,
                    source="fixture",
                )
                history = self._engine.create_node(
                    node_type=NodeType.PRICE_HISTORY,
                    source="price_history",
                    source_id=f"{product['product_id']}:history",
                    label=f"Price history for {product['label']}",
                    confidence=0.85,
                    data_status="mock",
                    metadata={"reference": "price_history_module"},
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_PRICE_HISTORY,
                    from_node_id=product_node.node_id,
                    to_node_id=history.node_id,
                    confidence=0.85,
                    source="fixture",
                )

            if product.get("rating") is not None:
                review = self._engine.create_node(
                    node_type=NodeType.REVIEW,
                    source="review_intelligence",
                    source_id=f"{product['product_id']}:rating",
                    label=f"Rating {product['rating']} ({product.get('review_count', 0)} reviews)",
                    confidence=0.88,
                    data_status="mock",
                    metadata={
                        "rating": product.get("rating"),
                        "review_count": product.get("review_count"),
                    },
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_REVIEW,
                    from_node_id=product_node.node_id,
                    to_node_id=review.node_id,
                    confidence=0.88,
                    source="fixture",
                    evidence_ids=(review.node_id,),
                )

            for topic_name in product.get("topics") or []:
                topic = self._engine.create_node(
                    node_type=NodeType.TOPIC,
                    source="fixture",
                    source_id=str(topic_name),
                    label=str(topic_name),
                    confidence=0.8,
                    data_status="mock",
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_TOPIC,
                    from_node_id=product_node.node_id,
                    to_node_id=topic.node_id,
                    confidence=0.8,
                    source="fixture",
                )

            if product.get("deal_score") is not None:
                evidence = self._engine.create_node(
                    node_type=NodeType.EVIDENCE,
                    source="dealscore",
                    source_id=f"{product['product_id']}:dealscore",
                    label=f"DealScore {product['deal_score']}",
                    confidence=0.9,
                    data_status="mock",
                    metadata={"deal_score": product.get("deal_score")},
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_EVIDENCE,
                    from_node_id=product_node.node_id,
                    to_node_id=evidence.node_id,
                    confidence=0.9,
                    source="fixture",
                    evidence_ids=(evidence.node_id,),
                )

            summary = self._engine.create_node(
                node_type=NodeType.AI_SUMMARY,
                source="ai_review_summary",
                source_id=f"{product['product_id']}:ai-summary",
                label=f"AI summary for {product['label']}",
                confidence=0.7,
                data_status="mock",
                metadata={"interpretive": True},
            )
            self._engine.create_edge(
                edge_type=EdgeType.HAS_AI_SUMMARY,
                from_node_id=product_node.node_id,
                to_node_id=summary.node_id,
                confidence=0.7,
                source="fixture",
            )
            # AI summary must be supported by underlying evidence, not itself.
            backing = self._engine.create_node(
                node_type=NodeType.EVIDENCE,
                source="review_intelligence",
                source_id=f"{product['product_id']}:summary-backing",
                label="Underlying review evidence for AI summary",
                confidence=0.85,
                data_status="mock",
            )
            self._engine.create_edge(
                edge_type=EdgeType.SUPPORTED_BY,
                from_node_id=summary.node_id,
                to_node_id=backing.node_id,
                confidence=0.85,
                source="fixture",
                evidence_ids=(backing.node_id,),
            )

            for complaint in product.get("complaints") or []:
                warning = self._engine.create_node(
                    node_type=NodeType.EVIDENCE,
                    source="fixture",
                    source_id=f"{product['product_id']}:warn:{complaint[:40]}",
                    label=str(complaint),
                    confidence=0.75,
                    data_status="mock",
                    metadata={"kind": "warning"},
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_WARNING,
                    from_node_id=product_node.node_id,
                    to_node_id=warning.node_id,
                    confidence=0.75,
                    source="fixture",
                    evidence_ids=(warning.node_id,),
                )

        # Community evidence (fixture + optional live adapter)
        community_items = list(records["community_evidence"])
        if self._community is not None:
            community_items.extend(self._community.evidence_for(list(product_nodes.keys())))
        for item in community_items:
            product_node_id = product_nodes.get(str(item["product_id"]))
            if not product_node_id:
                continue
            community = self._engine.create_node(
                node_type=NodeType.COMMUNITY_EVIDENCE,
                source=str(item.get("source") or "community"),
                source_id=str(item["source_id"]),
                label=str(item["label"]),
                confidence=float(item.get("confidence") or 0.7),
                data_status=item.get("data_status") or "mock",
                metadata={"topic": item.get("topic")},
            )
            self._engine.create_edge(
                edge_type=EdgeType.HAS_COMMUNITY_EVIDENCE,
                from_node_id=product_node_id,
                to_node_id=community.node_id,
                confidence=float(item.get("confidence") or 0.7),
                source="community",
                evidence_ids=(community.node_id,),
            )
            self._engine.create_edge(
                edge_type=EdgeType.DISCUSSED_IN,
                from_node_id=product_node_id,
                to_node_id=community.node_id,
                confidence=float(item.get("confidence") or 0.7),
                source="community",
            )
            if item.get("topic"):
                topic = self._engine.create_node(
                    node_type=NodeType.TOPIC,
                    source="community",
                    source_id=str(item["topic"]),
                    label=str(item["topic"]),
                    confidence=0.8,
                    data_status="mock",
                )
                self._engine.create_edge(
                    edge_type=EdgeType.HAS_TOPIC,
                    from_node_id=community.node_id,
                    to_node_id=topic.node_id,
                    confidence=0.8,
                    source="community",
                )

        for left_id, right_id, conf in records["similar_pairs"]:
            left = product_nodes.get(left_id)
            right = product_nodes.get(right_id)
            if not left or not right:
                continue
            self._engine.create_edge(
                edge_type=EdgeType.SIMILAR_TO,
                from_node_id=left,
                to_node_id=right,
                confidence=float(conf),
                source="fixture",
            )
            self._engine.create_edge(
                edge_type=EdgeType.ALTERNATIVE_TO,
                from_node_id=left,
                to_node_id=right,
                confidence=float(conf) - 0.05,
                source="fixture",
            )

        for item in records["contradictions"]:
            product_node_id = product_nodes.get(str(item["product_id"]))
            if not product_node_id:
                continue
            left = self._engine.create_node(
                node_type=NodeType.COMMUNITY_EVIDENCE
                if item["left"]["source"] == "community"
                else NodeType.REVIEW,
                source=item["left"]["source"],
                source_id=item["left"]["source_id"],
                label=item["left"]["label"],
                confidence=float(item["left"]["confidence"]),
                data_status="mock",
                metadata={"topic": item.get("topic")},
            )
            right = self._engine.create_node(
                node_type=NodeType.REVIEW
                if item["right"]["source"] == "review"
                else NodeType.COMMUNITY_EVIDENCE,
                source=item["right"]["source"],
                source_id=item["right"]["source_id"],
                label=item["right"]["label"],
                confidence=float(item["right"]["confidence"]),
                data_status="mock",
                metadata={"topic": item.get("topic")},
            )
            self._engine.create_edge(
                edge_type=EdgeType.HAS_COMMUNITY_EVIDENCE
                if left.node_type == NodeType.COMMUNITY_EVIDENCE
                else EdgeType.HAS_REVIEW,
                from_node_id=product_node_id,
                to_node_id=left.node_id,
                confidence=left.confidence,
                source="fixture",
            )
            self._engine.create_edge(
                edge_type=EdgeType.HAS_REVIEW
                if right.node_type == NodeType.REVIEW
                else EdgeType.HAS_COMMUNITY_EVIDENCE,
                from_node_id=product_node_id,
                to_node_id=right.node_id,
                confidence=right.confidence,
                source="fixture",
            )
            self._engine.create_edge(
                edge_type=EdgeType.CONTRADICTS,
                from_node_id=left.node_id,
                to_node_id=right.node_id,
                confidence=min(left.confidence, right.confidence),
                source="fixture",
                evidence_ids=(left.node_id, right.node_id),
                metadata={"topic": item.get("topic")},
            )

        snapshot = self._engine.repository.export_snapshot(data_status="mock")
        return {
            "product_nodes": product_nodes,
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "data_status": "mock",
            "warnings": list(records["warnings"]),
        }
