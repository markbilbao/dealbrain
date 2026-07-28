"""API tests for Review Intelligence endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.core.dependencies import get_review_repository, get_review_service
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
from app.main import create_app
from app.services.review_service import ReviewService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 29, 9, 0, tzinfo=UTC)
PRODUCT_ID = IPHONE_DEMO_PRODUCT_ID


@pytest.fixture
async def review_client() -> AsyncGenerator[AsyncClient, None]:
    repo = InMemoryReviewRepository()
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"api-rev-{counter['n']}"

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
    app = create_app()
    app.dependency_overrides[get_review_repository] = lambda: repo
    app.dependency_overrides[get_review_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_collect_and_compare_endpoints(review_client: AsyncClient) -> None:
    collected = await review_client.post(
        "/api/v1/reviews/collect",
        json={
            "product_id": PRODUCT_ID,
            "product_label": IPHONE_DEMO_PRODUCT_LABEL,
        },
    )
    assert collected.status_code == 200
    body = collected.json()
    assert body["product"] == IPHONE_DEMO_PRODUCT_LABEL
    assert body["collected_count"] == 4
    assert body["total_review_count"] == 12431 + 9821 + 5432 + 15680

    latest = await review_client.get(f"/api/v1/reviews/{PRODUCT_ID}")
    assert latest.status_code == 200
    latest_body = latest.json()
    assert latest_body["overall_rating"] is not None
    assert len(latest_body["marketplaces"]) == 4

    compared = await review_client.get(f"/api/v1/reviews/compare/{PRODUCT_ID}")
    assert compared.status_code == 200
    compare_body = compared.json()
    assert compare_body["product"] == IPHONE_DEMO_PRODUCT_LABEL
    by_name = {item["marketplace"]: item for item in compare_body["marketplaces"]}
    assert by_name["Shopee"]["rating"] == 4.8
    assert by_name["Shopee"]["reviews"] == 12431
    assert by_name["Shopee"]["seller_rating"] == 4.9
    assert by_name["Lazada"]["rating"] == 4.7
    assert by_name["Lazada"]["reviews"] == 9821


@pytest.mark.asyncio
async def test_history_endpoint(review_client: AsyncClient) -> None:
    await review_client.post(
        "/api/v1/reviews/collect",
        json={"product_id": PRODUCT_ID, "product_label": IPHONE_DEMO_PRODUCT_LABEL},
    )
    history = await review_client.get(f"/api/v1/reviews/history/{PRODUCT_ID}")
    assert history.status_code == 200
    body = history.json()
    assert body["count"] == 16
    assert body["snapshots"][0]["marketplace"] in {
        "Shopee",
        "Lazada",
        "TikTok Shop",
        "Amazon",
    }


@pytest.mark.asyncio
async def test_latest_not_found(review_client: AsyncClient) -> None:
    response = await review_client.get("/api/v1/reviews/missing-product")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_collect_validation_error(review_client: AsyncClient) -> None:
    response = await review_client.post(
        "/api/v1/reviews/collect",
        json={"product_id": "x", "marketplaces": ["Nope"]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_demo_includes_review_intelligence(review_client: AsyncClient) -> None:
    response = await review_client.get("/demo")
    assert response.status_code == 200
    assert "Review Intelligence" in response.text
    assert "/api/v1/reviews/collect" in response.text
