"""Watchlist / alert persistence ports."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.watchlist import Alert, Watchlist, WatchlistItem


class WatchlistRepository(ABC):
    """Persistence for watchlists and their tracked items."""

    @abstractmethod
    def save_watchlist(self, watchlist: Watchlist) -> Watchlist:
        """Create or replace a watchlist."""

    @abstractmethod
    def get_watchlist(self, watchlist_id: str) -> Watchlist | None:
        """Return a watchlist by id, or None."""

    @abstractmethod
    def list_watchlists(self, *, enabled: bool | None = None) -> list[Watchlist]:
        """Return watchlists in insertion order."""

    @abstractmethod
    def delete_watchlist(self, watchlist_id: str) -> bool:
        """Delete a watchlist and cascade its items. Returns False if missing."""

    @abstractmethod
    def save_item(self, item: WatchlistItem) -> WatchlistItem:
        """Create or replace a watchlist item."""

    @abstractmethod
    def get_item(self, item_id: str) -> WatchlistItem | None:
        """Return an item by id, or None."""

    @abstractmethod
    def list_items(
        self,
        *,
        watchlist_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[WatchlistItem]:
        """Return items, optionally filtered by watchlist and enabled flag."""

    @abstractmethod
    def delete_item(self, item_id: str) -> bool:
        """Delete an item. Returns False if missing."""


class AlertRepository(ABC):
    """Persistence for generated alerts."""

    @abstractmethod
    def save_alert(self, alert: Alert) -> Alert:
        """Create or replace an alert."""

    @abstractmethod
    def get_alert(self, alert_id: str) -> Alert | None:
        """Return an alert by id, or None."""

    @abstractmethod
    def list_alerts(
        self,
        *,
        watchlist_id: str | None = None,
        item_id: str | None = None,
        alert_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Alert]:
        """Return alerts newest-first with optional filters."""

    @abstractmethod
    def delete_alerts_for_watchlist(self, watchlist_id: str) -> int:
        """Delete all alerts for a watchlist. Returns count removed."""
