"""Aggregate community statistics for a product."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence, CommunityTopic


class CommunityStatisticsService:
    """Compute summary counts for dashboards and APIs."""

    def summarize(
        self,
        evidence: list[CommunityEvidence],
        topics: list[CommunityTopic] | None = None,
    ) -> dict[str, Any]:
        by_source: dict[str, int] = {}
        by_sentiment: dict[str, int] = {}
        for item in evidence:
            by_source[item.source] = by_source.get(item.source, 0) + 1
            label = item.sentiment.label
            by_sentiment[label] = by_sentiment.get(label, 0) + 1
        return {
            "evidence_count": len(evidence),
            "unique_authors": len({item.author for item in evidence if item.author}),
            "unique_threads": len({item.thread_id or item.evidence_id for item in evidence}),
            "source_counts": by_source,
            "sentiment_counts": by_sentiment,
            "topic_count": len(topics or []),
            "average_confidence": (
                round(sum(item.confidence for item in evidence) / len(evidence), 3)
                if evidence
                else 0.0
            ),
        }
