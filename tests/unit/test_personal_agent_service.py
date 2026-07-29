"""Unit tests for PersonalAgentService and profile fixtures."""

from __future__ import annotations

from app.domain.exceptions import PersonalAgentNotFoundError
from app.intelligence.personal.fixtures import DEMO_PROFILES, LIMITATIONS
from app.services.personal_agent_service import PersonalAgentService


def test_eight_demo_profiles_exist() -> None:
    assert len(DEMO_PROFILES) == 8
    names = {p.display_name for p in DEMO_PROFILES}
    assert "Budget Student" in names
    assert "Gaming Enthusiast" in names
    assert "Photographer" in names
    assert "Business Traveler" in names
    assert "Content Creator" in names
    assert "Apple Fan" in names
    assert "Android Fan" in names
    assert "Minimalist Buyer" in names


def test_demo_and_profile_switch() -> None:
    service = PersonalAgentService()
    demo = service.demo()
    assert demo.active_profile.profile_id
    assert len(demo.profiles) == 8
    assert demo.deals.recommendations
    assert set(LIMITATIONS).issubset(set(demo.limitations))

    switched = service.set_active_profile("profile-apple-fan")
    assert switched.display_name == "Apple Fan"
    deals = service.deals(profile_id="profile-apple-fan", limit=3)
    assert deals.profile_id == "profile-apple-fan"
    assert deals.recommendations[0].personal_deal_score >= 0


def test_recommendation_and_advice_for_product() -> None:
    service = PersonalAgentService()
    rec = service.recommendation(
        "sa-laptop-tuf-a15", profile_id="profile-gaming-enthusiast"
    )
    assert rec.product_id == "sa-laptop-tuf-a15"
    assert rec.advice is not None
    assert rec.explanation
    advice = service.advice("sa-laptop-tuf-a15", profile_id="profile-gaming-enthusiast")
    assert advice.verdict
    assert advice.explanation


def test_unknown_profile_raises() -> None:
    service = PersonalAgentService()
    try:
        service.get_profile("no-such-profile")
        raise AssertionError("expected PersonalAgentNotFoundError")
    except PersonalAgentNotFoundError:
        pass


def test_profile_switching_changes_deal_ranking() -> None:
    service = PersonalAgentService()
    apple_mac = service.personal_deal_score(
        "sa-laptop-macbook-air-m3", profile_id="profile-apple-fan"
    )
    android_mac = service.personal_deal_score(
        "sa-laptop-macbook-air-m3", profile_id="profile-android-fan"
    )
    assert apple_mac.personal_deal_score > android_mac.personal_deal_score

    gaming = service.deals(profile_id="profile-gaming-enthusiast", limit=5)
    apple = service.deals(profile_id="profile-apple-fan", limit=5)
    assert gaming.recommendations[0].product_id != apple.recommendations[0].product_id or (
        gaming.recommendations[0].personal_deal_score
        != apple.recommendations[0].personal_deal_score
    )

def test_meta_documents_limitations() -> None:
    meta = PersonalAgentService().meta()
    assert meta["authentication"] is False
    assert meta["cloud_sync"] is False
    assert meta["enabled"] is True
    assert len(meta["limitations"]) >= 4
