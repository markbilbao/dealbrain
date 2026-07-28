"""In-memory ReviewRepository for development and tests."""

from __future__ import annotations

from app.domain.entities.review import MarketplaceReviewSummary, ReviewSnapshot
from app.domain.interfaces.review_repository import ReviewRepository


class InMemoryReviewRepository(ReviewRepository):
    """Process-local review snapshot store with deterministic order."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ReviewSnapshot] = {}
        self._order: list[str] = []

    def save_snapshot(self, snapshot: ReviewSnapshot) -> ReviewSnapshot:
        if snapshot.snapshot_id not in self._snapshots:
            self._order.append(snapshot.snapshot_id)
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    def latest_snapshot(
        self,
        product_id: str,
        *,
        marketplace: str | None = None,
    ) -> ReviewSnapshot | None:
        cleaned = product_id.strip()
        marketplace_key = marketplace.strip().lower() if marketplace else None
        for snapshot_id in reversed(self._order):
            snap = self._snapshots.get(snapshot_id)
            if snap is None or snap.product_id != cleaned:
                continue
            if marketplace_key is not None and snap.marketplace.lower() != marketplace_key:
                continue
            return snap
        return None

    def history(
        self,
        product_id: str,
        *,
        marketplace: str | None = None,
        limit: int = 50,
    ) -> list[ReviewSnapshot]:
        cleaned = product_id.strip()
        marketplace_key = marketplace.strip().lower() if marketplace else None
        ordered = [
            self._snapshots[sid]
            for sid in reversed(self._order)
            if sid in self._snapshots and self._snapshots[sid].product_id == cleaned
        ]
        if marketplace_key is not None:
            ordered = [s for s in ordered if s.marketplace.lower() == marketplace_key]
        return ordered[: max(0, limit)]

    def marketplace_summary(self, product_id: str) -> list[MarketplaceReviewSummary]:
        cleaned = product_id.strip()
        latest_by_marketplace: dict[str, ReviewSnapshot] = {}
        for snapshot_id in self._order:
            snap = self._snapshots.get(snapshot_id)
            if snap is None or snap.product_id != cleaned:
                continue
            # Insertion order: later snapshots overwrite earlier ones.
            latest_by_marketplace[snap.marketplace] = snap

        summaries: list[MarketplaceReviewSummary] = []
        for marketplace in sorted(latest_by_marketplace):
            snap = latest_by_marketplace[marketplace]
            summaries.append(
                MarketplaceReviewSummary(
                    marketplace=snap.marketplace,
                    rating=snap.average_rating,
                    reviews=snap.review_count,
                    seller_rating=snap.seller_rating,
                    seller_followers=snap.seller_followers,
                    seller_products=snap.seller_products,
                    five_star_count=snap.five_star_count,
                    four_star_count=snap.four_star_count,
                    three_star_count=snap.three_star_count,
                    two_star_count=snap.two_star_count,
                    one_star_count=snap.one_star_count,
                    collected_at=snap.collected_at,
                    snapshot_id=snap.snapshot_id,
                )
            )
        return summaries

    def clear(self) -> None:
        """Reset all stored snapshots (tests)."""
        self._snapshots.clear()
        self._order.clear()
