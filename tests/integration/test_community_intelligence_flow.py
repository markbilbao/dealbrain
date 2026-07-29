"""End-to-end Community Intelligence flow (in-memory, no live HTTP)."""

from __future__ import annotations

from app.core.dependencies import (
    get_community_ai_orchestrator,
    get_community_registry,
    get_community_summary_registry,
)
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.services.community_intelligence_service import CommunityIntelligenceService
from app.services.shopping_assistant_service import ShoppingAssistantService


def _service() -> CommunityIntelligenceService:
    return CommunityIntelligenceService(
        CommunityOrchestrator(
            get_community_registry(),
            ai_orchestrator=get_community_ai_orchestrator(get_community_summary_registry()),
        )
    )


def test_end_to_end_dashboard_to_evidence_explorer():
    svc = _service()
    dash = svc.demo()
    assert dash.trust.score > 0
    product = svc.get_product(dash.product_id)
    evidence = svc.get_evidence(product.evidence[0].evidence_id)
    explorer = svc.evidence_explorer(product.product_id)
    assert evidence.product_id == product.product_id
    assert explorer["insights"]
    assert any(item["supported_by"] for item in explorer["insights"])


def test_end_to_end_timeline_and_topics_consistent():
    svc = _service()
    product = svc.get_product(DEMO_PRODUCT_ID)
    topics = svc.get_topics(DEMO_PRODUCT_ID)
    timeline = svc.get_timeline(DEMO_PRODUCT_ID)
    assert len(topics) == len(product.topics)
    assert len(timeline) == len(product.timeline)
    topic_names = {item.name for item in topics}
    for event in timeline:
        assert set(event.topics).issubset(topic_names) or event.topics


def test_end_to_end_shopping_assistant_uses_community():
    community = _service()
    assistant = ShoppingAssistantService(community_service=community)
    response = assistant.query(
        {"query": "What are community complaints about ASUS TUF A15 battery and heat?"}
    )
    assert any(item.type == "community" for item in response.evidence)
    assert response.answer


def test_end_to_end_disabled_discord_not_required():
    svc = _service()
    product = svc.get_product(DEMO_PRODUCT_ID)
    discord_metrics = [m for m in product.source_metrics if m.source == "discord"]
    assert discord_metrics
    assert discord_metrics[0].status == "disabled"
    assert discord_metrics[0].evidence_count == 0


def test_end_to_end_summary_cites_evidence():
    product = _service().get_product(DEMO_PRODUCT_ID)
    cited = (
        list(product.summary.most_praised)
        + list(product.summary.most_complaints)
        + list(product.summary.buying_advice)
    )
    assert cited
    for insight in cited:
        assert insight.evidence_ids
        for eid in insight.evidence_ids:
            assert any(item.evidence_id == eid for item in product.evidence)
