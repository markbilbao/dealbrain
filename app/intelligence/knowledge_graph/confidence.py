"""Deterministic path confidence for the Knowledge Graph.

Method: **minimum edge confidence along the path**.

Rationale:
- Conservative and explainable (a path is only as strong as its weakest link)
- Avoids false precision from long multiplicative chains
- Does not pretend weak evidence becomes strong via aggregation

Confidence bands (no false precision):
- high:   confidence >= 0.80
- medium: 0.50 <= confidence < 0.80
- low:    confidence < 0.50
"""

from __future__ import annotations

from app.domain.entities.knowledge_graph import ConfidenceBand, KnowledgeEdge


def confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.80:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def path_confidence(edges: list[KnowledgeEdge] | tuple[KnowledgeEdge, ...]) -> float:
    """Return the minimum edge confidence along the path (0.0 if empty)."""
    if not edges:
        return 0.0
    return round(min(edge.confidence for edge in edges), 4)


def combine_node_and_path_confidence(
    *,
    path_score: float,
    node_scores: list[float] | None = None,
) -> float:
    """Optionally tighten path score with the weakest node confidence."""
    scores = [path_score]
    if node_scores:
        scores.extend(node_scores)
    return round(min(scores), 4) if scores else 0.0
