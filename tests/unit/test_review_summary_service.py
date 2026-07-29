"""Unit tests for ReviewSummaryService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.exceptions import ReviewSummaryValidationError
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

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


def _build_services(
    *,
    auto_collect: bool = True,
) -> tuple[ReviewSummaryService, ReviewService]:
    review_repo = InMemoryReviewRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"rs-{counter['n']}"

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
        id_factory=lambda: "summary-fixed",
        auto_collect=auto_collect,
    )
    return summary_service, review_service


def test_summarize_auto_collects_reviews() -> None:
    service, _review = _build_services()
    summary = service.summarize(PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)
    assert summary.product == IPHONE_DEMO_PRODUCT_LABEL
    assert summary.product_id == PRODUCT_ID
    assert summary.overall_sentiment == "Very Positive"
    assert summary.recommendation.label == "Highly Recommended"
    assert summary.total_review_count == 12431 + 9821 + 5432 + 15680
    assert summary.average_rating is not None
    assert summary.average_rating > 4.6
    assert "Excellent camera" in summary.pros.items
    assert "Warms under heavy gaming" in summary.cons.items


def test_get_summary_uses_cache_when_force_refresh_false() -> None:
    service, _review = _build_services()
    first = service.summarize(PRODUCT_ID, force_refresh=True)
    second = service.summarize(PRODUCT_ID, force_refresh=False)
    assert first.summary_id == second.summary_id
    assert first.summary == second.summary


def test_demo_summary_returns_iphone() -> None:
    service, _review = _build_services()
    summary = service.demo_summary()
    assert summary.product == IPHONE_DEMO_PRODUCT_LABEL
    assert summary.product_id == PRODUCT_ID
    assert summary.overall_sentiment == "Very Positive"
    assert summary.warnings


def test_blank_product_id_rejected() -> None:
    service, _review = _build_services()
    with pytest.raises(ReviewSummaryValidationError):
        service.summarize("   ")


def test_to_dict_matches_api_shape() -> None:
    service, _review = _build_services()
    payload = service.demo_summary().to_dict()
    assert payload["product"] == IPHONE_DEMO_PRODUCT_LABEL
    assert payload["overall_sentiment"] == "Very Positive"
    assert isinstance(payload["pros"], list)
    assert isinstance(payload["cons"], list)
    assert isinstance(payload["warnings"], list)
    assert payload["recommendation"] == "Highly Recommended"
    assert "summary" in payload
