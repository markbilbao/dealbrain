"""Unit tests for ProfileService — profile, preferences, settings, and overrides."""

from __future__ import annotations

import pytest
from app.domain.exceptions import UserPlatformNotFoundError, UserPlatformValidationError
from app.profile.service import ProfileService
from app.user.fixtures import seed_demo_users
from app.user.memory import InMemoryUserPlatformStore

STUDENT_ID = "user-student"
CREATOR_ID = "user-creator"


def make_profile_service() -> tuple[ProfileService, InMemoryUserPlatformStore]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    service = ProfileService(users=store.users, profiles=store.profiles)
    return service, store


class TestGetProfile:
    def test_get_profile_returns_seeded_profile(self) -> None:
        service, _store = make_profile_service()
        profile = service.get_profile(STUDENT_ID)
        assert profile.user_id == STUDENT_ID
        assert profile.display_name == "Demo Student"

    def test_get_profile_unknown_user_raises_not_found(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformNotFoundError):
            service.get_profile("no-such-user")

    def test_get_profile_blank_user_id_raises_validation(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.get_profile("   ")

    def test_get_profile_includes_favorite_brands_and_marketplaces(self) -> None:
        service, _store = make_profile_service()
        profile = service.get_profile(STUDENT_ID)
        assert any(b.brand == "Lenovo" for b in profile.favorite_brands)
        assert any(m.marketplace == "Shopee" for m in profile.favorite_marketplaces)

    def test_get_profile_includes_wishlist(self) -> None:
        service, _store = make_profile_service()
        profile = service.get_profile(STUDENT_ID)
        assert profile.wishlist is not None
        assert "sa-phone-pixel-9" in profile.wishlist.product_ids


class TestUpdateProfile:
    def test_update_profile_changes_display_name(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"display_name": "Updated Name"})
        assert updated.display_name == "Updated Name"

    def test_update_profile_blank_display_name_keeps_prior_value(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"display_name": "   "})
        assert updated.display_name == "Demo Student"

    def test_update_profile_updates_flat_preference_fields(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"budget": 40000.0, "currency": "USD"})
        assert updated.preferences.budget == 40000.0
        assert updated.preferences.currency == "USD"

    def test_update_profile_sets_favorite_brands(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"favorite_brands": ["Apple", "Sony"]})
        brand_names = {b.brand for b in updated.favorite_brands}
        assert brand_names == {"Apple", "Sony"}

    def test_update_profile_sets_favorite_marketplaces(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"favorite_marketplaces": ["Amazon"]})
        assert [m.marketplace for m in updated.favorite_marketplaces] == ["Amazon"]

    def test_update_profile_sets_wishlist(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(STUDENT_ID, {"wishlist": ["sa-laptop-loq-15"]})
        assert updated.wishlist is not None
        assert updated.wishlist.product_ids == ("sa-laptop-loq-15",)

    def test_update_profile_sets_owned_products_and_accessories(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_profile(
            STUDENT_ID,
            {"owned_products": ["sa-phone-pixel-9"], "accessories": ["sa-earbuds-airpods-pro-2"]},
        )
        assert updated.owned_products == ("sa-phone-pixel-9",)
        assert updated.accessories == ("sa-earbuds-airpods-pro-2",)

    def test_update_profile_increments_version(self) -> None:
        service, _store = make_profile_service()
        before = service.get_profile(STUDENT_ID).version
        after = service.update_profile(STUDENT_ID, {"budget": 12345.0}).version
        assert before is not None and after is not None
        assert after.version == before.version + 1

    def test_update_profile_unknown_user_raises_not_found(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformNotFoundError):
            service.update_profile("ghost-user", {"budget": 1000.0})

    def test_update_profile_persists_across_calls(self) -> None:
        service, _store = make_profile_service()
        service.update_profile(STUDENT_ID, {"budget": 99999.0})
        refreshed = service.get_profile(STUDENT_ID)
        assert refreshed.preferences.budget == 99999.0


class TestPreferences:
    def test_get_preferences_returns_preferences(self) -> None:
        service, _store = make_profile_service()
        prefs = service.get_preferences(STUDENT_ID)
        assert prefs.user_id == STUDENT_ID
        assert prefs.student_mode is True

    def test_get_preferences_unknown_user_raises(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformNotFoundError):
            service.get_preferences("ghost-user")

    def test_update_preferences_updates_shopping_goals(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(STUDENT_ID, {"shopping_goals": ["gaming"]})
        assert updated.shopping_goals == ("gaming",)

    def test_update_preferences_updates_boolean_modes(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(CREATOR_ID, {"gaming_mode": True})
        assert updated.gaming_mode is True
        # Existing mode from fixtures should remain untouched unless updated.
        assert updated.creator_mode is True

    def test_update_preferences_keeps_profile_in_sync(self) -> None:
        service, _store = make_profile_service()
        service.update_preferences(STUDENT_ID, {"currency": "SGD"})
        profile = service.get_profile(STUDENT_ID)
        assert profile.preferences.currency == "SGD"

    @pytest.mark.parametrize(
        "field", ["battery_priority", "camera_priority", "performance_priority"]
    )
    def test_update_preferences_rejects_priority_above_one(self, field: str) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.update_preferences(STUDENT_ID, {field: 1.5})

    @pytest.mark.parametrize(
        "field", ["battery_priority", "camera_priority", "performance_priority"]
    )
    def test_update_preferences_rejects_priority_below_zero(self, field: str) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.update_preferences(STUDENT_ID, {field: -0.1})

    @pytest.mark.parametrize(
        "field", ["battery_priority", "camera_priority", "performance_priority"]
    )
    def test_update_preferences_accepts_priority_boundary_values(self, field: str) -> None:
        service, _store = make_profile_service()
        updated_low = service.update_preferences(STUDENT_ID, {field: 0.0})
        updated_high = service.update_preferences(STUDENT_ID, {field: 1.0})
        assert getattr(updated_low, field) == 0.0
        assert getattr(updated_high, field) == 1.0

    def test_update_preferences_rejects_negative_budget(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.update_preferences(STUDENT_ID, {"budget": -500.0})

    def test_update_preferences_allows_null_budget(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(STUDENT_ID, {"budget": None})
        assert updated.budget is None

    def test_update_preferences_clears_list_field_on_none(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(STUDENT_ID, {"categories": None})
        assert updated.categories == ()

    def test_update_preferences_sets_personal_profile_id(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(STUDENT_ID, {"personal_profile_id": "profile-gaming"})
        assert updated.personal_profile_id == "profile-gaming"

    def test_update_preferences_clears_personal_profile_id_when_blank(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_preferences(STUDENT_ID, {"personal_profile_id": ""})
        assert updated.personal_profile_id is None


class TestSettings:
    def test_get_settings_returns_settings(self) -> None:
        service, _store = make_profile_service()
        settings = service.get_settings(STUDENT_ID)
        assert settings.user_id == STUDENT_ID
        assert settings.theme == "system"

    def test_get_settings_unknown_user_raises(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformNotFoundError):
            service.get_settings("ghost-user")

    def test_update_settings_changes_theme(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_settings(STUDENT_ID, {"theme": "dark"})
        assert updated.theme == "dark"

    def test_update_settings_rejects_invalid_theme(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.update_settings(STUDENT_ID, {"theme": "solarized"})

    def test_update_settings_rejects_invalid_ai_mode(self) -> None:
        service, _store = make_profile_service()
        with pytest.raises(UserPlatformValidationError):
            service.update_settings(STUDENT_ID, {"ai_mode_preference": "turbo"})

    def test_update_settings_accepts_valid_ai_mode(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_settings(STUDENT_ID, {"ai_mode_preference": "maximum"})
        assert updated.ai_mode_preference == "maximum"

    def test_update_settings_updates_notification_settings(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_settings(
            STUDENT_ID, {"notification_settings": {"email_enabled": True, "newsletter": True}}
        )
        assert updated.notification_settings is not None
        assert updated.notification_settings.email_enabled is True
        assert updated.notification_settings.newsletter is True

    def test_update_settings_updates_privacy_settings(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_settings(
            STUDENT_ID, {"privacy_settings": {"share_community_activity": True}}
        )
        assert updated.privacy_settings["share_community_activity"] is True

    def test_update_settings_updates_language(self) -> None:
        service, _store = make_profile_service()
        updated = service.update_settings(STUDENT_ID, {"language": "fr"})
        assert updated.language == "fr"


class TestShoppingAssistantOverrides:
    def test_shopping_assistant_overrides_includes_currency(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(STUDENT_ID)
        assert overrides["currency"] == "PHP"

    def test_shopping_assistant_overrides_includes_student_use_case(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(STUDENT_ID)
        assert "student" in overrides["use_cases"]

    def test_shopping_assistant_overrides_includes_content_creation_use_case(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(CREATOR_ID)
        assert "content_creation" in overrides["use_cases"]

    def test_shopping_assistant_overrides_includes_budget_max(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(STUDENT_ID)
        assert overrides["budget_max"] == 35000.0

    def test_shopping_assistant_overrides_includes_category(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(STUDENT_ID)
        assert overrides["category"] == "laptop"

    def test_shopping_assistant_overrides_includes_personal_profile_id(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides(STUDENT_ID)
        assert overrides["profile_id"] == "profile-budget-student"

    def test_shopping_assistant_overrides_returns_empty_for_unknown_user(self) -> None:
        service, _store = make_profile_service()
        overrides = service.shopping_assistant_overrides("ghost-user")
        assert overrides == {}
