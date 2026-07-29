"""Knowledge Graph application service facade."""

from __future__ import annotations

from typing import Any

from app.domain.entities.knowledge_graph import (
    GraphExplanation,
    GraphLimits,
    GraphSnapshot,
    GraphSubgraph,
    KnowledgeEdge,
    KnowledgeNode,
)
from app.domain.exceptions import (
    KnowledgeGraphNotFoundError,
    KnowledgeGraphValidationError,
)
from app.intelligence.knowledge_graph.aggregator import KnowledgeGraphAggregator
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine
from app.intelligence.knowledge_graph.evidence import (
    ContradictionService,
    GraphEvidenceService,
)
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.intelligence.knowledge_graph.product_graph import ProductKnowledgeGraphService
from app.intelligence.knowledge_graph.query import GraphQueryService


class KnowledgeGraphService:
    """Application facade for Knowledge Graph queries and mutations."""

    def __init__(
        self,
        engine: KnowledgeGraphEngine,
        *,
        aggregator: KnowledgeGraphAggregator | None = None,
        product_graph: ProductKnowledgeGraphService | None = None,
        query_service: GraphQueryService | None = None,
        enabled: bool = True,
    ) -> None:
        self._engine = engine
        self._aggregator = aggregator or KnowledgeGraphAggregator(engine)
        self._products = product_graph or ProductKnowledgeGraphService(engine)
        self._query = query_service or GraphQueryService(engine, product_graph=self._products)
        self._evidence = GraphEvidenceService(engine.repository)
        self._contradictions = ContradictionService(engine.repository)
        self._enabled = enabled
        self._seeded = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def ensure_seeded(self) -> None:
        if self._seeded:
            return
        if not self._engine.repository.nodes.all():
            self._aggregator.seed_from_fixtures(clear=True)
        self._seeded = True

    def demo(self) -> GraphSubgraph:
        self._require_enabled()
        self.ensure_seeded()
        return self._products.demo()

    def product_graph(
        self,
        product_id: str,
        *,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        max_edges: int | None = None,
    ) -> GraphSubgraph:
        self._require_enabled()
        self.ensure_seeded()
        return self._products.product_graph(
            product_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    def get_node(self, node_id: str) -> KnowledgeNode:
        self._require_enabled()
        self.ensure_seeded()
        return self._engine.get_node(node_id)

    def neighbors(
        self,
        node_id: str,
        *,
        direction: str = "both",
        edge_types: list[str] | None = None,
        min_confidence: float | None = None,
        max_nodes: int | None = None,
    ) -> GraphSubgraph:
        self._require_enabled()
        self.ensure_seeded()
        return self._engine.neighbors(
            node_id,
            direction=direction,
            edge_types=edge_types,
            min_confidence=min_confidence,
            max_nodes=max_nodes,
        )

    def relationships(self, node_id: str) -> dict[str, Any]:
        self._require_enabled()
        self.ensure_seeded()
        node = self._engine.get_node(node_id)
        outgoing = [edge.to_dict() for edge in self._engine.repository.edges.list_outgoing(node_id)]
        incoming = [edge.to_dict() for edge in self._engine.repository.edges.list_incoming(node_id)]
        return {
            "node": node.to_dict(),
            "outgoing": outgoing,
            "incoming": incoming,
            "data_status": node.data_status,
        }

    def find_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        max_depth: int | None = None,
        edge_types: list[str] | None = None,
        min_confidence: float | None = None,
    ) -> dict[str, Any]:
        self._require_enabled()
        self.ensure_seeded()
        limits = self._engine.effective_limits(max_depth=max_depth, min_confidence=min_confidence)
        paths = self._engine.find_paths(
            from_node_id,
            to_node_id,
            max_depth=limits.max_depth,
            edge_types=edge_types,
            min_confidence=limits.min_confidence,
        )
        return {
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "paths": [path.to_dict() for path in paths],
            "truncated": len(paths) >= limits.max_paths,
            "limits": limits.to_dict(),
            "data_status": "mock",
        }

    def evidence(self, node_id: str) -> dict[str, Any]:
        self._require_enabled()
        self.ensure_seeded()
        payload = self._evidence.evidence_for(node_id)
        if payload.get("warnings") == ["Node not found."]:
            raise KnowledgeGraphNotFoundError(node_id)
        payload["contradictions"] = self._contradictions.contradictions_for(node_id)
        return payload

    def explain(
        self,
        *,
        from_node_id: str | None = None,
        to_node_id: str | None = None,
        from_product_id: str | None = None,
        to_product_id: str | None = None,
        claim: str | None = None,
        max_depth: int | None = None,
    ) -> GraphExplanation:
        self._require_enabled()
        self.ensure_seeded()
        if from_product_id and to_product_id:
            return self._explain_products(
                from_product_id, to_product_id, claim=claim, max_depth=max_depth
            )
        if not from_node_id or not to_node_id:
            raise KnowledgeGraphValidationError(
                "Provide from_node_id and to_node_id, or from_product_id and to_product_id."
            )
        return self._engine.explain_connection(
            from_node_id,
            to_node_id,
            claim=claim,
            max_depth=max_depth,
        )

    def _explain_products(
        self,
        from_product_id: str,
        to_product_id: str,
        *,
        claim: str | None = None,
        max_depth: int | None = None,
    ) -> GraphExplanation:
        from_id = self._products.resolve_product_node_id(from_product_id)
        to_id = self._products.resolve_product_node_id(to_product_id)
        return self._engine.explain_connection(
            from_id,
            to_id,
            claim=claim
            or f"Recommendation relationship between {from_product_id} and {to_product_id}",
            max_depth=max_depth,
        )

    def query(self, kind: str, **kwargs: Any) -> Any:
        self._require_enabled()
        self.ensure_seeded()
        mapping = {
            "sellers": self._query.find_sellers,
            "reviews": self._query.find_reviews,
            "community_evidence": self._query.find_community_evidence,
            "shared_brand": self._query.find_products_sharing_brand,
            "shared_category": self._query.find_products_sharing_category,
            "similar": self._query.find_similar_products,
            "topic_evidence": self._query.find_evidence_for_topic,
        }
        if kind not in mapping:
            raise KnowledgeGraphValidationError(f"Unsupported query kind: {kind}")
        return mapping[kind](**kwargs)

    def export_snapshot(self) -> GraphSnapshot:
        self._require_enabled()
        self.ensure_seeded()
        return self._engine.repository.export_snapshot(data_status="mock")

    def import_snapshot(self, payload: dict[str, Any] | GraphSnapshot) -> GraphSnapshot:
        self._require_enabled()
        imported = self._engine.repository.import_snapshot(payload)
        self._seeded = True
        return imported

    def clear_fixture_graph(self) -> None:
        self._engine.repository.clear()
        self._seeded = False

    def create_node(self, **kwargs: Any) -> KnowledgeNode:
        self._require_enabled()
        return self._engine.create_node(**kwargs)

    def create_edge(self, **kwargs: Any) -> KnowledgeEdge:
        self._require_enabled()
        return self._engine.create_edge(**kwargs)

    def shopping_assistant_evidence(
        self,
        product_ids: list[str],
        *,
        limit_per_product: int = 4,
    ) -> list[dict[str, Any]]:
        """Structured graph evidence for Shopping Assistant integration."""
        if not self._enabled:
            return []
        try:
            self.ensure_seeded()
        except Exception:  # noqa: BLE001
            return []
        results: list[dict[str, Any]] = []
        for product_id in product_ids:
            try:
                graph = self._products.product_graph(product_id, max_depth=1, max_nodes=40)
            except Exception:  # noqa: BLE001
                continue
            root = graph.root_node
            if root is None:
                continue
            summary = dict(graph.summary)
            # Graph path evidence
            for similar in (summary.get("similar_products") or [])[:2]:
                results.append(
                    {
                        "evidence_id": f"graph:related:{root.source_id}:{similar}",
                        "type": "related_product",
                        "product_id": root.source_id,
                        "description": f"Related product via knowledge graph: {similar}",
                        "value": similar,
                    }
                )
            for topic in (summary.get("topics") or [])[:2]:
                results.append(
                    {
                        "evidence_id": f"graph:topic:{root.source_id}:{topic}",
                        "type": "community_topic",
                        "product_id": root.source_id,
                        "description": f"Graph topic linked to product: {topic}",
                        "value": topic,
                    }
                )
            for item in list(graph.contradictions)[:1]:
                results.append(
                    {
                        "evidence_id": f"graph:contradiction:{item.get('edge_id')}",
                        "type": "contradiction",
                        "product_id": root.source_id,
                        "description": (
                            f"Conflicting evidence in knowledge graph: {item.get('other_label')}"
                        ),
                        "value": item.get("edge_id"),
                    }
                )
            results.append(
                {
                    "evidence_id": f"graph:path:{root.node_id}",
                    "type": "graph_path",
                    "product_id": root.source_id,
                    "description": (
                        f"Product graph includes {len(graph.nodes)} nodes and "
                        f"{len(graph.edges)} edges (data_status={graph.data_status})."
                    ),
                    "value": len(graph.edges),
                }
            )
            if len(results) >= limit_per_product * max(1, len(product_ids)):
                break
        return results[: limit_per_product * max(1, len(product_ids))]

    def meta(self) -> dict[str, Any]:
        limits = self._engine.limits
        return {
            "enabled": self._enabled,
            "demo_product_id": DEMO_PRODUCT_ID,
            "demo_product_name": DEMO_PRODUCT_LABEL,
            "data_status": "mock",
            "external_graph_database": False,
            "limits": limits.to_dict() if isinstance(limits, GraphLimits) else limits,
            "node_types": [item.value for item in self._engine._registry.all_node_types()],  # noqa: SLF001
            "edge_types": [item.value for item in self._engine._registry.all_edge_types()],  # noqa: SLF001
            "confidence_method": "minimum_edge_confidence",
        }

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise KnowledgeGraphValidationError("Knowledge Graph is disabled.")
