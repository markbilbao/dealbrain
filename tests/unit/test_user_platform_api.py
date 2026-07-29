"""FastAPI TestClient tests for the User Platform API (auth, profile, saved items)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import get_user_platform_service
from app.main import create_app
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from fastapi.testclient import TestClient

STUDENT_EMAIL = "student@example.com"
CREATOR_EMAIL = "creator@example.com"


def make_platform() -> UserPlatformService:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        audit=audit,
    )
    profiles = ProfileService(users=store.users, profiles=store.profiles)
    sessions = SessionService(sessions=store.sessions, auth=auth)
    return UserPlatformService(
        auth=auth,
        profiles=profiles,
        sessions=sessions,
        saved=store.saved,
        audit=audit,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    service = make_platform()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, email: str = STUDENT_EMAIL, password: str = DEMO_PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


class TestAuthEndpoints:
    def test_register_creates_account_and_session(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newbie@example.com",
                "password": "ValidPass123!",
                "display_name": "Newbie",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["user"]["email"] == "newbie@example.com"
        assert body["access_token"]

    def test_register_duplicate_email_returns_409(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": STUDENT_EMAIL,
                "password": "ValidPass123!",
                "display_name": "Dup",
            },
        )
        assert response.status_code == 409

    def test_register_weak_password_returns_400(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "weak", "display_name": "Weak"},
        )
        assert response.status_code in (400, 422)

    def test_login_success_returns_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": DEMO_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["user"]["email"] == STUDENT_EMAIL

    def test_login_wrong_password_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    def test_login_unknown_email_returns_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "WhoKnows123!"},
        )
        assert response.status_code == 401

    def test_logout_revokes_session(self, client: TestClient) -> None:
        token = login(client)
        response = client.post("/api/v1/auth/logout", headers=auth_header(token))
        assert response.status_code == 204
        me_response = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert me_response.status_code == 401

    def test_logout_without_token_succeeds_noop(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 204

    def test_get_me_returns_current_user(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["email"] == STUDENT_EMAIL

    def test_get_me_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_with_bogus_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me", headers=auth_header("not-a-real-token"))
        assert response.status_code == 401

    def test_demo_endpoint_lists_demo_users(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/demo")
        assert response.status_code == 200
        emails = {u["email"] for u in response.json()["demo_users"]}
        assert STUDENT_EMAIL in emails

    def test_meta_endpoint_returns_platform_metadata(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/meta")
        assert response.status_code == 200
        body = response.json()
        assert body["authentication"] is True
        assert body["mfa"] is False
        assert body["oauth"] is False


class TestProfileEndpoints:
    def test_get_profile_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/api/v1/profile")
        assert response.status_code == 401

    def test_get_profile_returns_seeded_data(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/profile", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["display_name"] == "Demo Student"

    def test_update_profile_changes_display_name(self, client: TestClient) -> None:
        token = login(client)
        response = client.put(
            "/api/v1/profile",
            json={"display_name": "Renamed Student"},
            headers=auth_header(token),
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Renamed Student"

    def test_get_preferences_returns_seeded_data(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/profile/preferences", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["student_mode"] is True

    def test_update_preferences_changes_budget(self, client: TestClient) -> None:
        token = login(client)
        response = client.put(
            "/api/v1/profile/preferences",
            json={"budget": 42000.0},
            headers=auth_header(token),
        )
        assert response.status_code == 200
        assert response.json()["budget"] == 42000.0

    def test_update_preferences_out_of_range_priority_returns_422(self, client: TestClient) -> None:
        token = login(client)
        response = client.put(
            "/api/v1/profile/preferences",
            json={"battery_priority": 5.0},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    def test_profile_requires_authentication_for_update(self, client: TestClient) -> None:
        response = client.put("/api/v1/profile", json={"display_name": "Nope"})
        assert response.status_code == 401


class TestSavedProductsEndpoints:
    def test_list_saved_products_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/user/saved-products")
        assert response.status_code == 401

    def test_list_saved_products_returns_seeded_item(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/user/saved-products", headers=auth_header(token))
        assert response.status_code == 200
        assert any(item["product_id"] == "sa-laptop-loq-15" for item in response.json())

    def test_create_saved_product(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/saved-products",
            json={"product_id": "sa-new", "product_name": "New Item"},
            headers=auth_header(token),
        )
        assert response.status_code == 201
        assert response.json()["product_id"] == "sa-new"

    def test_create_saved_product_missing_fields_returns_422(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/saved-products",
            json={"marketplace": "Shopee"},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    def test_delete_saved_product(self, client: TestClient) -> None:
        token = login(client)
        create_response = client.post(
            "/api/v1/user/saved-products",
            json={"product_id": "sa-delete-me", "product_name": "Delete Me"},
            headers=auth_header(token),
        )
        saved_id = create_response.json()["id"]
        delete_response = client.delete(
            f"/api/v1/user/saved-products/{saved_id}", headers=auth_header(token)
        )
        assert delete_response.status_code == 204

    def test_delete_nonexistent_saved_product_returns_404(self, client: TestClient) -> None:
        token = login(client)
        response = client.delete(
            "/api/v1/user/saved-products/does-not-exist", headers=auth_header(token)
        )
        assert response.status_code == 404


class TestHistoryComparisonsSearchesEndpoints:
    def test_list_history_returns_seeded_item(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/user/history", headers=auth_header(token))
        assert response.status_code == 200
        assert any(item["id"] == "hist-student-1" for item in response.json())

    def test_history_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/user/history")
        assert response.status_code == 401

    def test_list_comparisons_returns_seeded_item(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/user/comparisons", headers=auth_header(token))
        assert response.status_code == 200
        assert any(item["id"] == "cmp-student-1" for item in response.json())

    def test_create_comparison(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/comparisons",
            json={"product_ids": ["sa-a", "sa-b"], "title": "New comparison"},
            headers=auth_header(token),
        )
        assert response.status_code == 201
        assert response.json()["title"] == "New comparison"

    def test_create_comparison_requires_two_products(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/comparisons",
            json={"product_ids": ["sa-a"]},
            headers=auth_header(token),
        )
        assert response.status_code == 422

    def test_list_searches_returns_seeded_item(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/user/searches", headers=auth_header(token))
        assert response.status_code == 200
        assert any(item["id"] == "search-student-1" for item in response.json())

    def test_create_search(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/searches",
            json={"query": "gaming laptop", "filters": {"category": "laptop"}},
            headers=auth_header(token),
        )
        assert response.status_code == 201
        assert response.json()["query"] == "gaming laptop"

    def test_get_recently_viewed(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/user/recently-viewed", headers=auth_header(token))
        assert response.status_code == 200
        assert "sa-laptop-loq-15" in response.json()["product_ids"]

    def test_mark_viewed(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/user/recently-viewed",
            json={"product_id": "sa-just-viewed"},
            headers=auth_header(token),
        )
        assert response.status_code == 200
        assert response.json()["product_ids"][0] == "sa-just-viewed"


class TestAuthorizationIsolation:
    def test_saved_products_are_isolated_between_users(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)

        student_response = client.get(
            "/api/v1/user/saved-products", headers=auth_header(student_token)
        )
        creator_response = client.get(
            "/api/v1/user/saved-products", headers=auth_header(creator_token)
        )
        student_ids = {item["id"] for item in student_response.json()}
        creator_ids = {item["id"] for item in creator_response.json()}
        assert student_ids.isdisjoint(creator_ids)

    def test_new_saved_product_not_visible_to_other_user(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)

        create_response = client.post(
            "/api/v1/user/saved-products",
            json={"product_id": "sa-private", "product_name": "Private Item"},
            headers=auth_header(student_token),
        )
        saved_id = create_response.json()["id"]

        creator_items = client.get(
            "/api/v1/user/saved-products", headers=auth_header(creator_token)
        ).json()
        assert saved_id not in {item["id"] for item in creator_items}

    def test_profiles_are_isolated_between_users(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)

        student_profile = client.get("/api/v1/profile", headers=auth_header(student_token)).json()
        creator_profile = client.get("/api/v1/profile", headers=auth_header(creator_token)).json()
        assert student_profile["display_name"] != creator_profile["display_name"]
        assert student_profile["user_id"] != creator_profile["user_id"]

    def test_one_users_token_cannot_delete_anothers_saved_product(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)

        creator_items = client.get(
            "/api/v1/user/saved-products", headers=auth_header(creator_token)
        ).json()
        assert creator_items, "expected seeded saved product for creator"
        creator_saved_id = creator_items[0]["id"]

        response = client.delete(
            f"/api/v1/user/saved-products/{creator_saved_id}",
            headers=auth_header(student_token),
        )
        assert response.status_code == 404
