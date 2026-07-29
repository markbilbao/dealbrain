"""API tests for AI Review Summary endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.core.dependencies import (
    get_review_repository,
    get_review_service,
    get_review_summary_repository,
    get_review_summary_service,
)
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
from app.main import create_app
from app.services.review_service import ReviewService
from app.services.review_summary_service import ReviewSummaryService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 29, 13, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


@pytest.fixture
async def summary_client() -> AsyncGenerator[AsyncClient, None]:
    review_repo = InMemoryReviewRepository()
    summary_repo = InMemoryReviewSummaryRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"api-rs-{counter['n']}"

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
        summary_repo,
        DeterministicMockReviewSummarizer(),
        review_service,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "api-summary-1",
        auto_collect=True,
    )
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: review_repo
    app.dependency_overrides[get_review_service] = lambda: review_service
    app.dependency_overrides[get_review_summary_repository] = lambda: summary_repo
    app.dependency_overrides[get_review_summary_service] = lambda: summary_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_demo_endpoint(summary_client: AsyncClient) -> None:
    response = await summary_client.get("/api/v1/review-summary/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == IPHONE_DEMO_PRODUCT_LABEL
    assert body["product_id"] == PRODUCT_ID
    assert body["overall_sentiment"] == "Very Positive"
    assert body["recommendation"] == "Highly Recommended"
    assert "Excellent camera" in body["pros"]
    assert "Long battery life" in body["pros"]
    assert "Premium build" in body["pros"]
    assert "Fast delivery" in body["pros"]
    assert "Expensive" in body["cons"]
    assert "Warms under heavy gaming" in body["cons"]
    assert any("accessories" in item.lower() for item in body["warnings"])
    assert body["provider"] == "deterministic-mock"
    assert "Most buyers are satisfied" in body["summary"]


@pytest.mark.asyncio
async def test_product_summary_endpoint(summary_client: AsyncClient) -> None:
    response = await summary_client.get(f"/api/v1/review-summary/{PRODUCT_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["product"] == IPHONE_DEMO_PRODUCT_LABEL
    assert body["overall_sentiment"] == "Very Positive"
    assert isinstance(body["pros"], list)
    assert isinstance(body["cons"], list)


@pytest.mark.asyncio
async def test_blank_product_id_returns_400(summary_client: AsyncClient) -> None:
    response = await summary_client.get("/api/v1/review-summary/%20%20%20")
    assert response.status_code == 400
