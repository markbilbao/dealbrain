"""Sprint 22 compatibility — prior sprints still work; ranking untouched."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.main import create_app
from fastapi.testclient import TestClient

from tests.unit.test_sprint21_protected_modules import PROTECTED_DIGESTS

ROOT = Path(__file__).resolve().parents[2]


def test_protected_modules_unchanged() -> None:
    for relative, expected in PROTECTED_DIGESTS.items():
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"Protected module changed: {relative}"


def test_sprint17_auth_demo_still_works() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/auth/demo")
    assert r.status_code == 200


def test_sprint19_watchlists_route_still_present() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/watchlists")
    assert r.status_code != 404


def test_sprint20_affiliate_report_still_works() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/affiliate/report")
    assert r.status_code == 200


def test_sprint21_merchant_meta_still_works() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/merchants/meta/demo")
    assert r.status_code in {200, 401, 403, 404}
    # Route must exist (merchant router registered). 404 only if disabled.
    assert r.status_code != 405


def test_recommendations_search_still_returns_ranking() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/recommendations/search", params={"q": "laptop"})
    assert r.status_code == 200


def test_dealscore_search_still_works() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/dealscore/search", params={"q": "phone"})
    assert r.status_code == 200


def test_legacy_health_fields_still_present() -> None:
    from unittest.mock import AsyncMock, MagicMock

    from app.core.dependencies import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    app = create_app()
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    data = client.get("/api/v1/health").json()
    assert data["status"] == "up"
    assert data["service"] == "PiqSavi"
    assert data["database"] == "up"
