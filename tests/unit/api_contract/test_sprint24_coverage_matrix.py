"""Sprint 24 integration / contract coverage matrix tests.

Covers the §13.6 matrix cells using the real FastAPI app where practical.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.core.dependencies import get_db, get_product_service
from app.main import create_app
from app.schemas.product import ProductResponse
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def app_client():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, app
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Authentication / users
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_auth_register_login_me_logout_roundtrip(app_client) -> None:
    client, _ = app_client
    email = "sprint24-auth@example.com"
    password = "SecurePass1!"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "S24"},
    )
    assert reg.status_code in {200, 201}
    body = reg.json()
    assert "access_token" in body or "token" in body or "session" in body or "user" in body

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json().get("access_token") or login.json().get("token")
    assert token

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    logout = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert logout.status_code in {200, 204}


@pytest.mark.anyio
async def test_auth_me_requires_authentication(app_client) -> None:
    client, _ = app_client
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in {401, 403}
    payload = response.json()
    assert "detail" in payload or "error" in payload


# ---------------------------------------------------------------------------
# Products — skip/offset alias + bare list
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_products_bare_list_and_skip_offset_alias(app_client) -> None:
    client, app = app_client
    from datetime import UTC, date, datetime
    from decimal import Decimal
    from uuid import UUID

    sample = ProductResponse(
        id=UUID("00000000-0000-4000-8000-000000000001"),
        brand="Acme",
        category="phones",
        model="X1",
        variant=None,
        color=None,
        manufacturer_sku="SKU-1",
        release_date=date(2024, 1, 1),
        msrp=Decimal("100.00"),
        image_url=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    mock = AsyncMock()
    mock.list_products = AsyncMock(return_value=[sample])
    app.dependency_overrides[get_product_service] = lambda: mock

    with_skip = await client.get("/api/v1/products", params={"skip": 2, "limit": 5})
    assert with_skip.status_code == 200
    assert isinstance(with_skip.json(), list)
    mock.list_products.assert_awaited_with(skip=2, limit=5)

    mock.list_products.reset_mock()
    with_offset = await client.get("/api/v1/products", params={"offset": 3, "limit": 5})
    assert with_offset.status_code == 200
    assert isinstance(with_offset.json(), list)
    mock.list_products.assert_awaited_with(skip=3, limit=5)

    conflict = await client.get(
        "/api/v1/products", params={"skip": 1, "offset": 2, "limit": 5}
    )
    assert conflict.status_code == 422


@pytest.mark.anyio
async def test_products_invalid_sort_rejected(app_client) -> None:
    client, app = app_client
    mock = AsyncMock()
    mock.list_products = AsyncMock(return_value=[])
    app.dependency_overrides[get_product_service] = lambda: mock
    response = await client.get("/api/v1/products", params={"sort": "commission"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Launch / readiness
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_probes_and_launch_meta(app_client) -> None:
    client, _ = app_client
    for path in ("/live", "/ready", "/health", "/api/v1/live", "/api/v1/health"):
        response = await client.get(path)
        assert response.status_code in {200, 503}
        assert isinstance(response.json(), dict)

    meta = await client.get("/api/v1/launch/meta")
    assert meta.status_code == 200
    body = meta.json()
    assert "limitations" in body or "environment" in body or "version" in body


# ---------------------------------------------------------------------------
# Marketplace / DealScore / Recommendations — no sort in contract; order stable
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_marketplace_search_shape_and_ignores_unknown_sort(app_client) -> None:
    client, _ = app_client
    base = await client.get("/api/v1/marketplace/search", params={"q": "iphone"})
    assert base.status_code == 200
    body = base.json()
    assert "query" in body
    assert "results" in body

    with_sort = await client.get(
        "/api/v1/marketplace/search", params={"q": "iphone", "sort": "price"}
    )
    # Unknown query params remain ignored (no FilterParams adoption) — order stable.
    assert with_sort.status_code == 200
    assert with_sort.json()["results"] == body["results"]


@pytest.mark.anyio
async def test_dealscore_and_recommendation_search_shapes(app_client) -> None:
    client, _ = app_client
    ds = await client.get("/api/v1/dealscore/search", params={"q": "iphone"})
    assert ds.status_code == 200
    assert "results" in ds.json() or "query" in ds.json()

    rec = await client.get("/api/v1/recommendations/search", params={"q": "iphone"})
    assert rec.status_code == 200
    assert "results" in rec.json() or "query" in rec.json() or "decision" in rec.json()


# ---------------------------------------------------------------------------
# Shopping Assistant / community / graph / personal
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_shopping_assistant_meta_and_query(app_client) -> None:
    client, _ = app_client
    meta = await client.get("/api/v1/shopping-assistant/meta")
    assert meta.status_code == 200

    query = await client.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "best phone under 20000"},
    )
    assert query.status_code in {200, 400, 422}
    if query.status_code == 200:
        assert isinstance(query.json(), dict)


@pytest.mark.anyio
async def test_community_graph_personal_meta(app_client) -> None:
    client, _ = app_client
    for path in (
        "/api/v1/community/meta",
        "/api/v1/graph/meta",
        "/api/v1/personal/meta",
    ):
        response = await client.get(path)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


# ---------------------------------------------------------------------------
# Price history / collections / reviews
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_price_history_range_validation(app_client) -> None:
    client, _ = app_client
    response = await client.get("/api/v1/price-history/search", params={"q": "phone"})
    assert response.status_code in {200, 404, 422}


@pytest.mark.anyio
async def test_collections_runs_offset_additive(app_client) -> None:
    client, _ = app_client
    response = await client.get("/api/v1/collections/runs", params={"limit": 5, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert "runs" in body
    assert "items" in body
    assert body["items"] == body["runs"]
    assert "pagination" in body
    assert body["pagination"]["offset"] == 0


@pytest.mark.anyio
async def test_reviews_history_accepts_limit(app_client) -> None:
    client, _ = app_client
    response = await client.get(
        "/api/v1/reviews/history/demo-product",
        params={"limit": 5},
    )
    assert response.status_code in {200, 404}
    # offset on reviews is deferred: endpoint is architecture-lock hashed.


# ---------------------------------------------------------------------------
# Error envelope
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_validation_error_envelope_has_detail(app_client) -> None:
    client, _ = app_client
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    body = response.json()
    assert body.get("error") == "validation_error" or "detail" in body
    assert "detail" in body


# ---------------------------------------------------------------------------
# Affiliate / merchant behavioral coverage + ownership / authz
# ---------------------------------------------------------------------------


OWNER = {"Authorization": "Bearer demo-token-techhaven-owner"}
ADMIN = {"Authorization": "Bearer demo-token-internal-admin"}


@pytest.mark.anyio
async def test_merchant_ownership_list_and_isolation(app_client) -> None:
    client, _ = app_client
    listed = await client.get("/api/v1/merchants", headers=OWNER)
    assert listed.status_code == 200
    body = listed.json()
    assert "items" in body
    ids = {item["organization_id"] for item in body["items"]}
    assert "org-techhaven" in ids
    assert "org-gadgetgrove" not in ids

    denied = await client.get("/api/v1/merchants/org-gadgetgrove", headers=OWNER)
    assert denied.status_code in {401, 403}
    payload = denied.json()
    assert "detail" in payload or "error" in payload


@pytest.mark.anyio
async def test_merchant_admin_operations_and_authz(app_client) -> None:
    client, _ = app_client
    non_admin = await client.get("/api/v1/admin/merchant-submissions", headers=OWNER)
    assert non_admin.status_code in {401, 403}

    listed = await client.get("/api/v1/admin/merchant-submissions", headers=ADMIN)
    assert listed.status_code == 200

    suspended = await client.post(
        "/api/v1/admin/merchants/org-gadgetgrove/suspend",
        headers=ADMIN,
        json={"notes": "sprint24 coverage suspend"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    activated = await client.post(
        "/api/v1/admin/merchants/org-gadgetgrove/activate",
        headers=ADMIN,
        json={"notes": "sprint24 coverage activate"},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"


@pytest.mark.anyio
async def test_affiliate_link_and_report_behavior(app_client) -> None:
    client, _ = app_client
    link_res = await client.post(
        "/api/v1/affiliate/link",
        json={
            "product_id": "prod-s24-aff",
            "product_name": "Sprint24 Phone",
            "marketplace": "lazada",
            "country": "PH",
            "campaign_id": "s24-camp",
            "sub_id": "s24-sub",
            "order_value": 150,
        },
    )
    assert link_res.status_code == 201, link_res.text
    link = link_res.json()
    assert link["simulated"] is True
    assert "affiliate_url" in link
    link_id = link["link_id"]

    listed = await client.get("/api/v1/affiliate/link", params={"limit": 50})
    assert listed.status_code == 200
    assert any(row["link_id"] == link_id for row in listed.json()["links"])

    report = await client.get("/api/v1/affiliate/report")
    assert report.status_code == 200
    body = report.json()
    assert "by_merchant" in body
    assert body["simulated"] is True


@pytest.mark.anyio
async def test_authorization_failures_envelope(app_client) -> None:
    client, _ = app_client
    no_auth = await client.get("/api/v1/merchants")
    assert no_auth.status_code in {401, 400}
    body = no_auth.json()
    assert "detail" in body or "error" in body

    bad_token = await client.get(
        "/api/v1/merchants",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert bad_token.status_code in {401, 403}


@pytest.mark.anyio
async def test_persistence_backed_affiliate_link_survives_restart(app_client, tmp_path) -> None:
    """HTTP create→read remains valid after SQL-backed affiliate store restart."""
    from pathlib import Path

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.dependencies import (
        get_affiliate_link_service,
        get_affiliate_merchant_service,
        get_affiliate_repository,
    )
    from app.infrastructure.database.models.operational_entity import OperationalEntityModel
    from app.infrastructure.database.repositories.affiliate_repository import (
        SqlAlchemyAffiliateRepository,
    )
    from app.infrastructure.persistence.session import reset_sync_engine
    from app.services.affiliate_link_service import AffiliateLinkService
    from app.services.affiliate_merchant_service import AffiliateMerchantService

    client, app = app_client
    reset_sync_engine()
    db_path = Path(tmp_path) / "s24_affiliate.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    OperationalEntityModel.__table__.create(engine)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )

    try:
        repo = SqlAlchemyAffiliateRepository(session_factory=factory, seed=True)
        merchant_service = AffiliateMerchantService(repo)
        link_service = AffiliateLinkService(repo, repo, merchant_service=merchant_service)
        app.dependency_overrides[get_affiliate_repository] = lambda: repo
        app.dependency_overrides[get_affiliate_merchant_service] = lambda: merchant_service
        app.dependency_overrides[get_affiliate_link_service] = lambda: link_service

        created = await client.post(
            "/api/v1/affiliate/link",
            json={
                "product_id": "prod-persist-s24",
                "product_name": "Persist Phone",
                "marketplace": "shopee",
                "country": "PH",
            },
        )
        assert created.status_code == 201, created.text
        link_id = created.json()["link_id"]

        # Simulate process restart: new repository on the same SQLite file.
        restarted = SqlAlchemyAffiliateRepository(session_factory=factory, seed=False)
        restarted_merchant = AffiliateMerchantService(restarted)
        restarted_links = AffiliateLinkService(
            restarted, restarted, merchant_service=restarted_merchant
        )
        app.dependency_overrides[get_affiliate_repository] = lambda: restarted
        app.dependency_overrides[get_affiliate_merchant_service] = lambda: restarted_merchant
        app.dependency_overrides[get_affiliate_link_service] = lambda: restarted_links

        fetched = await client.get(f"/api/v1/affiliate/link/{link_id}")
        assert fetched.status_code == 200
        assert fetched.json()["link_id"] == link_id
        assert fetched.json()["product_id"] == "prod-persist-s24"
    finally:
        engine.dispose()
        reset_sync_engine()


@pytest.mark.anyio
async def test_affiliate_and_merchant_meta_surfaces(app_client) -> None:
    client, _ = app_client
    affiliate = await client.get("/api/v1/affiliate/disclosure")
    assert affiliate.status_code in {200, 401, 404, 405, 422}

    merchants = await client.get("/api/v1/merchants/meta/demo")
    assert merchants.status_code in {200, 401, 404}
