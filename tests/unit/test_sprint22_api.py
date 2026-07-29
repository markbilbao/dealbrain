"""Sprint 22 launch readiness API tests."""

from __future__ import annotations

from app.core.dependencies import get_db, get_rate_limiter
from app.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    return TestClient(create_app())


def test_root_live_probe() -> None:
    client = _client()
    r = client.get("/live")
    assert r.status_code == 200
    data = r.json()
    assert data["live"] is True
    assert data["status"] == "up"
    assert "version" in data
    assert "uptime_seconds" in data


def test_api_ready_and_health(mock_db_override=None) -> None:
    app = create_app()
    from unittest.mock import AsyncMock, MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "up"
    assert body["database"] == "up"
    assert body["cache"] in {"up", "degraded"}
    assert "version" in body
    assert "dependencies" in body


def test_security_headers_present() -> None:
    client = _client()
    r = client.get("/live")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in r.headers
    assert "Referrer-Policy" in r.headers
    assert "Permissions-Policy" in r.headers


def test_feature_flags_endpoint() -> None:
    client = _client()
    r = client.get("/api/v1/launch/feature-flags")
    assert r.status_code == 200
    flags = r.json()["as_dict"]
    assert flags["launch_readiness_enabled"] is True
    assert "affiliate_enabled" in flags
    assert "merchant_platform_enabled" in flags


def test_demo_launcher_switch() -> None:
    client = _client()
    r = client.post("/api/v1/launch/demo/switch", json={"persona": "merchant"})
    assert r.status_code == 200
    data = r.json()
    assert data["active_persona"] == "merchant"
    assert data["organization_id"] == "org-techhaven"
    assert data["auth_header"] == "Bearer demo-token-techhaven-owner"


def test_launch_dashboard_requires_admin() -> None:
    app = create_app()
    from unittest.mock import AsyncMock, MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    denied = client.get("/api/v1/launch/dashboard")
    assert denied.status_code == 401

    ok = client.get(
        "/api/v1/launch/dashboard",
        headers={"Authorization": "Bearer demo-token-internal-admin"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert "metrics" in body
    assert "feature_flags" in body
    assert "launch_checklist" in body
    assert "users" in body["metrics"]
    assert "merchants" in body["metrics"]
    assert "affiliate_clicks" in body["metrics"]


def test_config_export_redacts_secrets() -> None:
    client = _client()
    r = client.post(
        "/api/v1/launch/config/export",
        headers={"Authorization": "Bearer demo-token-internal-admin"},
    )
    assert r.status_code == 200
    payload = r.json()["payload"]
    assert payload["database_url"] == "***REDACTED***"
    assert payload["openai_api_key"] == "***REDACTED***"


def test_checklist_update() -> None:
    client = _client()
    before = client.get("/api/v1/launch/checklist").json()
    item_id = before["items"][0]["item_id"]
    r = client.patch(
        f"/api/v1/launch/checklist/{item_id}",
        headers={"Authorization": "Bearer demo-token-internal-admin"},
        json={"completed": True, "notes": "verified in test"},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True


def test_rate_limiting_blocks_excess_requests() -> None:
    limiter = get_rate_limiter()
    limiter.set_enabled(True)
    limiter.reset()
    # Tighten login bucket for the test.
    from app.launch.rate_limit import RateLimitRule

    limiter._rules["login"] = RateLimitRule("login", 2, 60)  # noqa: SLF001

    app = create_app()
    client = TestClient(app)
    # Hit login path classification even if auth fails validation.
    for _ in range(2):
        client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
    blocked = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"] == "rate_limited"
    assert "detail" in body
    limiter.set_enabled(False)
    limiter.reset()


def test_error_envelope_preserves_detail() -> None:
    client = _client()
    r = client.get(
        "/api/v1/launch/config/exports/missing-id",
        headers={"Authorization": "Bearer demo-token-internal-admin"},
    )
    assert r.status_code == 404
    body = r.json()
    assert "detail" in body
    assert body.get("error") == "not_found" or "not found" in str(body["detail"]).lower()


def test_performance_cache_stats() -> None:
    client = _client()
    r = client.get("/api/v1/launch/performance")
    assert r.status_code == 200
    assert "hits" in r.json()
    assert "namespaces" in r.json()


def test_openapi_includes_launch_tag() -> None:
    client = _client()
    schema = client.get("/openapi.json").json()
    tag_names = {t["name"] for t in schema.get("tags", [])}
    assert "launch-readiness" in tag_names or any(
        "/api/v1/launch/" in path for path in schema.get("paths", {})
    )
    assert "/api/v1/launch/dashboard" in schema["paths"]
    assert "/live" in schema["paths"]
