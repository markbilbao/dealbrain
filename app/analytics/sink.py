"""Analytics sink abstraction.

The production consent-on sink is the first-party repository. Consent-off uses
the null sink and does not write a product analytics row. A later external
provider can implement ``ProductAnalyticsSink`` without changing event meaning.
"""

from __future__ import annotations

from typing import Protocol

from app.analytics.schema import AnalyticsWriteResult, ProductAnalyticsEvent


class ProductAnalyticsSink(Protocol):
    """Persist one already-validated event, or report why it was not stored."""

    def persist(self, event: ProductAnalyticsEvent) -> AnalyticsWriteResult:
        """Store ``event`` or return a closed result. Must not rewrite semantics."""


class NullProductAnalyticsSink:
    """Suppression sink. It does not write, log, or forward the event."""

    def persist(self, event: ProductAnalyticsEvent) -> AnalyticsWriteResult:
        del event
        return AnalyticsWriteResult(status="suppressed_no_consent")

    def suppress(self) -> AnalyticsWriteResult:
        return AnalyticsWriteResult(status="suppressed_no_consent")
