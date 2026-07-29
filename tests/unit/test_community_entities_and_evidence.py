"""Entity serialization and evidence model contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.entities.community_intelligence import (
    CommunityDashboard,
    CommunityEngagement,
    CommunityEvidence,
    CommunityInsight,
    CommunityProductIntelligence,
    CommunitySentiment,
    CommunitySourceMetrics,
    CommunitySummary,
    CommunityTimelineEvent,
    CommunityTopic,
    CommunityTrustScore,
    CommunityWarning,
    DEFAULT_TOPICS,
)
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL


def _evidence(i: int = 0) -> CommunityEvidence:
    return CommunityEvidence(
        source="reddit",
        product=DEMO_PRODUCT_LABEL,
        product_id=DEMO_PRODUCT_ID,
        evidence_id=f"reddit:e{i}",
        url="https://example.com",
        title="Battery",
        body="Battery is good",
        topic="Battery",
        sentiment=CommunitySentiment(label="positive", score=0.5),
        confidence=0.8,
        engagement=CommunityEngagement(score=12, upvotes=5, comments=2),
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        author="user",
        thread_id="t1",
        permalink="https://example.com",
    )


REQUIRED_EVIDENCE_KEYS = [
    "source",
    "product",
    "evidence_id",
    "url",
    "title",
    "body",
    "topic",
    "sentiment",
    "confidence",
    "engagement",
    "timestamp",
]


@pytest.mark.parametrize("key", REQUIRED_EVIDENCE_KEYS)
def test_evidence_dict_has_common_key(key):
    assert key in _evidence().to_dict()


@pytest.mark.parametrize("label", ["positive", "neutral", "negative", "mixed"])
def test_sentiment_labels(label):
    assert CommunitySentiment(label=label, score=0.1).to_dict()["label"] == label  # type: ignore[arg-type]


@pytest.mark.parametrize("topic", list(DEFAULT_TOPICS))
def test_topic_entity(topic):
    item = CommunityTopic(
        name=topic,
        mention_count=2,
        sentiment=CommunitySentiment(label="neutral", score=0.0),
        confidence="Medium",
        evidence_ids=("a", "b"),
    )
    data = item.to_dict()
    assert data["name"] == topic
    assert data["evidence_ids"] == ["a", "b"]


@pytest.mark.parametrize("kind", [
    "most_praised",
    "most_complaints",
    "common_questions",
    "who_should_buy",
    "who_should_avoid",
    "buying_advice",
])
def test_insight_kinds(kind):
    insight = CommunityInsight(kind=kind, statement="x", evidence_ids=("e1",), confidence="High")
    assert insight.to_dict()["kind"] == kind


@pytest.mark.parametrize("score", list(range(0, 101, 5)))
def test_trust_score_range(score):
    trust = CommunityTrustScore(score=score, band="Medium")
    assert trust.to_dict()["score"] == score


@pytest.mark.parametrize(
    "status",
    ["enabled", "disabled", "mock", "error", "unavailable"],
)
def test_source_metrics_status(status):
    metrics = CommunitySourceMetrics(source="reddit", status=status)  # type: ignore[arg-type]
    assert metrics.to_dict()["status"] == status


def test_summary_and_dashboard_dicts():
    summary = CommunitySummary(product_id=DEMO_PRODUCT_ID, product_name=DEMO_PRODUCT_LABEL)
    product = CommunityProductIntelligence(
        product_id=DEMO_PRODUCT_ID,
        product_name=DEMO_PRODUCT_LABEL,
        trust=CommunityTrustScore(score=70, band="High"),
        topics=(),
        evidence=(_evidence(),),
        summary=summary,
        source_metrics=(),
        timeline=(
            CommunityTimelineEvent(
                timestamp=datetime(2026, 6, 1, tzinfo=UTC),
                evidence_count=1,
                positive_count=1,
                negative_count=0,
            ),
        ),
        warnings=(CommunityWarning(message="mock", code="mock_data"),),
        evidence_count=1,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
    )
    dash = CommunityDashboard(
        product_id=DEMO_PRODUCT_ID,
        product_name=DEMO_PRODUCT_LABEL,
        trust=product.trust,
        source_breakdown=(),
        topics=(),
        positive_topics=("Battery",),
        negative_topics=("Heat",),
        timeline=product.timeline,
        evidence_count=1,
        connector_status=(),
        recent_discussions=product.evidence,
        summary=summary,
        warnings=product.warnings,
        generated_at=product.generated_at,
    )
    assert "trust" in product.to_dict()
    assert "positive_topics" in dash.to_dict()
    assert dash.to_dict()["evidence_count"] == 1


@pytest.mark.parametrize("i", list(range(25)))
def test_evidence_ids_unique_series(i):
    assert _evidence(i).evidence_id == f"reddit:e{i}"
