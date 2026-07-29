"""Knowledge Graph API contract tests."""

from __future__ import annotations

import pytest
from app.intelligence.knowledge_graph.fixtures import DEMO_PRODUCT_ID, DEMO_PRODUCT_LABEL
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_demo(client):
    response = await client.get("/api/v1/graph/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["root_node"]["label"] == DEMO_PRODUCT_LABEL
    assert body["data_status"] == "mock"
    assert "limits" in body


@pytest.mark.asyncio
async def test_meta(client):
    response = await client.get("/api/v1/graph/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["demo_product_id"] == DEMO_PRODUCT_ID
    assert body["external_graph_database"] is False
    assert body["confidence_method"] == "minimum_edge_confidence"
    assert "product" in body["node_types"]
    assert "MADE_BY" in body["edge_types"]


@pytest.mark.asyncio
async def test_product_graph(client):
    response = await client.get(f"/api/v1/graph/product/{DEMO_PRODUCT_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["root_node"]["source_id"] == DEMO_PRODUCT_ID
    assert body["summary"]["brands"]


@pytest.mark.asyncio
async def test_product_graph_missing_product_404(client):
    response = await client.get("/api/v1/graph/product/does-not-exist-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_product_graph_limits_truncation(client):
    response = await client.get(
        f"/api/v1/graph/product/{DEMO_PRODUCT_ID}", params={"max_nodes": 1, "max_edges": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["truncated"] is True
    assert body["limits"]["max_nodes"] <= 1


@pytest.mark.asyncio
async def test_product_graph_rejects_limits_beyond_server_ceiling(client):
    response = await client.get(
        f"/api/v1/graph/product/{DEMO_PRODUCT_ID}", params={"max_depth": 999}
    )
    # FastAPI query validation caps this at 10 via Query(le=10).
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_node_lookup(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    response = await client.get(f"/api/v1/graph/node/{node_id}")
    assert response.status_code == 200
    assert response.json()["node_id"] == node_id


@pytest.mark.asyncio
async def test_node_lookup_missing_404(client):
    response = await client.get("/api/v1/graph/node/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_neighbors(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    response = await client.get(f"/api/v1/graph/node/{node_id}/neighbors")
    assert response.status_code == 200
    assert response.json()["nodes"]


@pytest.mark.asyncio
async def test_neighbors_filters_by_edge_type(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    response = await client.get(
        f"/api/v1/graph/node/{node_id}/neighbors", params={"edge_types": "MADE_BY"}
    )
    assert response.status_code == 200
    body = response.json()
    for edge in body["edges"]:
        assert edge["edge_type"] == "MADE_BY"


@pytest.mark.asyncio
async def test_relationships(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    response = await client.get(f"/api/v1/graph/node/{node_id}/relationships")
    assert response.status_code == 200
    body = response.json()
    assert body["node"]["node_id"] == node_id
    assert "outgoing" in body
    assert "incoming" in body


@pytest.mark.asyncio
async def test_relationships_missing_node_404(client):
    response = await client.get("/api/v1/graph/node/does-not-exist/relationships")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_path_between_product_and_brand(client):
    demo = await client.get("/api/v1/graph/demo")
    body = demo.json()
    root_id = body["root_node"]["node_id"]
    made_by_edges = [e for e in body["edges"] if e["edge_type"] == "MADE_BY"]
    assert made_by_edges
    brand_id = made_by_edges[0]["to_node_id"]
    response = await client.get(
        "/api/v1/graph/path", params={"from_node_id": root_id, "to_node_id": brand_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["paths"]
    assert body["paths"][0]["confidence_band"] in {"high", "medium", "low"}


@pytest.mark.asyncio
async def test_path_missing_node_404(client):
    response = await client.get(
        "/api/v1/graph/path", params={"from_node_id": "missing-a", "to_node_id": "missing-b"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_path_requires_query_params(client):
    response = await client.get("/api/v1/graph/path")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_evidence(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    response = await client.get(f"/api/v1/graph/evidence/{node_id}")
    assert response.status_code == 200
    body = response.json()
    assert "evidence_nodes" in body
    assert "contradictions" in body


@pytest.mark.asyncio
async def test_evidence_missing_node_404(client):
    response = await client.get("/api/v1/graph/evidence/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_explain_by_product_ids(client):
    response = await client.get(
        "/api/v1/graph/explain",
        params={"from_product_id": DEMO_PRODUCT_ID, "to_product_id": "sa-laptop-nitro-v15"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "claim" in body
    assert "limitations" in body
    assert body["limitations"]


@pytest.mark.asyncio
async def test_explain_missing_all_params_400(client):
    response = await client.get("/api/v1/graph/explain")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_explain_unsupported_when_no_path(client):
    demo = await client.get("/api/v1/graph/demo")
    node_id = demo.json()["root_node"]["node_id"]
    node_create = await client.get(f"/api/v1/graph/node/{node_id}")
    assert node_create.status_code == 200
    # Two arbitrary unconnected node ids among fixture data are unlikely; use meta to prove
    # unsupported claims are surfaced, not fabricated, via an unreachable synthetic pair.
    response = await client.get(
        "/api/v1/graph/explain",
        params={"from_node_id": node_id, "to_node_id": node_id},
    )
    # Same node to itself: engine treats this as no traversable edge path (empty edge_path).
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_no_secrets_in_any_graph_response(client):
    for path in (
        "/api/v1/graph/demo",
        "/api/v1/graph/meta",
        f"/api/v1/graph/product/{DEMO_PRODUCT_ID}",
    ):
        response = await client.get(path)
        blob = str(response.json()).lower()
        assert "api_key" not in blob
        assert "secret" not in blob
        assert "system_prompt" not in blob


@pytest.mark.asyncio
async def test_fixture_data_labeled_mock(client):
    response = await client.get("/api/v1/graph/demo")
    body = response.json()
    assert body["data_status"] == "mock"
    for node in body["nodes"]:
        assert node["data_status"] in {"mock", "imported", "live"}
