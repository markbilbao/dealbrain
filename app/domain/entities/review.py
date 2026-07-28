"""Review & Rating Intelligence domain entities and value objects.

Identifiers and timestamps are injected by callers — core types never generate
random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ReviewSnapshot:
    """Point-in-time marketplace review / rating observation for a product."""

    snapshot_id: str
    product_id: str
    marketplace: str
    average_rating: float
    review_count: int
    five_star_count: int
    four_star_count: int
    three_star_count: int
    two_star_count: int
    one_star_count: int
    seller_rating: float | None
    seller_followers: int | None
    seller_products: int | None
    collected_at: datetime
    product_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "product_id": self.product_id,
            "product_label": self.product_label,
            "marketplace": self.marketplace,
            "average_rating": self.average_rating,
            "review_count": self.review_count,
            "five_star_count": self.five_star_count,
            "four_star_count": self.four_star_count,
            "three_star_count": self.three_star_count,
            "two_star_count": self.two_star_count,
            "one_star_count": self.one_star_count,
            "seller_rating": self.seller_rating,
            "seller_followers": self.seller_followers,
            "seller_products": self.seller_products,
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MarketplaceReviewSummary:
    """Latest review headline for one marketplace."""

    marketplace: str
    rating: float
    reviews: int
    seller_rating: float | None = None
    seller_followers: int | None = None
    seller_products: int | None = None
    five_star_count: int = 0
    four_star_count: int = 0
    three_star_count: int = 0
    two_star_count: int = 0
    one_star_count: int = 0
    collected_at: datetime | None = None
    snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "marketplace": self.marketplace,
            "rating": self.rating,
            "reviews": self.reviews,
            "seller_rating": self.seller_rating,
            "seller_followers": self.seller_followers,
            "seller_products": self.seller_products,
            "five_star_count": self.five_star_count,
            "four_star_count": self.four_star_count,
            "three_star_count": self.three_star_count,
            "two_star_count": self.two_star_count,
            "one_star_count": self.one_star_count,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class MarketplaceReviewComparison:
    """Cross-marketplace rating comparison for one product."""

    product: str
    product_id: str
    marketplaces: tuple[MarketplaceReviewSummary, ...]
    overall_rating: float | None = None
    total_review_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "product_id": self.product_id,
            "marketplaces": [item.to_dict() for item in self.marketplaces],
            "overall_rating": self.overall_rating,
            "total_review_count": self.total_review_count,
        }


@dataclass(frozen=True, slots=True)
class ReviewCollectionResult:
    """Outcome of a mock review collection pass."""

    product_id: str
    product: str
    snapshots: tuple[ReviewSnapshot, ...]
    collected_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product": self.product,
            "snapshots": [snap.to_dict() for snap in self.snapshots],
            "collected_count": len(self.snapshots),
            "collected_at": self.collected_at.isoformat(),
        }
