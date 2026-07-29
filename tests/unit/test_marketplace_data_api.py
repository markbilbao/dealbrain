"""API tests for Sprint 18 Marketplace Data endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import get_marketplace_data_service, get_user_platform_service
from app.main import create_app
from app.marketplace.connectors.fixture import FixtureMarketplaceConnector
from app.marketplace.connectors.imported import ImportedMarketplaceConnector
from app.marketplace.connectors.mock_live import MockLiveMarketplaceConnector
from app.marketplace.memory import InMemoryMarketplaceDataRepository
from app.marketplace.registry import MarketplaceConnectorRegistry
from app.profile.service import ProfileService
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from httpx import ASGITransport, AsyncClient

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
STUDENT_EMAIL = "student@example.com"
ROOT = Path(__file__).resolve().parents[2]


def make_platform() -> UserPlatformService:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        audit=audit,
    )
    profiles = ProfileService(users=store.users, profiles=store.profiles)
    sessions = SessionService(sessions=store.sessions, auth=auth)
    return UserPlatformService(
        auth=auth,
        profiles=profiles,
        sessions=sessions,
        saved=store.saved,
        audit=audit,
    )


def make_marketplace_service() -> MarketplaceDataService:
    repo = InMemoryMarketplaceDataRepository()
    registry = MarketplaceConnectorRegistry(
        [
            FixtureMarketplaceConnector(),
            ImportedMarketplaceConnector(),
            MockLiveMarketplaceConnector(),
        ],
        register_stubs=True,
    )
    return MarketplaceDataService(
        repo,
        registry,
        clock=lambda: FIXED_NOW,
        require_auth_for_ops=True,
    )


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    platform = make_platform()
    marketplace = make_marketplace_service()
    app.dependency_overrides[get_user_platform_service] = lambda: platform
    app.dependency_overrides[get_marketplace_data_service] = lambda: marketplace
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def login(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": STUDENT_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_list_sources_and_connectors(client: AsyncClient) -> None:
    sources = await client.get("/api/v1/marketplaces/sources")
    assert sources.status_code == 200
    body = sources.json()
    assert body["count"] >= 3
    modes = {s["source_mode"] for s in body["sources"]}
    assert {"fixture", "imported", "live"} <= modes

    connectors = await client.get("/api/v1/marketplaces/connectors")
    assert connectors.status_code == 200
    ids = {c["connector_id"] for c in connectors.json()["connectors"]}
    assert "fixture-marketplace" in ids
    assert "mock-live-marketplace" in ids
    mock = next(
        c for c in connectors.json()["connectors"] if c["connector_id"] == "mock-live-marketplace"
    )
    assert mock["simulated"] is True
    assert "SIMULATED LIVE" in mock["label"]


@pytest.mark.asyncio
async def test_ops_require_auth(client: AsyncClient) -> None:
    sync = await client.post(
        "/api/v1/marketplaces/sync",
        json={"connector_id": "fixture-marketplace", "mode": "full"},
    )
    assert sync.status_code == 401

    imports = await client.post(
        "/api/v1/marketplaces/imports",
        json={
            "filename": "x.csv",
            "content": "marketplace_product_id,title,sale_price\na,b,1\n",
        },
    )
    assert imports.status_code == 401

    test = await client.post("/api/v1/marketplaces/connectors/fixture-marketplace/test")
    assert test.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_sync_import_and_offers(client: AsyncClient) -> None:
    token = await login(client)
    headers = {"Authorization": f"Bearer {token}"}

    sync = await client.post(
        "/api/v1/marketplaces/sync",
        headers=headers,
        json={"connector_id": "fixture-marketplace", "mode": "full"},
    )
    assert sync.status_code == 201
    job = sync.json()
    assert job["status"] in {"completed", "partially_completed"}

    got = await client.get(f"/api/v1/marketplaces/sync/{job['job_id']}")
    assert got.status_code == 200

    csv_body = (
        "marketplace_product_id,title,sale_price,currency\napi-1,API Imported Phone,2500,PHP\n"
    )
    imported = await client.post(
        "/api/v1/marketplaces/imports",
        headers=headers,
        json={"filename": "api.csv", "content": csv_body},
    )
    assert imported.status_code == 201
    assert imported.json()["source_mode"] == "imported"

    offers = await client.get("/api/v1/marketplaces/offers")
    assert offers.status_code == 200
    assert offers.json()["count"] >= 1

    seed = await client.post("/api/v1/marketplaces/demo/seed", headers=headers)
    assert seed.status_code == 200
    assert "SIMULATED LIVE" in seed.json()["label"]


@pytest.mark.asyncio
async def test_secret_redaction_on_connector_detail(client: AsyncClient) -> None:
    # Persist a config with secret-looking option via service override internals
    service = make_marketplace_service()
    from app.domain.entities.marketplace_data import ConnectorConfiguration

    service._repo.save_configuration(  # noqa: SLF001 — test setup
        ConnectorConfiguration(
            connector_id="fixture-marketplace",
            marketplace="fixture",
            options={"api_key": "super-secret-value", "region": "ph"},
        )
    )
    app = create_app()
    platform = make_platform()
    app.dependency_overrides[get_user_platform_service] = lambda: platform
    app.dependency_overrides[get_marketplace_data_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/marketplaces/connectors/fixture-marketplace")
        assert response.status_code == 200
        config = response.json()["configuration"]
        assert config is not None
        assert config["options"]["api_key"] == "***REDACTED***"
        assert config["options"]["region"] == "ph"
        assert "super-secret-value" not in response.text


@pytest.mark.asyncio
async def test_price_and_inventory_history_paths(client: AsyncClient) -> None:
    token = await login(client)
    headers = {"Authorization": f"Bearer {token}"}
    await client.post(
        "/api/v1/marketplaces/sync",
        headers=headers,
        json={"connector_id": "fixture-marketplace", "mode": "full"},
    )
    offers = (await client.get("/api/v1/marketplaces/offers")).json()["offers"]
    assert offers
    product_id = offers[0]["product_id"]
    prices = await client.get(f"/api/v1/products/{product_id}/price-history")
    assert prices.status_code == 200
    assert prices.json()["product_id"] == product_id
    inv = await client.get(f"/api/v1/products/{product_id}/inventory-history")
    assert inv.status_code == 200


@pytest.mark.asyncio
async def test_openapi_contains_marketplace_paths(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/marketplaces/sources" in paths
    assert "/api/v1/marketplaces/connectors" in paths
    assert "/api/v1/marketplaces/imports" in paths
    assert "/api/v1/marketplaces/sync" in paths
    assert "/api/v1/marketplaces/offers" in paths
    assert "/api/v1/products/{product_id}/price-history" in paths
    assert "/api/v1/products/{product_id}/inventory-history" in paths


@pytest.mark.asyncio
async def test_demo_html_marketplace_data_section(client: AsyncClient) -> None:
    response = await client.get("/demo")
    if response.status_code != 200:
        # Some deployments serve static file directly
        html = (ROOT / "app/static/demo.html").read_text(encoding="utf-8")
    else:
        html = response.text
    assert "Marketplace Data" in html
    assert "SIMULATED LIVE — NOT A REAL MARKETPLACE CONNECTION" in html
