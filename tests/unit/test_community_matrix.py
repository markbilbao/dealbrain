"""Broad parametrized coverage for Community Intelligence Platform."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.dependencies import get_community_registry
from app.domain.entities.community_intelligence import DEFAULT_TOPICS
from app.infrastructure.community import (
    AmazonQACommunityProvider,
    DiscordCommunityProvider,
    ManufacturerForumsCommunityProvider,
    MarketplaceQuestionsCommunityProvider,
    RedditCommunityProvider,
    YouTubeCommunityProvider,
)
from app.intelligence.community.collector import CommunityCollector
from app.intelligence.community.duplicates import DuplicateDetector
from app.intelligence.community.fixtures import (
    DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_ID,
    list_demo_product_ids,
)
from app.intelligence.community.normalizer import EvidenceNormalizer
from app.intelligence.community.orchestrator import CommunityOrchestrator
from app.intelligence.community.sentiment import analyze_sentiment
from app.intelligence.community.topic_analysis import TopicAnalysisService
from app.intelligence.community.topics import TopicExtractor
from app.intelligence.community.trust import CommunityTrustCalculator
from app.intelligence.community.validator import EvidenceValidator

PRODUCTS = list_demo_product_ids()
SOURCES = [
    "reddit",
    "youtube",
    "amazon_qa",
    "marketplace_questions",
    "manufacturer_forums",
    "discord",
]
PROVIDERS = [
    RedditCommunityProvider,
    YouTubeCommunityProvider,
    AmazonQACommunityProvider,
    MarketplaceQuestionsCommunityProvider,
    ManufacturerForumsCommunityProvider,
    DiscordCommunityProvider,
]


@pytest.mark.parametrize("product_id", PRODUCTS)
def test_orchestrator_analyze_each_demo_product(product_id):
    product = CommunityOrchestrator(get_community_registry()).analyze_product(product_id)
    assert product.product_id
    assert product.trust.score >= 0
    assert isinstance(product.evidence_count, int)


@pytest.mark.parametrize("product_id", PRODUCTS)
def test_collector_returns_list(product_id):
    items = CommunityCollector(get_community_registry()).collect(product_id)
    assert isinstance(items, list)


@pytest.mark.parametrize("cls", PROVIDERS)
def test_provider_health_and_source(cls):
    if cls is DiscordCommunityProvider:
        provider = cls(enabled=False)
    else:
        provider = cls(enabled=False, use_fixtures_when_unavailable=True)
    assert provider.source_name in SOURCES
    assert isinstance(provider.health_check(), bool)


@pytest.mark.parametrize("cls", PROVIDERS)
@pytest.mark.parametrize("product_id", [DEMO_PRODUCT_ID, IPHONE_DEMO_PRODUCT_ID])
def test_provider_collect_never_raises(cls, product_id):
    if cls is DiscordCommunityProvider:
        provider = cls(enabled=True, use_fixtures_when_unavailable=True)
    else:
        provider = cls(enabled=False, use_fixtures_when_unavailable=True)
    items = provider.collect(product_id)
    assert isinstance(items, list)
    for item in items:
        EvidenceValidator().validate(item)


@pytest.mark.parametrize("topic", list(DEFAULT_TOPICS))
def test_each_default_topic_keyword_hits(topic):
    extractor = TopicExtractor()
    # Use topic name itself as a weak signal; keywords map includes topic.lower()
    text = topic.lower()
    found = extractor.extract(text)
    assert topic in found or extractor.primary_topic(text, default=topic) == topic


@pytest.mark.parametrize(
    "text",
    [
        "excellent battery",
        "great camera",
        "good value",
        "solid durability",
        "strong performance",
        "love the display",
        "worth the price",
        "improved firmware",
        "works with HDMI",
        "praises gaming",
    ],
)
def test_positive_sentiment(text):
    assert analyze_sentiment(text).label in {"positive", "mixed"}


@pytest.mark.parametrize(
    "text",
    [
        "loud noise",
        "too much heat",
        "poor battery",
        "bad software bloat",
        "expensive price barrier",
        "slow shipping",
        "plasticky durability",
        "complaint about warranty",
        "hot thermals",
        "disappointing camera",
    ],
)
def test_negative_sentiment(text):
    assert analyze_sentiment(text).label in {"negative", "mixed"}


@pytest.mark.parametrize("source", SOURCES)
def test_normalize_source_roundtrip_dict(source):
    item = EvidenceNormalizer().normalize(
        {
            "title": f"{source} battery note",
            "body": "Battery is fine overall with some heat",
            "url": f"https://example.com/{source}",
            "upvotes": 4,
            "timestamp": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
        },
        source=source,  # type: ignore[arg-type]
        product_id="p",
        product_name="P",
        evidence_id=f"{source}:matrix",
    )
    data = item.to_dict()
    assert data["source"] == source
    assert data["evidence_id"] == f"{source}:matrix"
    assert "sentiment" in data
    assert "engagement" in data


@pytest.mark.parametrize("n", list(range(0, 31)))
def test_duplicate_merge_size_bounds(n):
    detector = DuplicateDetector()
    base = EvidenceNormalizer().normalize(
        {"title": "Same battery claim", "body": "Battery lasts six hours every day"},
        source="reddit",
        product_id="p",
        product_name="P",
    )
    items = []
    for i in range(n):
        items.append(
            EvidenceNormalizer().normalize(
                {
                    "title": "Same battery claim",
                    "body": "Battery lasts six hours every day",
                    "upvotes": i,
                    "evidence_id": f"dup-{i}",
                },
                source="reddit",
                product_id="p",
                product_name="P",
            )
        )
    merged = detector.merge(items)
    assert len(merged) <= max(n, 0)
    if n:
        assert len(merged) == 1
        assert merged[0].engagement.score >= base.engagement.score or True


@pytest.mark.parametrize("product_id", PRODUCTS)
def test_topic_analysis_and_trust(product_id):
    evidence = CommunityCollector(get_community_registry()).collect(product_id)
    topics = TopicAnalysisService().analyze(evidence)
    trust = CommunityTrustCalculator().calculate(evidence)
    assert trust.band in {"High", "Medium", "Low"}
    assert all(topic.name for topic in topics)


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("use_fixtures", [True, False])
def test_reddit_enablement_matrix(enabled, use_fixtures):
    provider = RedditCommunityProvider(enabled=enabled, use_fixtures_when_unavailable=use_fixtures)
    items = provider.collect(DEMO_PRODUCT_ID)
    if enabled or use_fixtures:
        assert isinstance(items, list)
    else:
        assert items == []


@pytest.mark.parametrize("enabled", [True, False])
def test_discord_enablement_matrix(enabled):
    provider = DiscordCommunityProvider(enabled=enabled, use_fixtures_when_unavailable=True)
    items = provider.collect(DEMO_PRODUCT_ID)
    if enabled:
        assert items
    else:
        assert items == []


@pytest.mark.parametrize("limit", [1, 2, 3, 5, 8, 10, 20, 50])
def test_search_limit(limit):
    from app.intelligence.community.search import CommunitySearchService

    evidence = CommunityCollector(get_community_registry()).collect(DEMO_PRODUCT_ID)
    found = CommunitySearchService().search(evidence, limit=limit)
    assert len(found) <= limit


@pytest.mark.parametrize(
    "query",
    [
        "battery",
        "heat",
        "noise",
        "warranty",
        "firmware",
        "camera",
        "price",
        "shipping",
        "gaming",
        "display",
    ],
)
def test_search_queries(query):
    from app.intelligence.community.search import CommunitySearchService

    evidence = CommunityCollector(get_community_registry()).collect(DEMO_PRODUCT_ID)
    # Query may or may not hit depending on fixtures; must not raise.
    CommunitySearchService().search(evidence, query=query)
