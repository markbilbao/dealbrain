"""Connector / mock transport tests."""

from __future__ import annotations

import pytest

from app.infrastructure.community import (
    AmazonQACommunityProvider,
    DiscordCommunityProvider,
    ManufacturerForumsCommunityProvider,
    MarketplaceQuestionsCommunityProvider,
    MockCommunityTransport,
    RedditCommunityProvider,
    ScriptedCommunityTransport,
    YouTubeCommunityProvider,
)
from app.infrastructure.community.transports import DisabledCommunityTransport
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID, IPHONE_DEMO_PRODUCT_ID

COMMON_KEYS = {
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
}


def test_reddit_collects_threads_and_comments():
    provider = RedditCommunityProvider(enabled=True)
    items = provider.collect(DEMO_PRODUCT_ID)
    assert items
    assert all(item.source == "reddit" for item in items)
    assert any("comment" in item.evidence_id or item.author for item in items)
    meta = provider.thread_metadata("r_tuf_battery_1")
    assert meta["upvotes"] == 142
    assert meta["comment_count"] == 38
    assert meta["permalink"]


def test_reddit_search_threads_filters():
    provider = RedditCommunityProvider(enabled=True)
    hits = provider.search_threads(DEMO_PRODUCT_ID, query="battery")
    assert hits
    assert all("battery" in str(h.get("title", "")).lower() or "battery" in str(h.get("body", "")).lower() for h in hits)


def test_reddit_extract_comments():
    provider = RedditCommunityProvider(enabled=True)
    comments = provider.extract_comments("r_tuf_battery_1")
    assert len(comments) >= 2


def test_reddit_disabled_without_fixtures_empty():
    provider = RedditCommunityProvider(
        enabled=False,
        transport=DisabledCommunityTransport(),
        use_fixtures_when_unavailable=False,
    )
    assert provider.collect(DEMO_PRODUCT_ID) == []


def test_reddit_uses_transport_when_items_present():
    transport = ScriptedCommunityTransport(
        [
            {
                "items": [
                    {
                        "thread_id": "live1",
                        "title": "Live battery thread",
                        "body": "Battery from API",
                        "upvotes": 3,
                        "comment_count": 1,
                        "url": "https://reddit.example/live1",
                        "permalink": "https://reddit.example/live1",
                        "created_utc": 1717200000,
                        "comments": [],
                    }
                ]
            }
        ]
    )
    provider = RedditCommunityProvider(
        enabled=True,
        transport=transport,
        use_fixtures_when_unavailable=False,
    )
    items = provider.collect(DEMO_PRODUCT_ID)
    assert any(item.evidence_id.endswith("live1") for item in items)


@pytest.mark.parametrize(
    ("cls", "source", "enabled"),
    [
        (YouTubeCommunityProvider, "youtube", False),
        (AmazonQACommunityProvider, "amazon_qa", False),
        (MarketplaceQuestionsCommunityProvider, "marketplace_questions", False),
        (ManufacturerForumsCommunityProvider, "manufacturer_forums", False),
    ],
)
def test_mock_adapters_return_normalized_fixtures(cls, source, enabled):
    provider = cls(enabled=enabled, use_fixtures_when_unavailable=True)
    items = provider.collect(DEMO_PRODUCT_ID)
    assert items
    for item in items:
        assert item.source == source
        payload = item.to_dict()
        assert COMMON_KEYS.issubset(payload.keys())


def test_youtube_fields_present():
    items = YouTubeCommunityProvider(use_fixtures_when_unavailable=True).collect(DEMO_PRODUCT_ID)
    assert any(item.engagement.views > 0 for item in items)
    assert any("youtube:" in item.evidence_id for item in items)


def test_amazon_qa_helpful_votes():
    items = AmazonQACommunityProvider(use_fixtures_when_unavailable=True).collect(DEMO_PRODUCT_ID)
    assert any(item.engagement.helpful_votes > 0 for item in items)


def test_marketplace_includes_community_responses():
    items = MarketplaceQuestionsCommunityProvider(use_fixtures_when_unavailable=True).collect(
        DEMO_PRODUCT_ID
    )
    assert len(items) >= 2


def test_forums_include_accepted_answers():
    items = ManufacturerForumsCommunityProvider(use_fixtures_when_unavailable=True).collect(
        DEMO_PRODUCT_ID
    )
    assert any("Accepted answer" in item.title or "Firmware" in item.topic for item in items)


def test_discord_disabled_by_default():
    provider = DiscordCommunityProvider()
    assert provider.is_enabled() is False
    assert provider.is_available() is False
    assert provider.collect(DEMO_PRODUCT_ID) == []


def test_discord_can_enable_with_fixtures():
    provider = DiscordCommunityProvider(enabled=True, use_fixtures_when_unavailable=True)
    items = provider.collect(DEMO_PRODUCT_ID)
    assert items
    assert all(item.source == "discord" for item in items)


def test_mock_transport_records_calls():
    transport = MockCommunityTransport({" /x": {"items": []}})
    transport.fetch("/health", params={"a": 1})
    assert transport.calls


def test_disabled_transport_raises():
    with pytest.raises(Exception):
        DisabledCommunityTransport().fetch("/nope")


@pytest.mark.parametrize("product_id", [DEMO_PRODUCT_ID, IPHONE_DEMO_PRODUCT_ID, "sa-laptop-loq-15"])
def test_reddit_supports_multiple_products(product_id):
    items = RedditCommunityProvider(enabled=True).collect(product_id)
    assert isinstance(items, list)


@pytest.mark.parametrize("method", ["health_check", "is_enabled", "is_available", "source_name"])
def test_provider_surface_methods(method):
    provider = RedditCommunityProvider(enabled=True)
    value = getattr(provider, method)
    value = value() if callable(value) else value
    assert value is not None
