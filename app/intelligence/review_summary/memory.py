"""In-memory Review Summary repository for demos and tests."""

from __future__ import annotations

from app.domain.entities.review_summary import ReviewSummary
from app.domain.interfaces.review_summary_repository import ReviewSummaryRepository


class InMemoryReviewSummaryRepository(ReviewSummaryRepository):
    """Process-local store keyed by product_id (latest summary wins)."""

    def __init__(self) -> None:
        self._by_product: dict[str, ReviewSummary] = {}

    def save(self, summary: ReviewSummary) -> ReviewSummary:
        self._by_product[summary.product_id] = summary
        return summary

    def get_by_product_id(self, product_id: str) -> ReviewSummary | None:
        return self._by_product.get(product_id.strip())

    def clear(self) -> None:
        self._by_product.clear()
