"""Community Intelligence Platform domain entities and value objects.

Provider-neutral evidence model. Shopping Assistant must never need to know
which connector produced an item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

CommunitySource = Literal[
    "reddit",
    "youtube",
    "amazon_qa",
    "marketplace_questions",
    "manufacturer_forums",
    "discord",
]

CommunitySentimentLabel = Literal["positive", "neutral", "negative", "mixed"]
ConfidenceBand = Literal["High", "Medium", "Low"]
AnalysisMode = Literal["economy", "balanced", "maximum"]
ConnectorStatus = Literal["enabled", "disabled", "mock", "error", "unavailable"]
DataStatus = Literal["mock", "imported", "live"]

MODE_RANK: dict[str, int] = {"economy": 0, "balanced": 1, "maximum": 2}

DEFAULT_TOPICS: tuple[str, ...] = (
    "Battery",
    "Camera",
    "Gaming",
    "Display",
    "Performance",
    "Heat",
    "Noise",
    "Durability",
    "Warranty",
    "Shipping",
    "Packaging",
    "Accessories",
    "Software",
    "Firmware",
    "Compatibility",
    "Customer Service",
    "Value",
    "Price",
)


@dataclass(frozen=True, slots=True)
class CommunityEngagement:
    """Normalized engagement signals across connectors."""

    score: float = 0.0
    upvotes: int = 0
    comments: int = 0
    likes: int = 0
    views: int = 0
    helpful_votes: int = 0
    replies: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "upvotes": self.upvotes,
            "comments": self.comments,
            "likes": self.likes,
            "views": self.views,
            "helpful_votes": self.helpful_votes,
            "replies": self.replies,
        }


@dataclass(frozen=True, slots=True)
class CommunitySentiment:
    """Sentiment for a single evidence item or aggregated topic."""

    label: CommunitySentimentLabel
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "score": self.score}


@dataclass(frozen=True, slots=True)
class CommunityEvidence:
    """Normalized community evidence — common model for every connector."""

    source: CommunitySource
    product: str
    evidence_id: str
    url: str
    title: str
    body: str
    topic: str
    sentiment: CommunitySentiment
    confidence: float
    engagement: CommunityEngagement
    timestamp: datetime
    product_id: str | None = None
    author: str | None = None
    thread_id: str | None = None
    permalink: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    data_status: DataStatus = "mock"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "product": self.product,
            "product_id": self.product_id,
            "evidence_id": self.evidence_id,
            "url": self.url,
            "title": self.title,
            "body": self.body,
            "topic": self.topic,
            "sentiment": self.sentiment.to_dict(),
            "confidence": self.confidence,
            "engagement": self.engagement.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "thread_id": self.thread_id,
            "permalink": self.permalink,
            "metadata": dict(self.metadata),
            "data_status": self.data_status,
        }


@dataclass(frozen=True, slots=True)
class CommunityTopic:
    """Aggregated topic signal with linked evidence."""

    name: str
    mention_count: int
    sentiment: CommunitySentiment
    confidence: ConfidenceBand
    evidence_ids: tuple[str, ...] = ()
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mention_count": self.mention_count,
            "sentiment": self.sentiment.to_dict(),
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
        }


@dataclass(frozen=True, slots=True)
class CommunityInsight:
    """AI or deterministic insight backed by evidence IDs."""

    kind: str
    statement: str
    evidence_ids: tuple[str, ...] = ()
    confidence: ConfidenceBand = "Medium"
    topic: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "statement": self.statement,
            "evidence_ids": list(self.evidence_ids),
            "confidence": self.confidence,
            "topic": self.topic,
        }


@dataclass(frozen=True, slots=True)
class CommunityTrustScore:
    """Deterministic community trust score (0–100)."""

    score: int
    factors: dict[str, float] = field(default_factory=dict)
    band: ConfidenceBand = "Medium"
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "factors": dict(self.factors),
            "band": self.band,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class CommunitySourceMetrics:
    """Per-source health and volume metrics."""

    source: CommunitySource
    status: ConnectorStatus
    evidence_count: int = 0
    unique_authors: int = 0
    unique_threads: int = 0
    average_engagement: float = 0.0
    freshness_hours: float | None = None
    enabled: bool = False
    transport: str = "mock"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "status": self.status,
            "evidence_count": self.evidence_count,
            "unique_authors": self.unique_authors,
            "unique_threads": self.unique_threads,
            "average_engagement": self.average_engagement,
            "freshness_hours": self.freshness_hours,
            "enabled": self.enabled,
            "transport": self.transport,
        }


@dataclass(frozen=True, slots=True)
class CommunitySummary:
    """Evidence-grounded community summary for a product."""

    product_id: str
    product_name: str
    most_praised: tuple[CommunityInsight, ...] = ()
    most_complaints: tuple[CommunityInsight, ...] = ()
    common_questions: tuple[CommunityInsight, ...] = ()
    who_should_buy: tuple[CommunityInsight, ...] = ()
    who_should_avoid: tuple[CommunityInsight, ...] = ()
    buying_advice: tuple[CommunityInsight, ...] = ()
    limitations: tuple[str, ...] = ()
    provider: str = "deterministic"
    model: str = "deterministic-community-v1"
    mode: AnalysisMode = "economy"
    providers_used: tuple[str, ...] = ()
    fallback_used: bool = True
    fallback_reason: str | None = None
    agreement_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "most_praised": [item.to_dict() for item in self.most_praised],
            "most_complaints": [item.to_dict() for item in self.most_complaints],
            "common_questions": [item.to_dict() for item in self.common_questions],
            "who_should_buy": [item.to_dict() for item in self.who_should_buy],
            "who_should_avoid": [item.to_dict() for item in self.who_should_avoid],
            "buying_advice": [item.to_dict() for item in self.buying_advice],
            "limitations": list(self.limitations),
            "provider": self.provider,
            "model": self.model,
            "mode": self.mode,
            "providers_used": list(self.providers_used),
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "agreement_score": self.agreement_score,
        }


@dataclass(frozen=True, slots=True)
class CommunityTimelineEvent:
    """Point-in-time community activity for a product."""

    timestamp: datetime
    evidence_count: int
    positive_count: int
    negative_count: int
    topics: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "evidence_count": self.evidence_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "topics": list(self.topics),
            "sources": list(self.sources),
        }


@dataclass(frozen=True, slots=True)
class CommunityWarning:
    """Non-fatal warning for dashboard / API consumers."""

    message: str
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"message": self.message, "code": self.code}


@dataclass(frozen=True, slots=True)
class CommunityProductIntelligence:
    """Full community intelligence payload for a product."""

    product_id: str
    product_name: str
    trust: CommunityTrustScore
    topics: tuple[CommunityTopic, ...]
    evidence: tuple[CommunityEvidence, ...]
    summary: CommunitySummary
    source_metrics: tuple[CommunitySourceMetrics, ...]
    timeline: tuple[CommunityTimelineEvent, ...]
    warnings: tuple[CommunityWarning, ...] = ()
    data_status: DataStatus = "mock"
    evidence_count: int = 0
    generated_at: datetime | None = None
    processing: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "trust": self.trust.to_dict(),
            "topics": [item.to_dict() for item in self.topics],
            "evidence": [item.to_dict() for item in self.evidence],
            "summary": self.summary.to_dict(),
            "source_metrics": [item.to_dict() for item in self.source_metrics],
            "timeline": [item.to_dict() for item in self.timeline],
            "warnings": [item.to_dict() for item in self.warnings],
            "data_status": self.data_status,
            "evidence_count": self.evidence_count,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "processing": dict(self.processing),
        }


@dataclass(frozen=True, slots=True)
class CommunityDashboard:
    """Demo dashboard aggregate view."""

    product_id: str
    product_name: str
    trust: CommunityTrustScore
    source_breakdown: tuple[CommunitySourceMetrics, ...]
    topics: tuple[CommunityTopic, ...]
    positive_topics: tuple[str, ...]
    negative_topics: tuple[str, ...]
    timeline: tuple[CommunityTimelineEvent, ...]
    evidence_count: int
    connector_status: tuple[CommunitySourceMetrics, ...]
    recent_discussions: tuple[CommunityEvidence, ...]
    summary: CommunitySummary
    warnings: tuple[CommunityWarning, ...]
    data_status: DataStatus = "mock"
    generated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "trust": self.trust.to_dict(),
            "source_breakdown": [item.to_dict() for item in self.source_breakdown],
            "topics": [item.to_dict() for item in self.topics],
            "positive_topics": list(self.positive_topics),
            "negative_topics": list(self.negative_topics),
            "timeline": [item.to_dict() for item in self.timeline],
            "evidence_count": self.evidence_count,
            "connector_status": [item.to_dict() for item in self.connector_status],
            "recent_discussions": [item.to_dict() for item in self.recent_discussions],
            "summary": self.summary.to_dict(),
            "warnings": [item.to_dict() for item in self.warnings],
            "data_status": self.data_status,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
