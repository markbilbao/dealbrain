"""Unit tests for mock review collectors."""

from __future__ import annotations

from datetime import UTC, datetime

from app.intelligence.reviews import (
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.intelligence.reviews.fixtures import IPHONE_DEMO_PRODUCT_ID

FIXED_NOW = datetime(2026, 7, 29, 7, 0, tzinfo=UTC)


def test_mock_collectors_return_realistic_demo_values() -> None:
    collectors = [
        MockShopeeReviewCollector(),
        MockLazadaReviewCollector(),
        MockTikTokShopReviewCollector(),
        MockAmazonReviewCollector(),
    ]
    expected = {
        "Shopee": (4.8, 12431, 4.9, 18000),
        "Lazada": (4.7, 9821, 4.8, 12500),
        "TikTok Shop": (4.6, 5432, 4.7, 92000),
        "Amazon": (4.5, 15680, 4.6, None),
    }
    for collector in collectors:
        assert collector.health_check() is True
        snap = collector.collect(
            IPHONE_DEMO_PRODUCT_ID,
            product_label="iPhone 17 Pro Max",
            snapshot_id=f"id-{collector.marketplace_name}",
            collected_at=FIXED_NOW,
        )
        rating, reviews, seller, followers = expected[collector.marketplace_name]
        assert snap.average_rating == rating
        assert snap.review_count == reviews
        assert snap.seller_rating == seller
        assert snap.seller_followers == followers
        assert (
            snap.five_star_count
            + snap.four_star_count
            + snap.three_star_count
            + snap.two_star_count
            + snap.one_star_count
            == snap.review_count
        )
