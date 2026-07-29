"""Aggregate CommunityTopic objects from normalized evidence."""

from __future__ import annotations

from collections import defaultdict

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunitySentiment,
    CommunityTopic,
)
from app.intelligence.community.confidence import confidence_band


class TopicAnalysisService:
    """Build topic charts and polarity lists from evidence."""

    def analyze(self, evidence: list[CommunityEvidence]) -> list[CommunityTopic]:
        buckets: dict[str, list[CommunityEvidence]] = defaultdict(list)
        for item in evidence:
            if item.topic:
                buckets[item.topic].append(item)

        topics: list[CommunityTopic] = []
        for name, items in buckets.items():
            pos = sum(1 for item in items if item.sentiment.label == "positive")
            neg = sum(1 for item in items if item.sentiment.label == "negative")
            neu = sum(1 for item in items if item.sentiment.label in {"neutral", "mixed"})
            score = 0.0
            if items:
                score = sum(item.sentiment.score for item in items) / len(items)
            if pos > neg and pos >= neu:
                label = "positive"
            elif neg > pos and neg >= neu:
                label = "negative"
            elif pos and neg:
                label = "mixed"
            else:
                label = "neutral"
            sources = {item.source for item in items}
            conf_score = min(1.0, len(items) / 5.0 + (0.15 if len(sources) > 1 else 0.0))
            topics.append(
                CommunityTopic(
                    name=name,
                    mention_count=len(items),
                    sentiment=CommunitySentiment(label=label, score=round(score, 3)),  # type: ignore[arg-type]
                    confidence=confidence_band(conf_score),
                    evidence_ids=tuple(item.evidence_id for item in items),
                    positive_count=pos,
                    negative_count=neg,
                    neutral_count=neu,
                )
            )
        topics.sort(key=lambda item: (-item.mention_count, item.name))
        return topics

    def positive_topics(self, topics: list[CommunityTopic], *, limit: int = 5) -> list[str]:
        ranked = [
            topic.name
            for topic in topics
            if topic.sentiment.label == "positive" and topic.positive_count >= topic.negative_count
        ]
        return ranked[:limit]

    def negative_topics(self, topics: list[CommunityTopic], *, limit: int = 5) -> list[str]:
        ranked = [
            topic.name
            for topic in topics
            if topic.sentiment.label == "negative" or topic.negative_count > topic.positive_count
        ]
        return ranked[:limit]
