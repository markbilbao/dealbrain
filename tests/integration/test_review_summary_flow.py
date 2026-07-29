"""Integration flow: collect reviews → summarize → inspect insights."""

from __future__ import annotations

from datetime import UTC, datetime

from app.intelligence.review_summary import (
    DeterministicMockReviewSummarizer,
    InMemoryReviewSummaryRepository,
)
from app.intelligence.review_summary.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.intelligence.reviews import (
    InMemoryReviewRepository,
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.services.review_service import ReviewService
from app.services.review_summary_service import ReviewSummaryService

FIXED_NOW = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


def test_review_summary_end_to_end_flow() -> None:
    review_repo = InMemoryReviewRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"flow-rs-{counter['n']}"

    review_service = ReviewService(
        review_repo,
        [
            MockShopeeReviewCollector(),
            MockLazadaReviewCollector(),
            MockTikTokShopReviewCollector(),
            MockAmazonReviewCollector(),
        ],
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        seed_demo_history=False,
    )
    summary_service = ReviewSummaryService(
        InMemoryReviewSummaryRepository(),
        DeterministicMockReviewSummarizer(),
        review_service,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "flow-summary",
        auto_collect=False,
    )

    collected = review_service.collect_reviews(
        PRODUCT_ID,
        product_label=IPHONE_DEMO_PRODUCT_LABEL,
    )
    assert len(collected.snapshots) == 4

    comparison = review_service.compare_marketplaces(PRODUCT_ID)
    assert comparison.overall_rating is not None
    assert comparison.overall_rating > 4.6

    summary = summary_service.summarize(
        PRODUCT_ID,
        product_label=IPHONE_DEMO_PRODUCT_LABEL,
    )
    assert summary.product == IPHONE_DEMO_PRODUCT_LABEL
    assert summary.overall_sentiment == "Very Positive"
    assert summary.recommendation.label == "Highly Recommended"
    assert summary.average_rating == comparison.overall_rating
    assert summary.total_review_count == comparison.total_review_count
    assert len(summary.pros.items) >= 3
    assert len(summary.cons.items) >= 1
    assert summary.warnings
    assert summary.insights

    cached = summary_service.get_summary(PRODUCT_ID)
    assert cached.summary_id == summary.summary_id

    demo = summary_service.demo_summary()
    assert demo.product_id == PRODUCT_ID
    assert demo.overall_sentiment == "Very Positive"
