"""Sprint 20 API surface tests for Affiliate Revenue Engine."""

from __future__ import annotations

from app.main import create_app
from fastapi.testclient import TestClient


def _client() -> TestClient:
    return TestClient(create_app())


def test_list_merchants() -> None:
    client = _client()
    response = client.get("/api/v1/affiliate/merchant")
    assert response.status_code == 200
    body = response.json()
    assert len(body["merchants"]) >= 6
    assert "placeholder" in body["disclaimer"].lower() or "no real" in body["disclaimer"].lower()


def test_generate_link_and_track_click_and_report() -> None:
    client = _client()
    link_res = client.post(
        "/api/v1/affiliate/link",
        json={
            "product_id": "prod-api-1",
            "product_name": "API Phone",
            "marketplace": "lazada",
            "country": "PH",
            "campaign_id": "api-camp",
            "sub_id": "api-sub",
            "order_value": 200,
        },
    )
    assert link_res.status_code == 201, link_res.text
    link = link_res.json()
    assert link["simulated"] is True
    assert "affiliate_url" in link

    click_res = client.post(
        "/api/v1/affiliate/click",
        json={
            "link_id": link["link_id"],
            "source": "recommendation_api",
            "user_id": "api-user",
            "session_id": "api-sess",
            "device": "desktop",
            "country": "PH",
        },
    )
    assert click_res.status_code == 201, click_res.text
    click = click_res.json()
    assert click["click_id"]

    conv = client.patch(
        f"/api/v1/affiliate/click/{click['click_id']}/conversion",
        json={"conversion_status": "converted", "revenue": 200, "estimated_commission": 9},
    )
    assert conv.status_code == 200

    report = client.get("/api/v1/affiliate/report")
    assert report.status_code == 200
    body = report.json()
    assert body["total_clicks"] >= 1
    assert "by_merchant" in body
    assert body["simulated"] is True


def test_merchant_activate_and_commission() -> None:
    client = _client()
    deactivated = client.post("/api/v1/affiliate/merchant/merchant-ebay-us/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    activated = client.post("/api/v1/affiliate/merchant/merchant-ebay-us/activate")
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"
    commission = client.patch(
        "/api/v1/affiliate/merchant/merchant-ebay-us/commission",
        json={"commission_type": "percent", "commission_value": 3.5},
    )
    assert commission.status_code == 200
    assert commission.json()["commission_value"] == 3.5


def test_disclosure_resolve() -> None:
    client = _client()
    response = client.get("/api/v1/affiliate/disclosure/resolve", params={"region": "US"})
    assert response.status_code == 200
    body = response.json()
    assert body["combined_text"]
    assert body["ftc_placeholder"] is True


def test_attribute_endpoint() -> None:
    client = _client()
    client.post(
        "/api/v1/affiliate/click",
        json={
            "merchant_id": "merchant-amazon-us",
            "product_id": "prod-attr",
            "source": "shopping_assistant",
            "user_id": "attr-user",
            "session_id": "attr-sess",
        },
    )
    response = client.post(
        "/api/v1/affiliate/click/attribute",
        json={
            "model": "last_click",
            "user_id": "attr-user",
            "session_id": "attr-sess",
            "revenue": 10,
            "estimated_commission": 0.4,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["model"] == "last_click"
