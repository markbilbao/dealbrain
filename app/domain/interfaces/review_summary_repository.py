"""Ports for AI Review Summary persistence and summarization providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from app.domain.entities.review_summary import ReviewSummary


class ReviewSummaryRepository(ABC):
    """Persistence for generated review summaries."""

    @abstractmethod
    def save(self, summary: ReviewSummary) -> ReviewSummary:
        """Create or replace the latest summary for a product."""

    @abstractmethod
    def get_by_product_id(self, product_id: str) -> ReviewSummary | None:
        """Return the newest summary for ``product_id``, if any."""


class ReviewSummarizer(ABC):
    """Abstract contract for review summarization providers.

    Sprint 12 ships a deterministic mock implementation. Future OpenAI /
    Claude / Gemini adapters should implement this port without changing
    callers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier (e.g. ``deterministic-mock``)."""

    @abstractmethod
    def summarize(
        self,
        *,
        product_id: str,
        product: str,
        review_texts: Sequence[str],
        average_rating: float | None,
        total_review_count: int,
        summary_id: str,
        generated_at: datetime,
    ) -> ReviewSummary:
        """Produce a review summary from rating stats and review texts."""
