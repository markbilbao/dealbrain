"""Amazon Q&A adapter — normalize questions, answers, helpful votes."""

from __future__ import annotations

from typing import Any

from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.intelligence.community.fixtures import AMAZON_QA_FIXTURES, get_product_meta


class AmazonQACommunityProvider(BaseCommunityProvider):
    source = "amazon_qa"  # type: ignore[assignment]

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

    def _raw_for_product(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._enabled and not self._use_fixtures:
            return []
        meta = get_product_meta(product_id, product_label)
        items = list(AMAZON_QA_FIXTURES.get(meta["product_id"], []))
        return [
            {
                **item,
                "title": item.get("question"),
                "body": item.get("answer"),
                "helpful_votes": item.get("helpful_votes", 0),
                "asked_at": item.get("asked_at"),
                "url": item.get("url"),
                "evidence_id": f"amazon_qa:{item.get('qa_id')}",
            }
            for item in items
        ]

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return AMAZON_QA_FIXTURES
