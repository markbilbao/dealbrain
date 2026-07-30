"""Tier-1 collection dual-run and pagination contract tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.dependencies import (
    get_alert_event_repository,
    get_alert_service,
    get_db,
    get_notification_center_service,
    get_user_platform_service,
    get_watchlist_service,
)
from app.domain.entities.alerts import AlertEvent, AlertEventType, AlertSeverity
from app.domain.entities.notifications import (
    Notification,
    NotificationChannel,
    NotificationSeverity,
    NotificationType,
)
from app.domain.entities.watchlist import Watchlist, WatchlistStatus
from app.main import create_app
from datetime import UTC, datetime
from httpx import ASGITransport, AsyncClient


def _user(user_id: str = "user-s24"):
    user = MagicMock()
    user.user_id = user_id
    return user


@pytest.fixture
async def client_with_overrides():
    app = create_app()
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    platform = MagicMock()
    platform.require_user.return_value = _user()
    app.dependency_overrides[get_user_platform_service] = lambda: platform

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, app, platform
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_notifications_dual_run_items_and_pagination(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    notes = [
        Notification(
            notification_id=f"n-{i}",
            user_id="user-s24",
            title=f"T{i}",
            body="b",
            type=NotificationType.PRICE_DROP,
            severity=NotificationSeverity.INFO,
            channel=NotificationChannel.IN_APP,
            created_at=now,
        )
        for i in range(3)
    ]
    service = MagicMock()
    service.list_notifications.return_value = notes[:2]
    app.dependency_overrides[get_notification_center_service] = lambda: service

    response = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": "Bearer tok"},
        params={"limit": 2, "offset": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert "notifications" in body
    assert body["items"] == body["notifications"]
    assert body["pagination"]["limit"] == 2
    assert body["pagination"]["offset"] == 0


@pytest.mark.anyio
async def test_notifications_invalid_sort(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    service = MagicMock()
    service.list_notifications.return_value = []
    app.dependency_overrides[get_notification_center_service] = lambda: service
    response = await client.get(
        "/api/v1/notifications",
        headers={"Authorization": "Bearer tok"},
        params={"sort": "affiliate_commission"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_watchlists_named_key_and_pagination(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    wl = Watchlist(
        watchlist_id="wl-1",
        name="Phones",
        owner_id="user-s24",
        created_at=now,
        updated_at=now,
        status=WatchlistStatus.ACTIVE,
    )
    service = MagicMock()
    service.list_watchlists.return_value = [wl]
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "watchlists" in body
    assert body["items"] == body["watchlists"]
    assert body["pagination"]["total"] == 1


@pytest.mark.anyio
async def test_watchlists_no_pagination_returns_full_list(client_with_overrides) -> None:
    """Legacy clients (no limit/offset/skip) must receive the complete collection."""
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    watchlists = [
        Watchlist(
            watchlist_id=f"wl-{i}",
            name=f"List {i}",
            owner_id="user-s24",
            created_at=now,
            updated_at=now,
            status=WatchlistStatus.ACTIVE,
        )
        for i in range(120)
    ]
    service = MagicMock()
    service.list_watchlists.return_value = watchlists
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["watchlists"]) == 120
    assert body["items"] == body["watchlists"]
    assert body["pagination"]["total"] == 120
    assert body["pagination"]["has_more"] is False


@pytest.mark.anyio
async def test_watchlists_limit_only(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    watchlists = [
        Watchlist(
            watchlist_id=f"wl-{i}",
            name=f"List {i}",
            owner_id="user-s24",
            created_at=now,
            updated_at=now,
            status=WatchlistStatus.ACTIVE,
        )
        for i in range(10)
    ]
    service = MagicMock()
    service.list_watchlists.return_value = watchlists
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
        params={"limit": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["watchlists"]) == 3
    assert body["pagination"]["limit"] == 3
    assert body["pagination"]["offset"] == 0
    assert body["pagination"]["total"] == 10
    assert body["pagination"]["has_more"] is True


@pytest.mark.anyio
async def test_watchlists_offset_only(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    watchlists = [
        Watchlist(
            watchlist_id=f"wl-{i}",
            name=f"List {i}",
            owner_id="user-s24",
            created_at=now,
            updated_at=now,
            status=WatchlistStatus.ACTIVE,
        )
        for i in range(10)
    ]
    service = MagicMock()
    service.list_watchlists.return_value = watchlists
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
        params={"offset": 2},
    )
    assert response.status_code == 200
    body = response.json()
    # offset-only uses default page size 100; all remaining rows fit.
    assert len(body["watchlists"]) == 8
    assert body["pagination"]["offset"] == 2
    assert body["watchlists"][0]["watchlist_id"] == "wl-2"


@pytest.mark.anyio
async def test_watchlists_limit_and_offset(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    watchlists = [
        Watchlist(
            watchlist_id=f"wl-{i}",
            name=f"List {i}",
            owner_id="user-s24",
            created_at=now,
            updated_at=now,
            status=WatchlistStatus.ACTIVE,
        )
        for i in range(10)
    ]
    service = MagicMock()
    service.list_watchlists.return_value = watchlists
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
        params={"limit": 2, "offset": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert [w["watchlist_id"] for w in body["watchlists"]] == ["wl-3", "wl-4"]
    assert body["pagination"]["limit"] == 2
    assert body["pagination"]["offset"] == 3
    assert body["items"] == body["watchlists"]


@pytest.mark.anyio
async def test_watchlists_conflicting_skip_offset(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    service = MagicMock()
    service.list_watchlists.return_value = []
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
        params={"skip": 1, "offset": 2, "limit": 5},
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body or body.get("error") == "validation_error"


@pytest.mark.anyio
async def test_watchlists_skip_alias_of_offset(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    watchlists = [
        Watchlist(
            watchlist_id=f"wl-{i}",
            name=f"List {i}",
            owner_id="user-s24",
            created_at=now,
            updated_at=now,
            status=WatchlistStatus.ACTIVE,
        )
        for i in range(5)
    ]
    service = MagicMock()
    service.list_watchlists.return_value = watchlists
    service.list_items.return_value = []
    app.dependency_overrides[get_watchlist_service] = lambda: service

    response = await client.get(
        "/api/v1/watchlists",
        headers={"Authorization": "Bearer tok"},
        params={"skip": 2, "limit": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert [w["watchlist_id"] for w in body["watchlists"]] == ["wl-2", "wl-3"]
    assert body["pagination"]["offset"] == 2


@pytest.mark.anyio
async def test_alert_events_offset_and_dual_run(client_with_overrides) -> None:
    client, app, _ = client_with_overrides
    now = datetime.now(tz=UTC)
    events = [
        AlertEvent(
            event_id=f"e-{i}",
            user_id="user-s24",
            rule_id="r-1",
            event_type=AlertEventType.PRICE_DROP,
            severity=AlertSeverity.INFO,
            created_at=now,
            dedupe_key=f"d-{i}",
        )
        for i in range(3)
    ]
    repo = MagicMock()
    repo.list_events.return_value = events
    app.dependency_overrides[get_alert_event_repository] = lambda: repo

    response = await client.get(
        "/api/v1/alerts/events",
        headers={"Authorization": "Bearer tok"},
        params={"limit": 2, "offset": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert body["items"] == body["events"]
    assert body["pagination"]["offset"] == 1
    assert len(body["events"]) == 2


@pytest.mark.anyio
async def test_legacy_alerts_still_available_and_deprecated_flag(
    client_with_overrides,
) -> None:
    client, app, _ = client_with_overrides
    alert_service = MagicMock()
    alert_service.list_alerts.return_value = []
    app.dependency_overrides[get_alert_service] = lambda: alert_service

    response = await client.get("/api/v1/alerts", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert "alerts" in body
    assert body["items"] == body["alerts"]

    schema = app.openapi()
    assert schema["paths"]["/api/v1/alerts"]["get"]["deprecated"] is True
