"""Watchlist application service — CRUD for watchlists and tracked items.

Reads Product Identity / Price History / DealScore via existing services.
Does not modify protected intelligence modules.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities.watchlist import Watchlist, WatchlistItem, WatchlistItemSnapshot
from app.domain.exceptions import (
    CanonicalProductNotFoundError,
    DealScoreValidationError,
    PriceHistoryValidationError,
    WatchlistItemNotFoundError,
    WatchlistNotFoundError,
    WatchlistValidationError,
)
from app.domain.interfaces.canonical_registry import CanonicalProductRegistry
from app.domain.interfaces.watchlist_repository import WatchlistRepository
from app.services.deal_recommendation_service import DealRecommendationService
from app.services.price_history_service import PriceHistoryService


class WatchlistService:
    """Manage watchlists and items; enrich items with price / DealScore reads."""

    def __init__(
        self,
        repository: WatchlistRepository,
        *,
        price_history_service: PriceHistoryService | None = None,
        deal_recommendation_service: DealRecommendationService | None = None,
        canonical_registry: CanonicalProductRegistry | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._price_history = price_history_service
        self._deal_recommendation = deal_recommendation_service
        self._registry = canonical_registry
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    # ------------------------------------------------------------------ watchlists
    def create_watchlist(
        self,
        *,
        name: str,
        owner_id: str | None = None,
        description: str | None = None,
        enabled: bool = True,
        watchlist_id: str | None = None,
    ) -> Watchlist:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise WatchlistValidationError("Watchlist name must not be blank.")
        stamp = self._clock()
        watchlist = Watchlist(
            watchlist_id=watchlist_id or self._id_factory(),
            name=cleaned_name,
            owner_id=owner_id.strip() if owner_id else None,
            description=description.strip() if description else None,
            enabled=enabled,
            created_at=stamp,
            updated_at=stamp,
        )
        return self._repository.save_watchlist(watchlist)

    def get_watchlist(self, watchlist_id: str) -> Watchlist:
        watchlist = self._repository.get_watchlist(watchlist_id)
        if watchlist is None:
            raise WatchlistNotFoundError(watchlist_id)
        return watchlist

    def list_watchlists(self, *, enabled: bool | None = None) -> list[Watchlist]:
        return self._repository.list_watchlists(enabled=enabled)

    def update_watchlist(
        self,
        watchlist_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        owner_id: str | None = None,
    ) -> Watchlist:
        watchlist = self.get_watchlist(watchlist_id)
        updates: dict[str, object] = {"updated_at": self._clock()}
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise WatchlistValidationError("Watchlist name must not be blank.")
            updates["name"] = cleaned
        if description is not None:
            updates["description"] = description.strip() or None
        if enabled is not None:
            updates["enabled"] = enabled
        if owner_id is not None:
            updates["owner_id"] = owner_id.strip() or None
        updated = replace(watchlist, **updates)  # type: ignore[arg-type]
        return self._repository.save_watchlist(updated)

    def delete_watchlist(self, watchlist_id: str) -> None:
        if not self._repository.delete_watchlist(watchlist_id):
            raise WatchlistNotFoundError(watchlist_id)

    # ------------------------------------------------------------------ items
    async def add_item(
        self,
        watchlist_id: str,
        *,
        canonical_product_id: str,
        product_label: str | None = None,
        target_price: float | None = None,
        currency: str = "PHP",
        search_query: str | None = None,
        enabled: bool = True,
        item_id: str | None = None,
        last_known_price: float | None = None,
        last_known_dealscore: float | None = None,
        last_historical_low: float | None = None,
    ) -> WatchlistItem:
        self.get_watchlist(watchlist_id)
        product_id = canonical_product_id.strip()
        if not product_id:
            raise WatchlistValidationError("canonical_product_id must not be blank.")
        if target_price is not None and target_price < 0:
            raise WatchlistValidationError("target_price must be non-negative.")
        cleaned_currency = currency.strip().upper()
        if not cleaned_currency:
            raise WatchlistValidationError("currency must not be blank.")

        await self._ensure_product_exists(product_id)

        # Reject duplicate product on the same watchlist.
        existing = self._repository.list_items(watchlist_id=watchlist_id)
        for item in existing:
            if item.canonical_product_id == product_id:
                raise WatchlistValidationError(
                    f"Product {product_id} is already on watchlist {watchlist_id}."
                )

        stamp = self._clock()
        item = WatchlistItem(
            item_id=item_id or self._id_factory(),
            watchlist_id=watchlist_id,
            canonical_product_id=product_id,
            product_label=product_label.strip() if product_label else None,
            target_price=target_price,
            currency=cleaned_currency,
            search_query=search_query.strip() if search_query else None,
            last_known_price=last_known_price,
            last_known_dealscore=last_known_dealscore,
            last_historical_low=last_historical_low,
            enabled=enabled,
            created_at=stamp,
            updated_at=stamp,
        )
        return self._repository.save_item(item)

    def get_item(self, item_id: str) -> WatchlistItem:
        item = self._repository.get_item(item_id)
        if item is None:
            raise WatchlistItemNotFoundError(item_id)
        return item

    def list_items(
        self,
        watchlist_id: str,
        *,
        enabled: bool | None = None,
    ) -> list[WatchlistItem]:
        self.get_watchlist(watchlist_id)
        return self._repository.list_items(watchlist_id=watchlist_id, enabled=enabled)

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
        item = self.get_item(item_id)
        updates: dict[str, object] = {"updated_at": self._clock()}
        if product_label is not None:
            updates["product_label"] = product_label.strip() or None
        if clear_target_price:
            updates["target_price"] = None
        elif target_price is not None:
            if target_price < 0:
                raise WatchlistValidationError("target_price must be non-negative.")
            updates["target_price"] = target_price
        if currency is not None:
            cleaned = currency.strip().upper()
            if not cleaned:
                raise WatchlistValidationError("currency must not be blank.")
            updates["currency"] = cleaned
        if search_query is not None:
            updates["search_query"] = search_query.strip() or None
        if enabled is not None:
            updates["enabled"] = enabled
        updated = replace(item, **updates)  # type: ignore[arg-type]
        return self._repository.save_item(updated)

    def delete_item(self, item_id: str) -> None:
        if not self._repository.delete_item(item_id):
            raise WatchlistItemNotFoundError(item_id)

    async def enrich_item(self, item: WatchlistItem) -> WatchlistItemSnapshot:
        """Attach current price, historical low, and optional DealScore."""
        current_price: float | None = None
        historical_low: float | None = None
        currency: str | None = item.currency
        observation_count = 0
        price_available = False
        dealscore: float | None = item.last_known_dealscore

        if self._price_history is not None:
            try:
                history = await self._price_history.get_product_history(
                    item.canonical_product_id
                )
            except PriceHistoryValidationError:
                history = None
            if history is not None and history.statistics is not None:
                stats = history.statistics
                current_price = stats.current_total_cost
                historical_low = stats.lowest_recorded_total_cost
                currency = stats.currency
                observation_count = stats.observation_count
                price_available = True

        if (
            self._deal_recommendation is not None
            and item.search_query
            and item.search_query.strip()
        ):
            try:
                ranking = self._deal_recommendation.recommend(item.search_query)
                if ranking.recommended is not None:
                    dealscore = ranking.recommended.deal_score.score
            except DealScoreValidationError:
                pass

        return WatchlistItemSnapshot(
            item=item,
            current_price=current_price,
            historical_low=historical_low,
            dealscore=dealscore,
            currency=currency,
            observation_count=observation_count,
            price_available=price_available,
        )

    async def list_enriched_items(
        self,
        watchlist_id: str,
        *,
        enabled: bool | None = None,
    ) -> list[WatchlistItemSnapshot]:
        items = self.list_items(watchlist_id, enabled=enabled)
        return [await self.enrich_item(item) for item in items]

    async def _ensure_product_exists(self, canonical_product_id: str) -> None:
        if self._registry is None:
            return
        try:
            product_uuid = UUID(canonical_product_id)
        except ValueError as exc:
            raise WatchlistValidationError(
                f"canonical_product_id is not a valid UUID: {canonical_product_id}"
            ) from exc
        product = await self._registry.get(product_uuid)
        if product is None:
            # Soft-check: allow tracking unknown IDs when registry has no entry
            # (price history may still have snapshots keyed by the same id).
            # Raise only when callers want strict identity — we keep soft for demo.
            return
        _ = product

    async def require_product_exists(self, canonical_product_id: str) -> None:
        """Strict identity check used by optional callers / tests."""
        if self._registry is None:
            return
        try:
            product_uuid = UUID(canonical_product_id)
        except ValueError as exc:
            raise WatchlistValidationError(
                f"canonical_product_id is not a valid UUID: {canonical_product_id}"
            ) from exc
        product = await self._registry.get(product_uuid)
        if product is None:
            raise CanonicalProductNotFoundError(product_uuid)
