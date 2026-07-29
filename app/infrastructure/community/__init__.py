"""Community source connectors (provider-neutral adapters)."""

from app.infrastructure.community.amazon_qa import AmazonQACommunityProvider
from app.infrastructure.community.discord import DiscordCommunityProvider
from app.infrastructure.community.manufacturer_forums import ManufacturerForumsCommunityProvider
from app.infrastructure.community.marketplace_questions import MarketplaceQuestionsCommunityProvider
from app.infrastructure.community.reddit import RedditCommunityProvider
from app.infrastructure.community.transports import (
    DisabledCommunityTransport,
    MockCommunityTransport,
    ScriptedCommunityTransport,
)
from app.infrastructure.community.youtube import YouTubeCommunityProvider

__all__ = [
    "AmazonQACommunityProvider",
    "DisabledCommunityTransport",
    "DiscordCommunityProvider",
    "ManufacturerForumsCommunityProvider",
    "MarketplaceQuestionsCommunityProvider",
    "MockCommunityTransport",
    "RedditCommunityProvider",
    "ScriptedCommunityTransport",
    "YouTubeCommunityProvider",
]
