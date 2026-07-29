"""User Dashboard application service — Sprint 19.

Assembles a per-user :class:`UserDashboard` from watchlists, alert rules,
alert events, notifications, and (optionally) marketplace freshness /
personalization context. All I/O happens here; the actual card/summary
construction is delegated to the pure functions in
``app.dashboard.assembler`` so the shaping logic stays independently
testable.

Every collaborator except ``watchlist_service`` is optional — a dashboard can
always be produced (possibly mostly empty) even when alerting, notifications,
or marketplace services are not wired up.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.dashboard.assembler import assemble_dashboard
from app.domain.entities.dashboard import DASHBOARD_LIMITATIONS_NOTE, UserActivity, UserDashboard
from app.domain.entities.watchlist import Watchlist, WatchlistItemSnapshot
from app.domain.exceptions import DashboardValidationError
from app.domain.interfaces.alert_rule_repository import AlertEventRepository
from app.domain.interfaces.watchlist_repository import AlertRepository
from app.services.alert_rule_service import AlertRuleService
from app.services.marketplace_data_service import MarketplaceDataService
from app.services.notification_center_service import NotificationCenterService
from app.services.user_platform_service import UserPlatformService
from app.services.watchlist_service import WatchlistService

_ACTIVITY_LIMIT = 20


class UserDashboardService:
    """Read-only aggregator producing a single-user dashboard view."""

    def __init__(
        self,
        watchlist_service: WatchlistService,
        *,
        alert_rule_service: AlertRuleService | None = None,
        alert_repository: AlertRepository | None = None,
        alert_event_repository: AlertEventRepository | None = None,
        notification_center_service: NotificationCenterService | None = None,
        marketplace_data_service: MarketplaceDataService | None = None,
        user_platform_service: UserPlatformService | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._watchlist_service = watchlist_service
        self._alert_rules = alert_rule_service
        self._alerts = alert_repository
        self._alert_events = alert_event_repository
        self._notification_center = notification_center_service
        self._marketplace_data = marketplace_data_service
        self._user_platform = user_platform_service
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    async def get_dashboard(self, user_id: str, *, currency: str = "PHP") -> UserDashboard:
        cleaned_user = (user_id or "").strip()
        if not cleaned_user:
            raise DashboardValidationError("user_id is required to assemble a dashboard.")

        watchlists = self._list_owned_watchlists(cleaned_user)
        watchlist_items = await self._collect_item_snapshots(watchlists)
        alert_rules = (
            self._alert_rules.list_rules(user_id=cleaned_user) if self._alert_rules else []
        )
        alert_events = (
            self._alert_events.list_events(user_id=cleaned_user, limit=100)
            if self._alert_events
            else []
        )
        alerts = self._collect_alerts(watchlists)
        notifications = (
            self._notification_center.list_notifications(cleaned_user, limit=50)
            if self._notification_center
            else []
        )
        recent_activity = self._build_activity(cleaned_user, watchlists, alert_events)

        dashboard = assemble_dashboard(
            user_id=cleaned_user,
            generated_at=self._clock(),
            id_factory=self._id_factory,
            watchlists=watchlists,
            watchlist_items=watchlist_items,
            alert_rules=alert_rules,
            alerts=alerts,
            alert_events=alert_events,
            notifications=notifications,
            recent_activity=recent_activity,
            currency=currency,
        )
        # Overlay a marketplace-source-mode-aware freshness note so
        # fixture/imported figures are never mistaken for live pricing.
        freshness_note = self._freshness_note()
        if freshness_note != dashboard.summary.savings_freshness_note:
            from dataclasses import replace

            dashboard = replace(
                dashboard,
                summary=replace(dashboard.summary, savings_freshness_note=freshness_note),
            )
        return dashboard

    async def get_dashboard_dict(self, user_id: str, *, currency: str = "PHP") -> dict[str, Any]:
        """Convenience wrapper returning the dashboard as a plain dict (API layer)."""
        dashboard = await self.get_dashboard(user_id, currency=currency)
        payload = dashboard.to_dict()
        payload["personalization"] = self._personalization_context(user_id)
        return payload

    # -------------------------------------------------------------------- helpers
    def _list_owned_watchlists(self, user_id: str) -> list[Watchlist]:
        """List a user's watchlists — works with base or Sprint 19-extended service."""
        try:
            return self._watchlist_service.list_watchlists(owner_id=user_id)  # type: ignore[call-arg]
        except TypeError:
            return [w for w in self._watchlist_service.list_watchlists() if w.owner_id == user_id]

    async def _collect_item_snapshots(
        self, watchlists: list[Watchlist]
    ) -> list[WatchlistItemSnapshot]:
        snapshots: list[WatchlistItemSnapshot] = []
        for watchlist in watchlists:
            items = self._watchlist_service.list_items(watchlist.watchlist_id)
            for item in items:
                snapshots.append(await self._watchlist_service.enrich_item(item))
        return snapshots

    def _collect_alerts(self, watchlists: list[Watchlist]) -> list[Any]:
        if self._alerts is None:
            return []
        alerts: list[Any] = []
        for watchlist in watchlists:
            alerts.extend(self._alerts.list_alerts(watchlist_id=watchlist.watchlist_id, limit=20))
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts

    def _build_activity(
        self, user_id: str, watchlists: list[Watchlist], alert_events: list[Any]
    ) -> list[UserActivity]:
        activity: list[UserActivity] = []
        get_history = getattr(self._watchlist_service, "get_history", None)
        if callable(get_history):
            for watchlist in watchlists:
                for entry in get_history(watchlist.watchlist_id, limit=10):
                    activity.append(
                        UserActivity(
                            activity_id=self._id_factory(),
                            user_id=user_id,
                            activity_type=entry.event_type,
                            message=entry.description,
                            created_at=entry.created_at,
                            watchlist_id=entry.watchlist_id,
                        )
                    )
        for event in alert_events:
            activity.append(
                UserActivity(
                    activity_id=self._id_factory(),
                    user_id=user_id,
                    activity_type=f"alert_event:{event.event_type.value}",
                    message=f"Alert event triggered: {event.event_type.value}.",
                    created_at=event.created_at,
                )
            )
        activity.sort(key=lambda a: a.created_at, reverse=True)
        return activity[:_ACTIVITY_LIMIT]

    def _freshness_note(self) -> str:
        """Note distinguishing live / imported / fixture / simulated-live sources.

        Never claims fixture/imported figures reflect current live pricing —
        appends the set of source modes actually backing the marketplace
        offers currently on record, when a marketplace data collaborator is
        available.
        """
        if self._marketplace_data is None:
            return DASHBOARD_LIMITATIONS_NOTE
        try:
            offers = self._marketplace_data.list_offers(limit=200)
        except Exception:  # noqa: BLE001 - freshness note is best-effort
            return DASHBOARD_LIMITATIONS_NOTE
        if not offers:
            return DASHBOARD_LIMITATIONS_NOTE

        from app.domain.entities.marketplace_data import SOURCE_MODE_LABELS, SourceMode

        labels: set[str] = set()
        for offer in offers:
            label = SOURCE_MODE_LABELS.get(offer.source_mode, offer.source_mode.value)
            if offer.simulated:
                label = SOURCE_MODE_LABELS.get(SourceMode.LIVE, "Simulated live")
            labels.add(label)
        joined = ", ".join(sorted(labels))
        return f"{DASHBOARD_LIMITATIONS_NOTE} Current marketplace sources: {joined}."

    def _personalization_context(self, user_id: str) -> dict[str, Any]:
        if self._user_platform is None:
            return {"authenticated": bool(user_id), "personalization_mode": "unknown"}
        return self._user_platform.shopping_assistant_context(user_id)
