"""Integration flow: collect → latest → history → compare across marketplaces."""

from __future__ import annotations

from datetime import UTC, datetime

from app.intelligence.reviews import (
    InMemoryReviewRepository,
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.intelligence.reviews.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.services.review_service import ReviewService

FIXED_NOW = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


def test_review_intelligence_end_to_end_flow() -> None:
    repo = InMemoryReviewRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"flow-rev-{counter['n']}"

    service = ReviewService(
        repo,
        [
            MockShopeeReviewCollector(),
            MockLazadaReviewCollector(),
            MockTikTokShopReviewCollector(),
            MockAmazonReviewCollector(),
        ],
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        seed_demo_history=True,
    )

    collected = service.collect_reviews(
        PRODUCT_ID,
        product_label=IPHONE_DEMO_PRODUCT_LABEL,
    )
    assert collected.collected_at == FIXED_NOW
    assert len(collected.snapshots) == 4

    latest = service.latest_reviews(PRODUCT_ID)
    assert len(latest) == 4

    history = service.review_history(PRODUCT_ID)
    assert len(history) >= 4
    # History includes older seeded waves plus the current collection.
    assert any(snap.collected_at < FIXED_NOW for snap in history)
    assert any(snap.collected_at == FIXED_NOW for snap in history)

    comparison = service.compare_marketplaces(PRODUCT_ID)
    assert comparison.product == IPHONE_DEMO_PRODUCT_LABEL
    assert comparison.product_id == PRODUCT_ID
    assert comparison.total_review_count == service.total_review_count(PRODUCT_ID)
    assert comparison.overall_rating == service.overall_rating(PRODUCT_ID)
    assert 4.0 <= (comparison.overall_rating or 0) <= 5.0

    # Second collection appends another current wave without re-seeding history.
    second = service.collect_reviews(PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)
    assert len(second.snapshots) == 4
    history_after = service.review_history(PRODUCT_ID)
    assert len(history_after) == len(history) + 4

    # Marketplace filter works on history.
    shopee_history = service.review_history(PRODUCT_ID, marketplace="Shopee")
    assert shopee_history
    assert all(snap.marketplace == "Shopee" for snap in shopee_history)
