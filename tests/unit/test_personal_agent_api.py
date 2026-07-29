"""API tests for Personal AI Shopping Agent endpoints."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_personal_meta() -> None:
    response = client.get("/api/v1/personal/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["profile_count"] == 8
    assert body["authentication"] is False


def test_personal_demo() -> None:
    response = client.get("/api/v1/personal/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["active_profile"]["profile_id"]
    assert len(body["profiles"]) == 8
    assert body["deals"]["recommendations"]
    assert body["limitations"]


def test_personal_profile_and_switch() -> None:
    response = client.get("/api/v1/personal/profile")
    assert response.status_code == 200
    switched = client.post(
        "/api/v1/personal/profile/switch",
        json={"profile_id": "profile-photographer"},
    )
    assert switched.status_code == 200
    assert switched.json()["display_name"] == "Photographer"
    active = client.get("/api/v1/personal/profile")
    assert active.json()["profile_id"] == "profile-photographer"


def test_personal_deals_and_recommendation() -> None:
    deals = client.get("/api/v1/personal/deals", params={"profile_id": "profile-gaming-enthusiast"})
    assert deals.status_code == 200
    body = deals.json()
    assert body["profile_id"] == "profile-gaming-enthusiast"
    assert body["recommendations"]
    top_id = body["recommendations"][0]["product_id"]
    rec = client.get(
        f"/api/v1/personal/recommendation/{top_id}",
        params={"profile_id": "profile-gaming-enthusiast"},
    )
    assert rec.status_code == 200
    assert rec.json()["personal_deal_score"] >= 0
    advice = client.get(
        f"/api/v1/personal/advice/{top_id}",
        params={"profile_id": "profile-gaming-enthusiast"},
    )
    assert advice.status_code == 200
    assert advice.json()["label"]


def test_unknown_product_returns_404() -> None:
    response = client.get("/api/v1/personal/recommendation/not-a-real-product")
    assert response.status_code == 404


def test_unknown_profile_returns_404() -> None:
    response = client.get("/api/v1/personal/profile", params={"profile_id": "missing"})
    assert response.status_code == 404
