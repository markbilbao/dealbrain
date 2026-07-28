"""Price History application service.

Records timestamped marketplace observations and computes statistics from
stored history only. No LLMs, no currency conversion, no price predictions.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.entities.marketplace_listing import AvailabilityStatus, MarketplaceListing
from app.domain.entities.price_history import (
    PriceHistory,
    PriceHistorySearchResult,
    PriceSnapshot,
    PriceStatistics,
)
from app.domain.exceptions import PriceHistoryValidationError, UnsupportedProductError
from app.domain.interfaces.price_history_store import PriceHistoryStore
from app.intelligence.dealscore.enrichment import resolve_deal_attributes
from app.intelligence.price_history.mock_fixture import (
    IPHONE_DEMO_CANONICAL_PRODUCT_ID,
    IPHONE_DEMO_IDENTITY_KEY,
)
from app.intelligence.price_history.statistics import (
    DEFAULT_TREND_THRESHOLD_PERCENT,
    build_marketplace_summaries,
    calculate_statistics,
    sort_snapshots,
)
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService
from app.services.product_intelligence_service import ProductIntelligenceService


class PriceHistoryService:
    """Use-case orchestration for price snapshots, history, and statistics."""

    def __init__(
        self,
        store: PriceHistoryStore,
        *,
        marketplace_service: MarketplaceIntelligenceService | None = None,
        product_intelligence_service: ProductIntelligenceService | None = None,
        trend_threshold_percent: float = DEFAULT_TREND_THRESHOLD_PERCENT,
        app_env: str = "development",
        seed_demo_mock_on_search: bool = False,
    ) -> None:
        self._store = store
        self._marketplace_service = marketplace_service
        self._product_intelligence = product_intelligence_service
        self._trend_threshold_percent = trend_threshold_percent
        self._app_env = app_env
        self._seed_demo_mock_on_search = seed_demo_mock_on_search
        self._demo_mock_seeded = False

    async def record_snapshot(self, snapshot: PriceSnapshot) -> PriceSnapshot:
        """Persist a single snapshot with duplicate protection."""
        return await self._store.save(snapshot)

    async def record_snapshots(self, snapshots: Sequence[PriceSnapshot]) -> list[PriceSnapshot]:
        """Persist multiple snapshots with duplicate protection."""
        return await self._store.save_many(list(snapshots))

    async def record_listing_snapshot(
        self,
        listing: MarketplaceListing,
        *,
        canonical_product_id: str,
        observed_at: datetime | None = None,
        shipping_cost: float | None = None,
        snapshot_id: UUID | None = None,
    ) -> PriceSnapshot:
        """Build and persist a snapshot from a normalized marketplace listing."""
        snapshot = self.build_snapshot_from_listing(
            listing,
            canonical_product_id=canonical_product_id,
            observed_at=observed_at,
            shipping_cost=shipping_cost,
            snapshot_id=snapshot_id,
        )
        return await self._store.save(snapshot)

    @staticmethod
    def build_snapshot_from_listing(
        listing: MarketplaceListing,
        *,
        canonical_product_id: str,
        observed_at: datetime | None = None,
        shipping_cost: float | None = None,
        snapshot_id: UUID | None = None,
    ) -> PriceSnapshot:
        """Map a normalized listing into a PriceSnapshot (no persistence)."""
        if shipping_cost is None:
            attrs = resolve_deal_attributes(listing)
            resolved_shipping = 0.0 if attrs.shipping_cost is None else float(attrs.shipping_cost)
        else:
            resolved_shipping = float(shipping_cost)

        item_price = round(float(listing.price), 2)
        shipping = round(resolved_shipping, 2)
        return PriceSnapshot(
            snapshot_id=snapshot_id or uuid4(),
            canonical_product_id=canonical_product_id,
            marketplace=listing.marketplace.strip().lower(),
            listing_id=listing.product_id,
            seller_name=listing.seller or None,
            currency=listing.currency.strip().upper(),
            item_price=item_price,
            shipping_cost=shipping,
            total_cost=round(item_price + shipping, 2),
            availability=listing.availability,
            observed_at=observed_at or datetime.now(UTC),
        )

    async def get_product_history(self, canonical_product_id: str) -> PriceHistory:
        """Return recorded history and statistics for a canonical product."""
        snapshots = await self._store.get_by_canonical_product(canonical_product_id)
        return self._to_history(
            snapshots,
            canonical_product_id=canonical_product_id,
            listing_id=None,
        )

    async def get_listing_history(self, listing_id: str) -> PriceHistory:
        """Return recorded history and statistics for one marketplace listing."""
        snapshots = await self._store.get_by_listing(listing_id)
        return self._to_history(
            snapshots,
            canonical_product_id=None,
            listing_id=listing_id,
        )

    async def get_history_in_range(
        self,
        *,
        canonical_product_id: str | None = None,
        listing_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> PriceHistory:
        """Return history filtered by optional product/listing and date range."""
        snapshots = await self._store.get_by_date_range(
            canonical_product_id=canonical_product_id,
            listing_id=listing_id,
            start=start,
            end=end,
        )
        return self._to_history(
            snapshots,
            canonical_product_id=canonical_product_id,
            listing_id=listing_id,
        )

    def calculate_statistics(self, snapshots: Sequence[PriceSnapshot]) -> PriceStatistics:
        """Calculate statistics from an explicit snapshot set."""
        return calculate_statistics(
            snapshots,
            threshold_percent=self._trend_threshold_percent,
        )

    async def search_and_record(self, query: str) -> PriceHistorySearchResult:
        """Search marketplaces, record current observations, return history stats.

        Uses the existing marketplace connectors and product intelligence pipeline
        for identity resolution. Does not invent historical prices.
        """
        cleaned = query.strip()
        if not cleaned:
            raise PriceHistoryValidationError("Search query must not be blank.")
        if self._marketplace_service is None:
            raise PriceHistoryValidationError(
                "Marketplace intelligence service is required for price-history search."
            )
        if self._product_intelligence is None:
            raise PriceHistoryValidationError(
                "Product intelligence service is required for price-history search."
            )

        await self._maybe_seed_demo_mock()

        search = self._marketplace_service.search(cleaned)
        recorded: list[PriceSnapshot] = []
        product_counts: dict[str, int] = {}

        for listing in search.results:
            canonical_id = await self._resolve_canonical_product_id(listing)
            if canonical_id is None:
                continue
            snapshot = await self.record_listing_snapshot(
                listing,
                canonical_product_id=canonical_id,
            )
            recorded.append(snapshot)
            product_counts[canonical_id] = product_counts.get(canonical_id, 0) + 1

        if not product_counts:
            return PriceHistorySearchResult(
                query=cleaned,
                currency="",
                statistics=None,
                history=(),
                marketplace_summaries=(),
                canonical_product_id=None,
                is_mock_history=False,
            )

        # Prefer the iPhone demo product when present so mock history surfaces;
        # otherwise use the most frequently resolved canonical product.
        primary_product_id = max(product_counts, key=product_counts.get)
        if IPHONE_DEMO_CANONICAL_PRODUCT_ID in product_counts:
            primary_product_id = IPHONE_DEMO_CANONICAL_PRODUCT_ID
        elif any(
            listing.title.lower().find("iphone 17 pro max") >= 0 for listing in search.results
        ):
            # Demo identity key maps to fixed id when parse resolves that variant.
            for candidate_id in product_counts:
                if candidate_id == IPHONE_DEMO_CANONICAL_PRODUCT_ID:
                    primary_product_id = candidate_id
                    break

        history = await self.get_product_history(primary_product_id)
        is_mock = primary_product_id == IPHONE_DEMO_CANONICAL_PRODUCT_ID and self._demo_mock_seeded
        return PriceHistorySearchResult(
            query=cleaned,
            currency=history.currency,
            statistics=history.statistics,
            history=history.snapshots,
            marketplace_summaries=history.marketplace_summaries,
            canonical_product_id=primary_product_id,
            is_mock_history=is_mock,
        )

    async def _resolve_canonical_product_id(self, listing: MarketplaceListing) -> str | None:
        assert self._product_intelligence is not None
        try:
            parsed = await self._product_intelligence.parse_listing(listing.title)
        except UnsupportedProductError:
            return None

        # Map the known iPhone demo identity onto the fixed mock product id so
        # development fixtures and live mock connectors share one history series.
        if parsed.product.identity_key == IPHONE_DEMO_IDENTITY_KEY:
            return IPHONE_DEMO_CANONICAL_PRODUCT_ID
        return str(parsed.product.id)

    async def _maybe_seed_demo_mock(self) -> None:
        if not self._seed_demo_mock_on_search:
            return
        if self._app_env == "production":
            return
        if self._demo_mock_seeded:
            return
        from app.intelligence.price_history.mock_fixture import load_iphone_demo_mock_history

        await load_iphone_demo_mock_history(self._store, app_env=self._app_env)
        self._demo_mock_seeded = True

    def _to_history(
        self,
        snapshots: Sequence[PriceSnapshot],
        *,
        canonical_product_id: str | None,
        listing_id: str | None,
    ) -> PriceHistory:
        ordered = sort_snapshots(snapshots)
        if not ordered:
            return PriceHistory(
                canonical_product_id=canonical_product_id,
                listing_id=listing_id,
                currency="",
                snapshots=(),
                statistics=None,
                marketplace_summaries=(),
            )
        statistics = calculate_statistics(
            ordered,
            threshold_percent=self._trend_threshold_percent,
        )
        summaries = build_marketplace_summaries(ordered)
        return PriceHistory(
            canonical_product_id=canonical_product_id
            or (ordered[0].canonical_product_id if ordered else None),
            listing_id=listing_id,
            currency=statistics.currency,
            snapshots=tuple(ordered),
            statistics=statistics,
            marketplace_summaries=summaries,
        )


def snapshot_from_payload(
    *,
    canonical_product_id: str,
    marketplace: str,
    listing_id: str,
    currency: str,
    item_price: float,
    shipping_cost: float,
    availability: str,
    observed_at: datetime,
    seller_name: str | None = None,
    snapshot_id: UUID | None = None,
) -> PriceSnapshot:
    """Build a PriceSnapshot from API/request fields."""
    item = round(float(item_price), 2)
    shipping = round(float(shipping_cost), 2)
    try:
        availability_status = AvailabilityStatus(availability)
    except ValueError as exc:
        raise PriceHistoryValidationError(
            f"Unsupported availability value: {availability}"
        ) from exc
    return PriceSnapshot(
        snapshot_id=snapshot_id or uuid4(),
        canonical_product_id=canonical_product_id,
        marketplace=marketplace.strip().lower(),
        listing_id=listing_id,
        seller_name=seller_name,
        currency=currency.strip().upper(),
        item_price=item,
        shipping_cost=shipping,
        total_cost=round(item + shipping, 2),
        availability=availability_status,
        observed_at=observed_at,
    )
