"""Review Intelligence application service.

Collects mock marketplace ratings, stores snapshots, and computes
cross-marketplace comparisons. Does not modify protected intelligence modules.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.entities.review import (
    MarketplaceReviewComparison,
    MarketplaceReviewSummary,
    ReviewCollectionResult,
    ReviewSnapshot,
)
from app.domain.exceptions import ReviewNotFoundError, ReviewValidationError
from app.domain.interfaces.review_repository import ReviewCollector, ReviewRepository
from app.intelligence.reviews.base import BaseMockReviewCollector
from app.intelligence.reviews.fixtures import (
    DEMO_HISTORY_WAVES,
    resolve_product_label,
)


class ReviewService:
    """Orchestrate mock review collection and marketplace rating comparison."""

    def __init__(
        self,
        repository: ReviewRepository,
        collectors: Sequence[ReviewCollector],
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        seed_demo_history: bool = True,
    ) -> None:
        if not collectors:
            raise ReviewValidationError("At least one review collector is required.")
        self._repository = repository
        self._collectors = list(collectors)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._seed_demo_history = seed_demo_history

    def collect_reviews(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        marketplaces: Sequence[str] | None = None,
    ) -> ReviewCollectionResult:
        cleaned = product_id.strip()
        if not cleaned:
            raise ReviewValidationError("product_id must not be blank.")

        label = resolve_product_label(cleaned, product_label)
        selected = self._select_collectors(marketplaces)
        stamp = self._clock()

        # Seed older demo waves once so history has more than one observation.
        if self._seed_demo_history and not self._repository.history(cleaned, limit=1):
            self._seed_historical_waves(cleaned, label=label, collectors=selected, now=stamp)

        snapshots: list[ReviewSnapshot] = []
        for collector in selected:
            snapshot = collector.collect(
                cleaned,
                product_label=label,
                snapshot_id=self._id_factory(),
                collected_at=stamp,
            )
            self._repository.save_snapshot(snapshot)
            snapshots.append(snapshot)

        return ReviewCollectionResult(
            product_id=cleaned,
            product=label,
            snapshots=tuple(snapshots),
            collected_at=stamp,
        )

    def latest_reviews(self, product_id: str) -> list[MarketplaceReviewSummary]:
        cleaned = self._require_product_id(product_id)
        summaries = self._repository.marketplace_summary(cleaned)
        if not summaries:
            raise ReviewNotFoundError(cleaned)
        return summaries

    def review_history(
        self,
        product_id: str,
        *,
        marketplace: str | None = None,
        limit: int = 50,
    ) -> list[ReviewSnapshot]:
        cleaned = self._require_product_id(product_id)
        if limit < 1:
            raise ReviewValidationError("limit must be at least 1.")
        history = self._repository.history(
            cleaned,
            marketplace=marketplace,
            limit=limit,
        )
        if not history:
            raise ReviewNotFoundError(cleaned)
        return history

    def compare_marketplaces(self, product_id: str) -> MarketplaceReviewComparison:
        cleaned = self._require_product_id(product_id)
        summaries = self._repository.marketplace_summary(cleaned)
        if not summaries:
            raise ReviewNotFoundError(cleaned)

        label = resolve_product_label(cleaned)
        for summary in summaries:
            snap = self._repository.latest_snapshot(cleaned, marketplace=summary.marketplace)
            if snap and snap.product_label:
                label = snap.product_label
                break

        return MarketplaceReviewComparison(
            product=label,
            product_id=cleaned,
            marketplaces=tuple(summaries),
            overall_rating=self.overall_rating(cleaned),
            total_review_count=self.total_review_count(cleaned),
        )

    def overall_rating(self, product_id: str) -> float | None:
        cleaned = self._require_product_id(product_id)
        summaries = self._repository.marketplace_summary(cleaned)
        if not summaries:
            return None
        weighted = sum(item.rating * item.reviews for item in summaries)
        total = sum(item.reviews for item in summaries)
        if total <= 0:
            return None
        return round(weighted / total, 2)

    def total_review_count(self, product_id: str) -> int:
        cleaned = self._require_product_id(product_id)
        summaries = self._repository.marketplace_summary(cleaned)
        return sum(item.reviews for item in summaries)

    def _require_product_id(self, product_id: str) -> str:
        cleaned = product_id.strip()
        if not cleaned:
            raise ReviewValidationError("product_id must not be blank.")
        return cleaned

    def _select_collectors(
        self,
        marketplaces: Sequence[str] | None,
    ) -> list[ReviewCollector]:
        if marketplaces is None:
            return list(self._collectors)
        wanted = {name.strip().lower() for name in marketplaces if name and name.strip()}
        if not wanted:
            raise ReviewValidationError("marketplaces must not be empty.")
        selected = [
            collector
            for collector in self._collectors
            if collector.marketplace_name.lower() in wanted
        ]
        if not selected:
            raise ReviewValidationError(
                "No matching review collectors for: " + ", ".join(sorted(wanted))
            )
        return selected

    def _seed_historical_waves(
        self,
        product_id: str,
        *,
        label: str,
        collectors: Sequence[ReviewCollector],
        now: datetime,
    ) -> None:
        for days_ago, rating_delta, count_scale_delta in DEMO_HISTORY_WAVES:
            stamp = now - timedelta(days=days_ago)
            scale = 1.0 + count_scale_delta
            for collector in collectors:
                if isinstance(collector, BaseMockReviewCollector):
                    snapshot = collector.build_snapshot(
                        product_id,
                        product_label=label,
                        snapshot_id=self._id_factory(),
                        collected_at=stamp,
                        rating_delta=rating_delta,
                        review_count_scale=scale,
                    )
                else:
                    snapshot = collector.collect(
                        product_id,
                        product_label=label,
                        snapshot_id=self._id_factory(),
                        collected_at=stamp,
                    )
                self._repository.save_snapshot(snapshot)
