"""Marketplace Questions adapter — product questions + seller/community responses."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.intelligence.community.fixtures import MARKETPLACE_QA_FIXTURES, get_product_meta


class MarketplaceQuestionsCommunityProvider(BaseCommunityProvider):
    source = "marketplace_questions"  # type: ignore[assignment]

    def __init__(
        self,
        *,
        enabled: bool = False,
        transport: CommunityTransport | None = None,
        use_fixtures_when_unavailable: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            enabled=enabled,
            transport=transport,
            use_fixtures_when_unavailable=use_fixtures_when_unavailable,
            **kwargs,
        )

    def collect(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[CommunityEvidence]:
        meta = get_product_meta(product_id, product_label)
        evidence: list[CommunityEvidence] = []
        for item in self._raw_for_product(product_id, product_label=product_label):
            evidence.append(
                self._normalizer.normalize(
                    item,
                    source="marketplace_questions",
                    product_id=meta["product_id"],
                    product_name=meta["product_name"],
                )
            )
            for idx, response in enumerate(item.get("community_responses") or []):
                evidence.append(
                    self._normalizer.normalize(
                        {
                            "title": f"Community response to: {item.get('question')}",
                            "body": response,
                            "asked_at": item.get("asked_at"),
                            "url": item.get("url"),
                            "evidence_id": f"marketplace_questions:{item.get('question_id')}:c{idx}",
                            "replies_count": 0,
                        },
                        source="marketplace_questions",
                        product_id=meta["product_id"],
                        product_name=meta["product_name"],
                    )
                )
        return self._validator.validate_many(evidence)

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._enabled and not self._use_fixtures:
            return []
        meta = get_product_meta(product_id, product_label)
        items = list(MARKETPLACE_QA_FIXTURES.get(meta["product_id"], []))
        return [
            {
                **item,
                "title": item.get("question"),
                "body": item.get("seller_response") or "",
                "community_responses": item.get("community_responses") or [],
                "asked_at": item.get("asked_at"),
                "url": item.get("url"),
                "evidence_id": f"marketplace_questions:{item.get('question_id')}",
            }
            for item in items
        ]

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return MARKETPLACE_QA_FIXTURES
