"""Integration flow tests for Personal AI Shopping Agent."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_personal_agent_end_to_end_profile_switch_and_shopping() -> None:
    demo = client.get("/api/v1/personal/demo", params={"profile_id": "profile-budget-student"})
    assert demo.status_code == 200
    student_top = demo.json()["deals"]["recommendations"][0]["product_id"]

    switched = client.post(
        "/api/v1/personal/profile/switch",
        json={"profile_id": "profile-gaming-enthusiast"},
    )
    assert switched.status_code == 200

    deals = client.get(
        "/api/v1/personal/deals",
        params={"profile_id": "profile-gaming-enthusiast", "limit": 5},
    )
    assert deals.status_code == 200
    gaming_recs = deals.json()["recommendations"]
    assert gaming_recs
    # Gaming enthusiast should surface gaming laptops near the top
    gaming_names = " ".join(r["product_name"].lower() for r in gaming_recs[:3])
    assert any(token in gaming_names for token in ("tuf", "nitro", "loq", "rtx", "gaming"))

    advice = client.get(
        f"/api/v1/personal/advice/{gaming_recs[0]['product_id']}",
        params={"profile_id": "profile-gaming-enthusiast"},
    )
    assert advice.status_code == 200
    assert advice.json()["explanation"]

    sa = client.post(
        "/api/v1/shopping-assistant/query",
        json={
            "query": "What is the best gaming laptop under 60000?",
            "profile_id": "profile-gaming-enthusiast",
            "mode": "economy",
        },
    )
    assert sa.status_code == 200
    body = sa.json()
    assert body["processing"]["personalization_mode"] == "personal"
    assert body["personal_recommendation"] is not None
    assert body["personal_recommendation"]["mode"] == "personal"

    generic = client.post(
        "/api/v1/shopping-assistant/query",
        json={"query": "What is the best gaming laptop under 60000?", "mode": "economy"},
    )
    assert generic.status_code == 200
    assert generic.json()["processing"]["personalization_mode"] == "generic"

    # Student vs gaming personal scores differ for an expensive Apple laptop
    student_score = client.get(
        "/api/v1/personal/recommendation/sa-laptop-macbook-air-m3",
        params={"profile_id": "profile-budget-student"},
    ).json()["personal_deal_score"]
    gaming_score = client.get(
        "/api/v1/personal/recommendation/sa-laptop-macbook-air-m3",
        params={"profile_id": "profile-gaming-enthusiast"},
    ).json()["personal_deal_score"]
    assert student_score != gaming_score or student_top != gaming_recs[0]["product_id"]
