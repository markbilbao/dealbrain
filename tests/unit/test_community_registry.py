"""Tests for CommunityRegistry and connector registration."""

from __future__ import annotations

import pytest

from app.infrastructure.community import (
    AmazonQACommunityProvider,
    DiscordCommunityProvider,
    ManufacturerForumsCommunityProvider,
    MarketplaceQuestionsCommunityProvider,
    RedditCommunityProvider,
    YouTubeCommunityProvider,
)
from app.intelligence.community.registry import CommunityRegistry


def _registry() -> CommunityRegistry:
    return CommunityRegistry(
        [
            RedditCommunityProvider(enabled=True),
            YouTubeCommunityProvider(enabled=False),
            AmazonQACommunityProvider(enabled=False),
            MarketplaceQuestionsCommunityProvider(enabled=False),
            ManufacturerForumsCommunityProvider(enabled=False),
            DiscordCommunityProvider(enabled=False),
        ]
    )


def test_registry_lists_all_sources():
    reg = _registry()
    assert set(reg.sources()) == {
        "reddit",
        "youtube",
        "amazon_qa",
        "marketplace_questions",
        "manufacturer_forums",
        "discord",
    }


def test_registry_get_known_and_unknown():
    reg = _registry()
    assert reg.get("reddit") is not None
    assert reg.get("missing") is None


def test_registry_enabled_only_reddit_by_default_config():
    reg = _registry()
    enabled = [p.source_name for p in reg.enabled()]
    assert enabled == ["reddit"]


def test_registry_available_includes_fixture_backed():
    reg = _registry()
    available = {p.source_name for p in reg.available()}
    assert "reddit" in available
    assert "youtube" in available  # fixtures when unavailable
    assert "discord" not in available


def test_registry_status_map_shape():
    status = _registry().status_map()
    assert status["reddit"]["enabled"] is True
    assert status["discord"]["enabled"] is False
    assert status["reddit"]["healthy"] is True


def test_registry_register_overrides():
    reg = CommunityRegistry()
    first = RedditCommunityProvider(enabled=False)
    second = RedditCommunityProvider(enabled=True)
    reg.register(first)
    reg.register(second)
    assert reg.get("reddit") is second


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
def test_registry_contains_each_source(source):
    assert _registry().get(source) is not None


def test_registry_all_count():
    assert len(_registry().all()) == 6
