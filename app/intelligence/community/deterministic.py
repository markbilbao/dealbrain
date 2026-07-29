"""Deterministic community summarizer — never fabricates beyond evidence."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunityInsight,
    CommunitySummary,
    CommunityTopic,
)
from app.intelligence.community.confidence import CommunityConfidenceService
from app.intelligence.community.recommendation import CommunityRecommendationService
from app.intelligence.community.topics import TopicExtractor


class DeterministicCommunitySummaryProvider:
    """Always-available evidence-grounded community summary."""

    provider_name = "deterministic"
    model_name = "deterministic-community-v1"

    def __init__(
        self,
        *,
        recommendation_service: CommunityRecommendationService | None = None,
        confidence: CommunityConfidenceService | None = None,
        topic_extractor: TopicExtractor | None = None,
    ) -> None:
        self._recommendations = recommendation_service or CommunityRecommendationService()
        self._confidence = confidence or CommunityConfidenceService()
        self._topics = topic_extractor or TopicExtractor()

    def is_available(self) -> bool:
        return True

    def summarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = str(payload.get("product_id") or "")
        product_name = str(payload.get("product_name") or product_id)
        evidence = list(payload.get("evidence") or [])
        topics = list(payload.get("topics") or [])
        # Accept domain objects or dicts.
        evidence_objs = self._as_evidence(evidence)
        topic_objs = self._as_topics(topics)

        praised = self._insights_for_polarity(
            topic_objs, evidence_objs, polarity="positive", kind="most_praised"
        )
        complaints = self._insights_for_polarity(
            topic_objs, evidence_objs, polarity="negative", kind="most_complaints"
        )
        questions = self._common_questions(evidence_objs)
        who_buy = self._recommendations.who_should_buy(topic_objs, evidence_objs)
        who_avoid = self._recommendations.who_should_avoid(topic_objs, evidence_objs)
        advice = self._recommendations.buying_advice(topic_objs, evidence_objs)

        summary = CommunitySummary(
            product_id=product_id,
            product_name=product_name,
            most_praised=tuple(praised),
            most_complaints=tuple(complaints),
            common_questions=tuple(questions),
            who_should_buy=tuple(who_buy),
            who_should_avoid=tuple(who_avoid),
            buying_advice=tuple(advice),
            limitations=(
                "Community summary uses mock/imported connector data by default.",
                "Statements are limited to evidence collected for this product.",
                "External AI providers are disabled unless configured server-side.",
            ),
            provider=self.provider_name,
            model=self.model_name,
            providers_used=(self.provider_name,),
            fallback_used=True,
            fallback_reason=payload.get("fallback_reason") or "deterministic_default",
        )
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "status": "ok",
            "summary": summary,
            "confidence": 0.7 if evidence_objs else 0.2,
        }

    def _insights_for_polarity(
        self,
        topics: list[CommunityTopic],
        evidence: list[CommunityEvidence],
        *,
        polarity: str,
        kind: str,
    ) -> list[CommunityInsight]:
        selected = [
            topic
            for topic in topics
            if (
                topic.sentiment.label == polarity
                or (polarity == "positive" and topic.positive_count > topic.negative_count)
                or (polarity == "negative" and topic.negative_count > topic.positive_count)
            )
        ]
        insights: list[CommunityInsight] = []
        for topic in selected[:4]:
            verb = "praised" if polarity == "positive" else "criticized"
            insights.append(
                CommunityInsight(
                    kind=kind,
                    statement=f"{topic.name} is frequently {verb} in community discussions.",
                    evidence_ids=topic.evidence_ids[:6],
                    confidence=self._confidence.for_evidence_ids(
                        evidence, topic.evidence_ids[:6]
                    ),
                    topic=topic.name,
                )
            )
        return insights

    def _common_questions(self, evidence: list[CommunityEvidence]) -> list[CommunityInsight]:
        insights: list[CommunityInsight] = []
        for item in evidence:
            text = f"{item.title} {item.body}"
            if self._topics.extract_questions(text) or "?" in item.title:
                insights.append(
                    CommunityInsight(
                        kind="common_questions",
                        statement=item.title or item.body[:160],
                        evidence_ids=(item.evidence_id,),
                        confidence=self._confidence.for_evidence_ids(
                            evidence, [item.evidence_id]
                        ),
                        topic=item.topic,
                    )
                )
            if len(insights) >= 5:
                break
        return insights

    def _as_evidence(self, items: list[Any]) -> list[CommunityEvidence]:
        result: list[CommunityEvidence] = []
        for item in items:
            if isinstance(item, CommunityEvidence):
                result.append(item)
        return result

    def _as_topics(self, items: list[Any]) -> list[CommunityTopic]:
        result: list[CommunityTopic] = []
        for item in items:
            if isinstance(item, CommunityTopic):
                result.append(item)
        return result
