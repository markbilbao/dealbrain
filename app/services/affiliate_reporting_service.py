"""Affiliate revenue reporting application service — Sprint 20.

Aggregates demo click/conversion data for the Affiliate Dashboard.
No real commissions, billing, or payouts.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from app.affiliate.reporting.aggregator import aggregate_revenue_report
from app.domain.entities.affiliate import AffiliateRevenueReport
from app.domain.interfaces.affiliate_repository import AffiliateClickRepository


class ImpressionCounter(Protocol):
    """Minimal impression counter used by affiliate reporting (demo metrics only)."""

    @property
    def impression_count(self) -> int: ...

    def record_impression(self, count: int = 1) -> int: ...


class AffiliateReportingService:
    """Build revenue reports from tracked clicks."""

    def __init__(
        self,
        click_repository: AffiliateClickRepository,
        *,
        impression_store: ImpressionCounter | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clicks = click_repository
        self._impressions = impression_store
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def build_report(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        currency: str = "USD",
        top_n: int = 5,
        limit: int = 1000,
    ) -> AffiliateRevenueReport:
        clicks = self._clicks.list_clicks(
            merchant_id=merchant_id, product_id=product_id, limit=limit
        )
        impressions = 0
        if self._impressions is not None:
            impressions = self._impressions.impression_count
        return aggregate_revenue_report(
            clicks,
            report_id=f"report-{self._id_factory()}",
            generated_at=self._clock(),
            impressions=impressions,
            currency=currency,
            top_n=top_n,
        )

    def record_impression(self, count: int = 1) -> int:
        """Increment synthetic impression counter (CTR denominator)."""
        if self._impressions is None:
            return 0
        return self._impressions.record_impression(count)
