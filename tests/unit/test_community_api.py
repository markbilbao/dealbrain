"""Community Intelligence API contract tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.intelligence.community.fixtures import DEMO_PRODUCT_ID
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_demo_dashboard(client):
    response = await client.get("/api/v1/community/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == DEMO_PRODUCT_ID
    assert "trust" in body
    assert body["evidence_count"] > 0
    assert "summary" in body
    assert "connector_status" in body


@pytest.mark.asyncio
async def test_meta(client):
    response = await client.get("/api/v1/community/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["demo_product_id"] == DEMO_PRODUCT_ID
    assert "reddit" in body["connectors"]


@pytest.mark.asyncio
async def test_product(client):
    response = await client.get(f"/api/v1/community/product/{DEMO_PRODUCT_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["evidence"]
    assert body["topics"]
    assert body["timeline"]
    assert "disclaimer" in body


@pytest.mark.asyncio
async def test_topics_and_timeline(client):
    topics = await client.get(f"/api/v1/community/topics/{DEMO_PRODUCT_ID}")
    timeline = await client.get(f"/api/v1/community/timeline/{DEMO_PRODUCT_ID}")
    assert topics.status_code == 200
    assert timeline.status_code == 200
    assert topics.json()["topics"]
    assert timeline.json()["timeline"]


@pytest.mark.asyncio
async def test_evidence_lookup(client):
    product = await client.get(f"/api/v1/community/product/{DEMO_PRODUCT_ID}")
    evidence_id = product.json()["evidence"][0]["evidence_id"]
    response = await client.get(f"/api/v1/community/evidence/{evidence_id}")
    assert response.status_code == 200
    assert response.json()["evidence"]["evidence_id"] == evidence_id


@pytest.mark.asyncio
async def test_evidence_missing(client):
    response = await client.get("/api/v1/community/evidence/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_blank_product_rejected_via_path(client):
    # FastAPI may 404 empty path; ensure no 500.
    response = await client.get("/api/v1/community/product/%20")
    assert response.status_code in {400, 404, 422}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["economy", "balanced", "maximum"])
async def test_demo_modes(client, mode):
    response = await client.get(f"/api/v1/community/demo?mode={mode}")
    assert response.status_code == 200
    assert response.json()["summary"]["mode"] in {"economy", "balanced", "maximum"}


@pytest.mark.asyncio
async def test_no_secrets_in_product_processing(client):
    response = await client.get(f"/api/v1/community/product/{DEMO_PRODUCT_ID}")
    body = response.json()
    blob = str(body).lower()
    assert "api_key" not in blob
    assert "secret" not in blob or "secrets_included" in blob
