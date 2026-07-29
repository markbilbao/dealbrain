"""Sprint 19 in-memory Watchlist store — extends the Sprint 10 repository.

``app.intelligence.watchlists.memory.InMemoryWatchlistRepository`` is a
protected Sprint 10 module (see ``tests/unit/test_review_protected_modules.py``)
and must not be edited. :class:`InMemoryWatchlistStore` subclasses it instead,
adding the Sprint 19 ``owner_id``/``status`` filters on ``list_watchlists`` and
watchlist history tracking, so dependency injection can swap the extended
store in without touching Sprint 10 callers or tests.
"""

from __future__ import annotations

from app.domain.entities.watchlist import Watchlist, WatchlistHistoryEntry, WatchlistStatus
from app.domain.exceptions import WatchlistOwnershipError
from app.intelligence.watchlists.memory import InMemoryWatchlistRepository


class InMemoryWatchlistStore(InMemoryWatchlistRepository):
    """Process-local watchlist store with Sprint 19 filters and history.

    Fully backwards compatible with :class:`InMemoryWatchlistRepository`:
    watchlist/item/alert storage and behavior are inherited unchanged. Only
    ``list_watchlists`` gains additional (optional) filters, and history
    tracking is added as new, purely additive state.
    """

    def __init__(self) -> None:
        super().__init__()
        self._history: dict[str, WatchlistHistoryEntry] = {}
        self._history_order: list[str] = []

    # ------------------------------------------------------------ watchlists
    def list_watchlists(
        self,
        *,
        enabled: bool | None = None,
        owner_id: str | None = None,
        status: str | None = None,
    ) -> list[Watchlist]:
        items = super().list_watchlists(enabled=enabled)
        if owner_id is not None:
            items = [item for item in items if item.owner_id == owner_id]
        if status is not None:
            cleaned = status.strip().lower()
            items = [item for item in items if item.status.value == cleaned]
        return items

    def list_by_owner(
        self,
        owner_id: str,
        *,
        status: WatchlistStatus | None = None,
    ) -> list[Watchlist]:
        """Convenience helper returning an owner's watchlists, optionally filtered."""
        return self.list_watchlists(
            owner_id=owner_id,
            status=status.value if status is not None else None,
        )

    # ---------------------------------------------------------- ownership
    def require_owner(self, watchlist_id: str, user_id: str | None) -> Watchlist:
        """Return the watchlist if owned by ``user_id``; otherwise raise.

        A watchlist with ``owner_id is None`` is treated as unowned/shared and
        is accessible to any caller (mirrors Sprint 10 fixtures that never set
        an owner).
        """
        watchlist = self.get_watchlist(watchlist_id)
        if watchlist is None:
            raise WatchlistOwnershipError(watchlist_id, user_id)
        if watchlist.owner_id is not None and watchlist.owner_id != user_id:
            raise WatchlistOwnershipError(watchlist_id, user_id)
        return watchlist

    # -------------------------------------------------------------- history
    def save_history_entry(self, entry: WatchlistHistoryEntry) -> WatchlistHistoryEntry:
        if entry.history_id not in self._history:
            self._history_order.append(entry.history_id)
        self._history[entry.history_id] = entry
        return entry

    def list_history(
        self,
        watchlist_id: str,
        *,
        limit: int = 50,
    ) -> list[WatchlistHistoryEntry]:
        ordered = [
            self._history[hid]
            for hid in reversed(self._history_order)
            if hid in self._history and self._history[hid].watchlist_id == watchlist_id
        ]
        return ordered[: max(0, limit)]

    # ------------------------------------------------------------------ misc
    def clear(self) -> None:
        """Reset all stored watchlists, items, alerts, and history (tests)."""
        super().clear()
        self._history.clear()
        self._history_order.clear()
