"""Sprint 21 Merchant Platform API tests — auth, authorization, workflows."""

from __future__ import annotations

from app.main import create_app
from fastapi.testclient import TestClient

OWNER = {"Authorization": "Bearer demo-token-techhaven-owner"}
EDITOR = {"Authorization": "Bearer demo-token-techhaven-editor"}
GG_OWNER = {"Authorization": "Bearer demo-token-gadgetgrove-owner"}
ADMIN = {"Authorization": "Bearer demo-token-internal-admin"}


def _client() -> TestClient:
    return TestClient(create_app())


def test_api_requires_authentication() -> None:
    client = _client()
    r = client.get("/api/v1/merchants")
    assert r.status_code in (401, 400)


def test_api_list_and_get_merchant() -> None:
    client = _client()
    r = client.get("/api/v1/merchants", headers=OWNER)
    assert r.status_code == 200
    ids = {i["organization_id"] for i in r.json()["items"]}
    assert "org-techhaven" in ids
    assert "org-gadgetgrove" not in ids  # isolation
    g = client.get("/api/v1/merchants/org-techhaven", headers=OWNER)
    assert g.status_code == 200
    assert g.json()["profile"]["display_name"] == "TechHaven"


def test_api_cross_merchant_forbidden() -> None:
    client = _client()
    r = client.get("/api/v1/merchants/org-gadgetgrove", headers=OWNER)
    assert r.status_code in (401, 403)


def test_api_product_offer_promotion_campaign_flow() -> None:
    client = _client()
    created = client.post(
        "/api/v1/merchants/org-techhaven/products",
        headers=OWNER,
        json={
            "title": "API NovaTech X1 Pro",
            "brand": "NovaTech",
            "model": "X1 Pro",
            "sku": "NT-X1PRO-14",
            "upc": "012345678901",
            "image_urls": ["https://cdn.techhaven.demo/api-x1.png"],
        },
    )
    assert created.status_code == 201, created.text
    submission_id = created.json()["submission_id"]
    submitted = client.post(
        f"/api/v1/merchants/org-techhaven/products/{submission_id}/submit",
        headers=OWNER,
    )
    assert submitted.status_code == 200
    assert submitted.json()["source_mode"] == "merchant_submitted"
    assert submitted.json()["match_result"] is not None

    offer = client.post(
        "/api/v1/merchants/org-techhaven/offers",
        headers=OWNER,
        json={
            "title": "API Offer",
            "currency": "USD",
            "price": 1100,
            "shipping_cost": 10,
            "marketplace_url": "https://techhaven.demo/api-offer",
        },
    )
    assert offer.status_code == 201

    promo = client.post(
        "/api/v1/merchants/org-techhaven/promotions",
        headers=OWNER,
        json={
            "promotion_type": "coupon_code",
            "title": "SAVE10",
            "coupon_code": "SAVE10",
            "status": "active",
        },
    )
    assert promo.status_code == 201
    assert promo.json()["dealscore_independent"] is True

    campaign = client.post(
        "/api/v1/merchants/org-techhaven/campaigns",
        headers=OWNER,
        json={
            "name": "API Sponsored Draft",
            "product_ids": ["prod-laptop-x1"],
            "placement_types": ["sponsored_product"],
            "daily_budget": 10,
        },
    )
    assert campaign.status_code == 201
    body = campaign.json()
    assert "Sponsored" in body["sponsored_label"]
    assert body["organic_ranking_independent"] is True
    assert body["billing"] == "not_implemented"


def test_api_editor_cannot_manage_users() -> None:
    client = _client()
    r = client.post(
        "/api/v1/merchants/org-techhaven/invitations",
        headers=EDITOR,
        json={"email": "nope@techhaven.demo", "role": "viewer"},
    )
    assert r.status_code in (401, 403)


def test_api_analytics_and_audit() -> None:
    client = _client()
    analytics = client.get("/api/v1/merchants/org-techhaven/analytics", headers=OWNER)
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["simulated"] is True
    assert "Demo" in data["label"] or data["simulated"]

    audit = client.get("/api/v1/merchants/org-techhaven/audit-log", headers=OWNER)
    assert audit.status_code == 200

    ranking = client.get(
        "/api/v1/merchants/org-techhaven/products/prod-laptop-x1/ranking-explanation",
        headers=OWNER,
    )
    assert ranking.status_code == 200
    assert ranking.json()["organic_ranking_independent"] is True


def test_api_admin_review_endpoints() -> None:
    client = _client()
    # Non-admin blocked
    denied = client.get("/api/v1/admin/merchant-submissions", headers=OWNER)
    assert denied.status_code in (401, 403)

    listed = client.get("/api/v1/admin/merchant-submissions", headers=ADMIN)
    assert listed.status_code == 200

    # Suspend / activate GadgetGrove
    suspended = client.post(
        "/api/v1/admin/merchants/org-gadgetgrove/suspend",
        headers=ADMIN,
        json={"notes": "demo suspend"},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"
    activated = client.post(
        "/api/v1/admin/merchants/org-gadgetgrove/activate",
        headers=ADMIN,
        json={"notes": "demo activate"},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"


def test_demo_meta_and_ui_compatibility() -> None:
    client = _client()
    meta = client.get("/api/v1/merchants/meta/demo")
    assert meta.status_code == 200
    body = meta.json()
    assert body["demo_accounts"]
    assert any("Demo merchants only" in lim for lim in body["limitations"])
    # demo.html still served
    page = client.get("/demo")
    assert page.status_code == 200
    assert "Merchant Platform" in page.text
    assert "demo analytics" in page.text.lower() or "Demo analytics" in page.text
