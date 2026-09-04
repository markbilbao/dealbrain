"""Sprint 28.1 account deletion foundation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import get_user_platform_service
from app.domain.entities.user_platform import SavedProduct
from app.domain.entities.watchlist import Watchlist
from app.main import create_app
from app.privacy.lifecycle import ACCOUNT_DELETE_CONFIRMATION, AccountLifecycleService
from app.profile.service import ProfileService
from app.services.user_platform_service import UserPlatformService
from app.session.service import SessionService
from app.user.fixtures import seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from app.watchlists.memory import InMemoryWatchlistStore
from fastapi.testclient import TestClient

PASSWORD = "ValidPass123!"


def _platform(store: InMemoryUserPlatformStore | None = None, *, watchlists=None):
    store = store or InMemoryUserPlatformStore()
    audit = AuditLogger(store.audit)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        audit=audit,
    )
    lifecycle = AccountLifecycleService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        saved=store.saved,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        consents=store.consents,
        audit=audit,
        watchlists=watchlists,
    )
    service = UserPlatformService(
        auth=auth,
        profiles=ProfileService(users=store.users, profiles=store.profiles),
        sessions=SessionService(sessions=store.sessions, auth=auth),
        saved=store.saved,
        lifecycle=lifecycle,
        consents=store.consents,
        audit=audit,
    )
    return store, service


def _client(service: UserPlatformService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_user_platform_service] = lambda: service
    return TestClient(app)


def _delete_body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "confirmation": ACCOUNT_DELETE_CONFIRMATION,
        "password": PASSWORD,
    }
    payload.update(overrides)
    return payload


def test_unauthenticated_delete_rejected() -> None:
    _store, service = _platform()
    client = _client(service)
    response = client.post("/api/v1/auth/account/delete", json=_delete_body())
    assert response.status_code == 401


def test_wrong_confirmation_rejected() -> None:
    store, service = _platform()
    result = service.register(email="del@example.com", password=PASSWORD, display_name="Del")
    client = _client(service)
    response = client.post(
        "/api/v1/auth/account/delete",
        json=_delete_body(confirmation="please-delete"),
        headers={"Authorization": f"Bearer {result.access_token}"},
    )
    assert response.status_code == 400
    assert store.users.get_by_id(result.user.user_id) is not None


def test_wrong_password_rejected() -> None:
    store, service = _platform()
    result = service.register(email="pw@example.com", password=PASSWORD, display_name="Pw")
    client = _client(service)
    response = client.post(
        "/api/v1/auth/account/delete",
        json=_delete_body(password="WrongPass123!"),
        headers={"Authorization": f"Bearer {result.access_token}"},
    )
    assert response.status_code == 401
    assert store.users.get_by_id(result.user.user_id) is not None


def test_client_supplied_user_id_cannot_delete_another_user() -> None:
    store, service = _platform()
    other = service.register(email="victim@example.com", password=PASSWORD, display_name="Victim")
    attacker = service.register(email="attacker@example.com", password=PASSWORD, display_name="Att")
    client = _client(service)
    response = client.post(
        "/api/v1/auth/account/delete",
        json=_delete_body(user_id=other.user.user_id),
        headers={"Authorization": f"Bearer {attacker.access_token}"},
    )
    assert response.status_code == 200
    assert store.users.get_by_id(other.user.user_id) is not None
    assert store.users.get_by_id(attacker.user.user_id) is None


def test_valid_deletion_revokes_sessions_and_removes_pii() -> None:
    store, service = _platform()
    first = service.register(email="keep-me@example.com", password=PASSWORD, display_name="Keep")
    target = service.register(email="erase-me@example.com", password=PASSWORD, display_name="Erase")
    service.save_product(
        target.access_token,
        {"product_id": "p1", "product_name": "Headphones"},
    )
    reset = service.request_password_reset("erase-me@example.com")
    watchlists = InMemoryWatchlistStore()
    now = datetime.now(UTC)
    watchlists.save_watchlist(
        Watchlist(
            watchlist_id="wl-erase",
            name="Mine",
            created_at=now,
            owner_id=target.user.user_id,
        )
    )
    watchlists.save_watchlist(
        Watchlist(
            watchlist_id="wl-keep",
            name="Theirs",
            created_at=now,
            owner_id=first.user.user_id,
        )
    )
    store, service = _platform(store, watchlists=watchlists)
    client = _client(service)
    response = client.post(
        "/api/v1/auth/account/delete",
        json=_delete_body(),
        headers={"Authorization": f"Bearer {target.access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "deleted"
    assert body["sessions_revoked"] >= 1
    assert store.users.get_by_id(target.user.user_id) is None
    assert store.users.get_by_email("erase-me@example.com") is None
    assert store.profiles.get_profile(target.user.user_id) is None
    assert store.saved.list_saved_products(target.user.user_id) == []
    assert store.sessions.list_for_user(target.user.user_id) == []
    assert watchlists.get_watchlist("wl-erase") is None
    assert watchlists.get_watchlist("wl-keep") is not None
    assert store.users.get_by_id(first.user.user_id) is not None
    assert store.users.get_by_email("keep-me@example.com") is not None
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {target.access_token}"},
    )
    assert me.status_code == 401
    demo_token = reset.get("reset_token_demo_only")
    if demo_token:
        confirm = service.confirm_password_reset
        try:
            confirm(demo_token, "NewValid123!")
            reset_ok = True
        except Exception:
            reset_ok = False
        assert reset_ok is False
    retained = " ".join(body["retained_limitations"]).lower()
    assert "backup" in retained
    assert "early access" in retained
    assert "audit" in retained


def test_other_users_untouched_and_repeat_delete_is_unauthorized() -> None:
    store, service = _platform()
    other = service.register(email="other@example.com", password=PASSWORD, display_name="Other")
    target = service.register(email="gone@example.com", password=PASSWORD, display_name="Gone")
    client = _client(service)
    headers = {"Authorization": f"Bearer {target.access_token}"}
    first = client.post("/api/v1/auth/account/delete", json=_delete_body(), headers=headers)
    assert first.status_code == 200
    repeat = client.post("/api/v1/auth/account/delete", json=_delete_body(), headers=headers)
    assert repeat.status_code == 401
    assert store.users.get_by_id(other.user.user_id) is not None
    assert store.saved.list_saved_products(other.user.user_id) == []


def test_seeded_demo_user_not_required_for_isolation() -> None:
    store = InMemoryUserPlatformStore()
    seed_demo_users(store)
    before = {user.user_id for user in store.users.list_users()}
    _store, service = _platform(store)
    created = service.register(email="temp-del@example.com", password=PASSWORD, display_name="Temp")
    client = _client(service)
    response = client.post(
        "/api/v1/auth/account/delete",
        json=_delete_body(),
        headers={"Authorization": f"Bearer {created.access_token}"},
    )
    assert response.status_code == 200
    remaining = {user.user_id for user in store.users.list_users()}
    assert before <= remaining
    assert created.user.user_id not in remaining


def test_saved_product_entity_roundtrip_for_propagation() -> None:
    store, service = _platform()
    user = service.register(email="save@example.com", password=PASSWORD, display_name="Save")
    item = SavedProduct(
        id="s1",
        user_id=user.user.user_id,
        product_id="p9",
        product_name="Camera",
    )
    store.saved.save_product(item)
    store.saved.delete_all_for_user(user.user.user_id)
    assert store.saved.list_saved_products(user.user.user_id) == []
