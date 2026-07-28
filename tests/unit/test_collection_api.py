"""API and demo tests for Marketplace Collection endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.core.dependencies import (
    get_collection_job_repository,
    get_collection_scheduler,
    get_marketplace_collection_service,
    get_marketplace_rate_limiter,
)
from app.intelligence.canonical_registry import (
    CanonicalProductRegistryService,
    InMemoryCanonicalProductStore,
)
from app.intelligence.collection.lazada import MockLazadaCollector
from app.intelligence.collection.memory import InMemoryCollectionJobRepository
from app.intelligence.collection.rate_limiter import InMemoryMarketplaceRateLimiter
from app.intelligence.collection.scheduler import InMemoryCollectionScheduler
from app.intelligence.collection.shopee import MockShopeeCollector
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.intelligence.product_matcher import ExactVariantProductMatcher
from app.intelligence.product_parser import RuleBasedProductParser
from app.main import create_app
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 28, 16, 0, tzinfo=UTC)


@pytest.fixture
async def collection_client() -> AsyncGenerator[AsyncClient, None]:
    repo = InMemoryCollectionJobRepository()
    store = InMemoryPriceHistoryStore()
    price = PriceHistoryService(store, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    service = MarketplaceCollectionService(
        [
            MockShopeeCollector(clock=lambda: FIXED_NOW),
            MockLazadaCollector(clock=lambda: FIXED_NOW),
        ],
        price_history_service=price,
        product_intelligence_service=product,
        repository=repo,
        rate_limiter=InMemoryMarketplaceRateLimiter(max_requests=100, window_seconds=60),
        clock=lambda: FIXED_NOW,
    )
    scheduler = InMemoryCollectionScheduler(repo, run_job=service.run_job, clock=lambda: FIXED_NOW)

    app = create_app()
    app.dependency_overrides[get_marketplace_collection_service] = lambda: service
    app.dependency_overrides[get_collection_scheduler] = lambda: scheduler
    app.dependency_overrides[get_collection_job_repository] = lambda: repo
    app.dependency_overrides[get_marketplace_rate_limiter] = (
        lambda: InMemoryMarketplaceRateLimiter()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_run_collection_endpoint(collection_client: AsyncClient) -> None:
    response = await collection_client.post(
        "/api/v1/collections/run",
        json={
            "query": "iPhone 17 Pro Max",
            "marketplaces": ["shopee", "lazada"],
            "observed_at": FIXED_NOW.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "iPhone 17 Pro Max"
    assert data["stored_snapshot_count"] >= 1
    assert data["collected_count"] >= 1
    assert "mocked marketplace data" in data["disclaimer"].lower()
    assert data["status"] in {"completed", "partially_completed"}


@pytest.mark.asyncio
async def test_list_and_get_runs(collection_client: AsyncClient) -> None:
    created = await collection_client.post(
        "/api/v1/collections/run",
        json={"query": "iPhone 17 Pro Max", "marketplaces": ["shopee"]},
    )
    run_id = created.json()["run_id"]

    listed = await collection_client.get("/api/v1/collections/runs")
    assert listed.status_code == 200
    assert any(run["run_id"] == run_id for run in listed.json()["runs"])

    fetched = await collection_client.get(f"/api/v1/collections/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == run_id


@pytest.mark.asyncio
async def test_job_lifecycle_and_run_due(collection_client: AsyncClient) -> None:
    created = await collection_client.post(
        "/api/v1/collections/jobs",
        json={
            "query": "iPhone 17 Pro Max",
            "marketplaces": ["shopee"],
            "interval_seconds": 60,
            "next_run_at": FIXED_NOW.isoformat(),
        },
    )
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    listed = await collection_client.get("/api/v1/collections/jobs")
    assert listed.status_code == 200
    assert any(job["job_id"] == job_id for job in listed.json()["jobs"])

    due = await collection_client.post("/api/v1/collections/jobs/run-due")
    assert due.status_code == 200
    payload = due.json()
    assert payload["jobs_executed"] >= 1
    assert payload["runs"]

    deleted = await collection_client.delete(f"/api/v1/collections/jobs/{job_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_blank_query_rejected(collection_client: AsyncClient) -> None:
    response = await collection_client.post(
        "/api/v1/collections/run",
        json={"query": "   ", "marketplaces": ["shopee"]},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_demo_includes_marketplace_collection(client: AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    html = response.text
    assert "Marketplace Collection" in html
    assert "Development collection uses mocked marketplace data" in html
    assert "/api/v1/collections/run" in html


@pytest.mark.asyncio
async def test_openapi_exposes_collection_endpoints(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/collections/run" in paths
    assert "/api/v1/collections/runs" in paths
    assert "/api/v1/collections/jobs" in paths
    assert "/api/v1/collections/jobs/run-due" in paths
