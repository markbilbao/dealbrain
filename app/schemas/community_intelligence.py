"""Community Intelligence API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SentimentPayload(BaseModel):
    label: str
    score: float = 0.0


class EngagementPayload(BaseModel):
    score: float = 0.0
    upvotes: int = 0
    comments: int = 0
    likes: int = 0
    views: int = 0
    helpful_votes: int = 0
    replies: int = 0


class CommunityEvidencePayload(BaseModel):
    source: str
    product: str
    product_id: str | None = None
    evidence_id: str
    url: str = ""
    title: str = ""
    body: str = ""
    topic: str = ""
    sentiment: SentimentPayload
    confidence: float = 0.0
    engagement: EngagementPayload
    timestamp: str | None = None
    author: str | None = None
    thread_id: str | None = None
    permalink: str | None = None
    data_status: str = "mock"


class CommunityTopicPayload(BaseModel):
    name: str
    mention_count: int = 0
    sentiment: SentimentPayload
    confidence: str = "Medium"
    evidence_ids: list[str] = Field(default_factory=list)
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0


class CommunityInsightPayload(BaseModel):
    kind: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "Medium"
    topic: str | None = None


class CommunityTrustPayload(BaseModel):
    score: int
    factors: dict[str, float] = Field(default_factory=dict)
    band: str = "Medium"
    explanation: str = ""


class CommunitySourceMetricsPayload(BaseModel):
    source: str
    status: str
    evidence_count: int = 0
    unique_authors: int = 0
    unique_threads: int = 0
    average_engagement: float = 0.0
    freshness_hours: float | None = None
    enabled: bool = False
    transport: str = "mock"


class CommunitySummaryPayload(BaseModel):
    product_id: str
    product_name: str
    most_praised: list[CommunityInsightPayload] = Field(default_factory=list)
    most_complaints: list[CommunityInsightPayload] = Field(default_factory=list)
    common_questions: list[CommunityInsightPayload] = Field(default_factory=list)
    who_should_buy: list[CommunityInsightPayload] = Field(default_factory=list)
    who_should_avoid: list[CommunityInsightPayload] = Field(default_factory=list)
    buying_advice: list[CommunityInsightPayload] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provider: str = "deterministic"
    model: str = "deterministic-community-v1"
    mode: str = "economy"
    providers_used: list[str] = Field(default_factory=list)
    fallback_used: bool = True
    fallback_reason: str | None = None
    agreement_score: float | None = None


class CommunityTimelinePayload(BaseModel):
    timestamp: str
    evidence_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    topics: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class CommunityWarningPayload(BaseModel):
    message: str
    code: str | None = None


class CommunityProductResponse(BaseModel):
    product_id: str
    product_name: str
    trust: CommunityTrustPayload
    topics: list[CommunityTopicPayload] = Field(default_factory=list)
    evidence: list[CommunityEvidencePayload] = Field(default_factory=list)
    summary: CommunitySummaryPayload
    source_metrics: list[CommunitySourceMetricsPayload] = Field(default_factory=list)
    timeline: list[CommunityTimelinePayload] = Field(default_factory=list)
    warnings: list[CommunityWarningPayload] = Field(default_factory=list)
    data_status: str = "mock"
    evidence_count: int = 0
    generated_at: str | None = None
    processing: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Community Intelligence aggregates mock/imported community evidence by default. "
        "Live connectors and external AI are disabled unless enabled server-side. "
        "Every insight should be verified against linked evidence."
    )


class CommunityDashboardResponse(BaseModel):
    product_id: str
    product_name: str
    trust: CommunityTrustPayload
    source_breakdown: list[CommunitySourceMetricsPayload] = Field(default_factory=list)
    topics: list[CommunityTopicPayload] = Field(default_factory=list)
    positive_topics: list[str] = Field(default_factory=list)
    negative_topics: list[str] = Field(default_factory=list)
    timeline: list[CommunityTimelinePayload] = Field(default_factory=list)
    evidence_count: int = 0
    connector_status: list[CommunitySourceMetricsPayload] = Field(default_factory=list)
    recent_discussions: list[CommunityEvidencePayload] = Field(default_factory=list)
    summary: CommunitySummaryPayload
    warnings: list[CommunityWarningPayload] = Field(default_factory=list)
    data_status: str = "mock"
    generated_at: str | None = None
    disclaimer: str = (
        "Demo dashboard uses fixture-backed community connectors. Not live social data."
    )


class CommunityTopicsResponse(BaseModel):
    product_id: str
    topics: list[CommunityTopicPayload] = Field(default_factory=list)


class CommunityTimelineResponse(BaseModel):
    product_id: str
    timeline: list[CommunityTimelinePayload] = Field(default_factory=list)


class CommunityEvidenceResponse(BaseModel):
    evidence: CommunityEvidencePayload


class CommunityMetaResponse(BaseModel):
    demo_product_id: str
    demo_product_name: str
    connectors: dict[str, Any] = Field(default_factory=dict)
    data_status: str = "mock"
    ai_enabled: bool = False
