"""Map Community Intelligence domain objects to HTTP schemas."""

from __future__ import annotations

from app.domain.entities.community_intelligence import (
    CommunityDashboard,
    CommunityEvidence,
    CommunityProductIntelligence,
    CommunitySummary,
)
from app.schemas.community_intelligence import (
    CommunityDashboardResponse,
    CommunityEvidencePayload,
    CommunityEvidenceResponse,
    CommunityInsightPayload,
    CommunityProductResponse,
    CommunitySourceMetricsPayload,
    CommunitySummaryPayload,
    CommunityTimelinePayload,
    CommunityTopicPayload,
    CommunityTopicsResponse,
    CommunityTimelineResponse,
    CommunityTrustPayload,
    CommunityWarningPayload,
    EngagementPayload,
    SentimentPayload,
)

_SECRET_KEYS = ("api_key", "apikey", "authorization", "secret", "token", "prompt")


def _sanitize_processing(processing: dict) -> dict:
    cleaned: dict = {}
    for key, value in processing.items():
        lowered = str(key).lower()
        if any(part in lowered for part in _SECRET_KEYS):
            continue
        cleaned[key] = value
    return cleaned


def _sentiment(item) -> SentimentPayload:
    return SentimentPayload(label=item.label, score=item.score)


def _engagement(item) -> EngagementPayload:
    return EngagementPayload(
        score=item.score,
        upvotes=item.upvotes,
        comments=item.comments,
        likes=item.likes,
        views=item.views,
        helpful_votes=item.helpful_votes,
        replies=item.replies,
    )


def to_evidence_payload(item: CommunityEvidence) -> CommunityEvidencePayload:
    return CommunityEvidencePayload(
        source=item.source,
        product=item.product,
        product_id=item.product_id,
        evidence_id=item.evidence_id,
        url=item.url,
        title=item.title,
        body=item.body,
        topic=item.topic,
        sentiment=_sentiment(item.sentiment),
        confidence=item.confidence,
        engagement=_engagement(item.engagement),
        timestamp=item.timestamp.isoformat() if item.timestamp else None,
        author=item.author,
        thread_id=item.thread_id,
        permalink=item.permalink,
        data_status=item.data_status,
    )


def _insight(item) -> CommunityInsightPayload:
    return CommunityInsightPayload(
        kind=item.kind,
        statement=item.statement,
        evidence_ids=list(item.evidence_ids),
        confidence=item.confidence,
        topic=item.topic,
    )


def _summary(summary: CommunitySummary) -> CommunitySummaryPayload:
    return CommunitySummaryPayload(
        product_id=summary.product_id,
        product_name=summary.product_name,
        most_praised=[_insight(item) for item in summary.most_praised],
        most_complaints=[_insight(item) for item in summary.most_complaints],
        common_questions=[_insight(item) for item in summary.common_questions],
        who_should_buy=[_insight(item) for item in summary.who_should_buy],
        who_should_avoid=[_insight(item) for item in summary.who_should_avoid],
        buying_advice=[_insight(item) for item in summary.buying_advice],
        limitations=list(summary.limitations),
        provider=summary.provider,
        model=summary.model,
        mode=summary.mode,
        providers_used=list(summary.providers_used),
        fallback_used=summary.fallback_used,
        fallback_reason=summary.fallback_reason,
        agreement_score=summary.agreement_score,
    )


def _topic(item) -> CommunityTopicPayload:
    return CommunityTopicPayload(
        name=item.name,
        mention_count=item.mention_count,
        sentiment=_sentiment(item.sentiment),
        confidence=item.confidence,
        evidence_ids=list(item.evidence_ids),
        positive_count=item.positive_count,
        negative_count=item.negative_count,
        neutral_count=item.neutral_count,
    )


def _metrics(item) -> CommunitySourceMetricsPayload:
    return CommunitySourceMetricsPayload(
        source=item.source,
        status=item.status,
        evidence_count=item.evidence_count,
        unique_authors=item.unique_authors,
        unique_threads=item.unique_threads,
        average_engagement=item.average_engagement,
        freshness_hours=item.freshness_hours,
        enabled=item.enabled,
        transport=item.transport,
    )


def _timeline(item) -> CommunityTimelinePayload:
    return CommunityTimelinePayload(
        timestamp=item.timestamp.isoformat(),
        evidence_count=item.evidence_count,
        positive_count=item.positive_count,
        negative_count=item.negative_count,
        topics=list(item.topics),
        sources=list(item.sources),
    )


def to_product_response(product: CommunityProductIntelligence) -> CommunityProductResponse:
    return CommunityProductResponse(
        product_id=product.product_id,
        product_name=product.product_name,
        trust=CommunityTrustPayload(
            score=product.trust.score,
            factors=dict(product.trust.factors),
            band=product.trust.band,
            explanation=product.trust.explanation,
        ),
        topics=[_topic(item) for item in product.topics],
        evidence=[to_evidence_payload(item) for item in product.evidence],
        summary=_summary(product.summary),
        source_metrics=[_metrics(item) for item in product.source_metrics],
        timeline=[_timeline(item) for item in product.timeline],
        warnings=[
            CommunityWarningPayload(message=item.message, code=item.code)
            for item in product.warnings
        ],
        data_status=product.data_status,
        evidence_count=product.evidence_count,
        generated_at=product.generated_at.isoformat() if product.generated_at else None,
        processing=_sanitize_processing(dict(product.processing)),
    )


def to_dashboard_response(dashboard: CommunityDashboard) -> CommunityDashboardResponse:
    return CommunityDashboardResponse(
        product_id=dashboard.product_id,
        product_name=dashboard.product_name,
        trust=CommunityTrustPayload(
            score=dashboard.trust.score,
            factors=dict(dashboard.trust.factors),
            band=dashboard.trust.band,
            explanation=dashboard.trust.explanation,
        ),
        source_breakdown=[_metrics(item) for item in dashboard.source_breakdown],
        topics=[_topic(item) for item in dashboard.topics],
        positive_topics=list(dashboard.positive_topics),
        negative_topics=list(dashboard.negative_topics),
        timeline=[_timeline(item) for item in dashboard.timeline],
        evidence_count=dashboard.evidence_count,
        connector_status=[_metrics(item) for item in dashboard.connector_status],
        recent_discussions=[to_evidence_payload(item) for item in dashboard.recent_discussions],
        summary=_summary(dashboard.summary),
        warnings=[
            CommunityWarningPayload(message=item.message, code=item.code)
            for item in dashboard.warnings
        ],
        data_status=dashboard.data_status,
        generated_at=dashboard.generated_at.isoformat() if dashboard.generated_at else None,
    )


def to_evidence_response(evidence: CommunityEvidence) -> CommunityEvidenceResponse:
    return CommunityEvidenceResponse(evidence=to_evidence_payload(evidence))


def to_topics_response(product_id: str, topics) -> CommunityTopicsResponse:
    return CommunityTopicsResponse(
        product_id=product_id,
        topics=[_topic(item) for item in topics],
    )


def to_timeline_response(product_id: str, timeline) -> CommunityTimelineResponse:
    return CommunityTimelineResponse(
        product_id=product_id,
        timeline=[_timeline(item) for item in timeline],
    )
