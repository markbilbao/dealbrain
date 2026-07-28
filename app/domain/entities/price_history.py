"""Price History domain value objects — stored observations only.

Statistics and trends are derived exclusively from recorded snapshots.
No fabricated history, currency conversion, or future price predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.entities.marketplace_listing import AvailabilityStatus


class PriceTrend(StrEnum):
    """Deterministic trend classification from stored observations."""

    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """A single timestamped marketplace price observation."""

    snapshot_id: UUID
    canonical_product_id: str
    marketplace: str
    listing_id: str
    currency: str
    item_price: float
    shipping_cost: float
    total_cost: float
    availability: AvailabilityStatus
    observed_at: datetime
    seller_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize public snapshot fields."""
        return {
            "snapshot_id": str(self.snapshot_id),
            "canonical_product_id": self.canonical_product_id,
            "marketplace": self.marketplace,
            "listing_id": self.listing_id,
            "seller_name": self.seller_name,
            "currency": self.currency,
            "item_price": self.item_price,
            "shipping_cost": self.shipping_cost,
            "total_cost": self.total_cost,
            "availability": self.availability.value,
            "observed_at": self.observed_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PriceStatistics:
    """Aggregate statistics computed from stored snapshots of one currency."""

    currency: str
    current_total_cost: float
    lowest_recorded_total_cost: float
    highest_recorded_total_cost: float
    average_total_cost: float
    median_total_cost: float
    observation_count: int
    first_observed: datetime
    last_observed: datetime
    absolute_change: float
    percentage_change: float
    trend: PriceTrend

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_total_cost": self.current_total_cost,
            "lowest_recorded_total_cost": self.lowest_recorded_total_cost,
            "highest_recorded_total_cost": self.highest_recorded_total_cost,
            "average_total_cost": self.average_total_cost,
            "median_total_cost": self.median_total_cost,
            "observation_count": self.observation_count,
            "first_observed": self.first_observed.isoformat(),
            "last_observed": self.last_observed.isoformat(),
            "absolute_change": self.absolute_change,
            "percentage_change": self.percentage_change,
            "trend": self.trend.value,
        }


@dataclass(frozen=True, slots=True)
class MarketplacePriceSummary:
    """Per-marketplace rollup from stored observations."""

    marketplace: str
    latest_total_cost: float
    lowest_recorded_total_cost: float
    average_total_cost: float
    observation_count: int
    latest_availability: AvailabilityStatus
    last_observed: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "marketplace": self.marketplace,
            "latest_total_cost": self.latest_total_cost,
            "lowest_recorded_total_cost": self.lowest_recorded_total_cost,
            "average_total_cost": self.average_total_cost,
            "observation_count": self.observation_count,
            "latest_availability": self.latest_availability.value,
            "last_observed": self.last_observed.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class PriceHistory:
    """Ordered collection of stored price observations for a product or listing."""

    canonical_product_id: str | None
    listing_id: str | None
    currency: str
    snapshots: tuple[PriceSnapshot, ...]
    statistics: PriceStatistics | None
    marketplace_summaries: tuple[MarketplacePriceSummary, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_product_id": self.canonical_product_id,
            "listing_id": self.listing_id,
            "currency": self.currency,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "history": [snapshot.to_dict() for snapshot in self.snapshots],
            "marketplace_summaries": [
                summary.to_dict() for summary in self.marketplace_summaries
            ],
        }


@dataclass(frozen=True, slots=True)
class PriceHistorySearchResult:
    """Search pipeline outcome: recorded current observations + history stats."""

    query: str
    currency: str
    statistics: PriceStatistics | None
    history: tuple[PriceSnapshot, ...]
    marketplace_summaries: tuple[MarketplacePriceSummary, ...]
    canonical_product_id: str | None = None
    is_mock_history: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "currency": self.currency,
            "statistics": self.statistics.to_dict() if self.statistics else None,
            "history": [snapshot.to_dict() for snapshot in self.history],
            "marketplace_summaries": [
                summary.to_dict() for summary in self.marketplace_summaries
            ],
        }
