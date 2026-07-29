"""Unit tests for saved items (products, comparisons, history, searches, recently
viewed) via UserPlatformService."""

from __future__ import annotations

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.domain.exceptions import UserPlatformAuthError, UserPlatformValidationError
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore

STUDENT_EMAIL = "student@example.com"


_AUTH_KWARGS = ("clock", "session_ttl_seconds", "remember_me_ttl_seconds", "rate_limiter")


def make_platform(**kwargs: object) -> tuple[UserPlatformService, InMemoryUserPlatformStore]:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        audit=AuditLogger(store.audit),
        **{k: v for k, v in kwargs.items() if k in _AUTH_KWARGS},
    )
    clock = kwargs.get("clock")
    profiles = ProfileService(users=store.users, profiles=store.profiles, clock=clock)  # type: ignore[arg-type]
    sessions = SessionService(sessions=store.sessions, auth=auth, clock=clock)  # type: ignore[arg-type]
    return (
        UserPlatformService(
            auth=auth,
            profiles=profiles,
            sessions=sessions,
            saved=store.saved,
            audit=AuditLogger(store.audit),
            clock=kwargs.get("clock"),  # type: ignore[arg-type]
        ),
        store,
    )


def login_student(platform: UserPlatformService) -> str:
    result = platform.login(email=STUDENT_EMAIL, password=DEMO_PASSWORD)
    return result.access_token


