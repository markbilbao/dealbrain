"""Community confidence banding helpers."""

from __future__ import annotations

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunityTopic,
    ConfidenceBand,
)


def confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.75:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


class CommunityConfidenceService:
    """Derive confidence for topics and insights from evidence support."""

    def for_evidence_ids(
        self,
        evidence: list[CommunityEvidence],
        evidence_ids: list[str] | tuple[str, ...],
    ) -> ConfidenceBand:
        wanted = set(evidence_ids)
        matched = [item for item in evidence if item.evidence_id in wanted]
        if not matched:
            return "Low"
        sources = {item.source for item in matched}
        avg_conf = sum(item.confidence for item in matched) / len(matched)
        score = avg_conf
        if len(matched) >= 3:
            score += 0.1
        if len(sources) >= 2:
            score += 0.1
        return confidence_band(min(1.0, score))

    def for_topic(self, topic: CommunityTopic) -> ConfidenceBand:
        return topic.confidence

    def score_from_counts(self, *, mentions: int, sources: int, agreement: float = 0.5) -> float:
        base = min(1.0, mentions / 6.0) * 0.5
        diversity = min(1.0, sources / 3.0) * 0.3
        return round(min(1.0, base + diversity + agreement * 0.2), 3)
