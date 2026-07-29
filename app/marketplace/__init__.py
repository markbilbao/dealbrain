"""Marketplace Data Synchronization — Sprint 18.

Collect, import, normalize, synchronize, and monitor marketplace product data
with explicit source modes (fixture / imported / live). No unofficial scraping,
no real marketplace credentials, no external scheduler.
"""

from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.registry import MarketplaceConnectorRegistry

__all__ = [
    "FixtureMarketplaceConnector",
    "ImportedMarketplaceConnector",
    "InMemoryMarketplaceDataRepository",
    "MarketplaceConnectorRegistry",
    "MockLiveMarketplaceConnector",
]
