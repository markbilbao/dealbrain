"""Review persistence and marketplace review collector ports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.review import MarketplaceReviewSummary, ReviewSnapshot


class ReviewRepository(ABC):
    """Persistence for marketplace review snapshots."""

    @abstractmethod
    def save_snapshot(self, snapshot: ReviewSnapshot) -> ReviewSnapshot:
        """Create or replace a review snapshot."""

    @abstractmethod
    def latest_snapshot(
        self,
        product_id: str,
        *,
        marketplace: str | None = None,
    ) -> ReviewSnapshot | None:
        """Return the newest snapshot for a product (optionally one marketplace)."""

    @abstractmethod
    def history(
        self,
        product_id: str,
        *,
        marketplace: str | None = None,
        limit: int = 50,
    ) -> list[ReviewSnapshot]:
        """Return snapshots newest-first for a product."""

    @abstractmethod
    def marketplace_summary(self, product_id: str) -> list[MarketplaceReviewSummary]:
        """Return the latest snapshot summary for each marketplace."""


class ReviewCollector(ABC):
    """Abstract contract for collecting review snapshots from one marketplace.

    Implementations must use canned fixtures only — no live HTTP, scraping,
    or browser automation.
    """

    @property
    @abstractmethod
    def marketplace_name(self) -> str:
        """Stable marketplace identifier (e.g. ``Shopee``, ``Lazada``)."""

    @abstractmethod
    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        snapshot_id: str,
        collected_at: datetime,
    ) -> ReviewSnapshot:
        """Return a mock review snapshot for ``product_id``."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return ``True`` when the collector is ready to accept work."""
