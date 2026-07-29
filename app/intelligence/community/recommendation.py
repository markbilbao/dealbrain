"""Community-derived buying recommendations grounded in evidence."""

from __future__ import annotations

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunityInsight,
    CommunityTopic,
)
from app.intelligence.community.confidence import CommunityConfidenceService


class CommunityRecommendationService:
    """Produce who-should-buy / avoid style insights from topics + evidence."""

    def __init__(self, confidence: CommunityConfidenceService | None = None) -> None:
        self._confidence = confidence or CommunityConfidenceService()

    def who_should_buy(
        self,
        topics: list[CommunityTopic],
        evidence: list[CommunityEvidence],
    ) -> list[CommunityInsight]:
        positive = [
            topic
            for topic in topics
            if topic.sentiment.label == "positive" and topic.mention_count > 0
        ]
        insights: list[CommunityInsight] = []
        for topic in positive[:3]:
            insights.append(
                CommunityInsight(
                    kind="who_should_buy",
                    statement=(
                        f"Buyers who prioritize {topic.name.lower()} may like this product "
                        f"based on community praise."
                    ),
                    evidence_ids=topic.evidence_ids[:5],
                    confidence=self._confidence.for_evidence_ids(
                        evidence, topic.evidence_ids[:5]
                    ),
                    topic=topic.name,
                )
            )
        return insights

    def who_should_avoid(
        self,
        topics: list[CommunityTopic],
        evidence: list[CommunityEvidence],
    ) -> list[CommunityInsight]:
        negative = [
            topic
            for topic in topics
            if topic.negative_count > topic.positive_count and topic.mention_count > 0
        ]
        insights: list[CommunityInsight] = []
        for topic in negative[:3]:
            insights.append(
                CommunityInsight(
                    kind="who_should_avoid",
                    statement=(
                        f"Buyers sensitive to {topic.name.lower()} issues may want to "
                        f"consider alternatives."
                    ),
                    evidence_ids=topic.evidence_ids[:5],
                    confidence=self._confidence.for_evidence_ids(
                        evidence, topic.evidence_ids[:5]
                    ),
                    topic=topic.name,
                )
            )
        return insights

    def buying_advice(
        self,
        topics: list[CommunityTopic],
        evidence: list[CommunityEvidence],
    ) -> list[CommunityInsight]:
        advice: list[CommunityInsight] = []
        for topic in topics:
            if topic.name in {"Heat", "Noise"} and topic.negative_count:
                advice.append(
                    CommunityInsight(
                        kind="buying_advice",
                        statement=(
                            f"Plan for {topic.name.lower()} management "
                            f"(cooling pad / quieter environments) based on community reports."
                        ),
                        evidence_ids=topic.evidence_ids[:4],
                        confidence=self._confidence.for_evidence_ids(
                            evidence, topic.evidence_ids[:4]
                        ),
                        topic=topic.name,
                    )
                )
            if topic.name == "Warranty" and topic.mention_count:
                advice.append(
                    CommunityInsight(
                        kind="buying_advice",
                        statement="Prefer official-store warranty channels when available.",
                        evidence_ids=topic.evidence_ids[:4],
                        confidence=self._confidence.for_evidence_ids(
                            evidence, topic.evidence_ids[:4]
                        ),
                        topic=topic.name,
                    )
                )
        return advice[:4]
