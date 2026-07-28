"""Marketplace Connector port — pluggable marketplace adapters.

Implementations provide search and product lookup for a single marketplace
and normalize raw listings into domain value objects. No scraping or live
API calls are required at this layer; mocked adapters are valid.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing


class MarketplaceConnector(ABC):
    """Abstract contract for a single marketplace data source.

    Concrete adapters (Shopee, Lazada, Amazon, eBay, Facebook Marketplace,
    Carousell, …) implement this port and may be swapped independently.
    """

    @property
    @abstractmethod
    def marketplace_name(self) -> str:
        """Stable marketplace identifier (e.g. ``shopee``, ``lazada``)."""

    @abstractmethod
    def search(self, query: str) -> list[MarketplaceListing]:
        """Search listings matching ``query`` on this marketplace."""

    @abstractmethod
    def get_product(self, product_id: str) -> MarketplaceListing | None:
        """Fetch a single listing by marketplace-native product id."""

    @abstractmethod
    def normalize_listing(self, raw: Mapping[str, Any]) -> MarketplaceListing:
        """Convert marketplace-specific raw data into a normalized listing."""

    @abstractmethod
    def get_price(self, product_id: str) -> float | None:
        """Return the current price for ``product_id``, or ``None`` if unknown."""

    @abstractmethod
    def get_availability(self, product_id: str) -> AvailabilityStatus:
        """Return stock availability for ``product_id``."""
