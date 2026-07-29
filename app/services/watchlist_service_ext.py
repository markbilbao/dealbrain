"""Sprint 19 Watchlist service extensions.

``app.services.watchlist_service.WatchlistService`` is a protected Sprint 10
module (see ``PROTECTED_DIGESTS["app/services/watchlist_service.py"]`` in
``tests/unit/test_shopping_assistant_protected_modules.py`` and every sprint
guard that inherits from it through ``tests/unit/test_marketplace_data_protected_modules.py``).
It must not be edited in place. :class:`ExtendedWatchlistService` subclasses
it instead, adding every Sprint 19 capability (owner-scoped listing, default
watchlists, pause/resume/archive lifecycle, marketplace-offer items, preferred
seller/marketplace tagging, idempotent item adds, item notes, and history) as
new methods and safe overrides. All Sprint 10 method signatures and behavior
are inherited unchanged, so existing callers (``WatchlistService`` instances,
``tests/unit/test_watchlist_service.py``, ``tests/unit/test_watchlist_api.py``)
continue to work whether or not this subclass is used.

DI wiring: construct with the same arguments as ``WatchlistService`` plus an
optional ``audit_logger``, and prefer injecting
``app.watchlists.memory.InMemoryWatchlistStore`` (or any
``WatchlistRepository`` that also honors the ``owner_id``/``status`` keyword
filters and ``require_owner``/``save_history_entry``/``list_history``) as the
repository so owner-scoped listing and history are fully persisted rather
than falling back to in-process filtering.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime

from app.domain.entities.watchlist import (
    ItemKind,
    Watchlist,
    WatchlistHistoryEntry,
    WatchlistItem,
    WatchlistStatus,
)
from app.domain.exceptions import WatchlistValidationError
from app.domain.interfaces.canonical_registry import CanonicalProductRegistry
from app.domain.interfaces.watchlist_repository import WatchlistRepository
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.price_history_service import PriceHistoryService
from app.services.watchlist_service import WatchlistService
from app.watchlists.security import WatchlistAuditLogger, require_owner


class ExtendedWatchlistService(WatchlistService):
    """Sprint 19 watchlist orchestration — extends, never edits, Sprint 10."""

    def __init__(
        self,
        repository: WatchlistRepository,
        *,
        price_history_service: PriceHistoryService | None = None,
        deal_recommendation_service: DealRecommendationService | None = None,
        canonical_registry: CanonicalProductRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        audit_logger: WatchlistAuditLogger | None = None,
    ) -> None:
        super().__init__(
            repository,
            price_history_service=price_history_service,
            deal_recommendation_service=deal_recommendation_service,
            canonical_registry=canonical_registry,
            clock=clock,
            id_factory=id_factory,
        )
        self._audit = audit_logger

    # ------------------------------------------------------------ ownership
    def require_owner(self, watchlist_id: str, user_id: str | None) -> Watchlist:
        """Return the watchlist if owned by ``user_id``, else raise."""
        native = getattr(self._repository, "require_owner", None)
        if callable(native):
            return native(watchlist_id, user_id)
        watchlist = self.get_watchlist(watchlist_id)
        return require_owner(watchlist, user_id)

    # -------------------------------------------------------------- listing
    def list_watchlists(
        self,
        *,
        owner_id: str | None = None,
        enabled: bool | None = None,
        status: str | None = None,
    ) -> list[Watchlist]:
        """List watchlists, optionally filtered by owner and/or status.

        ``owner_id``/``status`` are optional keywords (default ``None``) so
        Sprint 10 callers passing only ``enabled`` — or nothing at all —
        keep working unchanged.
        """
        try:
            return self._repository.list_watchlists(
                enabled=enabled, owner_id=owner_id, status=status
            )
        except TypeError:
            items = self._repository.list_watchlists(enabled=enabled)
            if owner_id is not None:
                items = [item for item in items if item.owner_id == owner_id]
            if status is not None:
                cleaned = status.strip().lower() if isinstance(status, str) else status.value
                items = [item for item in items if item.status.value == cleaned]
            return items

    # ---------------------------------------------------------- watchlists
    def create_watchlist(
        self,
        *,
        name: str,
        owner_id: str | None = None,
        description: str | None = None,
        enabled: bool = True,
        watchlist_id: str | None = None,
        is_default: bool = False,
    ) -> Watchlist:
        cleaned_owner = owner_id.strip() if owner_id else None
        if is_default and cleaned_owner:
            self._clear_default(cleaned_owner)
        created = super().create_watchlist(
            name=name,
            owner_id=owner_id,
            description=description,
            enabled=enabled,
            watchlist_id=watchlist_id,
        )
        if is_default:
            created = self._repository.save_watchlist(replace(created, is_default=True))
        self._record_history(
            created.watchlist_id,
            "watchlist_created",
            f"Watchlist '{created.name}' created.",
            actor_id=cleaned_owner,
        )
        return created

    def _clear_default(self, owner_id: str) -> None:
        for watchlist in self.list_watchlists(owner_id=owner_id):
            if watchlist.is_default:
                self._repository.save_watchlist(
                    replace(watchlist, is_default=False, updated_at=self._clock())
                )

    def rename(self, watchlist_id: str, *, name: str, actor_id: str | None = None) -> Watchlist:
        """Rename a watchlist (thin wrapper over ``update_watchlist`` with history)."""
        updated = self.update_watchlist(watchlist_id, name=name)
        self._record_history(
            watchlist_id, "watchlist_renamed", f"Renamed to '{updated.name}'.", actor_id=actor_id
        )
        return updated

    def update_watchlist(
        self,
        watchlist_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        owner_id: str | None = None,
    ) -> Watchlist:
        updated = super().update_watchlist(
            watchlist_id,
            name=name,
            description=description,
            enabled=enabled,
            owner_id=owner_id,
        )
        self._record_history(watchlist_id, "watchlist_updated", "Watchlist details updated.")
        return updated

    def delete_watchlist(self, watchlist_id: str) -> None:
        # Fetch first so we can still describe the deletion in the (best-effort)
        # audit log even though history rows are cascade-deleted with the
        # watchlist itself in most repositories.
        watchlist = self.get_watchlist(watchlist_id)
        super().delete_watchlist(watchlist_id)
        if self._audit is not None:
            self._audit.record(
                "watchlist_deleted",
                watchlist_id=watchlist_id,
                detail=f"Watchlist '{watchlist.name}' deleted.",
            )

    def pause_watchlist(self, watchlist_id: str, *, actor_id: str | None = None) -> Watchlist:
        """Pause a watchlist: disables alert evaluation until resumed."""
        watchlist = self.get_watchlist(watchlist_id)
        stamp = self._clock()
        updated = self._repository.save_watchlist(
            replace(
                watchlist,
                status=WatchlistStatus.PAUSED,
                enabled=False,
                paused_at=stamp,
                updated_at=stamp,
            )
        )
        self._record_history(
            watchlist_id, "watchlist_paused", "Watchlist paused.", actor_id=actor_id
        )
        return updated

    def resume_watchlist(self, watchlist_id: str, *, actor_id: str | None = None) -> Watchlist:
        watchlist = self.get_watchlist(watchlist_id)
        stamp = self._clock()
        updated = self._repository.save_watchlist(
            replace(
                watchlist,
                status=WatchlistStatus.ACTIVE,
                enabled=True,
                paused_at=None,
                updated_at=stamp,
            )
        )
        self._record_history(
            watchlist_id, "watchlist_resumed", "Watchlist resumed.", actor_id=actor_id
        )
        return updated

    def archive_watchlist(self, watchlist_id: str, *, actor_id: str | None = None) -> Watchlist:
        watchlist = self.get_watchlist(watchlist_id)
        stamp = self._clock()
        updated = self._repository.save_watchlist(
            replace(
                watchlist,
                status=WatchlistStatus.ARCHIVED,
                enabled=False,
                archived_at=stamp,
                updated_at=stamp,
            )
        )
        self._record_history(
            watchlist_id, "watchlist_archived", "Watchlist archived.", actor_id=actor_id
        )
        return updated

    def set_watchlist_preferred_sellers(
        self, watchlist_id: str, *, sellers: Sequence[str]
    ) -> Watchlist:
        watchlist = self.get_watchlist(watchlist_id)
        cleaned = self._clean_str_tuple(sellers)
        updated = self._repository.save_watchlist(
            replace(watchlist, preferred_sellers=cleaned, updated_at=self._clock())
        )
        self._record_history(
            watchlist_id, "preferred_sellers_updated", f"Preferred sellers set to {list(cleaned)}."
        )
        return updated

    def set_watchlist_preferred_marketplaces(
        self, watchlist_id: str, *, marketplaces: Sequence[str]
    ) -> Watchlist:
        watchlist = self.get_watchlist(watchlist_id)
        cleaned = self._clean_str_tuple(marketplaces)
        updated = self._repository.save_watchlist(
            replace(watchlist, preferred_marketplaces=cleaned, updated_at=self._clock())
        )
        self._record_history(
            watchlist_id,
            "preferred_marketplaces_updated",
            f"Preferred marketplaces set to {list(cleaned)}.",
        )
        return updated

    # -------------------------------------------------------------------- items
    async def add_item_idempotent(
        self,
        watchlist_id: str,
        *,
        canonical_product_id: str,
        return_existing: bool = True,
        **kwargs: object,
    ) -> WatchlistItem:
        """Add an item; return the existing one instead of raising on duplicates.

        Set ``return_existing=False`` to fall back to the Sprint 10
        raise-on-duplicate behavior of ``add_item`` while still recording
        history on success.
        """
        self.get_watchlist(watchlist_id)
        product_id = canonical_product_id.strip()
        for item in self._repository.list_items(watchlist_id=watchlist_id):
            if item.canonical_product_id == product_id:
                if return_existing:
                    return item
                raise WatchlistValidationError(
                    f"Product {product_id} is already on watchlist {watchlist_id}."
                )
        item = await super().add_item(
            watchlist_id, canonical_product_id=canonical_product_id, **kwargs
        )
        self._record_history(
            watchlist_id, "item_added", f"Item {item.item_id} added.", item_id=item.item_id
        )
        return item

    async def add_offer(
        self,
        watchlist_id: str,
        *,
        marketplace_offer_id: str,
        canonical_product_id: str | None = None,
        product_label: str | None = None,
        target_price: float | None = None,
        currency: str = "PHP",
        notes: str | None = None,
        return_existing: bool = True,
    ) -> WatchlistItem:
        """Track a specific marketplace offer (``item_kind=offer``).

        When ``canonical_product_id`` is omitted, the offer id itself is used
        as the tracked identity — callers that have resolved a canonical
        product for the offer should pass it explicitly for richer price
        history / DealScore enrichment.
        """
        cleaned_offer_id = marketplace_offer_id.strip()
        if not cleaned_offer_id:
            raise WatchlistValidationError("marketplace_offer_id must not be blank.")
        resolved_product_id = (canonical_product_id or cleaned_offer_id).strip()
        item = await self.add_item_idempotent(
            watchlist_id,
            canonical_product_id=resolved_product_id,
            product_label=product_label,
            target_price=target_price,
            currency=currency,
            return_existing=return_existing,
        )
        needs_update = (
            item.marketplace_offer_id != cleaned_offer_id
            or item.item_kind != ItemKind.OFFER
            or (notes is not None and item.notes != notes)
        )
        if needs_update:
            item = self._repository.save_item(
                replace(
                    item,
                    marketplace_offer_id=cleaned_offer_id,
                    item_kind=ItemKind.OFFER,
                    notes=notes if notes is not None else item.notes,
                    updated_at=self._clock(),
                )
            )
            self._record_history(
                watchlist_id,
                "offer_tracked",
                f"Marketplace offer {cleaned_offer_id} tracked.",
                item_id=item.item_id,
            )
        return item

    def update_item(
        self,
        item_id: str,
        *,
        product_label: str | None = None,
        target_price: float | None = None,
        currency: str | None = None,
        search_query: str | None = None,
        enabled: bool | None = None,
        clear_target_price: bool = False,
    ) -> WatchlistItem:
        updated = super().update_item(
            item_id,
            product_label=product_label,
            target_price=target_price,
            currency=currency,
            search_query=search_query,
            enabled=enabled,
            clear_target_price=clear_target_price,
        )
        self._record_history(
            updated.watchlist_id, "item_updated", "Item details updated.", item_id=item_id
        )
        return updated

    def delete_item(self, item_id: str) -> None:
        item = self.get_item(item_id)
        super().delete_item(item_id)
        self._record_history(
            item.watchlist_id, "item_removed", f"Item {item_id} removed.", item_id=item_id
        )

    def set_item_notes(self, item_id: str, *, notes: str | None) -> WatchlistItem:
        item = self.get_item(item_id)
        cleaned = notes.strip() if notes else None
        updated = self._repository.save_item(replace(item, notes=cleaned, updated_at=self._clock()))
        self._record_history(
            item.watchlist_id, "item_notes_updated", "Item notes updated.", item_id=item_id
        )
        return updated

    def pause_item_monitoring(self, item_id: str) -> WatchlistItem:
        item = self.get_item(item_id)
        updated = self._repository.save_item(
            replace(item, monitoring_paused=True, updated_at=self._clock())
        )
        self._record_history(
            item.watchlist_id, "item_monitoring_paused", "Item monitoring paused.", item_id=item_id
        )
        return updated

    def resume_item_monitoring(self, item_id: str) -> WatchlistItem:
        item = self.get_item(item_id)
        updated = self._repository.save_item(
            replace(item, monitoring_paused=False, updated_at=self._clock())
        )
        self._record_history(
            item.watchlist_id,
            "item_monitoring_resumed",
            "Item monitoring resumed.",
            item_id=item_id,
        )
        return updated

    def set_item_preferred_sellers(self, item_id: str, *, sellers: Sequence[str]) -> WatchlistItem:
        item = self.get_item(item_id)
        cleaned = self._clean_str_tuple(sellers)
        updated = self._repository.save_item(
            replace(item, preferred_sellers=cleaned, updated_at=self._clock())
        )
        self._record_history(
            item.watchlist_id,
            "item_preferred_sellers_updated",
            f"Preferred sellers set to {list(cleaned)}.",
            item_id=item_id,
        )
        return updated

    def set_item_preferred_marketplaces(
        self, item_id: str, *, marketplaces: Sequence[str]
    ) -> WatchlistItem:
        item = self.get_item(item_id)
        cleaned = self._clean_str_tuple(marketplaces)
        updated = self._repository.save_item(
            replace(item, preferred_marketplaces=cleaned, updated_at=self._clock())
        )
        self._record_history(
            item.watchlist_id,
            "item_preferred_marketplaces_updated",
            f"Preferred marketplaces set to {list(cleaned)}.",
            item_id=item_id,
        )
        return updated

    # ------------------------------------------------------------------- history
    def get_history(self, watchlist_id: str, *, limit: int = 50) -> list[WatchlistHistoryEntry]:
        self.get_watchlist(watchlist_id)
        return self._repository.list_history(watchlist_id, limit=limit)

    def _record_history(
        self,
        watchlist_id: str,
        event_type: str,
        description: str,
        *,
        actor_id: str | None = None,
        item_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        entry = WatchlistHistoryEntry(
            history_id=self._id_factory(),
            watchlist_id=watchlist_id,
            event_type=event_type,
            description=description,
            created_at=self._clock(),
            actor_id=actor_id,
            item_id=item_id,
            metadata=metadata,
        )
        self._repository.save_history_entry(entry)
        if self._audit is not None:
            self._audit.record(
                event_type,
                user_id=actor_id,
                watchlist_id=watchlist_id,
                detail=description,
                metadata=metadata,
            )

    @staticmethod
    def _clean_str_tuple(values: Sequence[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(v.strip() for v in values if v and v.strip()))
