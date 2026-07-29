"""Community Intelligence Platform application service."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import (
    CommunityDashboard,
    CommunityEvidence,
    CommunityProductIntelligence,
    CommunityTimelineEvent,
    CommunityTopic,
)
from app.domain.exceptions import (
    CommunityIntelligenceNotFoundError,
    CommunityIntelligenceValidationError,
)
from app.intelligence.community.fixtures import DEMO_PRODUCT_ID, get_product_meta
from app.intelligence.community.orchestrator import CommunityOrchestrator


class CommunityIntelligenceService:
    """Application facade for community intelligence queries."""

    def __init__(self, orchestrator: CommunityOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._cache: dict[str, CommunityProductIntelligence] = {}

    def demo(self, *, mode: str | None = None) -> CommunityDashboard:
        product = self.get_product(DEMO_PRODUCT_ID, mode=mode)
        return self._orchestrator.dashboard_service.from_product(product)

    def get_product(
        self,
        product_id: str,
        *,
        mode: str | None = None,
        refresh: bool = False,
    ) -> CommunityProductIntelligence:
        cleaned = (product_id or "").strip()
        if not cleaned:
            raise CommunityIntelligenceValidationError("product_id must not be blank.")
        cache_key = f"{cleaned}:{mode or 'default'}"
        if not refresh and cache_key in self._cache:
            return self._cache[cache_key]
        product = self._orchestrator.analyze_product(cleaned, mode=mode)
        self._cache[cache_key] = product
        return product

    def get_evidence(self, evidence_id: str) -> CommunityEvidence:
        cleaned = (evidence_id or "").strip()
        if not cleaned:
            raise CommunityIntelligenceValidationError("evidence_id must not be blank.")
        # Search across known demo products + any cached analyses.
        candidates = list(self._cache.values())
        if not candidates:
            candidates.append(self.get_product(DEMO_PRODUCT_ID))
        for product in candidates:
            found = self._orchestrator.search.get_by_id(list(product.evidence), cleaned)
            if found is not None:
                return found
        # Broaden search by collecting demo catalog products.
        from app.intelligence.community.fixtures import list_demo_product_ids

        for product_id in list_demo_product_ids():
            product = self.get_product(product_id)
            found = self._orchestrator.search.get_by_id(list(product.evidence), cleaned)
            if found is not None:
                return found
        raise CommunityIntelligenceNotFoundError(cleaned)

    def get_topics(self, product_id: str) -> list[CommunityTopic]:
        return list(self.get_product(product_id).topics)

    def get_timeline(self, product_id: str) -> list[CommunityTimelineEvent]:
        return list(self.get_product(product_id).timeline)

    def evidence_explorer(
        self,
        product_id: str,
        *,
        topic: str | None = None,
    ) -> dict[str, Any]:
        product = self.get_product(product_id)
        topics = list(product.topics)
        if topic:
            topics = [item for item in topics if item.name.lower() == topic.lower()]
        explorer = []
        for item in topics:
            supporting = [
                evidence
                for evidence in product.evidence
                if evidence.evidence_id in item.evidence_ids
            ]
            explorer.append(
                {
                    "topic": item.name,
                    "sentiment": item.sentiment.to_dict(),
                    "confidence": item.confidence,
                    "statement": (
                        f"{item.name} "
                        f"{'Excellent' if item.sentiment.label == 'positive' else item.sentiment.label.title()}"
                    ),
                    "supported_by": [
                        {
                            "evidence_id": evidence.evidence_id,
                            "source": evidence.source,
                            "title": evidence.title,
                            "url": evidence.url,
                        }
                        for evidence in supporting
                    ],
                }
            )
        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "insights": explorer,
        }

    def shopping_assistant_evidence(
        self,
        product_ids: list[str],
        *,
        limit_per_product: int = 4,
    ) -> list[CommunityEvidence]:
        """Provider-neutral evidence slice for Shopping Assistant integration."""
        collected: list[CommunityEvidence] = []
        for product_id in product_ids:
            try:
                product = self.get_product(product_id)
            except CommunityIntelligenceValidationError:
                continue
            ranked = sorted(
                product.evidence,
                key=lambda item: item.engagement.score,
                reverse=True,
            )
            collected.extend(ranked[:limit_per_product])
        return collected

    def meta(self) -> dict[str, Any]:
        health = self._orchestrator.health.check()
        demo_meta = get_product_meta(DEMO_PRODUCT_ID)
        return {
            "demo_product_id": demo_meta["product_id"],
            "demo_product_name": demo_meta["product_name"],
            "connectors": health.get("connectors") or {},
            "data_status": "mock",
            "ai_enabled": bool(
                self._orchestrator._ai is not None  # noqa: SLF001
                and getattr(self._orchestrator._ai, "_ai_enabled", False)  # noqa: SLF001
            ),
        }
