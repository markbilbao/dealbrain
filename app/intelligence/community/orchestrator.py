"""End-to-end Community Intelligence orchestrator."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.community_intelligence import (
    CommunityProductIntelligence,
    CommunityWarning,
)
from app.domain.exceptions import CommunityIntelligenceValidationError
from app.intelligence.community.ai_orchestrator import CommunityAIOrchestrator
from app.intelligence.community.collector import CommunityCollector
from app.intelligence.community.dashboard import CommunityDashboardService
from app.intelligence.community.deterministic import DeterministicCommunitySummaryProvider
from app.intelligence.community.fixtures import get_product_meta
from app.intelligence.community.health import CommunityHealthService
from app.intelligence.community.metrics import CommunitySourceMetricsService
from app.intelligence.community.registry import CommunityRegistry
from app.intelligence.community.search import CommunitySearchService
from app.intelligence.community.statistics import CommunityStatisticsService
from app.intelligence.community.timeline import CommunityTimelineService
from app.intelligence.community.topic_analysis import TopicAnalysisService
from app.intelligence.community.trust import CommunityTrustCalculator


class CommunityOrchestrator:
    """Collect → normalize/dedupe → analyze → summarize community intelligence."""

    def __init__(
        self,
        registry: CommunityRegistry,
        *,
        collector: CommunityCollector | None = None,
        topic_analysis: TopicAnalysisService | None = None,
        trust_calculator: CommunityTrustCalculator | None = None,
        metrics_service: CommunitySourceMetricsService | None = None,
        timeline_service: CommunityTimelineService | None = None,
        statistics_service: CommunityStatisticsService | None = None,
        search_service: CommunitySearchService | None = None,
        dashboard_service: CommunityDashboardService | None = None,
        health_service: CommunityHealthService | None = None,
        ai_orchestrator: CommunityAIOrchestrator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._registry = registry
        self._collector = collector or CommunityCollector(registry)
        self._topics = topic_analysis or TopicAnalysisService()
        self._trust = trust_calculator or CommunityTrustCalculator()
        self._metrics = metrics_service or CommunitySourceMetricsService()
        self._timeline = timeline_service or CommunityTimelineService()
        self._statistics = statistics_service or CommunityStatisticsService()
        self._search = search_service or CommunitySearchService()
        self._dashboard = dashboard_service or CommunityDashboardService(self._topics)
        self._health = health_service or CommunityHealthService(registry)
        self._ai = ai_orchestrator
        self._deterministic = DeterministicCommunitySummaryProvider()
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def registry(self) -> CommunityRegistry:
        return self._registry

    @property
    def search(self) -> CommunitySearchService:
        return self._search

    @property
    def health(self) -> CommunityHealthService:
        return self._health

    @property
    def dashboard_service(self) -> CommunityDashboardService:
        return self._dashboard

    def analyze_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        mode: str | None = None,
        sources: list[str] | None = None,
    ) -> CommunityProductIntelligence:
        cleaned = (product_id or "").strip()
        if not cleaned:
            raise CommunityIntelligenceValidationError("product_id must not be blank.")

        meta = get_product_meta(cleaned, product_label)
        evidence = self._collector.collect(
            meta["product_id"],
            product_label=meta["product_name"],
            sources=sources,
        )
        topics = self._topics.analyze(evidence)
        source_metrics = self._metrics.for_all(self._registry.all(), evidence, now=self._clock())
        timeline = self._timeline.build(evidence)

        payload: dict[str, Any] = {
            "product_id": meta["product_id"],
            "product_name": meta["product_name"],
            "evidence": evidence,
            "topics": topics,
            "evidence_dicts": [item.to_dict() for item in evidence],
            "topic_dicts": [item.to_dict() for item in topics],
        }
        if self._ai is not None:
            try:
                explained = self._ai.summarize(payload, mode=mode)
            except ValueError as exc:
                raise CommunityIntelligenceValidationError(str(exc)) from exc
        else:
            explained = self._deterministic.summarize(payload)
            explained.update(
                {
                    "mode": "economy",
                    "providers_used": ("deterministic",),
                    "fallback_used": True,
                    "fallback_reason": "ai_orchestrator_not_configured",
                    "agreement_score": None,
                }
            )

        summary = explained.get("summary")
        if summary is None:
            summary = self._deterministic.summarize(payload)["summary"]

        trust = self._trust.calculate(
            evidence,
            ai_agreement=explained.get("agreement_score"),
            now=self._clock(),
        )
        stats = self._statistics.summarize(evidence, topics)
        warnings = [
            CommunityWarning(
                message=(
                    "Community Intelligence uses mock/imported connector data by default. "
                    "Live connectors remain disabled unless configured."
                ),
                code="mock_data",
            )
        ]
        if not evidence:
            warnings.append(
                CommunityWarning(
                    message="No community evidence found for this product.",
                    code="no_evidence",
                )
            )
        health = self._health.check()
        if health.get("enabled_connectors", 0) == 0:
            warnings.append(
                CommunityWarning(
                    message="No live community connectors are enabled; serving fixture-backed data.",
                    code="connectors_disabled",
                )
            )

        return CommunityProductIntelligence(
            product_id=meta["product_id"],
            product_name=meta["product_name"],
            trust=trust,
            topics=tuple(topics),
            evidence=tuple(evidence),
            summary=summary,
            source_metrics=tuple(source_metrics),
            timeline=tuple(timeline),
            warnings=tuple(warnings),
            data_status="mock",
            evidence_count=len(evidence),
            generated_at=self._clock(),
            processing={
                "mode": explained.get("mode") or "economy",
                "providers_used": list(explained.get("providers_used") or []),
                "fallback_used": bool(explained.get("fallback_used")),
                "fallback_reason": explained.get("fallback_reason"),
                "statistics": stats,
                "health": health,
                "secrets_included": False,
            },
        )
