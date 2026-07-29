"""Community Trust Score tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.entities.community_intelligence import (
    CommunityEngagement,
    CommunityEvidence,
    CommunitySentiment,
)
from app.intelligence.community.trust import CommunityTrustCalculator

CALC = CommunityTrustCalculator()
NOW = datetime(2026, 7, 1, tzinfo=UTC)


def _ev(
    *,
    eid: str,
    source: str = "reddit",
    author: str | None = "u1",
    thread: str | None = "t1",
    topic: str = "Battery",
    days_ago: int = 5,
) -> CommunityEvidence:
    return CommunityEvidence(
        source=source,  # type: ignore[arg-type]
        product="P",
        product_id="p",
        evidence_id=eid,
        url="https://example.com",
        title=topic,
        body=f"{topic} discussion body",
        topic=topic,
        sentiment=CommunitySentiment(label="positive", score=0.4),
        confidence=0.7,
        engagement=CommunityEngagement(score=8),
        timestamp=NOW - timedelta(days=days_ago),
        author=author,
        thread_id=thread,
    )


def test_empty_evidence_zero_trust():
    trust = CALC.calculate([], now=NOW)
    assert trust.score == 0
    assert trust.band == "Low"
    assert trust.factors["evidence_count"] == 0.0


def test_rich_evidence_high_trust():
    items = []
    sources = ["reddit", "youtube", "amazon_qa", "marketplace_questions"]
    topics = ["Battery", "Gaming", "Heat", "Noise", "Price", "Value", "Display", "Software"]
    for i in range(20):
        items.append(
            _ev(
                eid=f"e{i}",
                source=sources[i % len(sources)],
                author=f"user{i}",
                thread=f"thread{i}",
                topic=topics[i % len(topics)],
                days_ago=i,
            )
        )
    trust = CALC.calculate(items, ai_agreement=0.9, now=NOW)
    assert trust.score >= 70
    assert trust.band in {"High", "Medium"}
    assert set(trust.factors) == {
        "evidence_count",
        "independent_threads",
        "independent_users",
        "source_diversity",
        "topic_consistency",
        "ai_agreement",
        "data_freshness",
        "coverage",
    }


def test_stale_data_lowers_freshness():
    items = [_ev(eid="old", days_ago=400, author="a", thread="t")]
    trust = CALC.calculate(items, now=NOW)
    assert trust.factors["data_freshness"] == 0.0


def test_source_diversity_factor():
    one_source = [_ev(eid=f"a{i}", source="reddit", author=f"u{i}", thread=f"t{i}") for i in range(8)]
    multi = [
        _ev(eid=f"b{i}", source=["reddit", "youtube", "amazon_qa", "marketplace_questions"][i % 4], author=f"u{i}", thread=f"t{i}")
        for i in range(8)
    ]
    a = CALC.calculate(one_source, now=NOW)
    b = CALC.calculate(multi, now=NOW)
    assert b.factors["source_diversity"] > a.factors["source_diversity"]


@pytest.mark.parametrize("agreement", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_ai_agreement_factor_passthrough(agreement):
    items = [_ev(eid="e1"), _ev(eid="e2", author="u2", thread="t2")]
    trust = CALC.calculate(items, ai_agreement=agreement, now=NOW)
    assert trust.factors["ai_agreement"] == agreement


@pytest.mark.parametrize("count", [1, 2, 5, 10, 20, 40])
def test_evidence_count_factor_monotone(count):
    items = [
        _ev(eid=f"e{i}", author=f"u{i}", thread=f"t{i}", topic=["Battery", "Heat"][i % 2])
        for i in range(count)
    ]
    trust = CALC.calculate(items, now=NOW)
    assert 0 <= trust.score <= 100
    assert trust.factors["evidence_count"] == min(1.0, count / 20.0)


def test_score_clamped():
    trust = CALC.calculate([_ev(eid="x")], now=NOW)
    assert 0 <= trust.score <= 100
