"""Collect evidence across registered community providers."""

from __future__ import annotations

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.interfaces.community_intelligence_repository import CommunityProvider
from app.intelligence.community.duplicates import DuplicateDetector
from app.intelligence.community.registry import CommunityRegistry
from app.intelligence.community.validator import EvidenceValidator


class CommunityCollector:
    """Aggregate normalized evidence from all available connectors."""

    def __init__(
        self,
        registry: CommunityRegistry,
        *,
        duplicate_detector: DuplicateDetector | None = None,
        validator: EvidenceValidator | None = None,
        include_disabled_fixtures: bool = True,
    ) -> None:
        self._registry = registry
        self._duplicates = duplicate_detector or DuplicateDetector()
        self._validator = validator or EvidenceValidator()
        self._include_disabled_fixtures = include_disabled_fixtures

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        sources: list[str] | None = None,
    ) -> list[CommunityEvidence]:
        providers = self._select_providers(sources)
        evidence: list[CommunityEvidence] = []
        for provider in providers:
            if not provider.is_available() and not self._include_disabled_fixtures:
                continue
            try:
                items = provider.collect(product_id, product_label=product_label)
            except Exception:  # noqa: BLE001
                continue
            evidence.extend(self._validator.validate_many(items))
        return self._duplicates.merge(evidence)

    def collect_by_source(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> dict[str, list[CommunityEvidence]]:
        result: dict[str, list[CommunityEvidence]] = {}
        for provider in self._registry.all():
            if not provider.is_available() and not self._include_disabled_fixtures:
                result[provider.source_name] = []
                continue
            try:
                result[provider.source_name] = provider.collect(
                    product_id, product_label=product_label
                )
            except Exception:  # noqa: BLE001
                result[provider.source_name] = []
        return result

    def _select_providers(self, sources: list[str] | None) -> list[CommunityProvider]:
        if not sources:
            return self._registry.all()
        selected: list[CommunityProvider] = []
        for name in sources:
            provider = self._registry.get(name)
            if provider is not None:
                selected.append(provider)
        return selected
