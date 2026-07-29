"""Build the Community Intelligence demo dashboard payload."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.community_intelligence import (
    CommunityDashboard,
    CommunityEvidence,
    CommunityProductIntelligence,
    CommunitySourceMetrics,
    CommunitySummary,
    CommunityTopic,
    CommunityTrustScore,
    CommunityWarning,
)
from app.intelligence.community.topic_analysis import TopicAnalysisService


class CommunityDashboardService:
    """Assemble dashboard fields from product intelligence components."""

    def __init__(self, topic_analysis: TopicAnalysisService | None = None) -> None:
        self._topics = topic_analysis or TopicAnalysisService()

    def build(
        self,
        *,
        product_id: str,
        product_name: str,
        trust: CommunityTrustScore,
        evidence: list[CommunityEvidence],
        topics: list[CommunityTopic],
        source_metrics: list[CommunitySourceMetrics],
        timeline,
        summary: CommunitySummary,
        warnings: list[CommunityWarning] | None = None,
        generated_at: datetime | None = None,
        recent_limit: int = 8,
    ) -> CommunityDashboard:
        recent = sorted(evidence, key=lambda item: item.timestamp, reverse=True)[:recent_limit]
        return CommunityDashboard(
            product_id=product_id,
            product_name=product_name,
            trust=trust,
            source_breakdown=tuple(source_metrics),
            topics=tuple(topics),
            positive_topics=tuple(self._topics.positive_topics(topics)),
            negative_topics=tuple(self._topics.negative_topics(topics)),
            timeline=tuple(timeline),
            evidence_count=len(evidence),
            connector_status=tuple(source_metrics),
            recent_discussions=tuple(recent),
            summary=summary,
            warnings=tuple(warnings or []),
            data_status="mock",
            generated_at=generated_at or datetime.now(UTC),
        )

    def from_product(self, product: CommunityProductIntelligence) -> CommunityDashboard:
        return self.build(
            product_id=product.product_id,
            product_name=product.product_name,
            trust=product.trust,
            evidence=list(product.evidence),
            topics=list(product.topics),
            source_metrics=list(product.source_metrics),
            timeline=list(product.timeline),
            summary=product.summary,
            warnings=list(product.warnings),
            generated_at=product.generated_at,
        )
