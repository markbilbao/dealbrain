"""Shared base for community source adapters."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence, CommunitySource
from app.domain.interfaces.community_intelligence_repository import (
    CommunityProvider,
    CommunityTransport,
)
from app.infrastructure.community.transports import DisabledCommunityTransport, MockCommunityTransport
from app.intelligence.community.fixtures import get_product_meta
from app.intelligence.community.normalizer import EvidenceNormalizer
from app.intelligence.community.validator import EvidenceValidator


class BaseCommunityProvider(CommunityProvider):
    """Common adapter behavior: fixture/mock transport, normalize, validate."""

    source: CommunitySource = "reddit"

    def __init__(
        self,
        *,
        enabled: bool = False,
        transport: CommunityTransport | None = None,
        use_fixtures_when_unavailable: bool = True,
        normalizer: EvidenceNormalizer | None = None,
        validator: EvidenceValidator | None = None,
    ) -> None:
        self._enabled = enabled
        self._transport = transport or (
            MockCommunityTransport() if enabled else DisabledCommunityTransport()
        )
        self._use_fixtures = use_fixtures_when_unavailable
        self._normalizer = normalizer or EvidenceNormalizer()
        self._validator = validator or EvidenceValidator()

    @property
    def source_name(self) -> CommunitySource:
        return self.source

    def is_enabled(self) -> bool:
        return self._enabled

    def is_available(self) -> bool:
        if not self._enabled:
            return self._use_fixtures
        return True

    def health_check(self) -> bool:
        try:
            if not self._enabled and self._use_fixtures:
                return True
            if isinstance(self._transport, DisabledCommunityTransport):
                return self._use_fixtures
            self._transport.fetch(f"/{self.source}/health")
            return True
        except Exception:  # noqa: BLE001
            return self._use_fixtures

    def search_product(self, product_id: str, *, product_label: str | None = None) -> list[dict[str, Any]]:
        return self._raw_for_product(product_id, product_label=product_label)

    def search_threads(self, product_id: str, *, query: str | None = None) -> list[dict[str, Any]]:
        items = self._raw_for_product(product_id)
        if not query:
            return items
        needle = query.lower()
        return [
            item
            for item in items
            if needle in str(item.get("title", "")).lower()
            or needle in str(item.get("body", "")).lower()
            or needle in str(item.get("question", "")).lower()
        ]

    def extract_comments(self, thread_id: str) -> list[dict[str, Any]]:
        return []

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[CommunityEvidence]:
        meta = get_product_meta(product_id, product_label)
        raw_items = self._raw_for_product(product_id, product_label=product_label)
        evidence = self._normalizer.normalize_many(
            raw_items,
            source=self.source_name,
            product_id=meta["product_id"],
            product_name=meta["product_name"],
        )
        return self._validator.validate_many(evidence)

    def transport_name(self) -> str:
        return type(self._transport).__name__

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return {}
