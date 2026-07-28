"""API tests for Collection Operations endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from app.core.dependencies import (
    get_collection_job_repository,
    get_collection_operations_service,
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
from app.services.collection_operations_service import CollectionOperationsService
from app.services.marketplace_collection_service import MarketplaceCollectionService
from app.services.price_history_service import PriceHistoryService
from app.services.product_intelligence_service import ProductIntelligenceService
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 28, 21, 30, tzinfo=UTC)


@pytest.fixture
async def ops_client() -> AsyncGenerator[AsyncClient, None]:
    repo = InMemoryCollectionJobRepository()
    store = InMemoryPriceHistoryStore()
    price = PriceHistoryService(store, app_env="development")
    product = ProductIntelligenceService(
        parser=RuleBasedProductParser(),
        registry=CanonicalProductRegistryService(InMemoryCanonicalProductStore()),
        matcher=ExactVariantProductMatcher(),
    )
    collectors = [
        MockShopeeCollector(clock=lambda: FIXED_NOW),
        MockLazadaCollector(clock=lambda: FIXED_NOW),
    ]
    collection = MarketplaceCollectionService(
        collectors,
        price_history_service=price,
        product_intelligence_service=product,
        repository=repo,
        rate_limiter=InMemoryMarketplaceRateLimiter(max_requests=100, window_seconds=60),
        clock=lambda: FIXED_NOW,
    )
    scheduler = InMemoryCollectionScheduler(
        repo, run_job=collection.run_job, clock=lambda: FIXED_NOW
    )
    ops = CollectionOperationsService(
        collection_service=collection,
        repository=repo,
        run_repository=repo,
        scheduler=scheduler,
        collectors=collectors,
        price_history_store=store,
        clock=lambda: FIXED_NOW,
    )

    app = create_app()
    app.dependency_overrides[get_marketplace_collection_service] = lambda: collection
    app.dependency_overrides[get_collection_scheduler] = lambda: scheduler
    app.dependency_overrides[get_collection_job_repository] = lambda: repo
    app.dependency_overrides[get_collection_operations_service] = lambda: ops
    app.dependency_overrides[get_marketplace_rate_limiter] = (
        lambda: InMemoryMarketplaceRateLimiter()
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_job_crud_and_manual_run(ops_client: AsyncClient) -> None:
    created = await ops_client.post(
        "/api/v1/collection-operations/jobs",
        json={
            "name": "API job",
            "query": "iPhone 17 Pro Max",
            "marketplaces": ["shopee", "lazada"],
            "interval_minutes": 60,
        },
    )
    assert created.status_code == 200
    job = created.json()
    assert job["name"] == "API job"
    assert job["interval_minutes"] == 60
    assert job["status"] == "active"
    job_id = job["job_id"]

    fetched = await ops_client.get(f"/api/v1/collection-operations/jobs/{job_id}")
    assert fetched.status_code == 200

    patched = await ops_client.patch(
        f"/api/v1/collection-operations/jobs/{job_id}",
        json={"interval_minutes": 30},
    )
    assert patched.status_code == 200
    assert patched.json()["interval_minutes"] == 30

    paused = await ops_client.post(f"/api/v1/collection-operations/jobs/{job_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    blocked = await ops_client.post(
        f"/api/v1/collection-operations/jobs/{job_id}/run",
        json={},
    )
    assert blocked.status_code == 409

    resumed = await ops_client.post(f"/api/v1/collection-operations/jobs/{job_id}/resume")
    assert resumed.status_code == 200

    run = await ops_client.post(
        f"/api/v1/collection-operations/jobs/{job_id}/run",
        json={"idempotency_key": "api-key-1"},
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["trigger"] == "manual"
    assert payload["duration_ms"] is not None
    assert "job_id" in payload

    again = await ops_client.post(
        f"/api/v1/collection-operations/jobs/{job_id}/run",
        json={"idempotency_key": "api-key-1"},
    )
    assert again.json()["run_id"] == payload["run_id"]

    runs = await ops_client.get(f"/api/v1/collection-operations/jobs/{job_id}/runs")
    assert runs.status_code == 200
    assert runs.json()["runs"]

    deleted = await ops_client.delete(f"/api/v1/collection-operations/jobs/{job_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_status_health_readiness_and_run_due(ops_client: AsyncClient) -> None:
    await ops_client.post(
        "/api/v1/collection-operations/jobs",
        json={
            "name": "Due",
            "query": "iPhone 17 Pro Max",
            "marketplaces": ["shopee"],
            "interval_minutes": 1,
            "next_run_at": FIXED_NOW.isoformat(),
        },
    )
    due = await ops_client.post("/api/v1/collection-operations/run-due")
    assert due.status_code == 200
    assert due.json()["jobs_executed"] >= 1

    status = await ops_client.get("/api/v1/collection-operations/status")
    assert status.status_code == 200
    body = status.json()
    assert body["total_jobs"] >= 1
    assert "collector_availability" in body

    health = await ops_client.get("/api/v1/collection-operations/health")
    assert health.status_code == 200
    assert health.json()["running"] is True

    ready = await ops_client.get("/api/v1/collection-operations/readiness")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True

    listed = await ops_client.get("/api/v1/collection-operations/runs")
    assert listed.status_code == 200
    run_id = listed.json()["runs"][0]["run_id"]
    detail = await ops_client.get(f"/api/v1/collection-operations/runs/{run_id}")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_api_validation_unknown_marketplace(ops_client: AsyncClient) -> None:
    response = await ops_client.post(
        "/api/v1/collection-operations/jobs",
        json={
            "name": "Bad",
            "query": "iPhone",
            "marketplaces": ["amazon"],
            "interval_minutes": 10,
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_demo_includes_collection_operations(client: AsyncClient) -> None:
    response = await client.get("/demo")
    assert response.status_code == 200
    html = response.text
    assert "Collection Operations" in html
    assert "/api/v1/collection-operations/status" in html
    assert "Run Due Jobs" in html


@pytest.mark.asyncio
async def test_openapi_exposes_collection_operations(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/collection-operations/status" in paths
    assert "/api/v1/collection-operations/jobs" in paths
    assert "/api/v1/collection-operations/run-due" in paths
    assert "/api/v1/collection-operations/health" in paths
    assert "/api/v1/collection-operations/readiness" in paths
