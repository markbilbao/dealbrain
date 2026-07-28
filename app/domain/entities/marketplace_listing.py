"""Marketplace listing value objects for cross-marketplace intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AvailabilityStatus(StrEnum):
    """Normalized stock status across marketplaces."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LIMITED = "limited"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MarketplaceListing:
    """Normalized listing returned by a MarketplaceConnector."""

    marketplace: str
    product_id: str
    title: str
    price: float
    currency: str
    seller: str
    rating: float | None
    url: str
    availability: AvailabilityStatus = AvailabilityStatus.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        """Serialize the public listing fields."""
        return {
            "marketplace": self.marketplace,
            "product_id": self.product_id,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "seller": self.seller,
            "rating": self.rating,
            "url": self.url,
            "availability": self.availability.value,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceSearchResult:
    """Aggregated search outcome across one or more connectors."""

    query: str
    results: tuple[MarketplaceListing, ...] = ()
