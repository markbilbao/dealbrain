"""Per-source community metrics."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.community_intelligence import (
    CommunityEvidence,
    CommunitySourceMetrics,
    ConnectorStatus,
)
from app.domain.interfaces.community_intelligence_repository import CommunityProvider


class CommunitySourceMetricsService:
    """Compute CommunitySourceMetrics for connectors and evidence."""

    def for_provider(
        self,
        provider: CommunityProvider,
        evidence: list[CommunityEvidence],
        *,
        now: datetime | None = None,
    ) -> CommunitySourceMetrics:
        now = now or datetime.now(UTC)
        source_items = [item for item in evidence if item.source == provider.source_name]
        status = self._status(provider, source_items)
        authors = {item.author for item in source_items if item.author}
        threads = {item.thread_id or item.evidence_id for item in source_items}
        avg_engagement = (
            sum(item.engagement.score for item in source_items) / len(source_items)
            if source_items
            else 0.0
        )
        freshness = None
        if source_items:
            newest = max(source_items, key=lambda item: item.timestamp)
            ts = newest.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            freshness = round((now - ts).total_seconds() / 3600.0, 2)
        transport = "mock"
        transport_name = getattr(provider, "transport_name", None)
        if callable(transport_name):
            transport = transport_name()
        return CommunitySourceMetrics(
            source=provider.source_name,
            status=status,
            evidence_count=len(source_items),
            unique_authors=len(authors),
            unique_threads=len(threads),
            average_engagement=round(avg_engagement, 3),
            freshness_hours=freshness,
            enabled=provider.is_enabled(),
            transport=transport,
        )

    def for_all(
        self,
        providers: list[CommunityProvider],
        evidence: list[CommunityEvidence],
        *,
        now: datetime | None = None,
    ) -> list[CommunitySourceMetrics]:
        return [self.for_provider(provider, evidence, now=now) for provider in providers]

    def _status(
        self,
        provider: CommunityProvider,
        source_items: list[CommunityEvidence],
    ) -> ConnectorStatus:
        if not provider.is_enabled():
            if source_items:
                return "mock"
            return "disabled"
        if not provider.health_check():
            return "error"
        if not provider.is_available():
            return "unavailable"
        if source_items and all(item.data_status == "mock" for item in source_items):
            return "mock"
        return "enabled"
