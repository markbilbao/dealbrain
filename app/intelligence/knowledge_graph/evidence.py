"""Evidence tracing, path services, validation, and contradiction handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.entities.knowledge_graph import (
    EdgeType,
    GraphPath,
    KnowledgeEdge,
    KnowledgeNode,
    NodeType,
)
from app.domain.exceptions import KnowledgeGraphValidationError
from app.domain.interfaces.knowledge_graph_repository import KnowledgeGraphRepository
from app.intelligence.knowledge_graph.confidence import confidence_band, path_confidence
from app.intelligence.knowledge_graph.engine import KnowledgeGraphEngine


class EvidenceValidationService:
    """Reject unsupported graph claims and AI-as-own-evidence loops."""

    def validate_evidence_refs(
        self,
        *,
        subject: KnowledgeNode,
        evidence_nodes: list[KnowledgeNode],
    ) -> list[str]:
        warnings: list[str] = []
        for evidence in evidence_nodes:
            if (
                evidence.node_type == NodeType.AI_SUMMARY
                and subject.node_type == NodeType.AI_SUMMARY
                and evidence.node_id == subject.node_id
            ):
                raise KnowledgeGraphValidationError(
                    "An AI summary node cannot be evidence for its own claims."
                )
            if evidence.node_type == NodeType.AI_SUMMARY and subject.node_id == evidence.node_id:
                raise KnowledgeGraphValidationError(
                    "AI-generated interpretations may reference underlying evidence "
                    "but must not replace it."
                )
            if evidence.node_type == NodeType.AI_SUMMARY:
                warnings.append(
                    f"AI summary {evidence.node_id} is interpretive and must not replace "
                    "underlying evidence."
                )
        return warnings

    def reject_unsupported_claim(self, claim: str, *, supported: bool) -> None:
        if not supported:
            raise KnowledgeGraphValidationError(f"Unsupported graph claim rejected: {claim}")


class GraphEvidenceService:
    """Collect evidence linked to a node."""

    def __init__(self, repository: KnowledgeGraphRepository) -> None:
        self._repo = repository
        self._validator = EvidenceValidationService()

    def evidence_for(self, node_id: str) -> dict[str, Any]:
        node = self._repo.get_node(node_id)
        if node is None:
            return {
                "node_id": node_id,
                "evidence_nodes": [],
                "evidence_edges": [],
                "stale": [],
                "warnings": ["Node not found."],
            }
        evidence_nodes: list[KnowledgeNode] = []
        evidence_edges: list[KnowledgeEdge] = []
        for edge in [
            *self._repo.edges.list_outgoing(node_id),
            *self._repo.edges.list_incoming(node_id),
        ]:
            if edge.edge_type in {
                EdgeType.HAS_EVIDENCE,
                EdgeType.SUPPORTED_BY,
                EdgeType.HAS_REVIEW,
                EdgeType.HAS_COMMUNITY_EVIDENCE,
                EdgeType.DISCUSSED_IN,
            }:
                evidence_edges.append(edge)
                other = edge.to_node_id if edge.from_node_id == node_id else edge.from_node_id
                other_node = self._repo.get_node(other)
                if other_node is not None:
                    evidence_nodes.append(other_node)
            for eid in edge.evidence_ids:
                ref = self._repo.get_node(eid)
                if ref is not None:
                    evidence_nodes.append(ref)

        # Deduplicate by node_id preserving order.
        deduped: dict[str, KnowledgeNode] = {item.node_id: item for item in evidence_nodes}
        warnings = self._validator.validate_evidence_refs(
            subject=node, evidence_nodes=list(deduped.values())
        )
        stale = [item.to_dict() for item in deduped.values() if self.is_stale(item)]
        return {
            "node_id": node_id,
            "root": node.to_dict(),
            "evidence_nodes": [item.to_dict() for item in deduped.values()],
            "evidence_edges": [item.to_dict() for item in evidence_edges],
            "stale": stale,
            "warnings": warnings,
            "data_status": node.data_status,
        }

    @staticmethod
    def is_stale(node: KnowledgeNode, *, max_age_days: int = 180) -> bool:
        flag = bool(node.metadata.get("stale")) if node.metadata else False
        if flag:
            return True
        stamp = node.updated_at or node.created_at
        if stamp is None:
            return False
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        return datetime.now(UTC) - stamp > timedelta(days=max_age_days)


class EvidencePathService:
    """Return supporting evidence paths within server limits."""

    def __init__(self, engine: KnowledgeGraphEngine) -> None:
        self._engine = engine

    def supporting_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        *,
        max_depth: int | None = None,
        max_paths: int | None = None,
        min_confidence: float | None = None,
    ) -> list[GraphPath]:
        return self._engine.find_paths(
            from_node_id,
            to_node_id,
            max_depth=max_depth,
            max_paths=max_paths,
            min_confidence=min_confidence,
        )

    def path_score(self, edge_ids: list[str]) -> tuple[float, str]:
        edges = []
        for edge_id in edge_ids:
            edge = self._engine.repository.get_edge(edge_id)
            if edge is not None:
                edges.append(edge)
        score = path_confidence(edges)
        return score, confidence_band(score)


class ContradictionService:
    """Detect and summarize conflicting evidence relationships."""

    def __init__(self, repository: KnowledgeGraphRepository) -> None:
        self._repo = repository

    def contradictions_for(self, node_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for edge in [
            *self._repo.edges.list_outgoing(node_id),
            *self._repo.edges.list_incoming(node_id),
        ]:
            if edge.edge_type != EdgeType.CONTRADICTS:
                continue
            other = edge.to_node_id if edge.from_node_id == node_id else edge.from_node_id
            other_node = self._repo.get_node(other)
            results.append(
                {
                    "edge_id": edge.edge_id,
                    "from_node_id": edge.from_node_id,
                    "to_node_id": edge.to_node_id,
                    "confidence": edge.confidence,
                    "confidence_band": confidence_band(edge.confidence),
                    "other_label": other_node.label if other_node else other,
                    "evidence_ids": list(edge.evidence_ids),
                    "metadata": dict(edge.metadata),
                }
            )
        return results