class TestSavedProducts:
    def test_list_saved_products_includes_seeded_item(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        items = platform.list_saved_products(token)
        assert any(item.product_id == "sa-laptop-loq-15" for item in items)

    def test_save_product_requires_product_id_and_name(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        with pytest.raises(UserPlatformValidationError):
            platform.save_product(token, {"marketplace": "Shopee"})

    def test_save_product_success(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        item = platform.save_product(
            token,
            {
                "product_id": "sa-phone-new",
                "product_name": "New Phone",
                "marketplace": "Lazada",
                "price": 19999.0,
                "favorite": True,
            },
        )
        assert item.product_id == "sa-phone-new"
        assert item.favorite is True
        assert item.price == 19999.0

    def test_save_product_defaults_currency_to_php(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        item = platform.save_product(token, {"product_id": "sa-x", "product_name": "X Product"})
        assert item.currency == "PHP"

    def test_delete_saved_product_removes_item(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        saved = platform.save_product(
            token, {"product_id": "sa-temp", "product_name": "Temp Product"}
        )
        platform.delete_saved_product(token, saved.id)
        remaining_ids = {item.id for item in platform.list_saved_products(token)}
        assert saved.id not in remaining_ids

    def test_delete_nonexistent_product_raises(self) -> None:
        from app.domain.exceptions import UserPlatformNotFoundError

        platform, _store = make_platform()
        token = login_student(platform)
        with pytest.raises(UserPlatformNotFoundError):
            platform.delete_saved_product(token, "no-such-saved-id")

    def test_saved_products_require_authentication(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.list_saved_products(None)

    def test_saved_products_require_valid_token(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.list_saved_products("bogus-token")


class TestSavedComparisons:
    def test_list_comparisons_includes_seeded_item(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        comparisons = platform.list_comparisons(token)
        assert any(c.id == "cmp-student-1" for c in comparisons)

    def test_save_comparison_requires_two_products(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        with pytest.raises(UserPlatformValidationError):
            platform.save_comparison(token, {"product_ids": ["only-one"]})

    def test_save_comparison_success(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        comparison = platform.save_comparison(
            token,
            {"product_ids": ["sa-a", "sa-b"], "title": "New comparison"},
        )
        assert comparison.product_ids == ("sa-a", "sa-b")
        assert comparison.title == "New comparison"

    def test_save_comparison_requires_authentication(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.save_comparison(None, {"product_ids": ["sa-a", "sa-b"]})


class TestRecommendationHistory:
    def test_list_history_includes_seeded_item(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        history = platform.list_history(token)
        assert any(h.id == "hist-student-1" for h in history)

    def test_add_history_direct_by_user_id(self) -> None:
        platform, store = make_platform()
        user = store.users.get_by_email(STUDENT_EMAIL)
        assert user is not None
        entry = platform.add_history(
            user.user_id,
            query="Best budget phone",
            recommendation_summary="Pixel wins on camera.",
            product_ids=("sa-phone-pixel-9",),
        )
        assert entry.query == "Best budget phone"
        token = login_student(platform)
        history = platform.list_history(token)
        assert any(h.id == entry.id for h in history)

    def test_history_requires_authentication_via_token_api(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.list_history(None)


class TestSavedSearches:
    def test_list_searches_includes_seeded_item(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        searches = platform.list_searches(token)
        assert any(s.id == "search-student-1" for s in searches)

    def test_save_search_requires_query(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        with pytest.raises(UserPlatformValidationError):
            platform.save_search(token, {"query": "   "})

    def test_save_search_success(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        search = platform.save_search(
            token, {"query": "gaming laptop", "filters": {"category": "laptop"}}
        )
        assert search.query == "gaming laptop"
        assert search.filters["category"] == "laptop"

    def test_save_search_requires_authentication(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.save_search(None, {"query": "anything"})


class TestRecentlyViewed:
    def test_get_recently_viewed_includes_seeded_items(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        recent = platform.get_recently_viewed(token)
        assert "sa-laptop-loq-15" in recent.product_ids

    def test_mark_viewed_adds_product_to_front(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        updated = platform.mark_viewed(token, "sa-new-product")
        assert updated.product_ids[0] == "sa-new-product"

    def test_mark_viewed_deduplicates_existing_entry(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        platform.mark_viewed(token, "sa-laptop-loq-15")
        updated = platform.get_recently_viewed(token)
        assert updated.product_ids.count("sa-laptop-loq-15") == 1

    def test_mark_viewed_moves_existing_entry_to_front(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        updated = platform.mark_viewed(token, "sa-phone-pixel-9")
        assert updated.product_ids[0] == "sa-phone-pixel-9"

    def test_mark_viewed_blank_product_raises(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        with pytest.raises(UserPlatformValidationError):
            platform.mark_viewed(token, "   ")

    def test_mark_viewed_caps_history_length(self) -> None:
        platform, _store = make_platform()
        token = login_student(platform)
        for i in range(25):
            platform.mark_viewed(token, f"sa-product-{i}")
        updated = platform.get_recently_viewed(token)
        assert len(updated.product_ids) <= 20

    def test_get_recently_viewed_for_user_without_history_is_empty(self) -> None:
        platform, _store = make_platform()
        result = platform.register(
            email="fresh@example.com",
            password="ValidPass123!",
            display_name="Fresh User",
        )
        recent = platform.get_recently_viewed(result.access_token)
        assert recent.product_ids == ()

    def test_recently_viewed_requires_authentication(self) -> None:
        platform, _store = make_platform()
        with pytest.raises(UserPlatformAuthError):
            platform.get_recently_viewed(None)


class TestCrossUserIsolation:
    def test_saved_products_are_isolated_between_users(self) -> None:
        platform, _store = make_platform()
        student_token = login_student(platform)
        creator_result = platform.login(email="creator@example.com", password=DEMO_PASSWORD)
        creator_token = creator_result.access_token

        student_items = platform.list_saved_products(student_token)
        creator_items = platform.list_saved_products(creator_token)

        student_ids = {item.id for item in student_items}
        creator_ids = {item.id for item in creator_items}
        assert student_ids.isdisjoint(creator_ids)

    def test_new_saved_product_only_visible_to_owner(self) -> None:
        platform, _store = make_platform()
        student_token = login_student(platform)
        creator_result = platform.login(email="creator@example.com", password=DEMO_PASSWORD)
        creator_token = creator_result.access_token

        saved = platform.save_product(
            student_token, {"product_id": "sa-only-student", "product_name": "Only Student"}
        )
        creator_ids = {item.id for item in platform.list_saved_products(creator_token)}
        assert saved.id not in creator_ids
