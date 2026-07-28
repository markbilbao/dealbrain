"""Unit tests for ReviewService."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.exceptions import ReviewNotFoundError, ReviewValidationError
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

FIXED_NOW = datetime(2026, 7, 29, 8, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


def _build_service(*, seed_demo_history: bool = True) -> tuple[ReviewService, InMemoryReviewRepository]:
    repo = InMemoryReviewRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"rev-{counter['n']}"

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
        seed_demo_history=seed_demo_history,
    )
    return service, repo


def test_collect_reviews_from_all_marketplaces() -> None:
    service, _repo = _build_service()
    result = service.collect_reviews(
        PRODUCT_ID,
        product_label=IPHONE_DEMO_PRODUCT_LABEL,
    )
    assert result.product == IPHONE_DEMO_PRODUCT_LABEL
    assert result.product_id == PRODUCT_ID
    assert len(result.snapshots) == 4
    marketplaces = {snap.marketplace for snap in result.snapshots}
    assert marketplaces == {"Shopee", "Lazada", "TikTok Shop", "Amazon"}

    shopee = next(snap for snap in result.snapshots if snap.marketplace == "Shopee")
    assert shopee.average_rating == 4.8
    assert shopee.review_count == 12431
    assert shopee.seller_rating == 4.9
    assert shopee.seller_followers == 18000


def test_collect_reviews_subset_of_marketplaces() -> None:
    service, _repo = _build_service(seed_demo_history=False)
    result = service.collect_reviews(PRODUCT_ID, marketplaces=["Shopee", "Lazada"])
    assert len(result.snapshots) == 2
    assert {snap.marketplace for snap in result.snapshots} == {"Shopee", "Lazada"}


def test_latest_compare_overall_and_total() -> None:
    service, _repo = _build_service()
    service.collect_reviews(PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)

    latest = service.latest_reviews(PRODUCT_ID)
    assert len(latest) == 4

    comparison = service.compare_marketplaces(PRODUCT_ID)
    assert comparison.product == IPHONE_DEMO_PRODUCT_LABEL
    assert comparison.total_review_count == 12431 + 9821 + 5432 + 15680
    assert comparison.overall_rating == service.overall_rating(PRODUCT_ID)
    assert service.total_review_count(PRODUCT_ID) == comparison.total_review_count

    # Sample-shaped marketplace entries.
    by_name = {item.marketplace: item for item in comparison.marketplaces}
    assert by_name["Shopee"].rating == 4.8
    assert by_name["Shopee"].reviews == 12431
    assert by_name["Lazada"].rating == 4.7
    assert by_name["Lazada"].reviews == 9821


def test_review_history_includes_seeded_waves() -> None:
    service, _repo = _build_service(seed_demo_history=True)
    service.collect_reviews(PRODUCT_ID)
    history = service.review_history(PRODUCT_ID)
    # 3 historical waves × 4 marketplaces + 4 current = 16
    assert len(history) == 16
    assert history[0].collected_at == FIXED_NOW


def test_blank_product_id_rejected() -> None:
    service, _repo = _build_service(seed_demo_history=False)
    with pytest.raises(ReviewValidationError):
        service.collect_reviews("   ")


def test_unknown_marketplace_rejected() -> None:
    service, _repo = _build_service(seed_demo_history=False)
    with pytest.raises(ReviewValidationError):
        service.collect_reviews(PRODUCT_ID, marketplaces=["NotAMarket"])


def test_latest_without_collection_raises() -> None:
    service, _repo = _build_service(seed_demo_history=False)
    with pytest.raises(ReviewNotFoundError):
        service.latest_reviews(PRODUCT_ID)


def test_overall_rating_none_without_data() -> None:
    service, _repo = _build_service(seed_demo_history=False)
    assert service.overall_rating(PRODUCT_ID) is None
    assert service.total_review_count(PRODUCT_ID) == 0
