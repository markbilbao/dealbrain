"""Base mock review collector — canned fixtures only, no live HTTP."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.entities.review import ReviewSnapshot
from app.domain.interfaces.review_repository import ReviewCollector
from app.intelligence.reviews.fixtures import resolve_product_label


class BaseMockReviewCollector(ReviewCollector):
    """Shared mock collector that materializes a fixture into a ReviewSnapshot."""

    def __init__(self, marketplace_name: str, fixture: dict[str, Any]) -> None:
        self._marketplace_name = marketplace_name
        self._fixture = fixture

    @property
    def marketplace_name(self) -> str:
        return self._marketplace_name

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        snapshot_id: str,
        collected_at: datetime,
    ) -> ReviewSnapshot:
        return self.build_snapshot(
            product_id,
            product_label=product_label,
            snapshot_id=snapshot_id,
            collected_at=collected_at,
        )

    def build_snapshot(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        snapshot_id: str,
        collected_at: datetime,
        rating_delta: float = 0.0,
        review_count_scale: float = 1.0,
    ) -> ReviewSnapshot:
        """Materialize a fixture, optionally adjusted for demo history waves."""
        cleaned_id = product_id.strip()
        label = resolve_product_label(cleaned_id, product_label)
        review_count = max(1, int(round(self._fixture["review_count"] * review_count_scale)))
        rating = round(min(5.0, max(1.0, self._fixture["average_rating"] + rating_delta)), 2)

        base_total = max(1, int(self._fixture["review_count"]))
        scale = review_count / base_total
        five = max(0, int(round(self._fixture["five_star_count"] * scale)))
        four = max(0, int(round(self._fixture["four_star_count"] * scale)))
        three = max(0, int(round(self._fixture["three_star_count"] * scale)))
        two = max(0, int(round(self._fixture["two_star_count"] * scale)))
        one = max(0, review_count - five - four - three - two)

        followers = self._fixture.get("seller_followers")
        if followers is not None and review_count_scale != 1.0:
            followers = max(0, int(round(followers * review_count_scale)))

        return ReviewSnapshot(
            snapshot_id=snapshot_id,
            product_id=cleaned_id,
            product_label=label,
            marketplace=self._marketplace_name,
            average_rating=rating,
            review_count=review_count,
            five_star_count=five,
            four_star_count=four,
            three_star_count=three,
            two_star_count=two,
            one_star_count=one,
            seller_rating=self._fixture.get("seller_rating"),
            seller_followers=followers,
            seller_products=self._fixture.get("seller_products"),
            collected_at=collected_at,
        )

    def health_check(self) -> bool:
        return True
