"""FastAPI TestClient tests for the Sprint 19 authenticated API surface.

Covers watchlists (auth + ownership + lifecycle), alert rules, notifications
& preferences, and the user dashboard endpoint — all wired through
dependency overrides on process-scoped, in-memory services (mirrors
``tests/unit/test_user_platform_api.py`` and ``tests/unit/test_watchlist_api.py``).

``settings.watchlists_require_auth`` defaults to True and is *not* patched
here — these tests exercise the real Bearer-token-required path via
``/api/v1/auth/login``, in contrast to the Sprint 10 anonymous-mode tests in
``test_watchlist_api.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.alerts.memory import InMemoryAlertRuleRepository
from app.auth.security import AuditLogger
from app.auth.service import AuthService
from app.core.dependencies import (
    get_alert_rule_repository,
    get_alert_rule_service,
    get_notification_center_repository,
    get_notification_center_service,
    get_notification_preference_service,
    get_user_dashboard_service,
    get_user_platform_service,
    get_watchlist_service,
)
from app.domain.entities.notifications import NotificationType
from app.intelligence.price_history import InMemoryPriceHistoryStore
from app.main import create_app
from app.notifications.memory import InMemoryNotificationCenterRepository
from app.profile.service import ProfileService
from app.services.alert_rule_service import AlertRuleService
from app.services.notification_center_service import NotificationCenterService
from app.services.notification_preference_service import NotificationPreferenceService
from app.services.price_history_service import PriceHistoryService
from app.services.user_dashboard_service import UserDashboardService
from app.services.user_platform_service import UserPlatformService
from app.services.watchlist_service_ext import ExtendedWatchlistService
from app.session.service import SessionService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore
from app.watchlists.memory import InMemoryWatchlistStore
from app.watchlists.security import WatchlistAuditLogger
from fastapi.testclient import TestClient

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
STUDENT_EMAIL = "student@example.com"
CREATOR_EMAIL = "creator@example.com"


def _make_platform() -> UserPlatformService:
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
        auth=auth, profiles=profiles, sessions=sessions, saved=store.saved, audit=audit
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    id_counter = {"n": 0}

    def next_id() -> str:
        id_counter["n"] += 1
        return f"api19-{id_counter['n']}"

    user_platform = _make_platform()

    watchlist_store = InMemoryWatchlistStore()
    price_service = PriceHistoryService(InMemoryPriceHistoryStore(), app_env="development")
    watchlists = ExtendedWatchlistService(
        watchlist_store,
        price_history_service=price_service,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        audit_logger=WatchlistAuditLogger(clock=lambda: FIXED_NOW, id_factory=next_id),
    )

    rule_repo = InMemoryAlertRuleRepository()
    alert_rules = AlertRuleService(
        rule_repo, watchlist_repository=watchlist_store, clock=lambda: FIXED_NOW, id_factory=next_id
    )

    notif_repo = InMemoryNotificationCenterRepository()
    notif_prefs = NotificationPreferenceService(notif_repo, clock=lambda: FIXED_NOW)
    notifications = NotificationCenterService(
        notif_repo, preference_service=notif_prefs, clock=lambda: FIXED_NOW, id_factory=next_id
    )

    dashboard_service = UserDashboardService(
        watchlists,
        alert_rule_service=alert_rules,
        alert_repository=watchlist_store,
        alert_event_repository=rule_repo,
        notification_center_service=notifications,
        user_platform_service=user_platform,
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
    )

    app.dependency_overrides[get_user_platform_service] = lambda: user_platform
    app.dependency_overrides[get_watchlist_service] = lambda: watchlists
    app.dependency_overrides[get_alert_rule_repository] = lambda: rule_repo
    app.dependency_overrides[get_alert_rule_service] = lambda: alert_rules
    app.dependency_overrides[get_notification_center_repository] = lambda: notif_repo
    app.dependency_overrides[get_notification_preference_service] = lambda: notif_prefs
    app.dependency_overrides[get_notification_center_service] = lambda: notifications
    app.dependency_overrides[get_user_dashboard_service] = lambda: dashboard_service

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, email: str = STUDENT_EMAIL, password: str = DEMO_PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


# --------------------------------------------------------------------- watchlists: auth


class TestWatchlistAuth:
    def test_create_watchlist_without_token_returns_401(self, client: TestClient) -> None:
        response = client.post("/api/v1/watchlists", json={"name": "Phones"})
        assert response.status_code == 401

    def test_list_watchlists_without_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/api/v1/watchlists")
        assert response.status_code == 401

    def test_create_and_list_watchlist_authenticated(self, client: TestClient) -> None:
        token = login(client)
        created = client.post(
            "/api/v1/watchlists",
            json={"name": "Phones", "is_default": True},
            headers=auth_header(token),
        )
        assert created.status_code == 200
        body = created.json()
        assert body["is_default"] is True
        assert body["status"] == "active"

        listed = client.get("/api/v1/watchlists", headers=auth_header(token))
        assert listed.status_code == 200
        names = [w["name"] for w in listed.json()["watchlists"]]
        assert "Phones" in names

    def test_watchlists_are_scoped_to_owner(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)
        client.post(
            "/api/v1/watchlists",
            json={"name": "Student's list"},
            headers=auth_header(student_token),
        )
        creator_listed = client.get("/api/v1/watchlists", headers=auth_header(creator_token))
        assert creator_listed.status_code == 200
        assert all(w["name"] != "Student's list" for w in creator_listed.json()["watchlists"])


class TestWatchlistOwnershipAndLifecycle:
    def test_other_user_cannot_access_watchlist(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)
        created = client.post(
            "/api/v1/watchlists", json={"name": "Private"}, headers=auth_header(student_token)
        )
        watchlist_id = created.json()["watchlist_id"]

        forbidden = client.get(
            f"/api/v1/watchlists/{watchlist_id}", headers=auth_header(creator_token)
        )
        assert forbidden.status_code == 403

    def test_pause_resume_archive_lifecycle_via_api(self, client: TestClient) -> None:
        token = login(client)
        created = client.post(
            "/api/v1/watchlists", json={"name": "Lifecycle"}, headers=auth_header(token)
        )
        watchlist_id = created.json()["watchlist_id"]

        paused = client.post(f"/api/v1/watchlists/{watchlist_id}/pause", headers=auth_header(token))
        assert paused.status_code == 200
        assert paused.json()["status"] == "paused"
        assert paused.json()["paused_at"] is not None

        resumed = client.post(
            f"/api/v1/watchlists/{watchlist_id}/resume", headers=auth_header(token)
        )
        assert resumed.status_code == 200
        assert resumed.json()["status"] == "active"

        archived = client.post(
            f"/api/v1/watchlists/{watchlist_id}/archive", headers=auth_header(token)
        )
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert archived.json()["archived_at"] is not None

    def test_watchlist_history_via_api(self, client: TestClient) -> None:
        token = login(client)
        created = client.post(
            "/api/v1/watchlists", json={"name": "History"}, headers=auth_header(token)
        )
        watchlist_id = created.json()["watchlist_id"]
        # The dedicated /offers endpoint (Sprint 19) records watchlist history;
        # the plain Sprint-10-compat POST /items endpoint intentionally does not.
        client.post(
            f"/api/v1/watchlists/{watchlist_id}/offers",
            json={"marketplace_offer_id": "offer-1", "canonical_product_id": "prod-1"},
            headers=auth_header(token),
        )
        history = client.get(
            f"/api/v1/watchlists/{watchlist_id}/history", headers=auth_header(token)
        )
        assert history.status_code == 200
        entries = history.json()["history"]
        assert any(e["event_type"] == "watchlist_created" for e in entries)
        assert any(e["event_type"] == "offer_tracked" for e in entries)


# --------------------------------------------------------------------- alert rules


class TestAlertRuleApi:
    def test_create_rule_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Price drop",
                "conditions": [{"condition_type": "price_drop"}],
            },
        )
        assert response.status_code == 401

    def test_create_list_get_delete_rule(self, client: TestClient) -> None:
        token = login(client)
        created = client.post(
            "/api/v1/alerts/rules",
            json={
                "name": "Any price drop",
                "conditions": [{"condition_type": "price_drop"}],
                "cooldown_seconds": 3600,
            },
            headers=auth_header(token),
        )
        assert created.status_code == 201
        rule = created.json()
        assert rule["name"] == "Any price drop"
        assert rule["status"] == "enabled"
        rule_id = rule["rule_id"]

        listed = client.get("/api/v1/alerts/rules", headers=auth_header(token))
        assert listed.status_code == 200
        assert any(r["rule_id"] == rule_id for r in listed.json()["rules"])

        got = client.get(f"/api/v1/alerts/rules/{rule_id}", headers=auth_header(token))
        assert got.status_code == 200

        deleted = client.delete(f"/api/v1/alerts/rules/{rule_id}", headers=auth_header(token))
        assert deleted.status_code == 204

        missing = client.get(f"/api/v1/alerts/rules/{rule_id}", headers=auth_header(token))
        assert missing.status_code == 404

    def test_rules_are_scoped_to_owner(self, client: TestClient) -> None:
        student_token = login(client, STUDENT_EMAIL)
        creator_token = login(client, CREATOR_EMAIL)
        client.post(
            "/api/v1/alerts/rules",
            json={"name": "Student rule", "conditions": [{"condition_type": "price_drop"}]},
            headers=auth_header(student_token),
        )
        creator_rules = client.get("/api/v1/alerts/rules", headers=auth_header(creator_token))
        assert creator_rules.status_code == 200
        assert creator_rules.json()["rules"] == []

    def test_invalid_condition_type_returns_400(self, client: TestClient) -> None:
        token = login(client)
        response = client.post(
            "/api/v1/alerts/rules",
            json={"name": "Bad", "conditions": [{"condition_type": "not_a_condition"}]},
            headers=auth_header(token),
        )
        assert response.status_code == 400


# --------------------------------------------------------------------- notifications


class TestNotificationApi:
    def test_list_notifications_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/notifications")
        assert response.status_code == 401

    def test_unread_count_mark_read_and_mark_all_read(self, client: TestClient) -> None:
        token = login(client)
        # Seed notifications directly via the overridden service instance so
        # the API surface (list/unread-count/mark-read) has data to act on.
        service: NotificationCenterService = client.app.dependency_overrides[
            get_notification_center_service
        ]()
        user = client.app.dependency_overrides[get_user_platform_service]().require_user(token)
        service.create_notification(
            user_id=user.user_id,
            title="Price drop!",
            body="iPhone dropped",
            type=NotificationType.PRICE_DROP,
        )
        service.create_notification(
            user_id=user.user_id,
            title="Restocked",
            body="Back in stock",
            type=NotificationType.RESTOCK,
        )

        unread = client.get("/api/v1/notifications/unread-count", headers=auth_header(token))
        assert unread.status_code == 200
        assert unread.json()["unread_count"] == 2

        listed = client.get("/api/v1/notifications", headers=auth_header(token))
        assert listed.status_code == 200
        notifications = listed.json()["notifications"]
        assert len(notifications) == 2

        first_id = notifications[0]["notification_id"]
        marked = client.post(f"/api/v1/notifications/{first_id}/read", headers=auth_header(token))
        assert marked.status_code == 200
        assert marked.json()["is_read"] is True

        after_one_read = client.get(
            "/api/v1/notifications/unread-count", headers=auth_header(token)
        )
        assert after_one_read.json()["unread_count"] == 1

        mark_all = client.post("/api/v1/notifications/read-all", headers=auth_header(token))
        assert mark_all.status_code == 200
        assert mark_all.json()["marked_read"] == 1

        final_unread = client.get("/api/v1/notifications/unread-count", headers=auth_header(token))
        assert final_unread.json()["unread_count"] == 0

    def test_archive_and_delete_notification(self, client: TestClient) -> None:
        token = login(client)
        service: NotificationCenterService = client.app.dependency_overrides[
            get_notification_center_service
        ]()
        user = client.app.dependency_overrides[get_user_platform_service]().require_user(token)
        notification = service.create_notification(
            user_id=user.user_id, title="Hi", body="body", type=NotificationType.SYSTEM
        )

        archived = client.post(
            f"/api/v1/notifications/{notification.notification_id}/archive",
            headers=auth_header(token),
        )
        assert archived.status_code == 200
        assert archived.json()["is_archived"] is True

        deleted = client.delete(
            f"/api/v1/notifications/{notification.notification_id}", headers=auth_header(token)
        )
        assert deleted.status_code == 204

        # Second delete of the same id now 404s.
        redelete = client.delete(
            f"/api/v1/notifications/{notification.notification_id}", headers=auth_header(token)
        )
        assert redelete.status_code == 404


class TestNotificationPreferencesApi:
    def test_get_preferences_defaults_marketing_off(self, client: TestClient) -> None:
        token = login(client)
        response = client.get("/api/v1/notification-preferences", headers=auth_header(token))
        assert response.status_code == 200
        body = response.json()
        assert body["marketing_enabled"] is False
        assert body["in_app_enabled"] is True

    def test_update_preferences_quiet_hours_and_price_alerts(self, client: TestClient) -> None:
        token = login(client)
        response = client.put(
            "/api/v1/notification-preferences",
            json={
                "price_alerts": False,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
            },
            headers=auth_header(token),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["price_alerts"] is False
        assert body["quiet_hours_start"] == "22:00"
        assert body["quiet_hours_end"] == "07:00"


# --------------------------------------------------------------------- dashboard


class TestDashboardApi:
    def test_dashboard_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 401

    def test_dashboard_returns_summary_and_limitations(self, client: TestClient) -> None:
        token = login(client)
        client.post("/api/v1/watchlists", json={"name": "Phones"}, headers=auth_header(token))
        response = client.get("/api/v1/dashboard", headers=auth_header(token))
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["watched_products"] == 0
        assert body["limitations"]
        card_types = {card["card_type"] for card in body["cards"]}
        assert "watchlists" in card_types

    def test_dashboard_reflects_created_alert_rule(self, client: TestClient) -> None:
        token = login(client)
        client.post(
            "/api/v1/alerts/rules",
            json={"name": "Rule", "conditions": [{"condition_type": "price_drop"}]},
            headers=auth_header(token),
        )
        response = client.get("/api/v1/dashboard", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["summary"]["active_alert_rules"] == 1
