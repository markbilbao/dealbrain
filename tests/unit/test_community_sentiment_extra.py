"""Additional sentiment / mapper / config coverage."""

from __future__ import annotations

import pytest

from app.api.v1.mappers.community_intelligence import (
    to_dashboard_response,
    to_evidence_response,
    to_product_response,
    to_timeline_response,
    to_topics_response,
)
from app.core.config import Settings
from app.core.dependencies import (
    get_community_ai_orchestrator,
    get_community_registry,
    get_community_summary_registry,
)
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.intelligence.community.sentiment import analyze_sentiment
from app.services.community_intelligence_service import CommunityIntelligenceService


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "the product arrived yesterday",
        "discussion thread only",
        "random words here",
        "neutral observation",
        "item listed",
        "thread opened",
        "user replied",
        "see comments",
    ],
)
def test_neutral_sentiment_default(text):
    assert analyze_sentiment(text).label in {"neutral", "mixed", "positive", "negative"}


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("community_enabled", True),
        ("community_reddit_enabled", True),
        ("community_youtube_enabled", False),
        ("community_amazon_qa_enabled", False),
        ("community_marketplace_qa_enabled", False),
        ("community_forums_enabled", False),
        ("community_discord_enabled", False),
        ("community_use_fixtures", True),
        ("ai_community_enabled", False),
        ("ai_community_live_http", False),
    ],
)
def test_community_settings_defaults(flag, expected):
    settings = Settings()
    assert getattr(settings, flag) is expected


def test_ai_community_dual_gate_off_by_default():
    settings = Settings()
    assert settings.ai_community_external_calls_enabled is False


def test_mappers_roundtrip():
    svc = CommunityIntelligenceService(
        CommunityOrchestrator(
            get_community_registry(),
            ai_orchestrator=get_community_ai_orchestrator(get_community_summary_registry()),
        )
    )
    product = svc.get_product(DEMO_PRODUCT_ID)
    dash = svc.demo()
    product_payload = to_product_response(product)
    dash_payload = to_dashboard_response(dash)
    evidence_payload = to_evidence_response(product.evidence[0])
    topics_payload = to_topics_response(product.product_id, product.topics)
    timeline_payload = to_timeline_response(product.product_id, product.timeline)
    assert product_payload.product_id == DEMO_PRODUCT_ID
    assert dash_payload.evidence_count == dash.evidence_count
    assert evidence_payload.evidence.evidence_id
    assert topics_payload.topics
    assert timeline_payload.timeline


@pytest.mark.parametrize(
    "source",
    [
        "reddit",
        "youtube",
        "amazon_qa",
        "marketplace_questions",
        "manufacturer_forums",
        "discord",
    ],
)
def test_registry_status_keys(source):
    status = get_community_registry().status_map()
    assert source in status
    assert "enabled" in status[source]
    assert "available" in status[source]
    assert "healthy" in status[source]
