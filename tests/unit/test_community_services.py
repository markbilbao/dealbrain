"""Community intelligence services: dashboard, timeline, search, health, stats."""

from __future__ import annotations

import pytest

from app.core.dependencies import (
    get_community_ai_orchestrator,
    get_community_registry,
    get_community_summary_registry,
)
from app.intelligence.community.collector import CommunityCollector
from app.intelligence.community.confidence import CommunityConfidenceService, confidence_band
from app.intelligence.community.dashboard import CommunityDashboardService
from app.intelligence.community.health import CommunityHealthService
from app.intelligence.community.metrics import CommunitySourceMetricsService
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.intelligence.community.recommendation import CommunityRecommendationService
from app.intelligence.community.search import CommunitySearchService
from app.intelligence.community.statistics import CommunityStatisticsService
from app.intelligence.community.timeline import CommunityTimelineService
from app.intelligence.community.topic_analysis import TopicAnalysisService
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID
from app.services.community_intelligence_service import CommunityIntelligenceService


def _service() -> CommunityIntelligenceService:
    registry = get_community_registry()
    orch = CommunityOrchestrator(
        registry,
        ai_orchestrator=get_community_ai_orchestrator(get_community_summary_registry()),
    )
    return CommunityIntelligenceService(orch)


def test_demo_dashboard_fields():
    dash = _service().demo()
    assert dash.product_id == DEMO_PRODUCT_ID
    assert 0 <= dash.trust.score <= 100
    assert dash.evidence_count > 0
    assert dash.topics
    assert dash.source_breakdown
    assert dash.summary.most_praised or dash.summary.most_complaints
    assert dash.recent_discussions
    assert dash.warnings


def test_product_intelligence():
    product = _service().get_product(DEMO_PRODUCT_ID)
    assert product.evidence_count == len(product.evidence)
    assert product.timeline
    assert product.summary.limitations


def test_get_evidence_and_topics_timeline():
    svc = _service()
    product = svc.get_product(DEMO_PRODUCT_ID)
    evidence = svc.get_evidence(product.evidence[0].evidence_id)
    assert evidence.evidence_id == product.evidence[0].evidence_id
    assert svc.get_topics(DEMO_PRODUCT_ID)
    assert svc.get_timeline(DEMO_PRODUCT_ID)


def test_evidence_not_found():
    with pytest.raises(Exception):
        _service().get_evidence("missing-evidence-id-xyz")


def test_blank_product_validation():
    with pytest.raises(Exception):
        _service().get_product("  ")


def test_evidence_explorer_links_topics():
    explorer = _service().evidence_explorer(DEMO_PRODUCT_ID)
    assert explorer["insights"]
    first = explorer["insights"][0]
    assert "supported_by" in first
    assert first["confidence"]


def test_shopping_assistant_evidence_slice():
    items = _service().shopping_assistant_evidence([DEMO_PRODUCT_ID], limit_per_product=3)
    assert 0 < len(items) <= 3


def test_meta_includes_connectors():
    meta = _service().meta()
    assert "reddit" in meta["connectors"]
    assert meta["data_status"] == "mock"


def test_collector_by_source():
    registry = get_community_registry()
    by_source = CommunityCollector(registry).collect_by_source(DEMO_PRODUCT_ID)
    assert "reddit" in by_source
    assert by_source["reddit"]


def test_timeline_and_statistics():
    product = _service().get_product(DEMO_PRODUCT_ID)
    timeline = CommunityTimelineService().build(list(product.evidence))
    stats = CommunityStatisticsService().summarize(list(product.evidence), list(product.topics))
    assert timeline
    assert stats["evidence_count"] == product.evidence_count


def test_search_filters():
    product = _service().get_product(DEMO_PRODUCT_ID)
    search = CommunitySearchService()
    by_topic = search.search(list(product.evidence), topic="Battery")
    assert all(item.topic == "Battery" for item in by_topic)
    by_source = search.search(list(product.evidence), source="reddit")
    assert all(item.source == "reddit" for item in by_source)
    by_query = search.search(list(product.evidence), query="battery")
    assert by_query


def test_health_service():
    health = CommunityHealthService(get_community_registry()).check()
    assert health["total_connectors"] == 6
    assert health["overall"] in {"ok", "degraded"}


def test_metrics_and_topic_analysis():
    registry = get_community_registry()
    evidence = CommunityCollector(registry).collect(DEMO_PRODUCT_ID)
    topics = TopicAnalysisService().analyze(evidence)
    metrics = CommunitySourceMetricsService().for_all(registry.all(), evidence)
    assert topics
    assert metrics
    assert TopicAnalysisService().positive_topics(topics) is not None


def test_recommendation_service():
    product = _service().get_product(DEMO_PRODUCT_ID)
    rec = CommunityRecommendationService()
    buy = rec.who_should_buy(list(product.topics), list(product.evidence))
    avoid = rec.who_should_avoid(list(product.topics), list(product.evidence))
    advice = rec.buying_advice(list(product.topics), list(product.evidence))
    assert isinstance(buy, list)
    assert isinstance(avoid, list)
    assert isinstance(advice, list)


@pytest.mark.parametrize(
    ("score", "band"),
    [(0.9, "High"), (0.6, "Medium"), (0.2, "Low"), (0.75, "High"), (0.5, "Medium")],
)
def test_confidence_band(score, band):
    assert confidence_band(score) == band


def test_confidence_service_for_ids():
    product = _service().get_product(DEMO_PRODUCT_ID)
    ids = [product.evidence[0].evidence_id]
    band = CommunityConfidenceService().for_evidence_ids(list(product.evidence), ids)
    assert band in {"High", "Medium", "Low"}


def test_dashboard_from_product():
    product = _service().get_product(DEMO_PRODUCT_ID)
    dash = CommunityDashboardService().from_product(product)
    assert dash.evidence_count == product.evidence_count


@pytest.mark.parametrize("mode", [None, "economy", "balanced", "maximum"])
def test_analyze_modes(mode):
    product = _service().get_product(DEMO_PRODUCT_ID, mode=mode)
    assert product.summary is not None
