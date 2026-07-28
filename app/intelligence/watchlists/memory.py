"""In-memory Watchlist / Alert repository for development and tests."""

from __future__ import annotations

from app.domain.entities.watchlist import Alert, Watchlist, WatchlistItem
from app.domain.interfaces.watchlist_repository import AlertRepository, WatchlistRepository


class InMemoryWatchlistRepository(WatchlistRepository, AlertRepository):
    """Process-local watchlist, item, and alert store with deterministic order."""

    def __init__(self) -> None:
        self._watchlists: dict[str, Watchlist] = {}
        self._watchlist_order: list[str] = []
        self._items: dict[str, WatchlistItem] = {}
        self._item_order: list[str] = []
        self._alerts: dict[str, Alert] = {}
        self._alert_order: list[str] = []

    # ------------------------------------------------------------------ watchlists
    def save_watchlist(self, watchlist: Watchlist) -> Watchlist:
        if watchlist.watchlist_id not in self._watchlists:
            self._watchlist_order.append(watchlist.watchlist_id)
        self._watchlists[watchlist.watchlist_id] = watchlist
        return watchlist

    def get_watchlist(self, watchlist_id: str) -> Watchlist | None:
        return self._watchlists.get(watchlist_id)

    def list_watchlists(self, *, enabled: bool | None = None) -> list[Watchlist]:
        items = [
            self._watchlists[wid]
            for wid in self._watchlist_order
            if wid in self._watchlists
        ]
        if enabled is None:
            return items
        return [item for item in items if item.enabled is enabled]

    def delete_watchlist(self, watchlist_id: str) -> bool:
        if watchlist_id not in self._watchlists:
            return False
        del self._watchlists[watchlist_id]
        self._watchlist_order = [wid for wid in self._watchlist_order if wid != watchlist_id]
        item_ids = [
            item.item_id
            for item in self._items.values()
            if item.watchlist_id == watchlist_id
        ]
        for item_id in item_ids:
            self.delete_item(item_id)
        self.delete_alerts_for_watchlist(watchlist_id)
        return True

    # ------------------------------------------------------------------ items
    def save_item(self, item: WatchlistItem) -> WatchlistItem:
        if item.item_id not in self._items:
            self._item_order.append(item.item_id)
        self._items[item.item_id] = item
        return item

    def get_item(self, item_id: str) -> WatchlistItem | None:
        return self._items.get(item_id)

    def list_items(
        self,
        *,
        watchlist_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[WatchlistItem]:
        items = [
            self._items[item_id]
            for item_id in self._item_order
            if item_id in self._items
        ]
        if watchlist_id is not None:
            items = [item for item in items if item.watchlist_id == watchlist_id]
        if enabled is not None:
            items = [item for item in items if item.enabled is enabled]
        return items

    def delete_item(self, item_id: str) -> bool:
        if item_id not in self._items:
            return False
        del self._items[item_id]
        self._item_order = [iid for iid in self._item_order if iid != item_id]
        return True

    # ------------------------------------------------------------------ alerts
    def save_alert(self, alert: Alert) -> Alert:
        if alert.alert_id not in self._alerts:
            self._alert_order.append(alert.alert_id)
        self._alerts[alert.alert_id] = alert
        return alert

    def get_alert(self, alert_id: str) -> Alert | None:
        return self._alerts.get(alert_id)

    def list_alerts(
        self,
        *,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        ordered = [
            self._alerts[aid]
            for aid in reversed(self._alert_order)
            if aid in self._alerts
        ]
        if watchlist_id is not None:
            ordered = [a for a in ordered if a.watchlist_id == watchlist_id]
        if item_id is not None:
            ordered = [a for a in ordered if a.item_id == item_id]
        if alert_type is not None:
            cleaned = alert_type.strip().lower()
            ordered = [a for a in ordered if a.alert_type.value == cleaned]
        if status is not None:
            cleaned_status = status.strip().lower()
            ordered = [a for a in ordered if a.status.value == cleaned_status]
        return ordered[: max(0, limit)]

    def delete_alerts_for_watchlist(self, watchlist_id: str) -> int:
        to_remove = [
            alert_id
            for alert_id, alert in self._alerts.items()
            if alert.watchlist_id == watchlist_id
        ]
        for alert_id in to_remove:
            del self._alerts[alert_id]
        self._alert_order = [aid for aid in self._alert_order if aid not in set(to_remove)]
        return len(to_remove)

    def clear(self) -> None:
        """Reset all stored watchlists, items, and alerts (tests)."""
        self._watchlists.clear()
        self._watchlist_order.clear()
        self._items.clear()
        self._item_order.clear()
        self._alerts.clear()
        self._alert_order.clear()
