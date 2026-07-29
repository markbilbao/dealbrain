"""Manufacturer Forums adapter — discussions, replies, accepted answers."""

from __future__ import annotations

from typing import Any

from app.domain.entities.community_intelligence import CommunityEvidence
from app.domain.interfaces.community_intelligence_repository import CommunityTransport
from app.infrastructure.community.base import BaseCommunityProvider
from app.intelligence.community.fixtures import FORUM_FIXTURES, get_product_meta


class ManufacturerForumsCommunityProvider(BaseCommunityProvider):
    source = "manufacturer_forums"  # type: ignore[assignment]

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
                    source="manufacturer_forums",
                    product_id=meta["product_id"],
                    product_name=meta["product_name"],
                )
            )
            for idx, reply in enumerate(item.get("replies") or []):
                accepted = bool(reply.get("accepted"))
                evidence.append(
                    self._normalizer.normalize(
                        {
                            "title": (
                                f"{'Accepted answer' if accepted else 'Reply'}: "
                                f"{item.get('title')}"
                            ),
                            "body": reply.get("body", ""),
                            "author": reply.get("author"),
                            "created_at": item.get("created_at"),
                            "url": item.get("url"),
                            "evidence_id": f"manufacturer_forums:{item.get('thread_id')}:r{idx}",
                            "thread_id": item.get("thread_id"),
                            "metadata_accepted": accepted,
                        },
                        source="manufacturer_forums",
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
        items = list(FORUM_FIXTURES.get(meta["product_id"], []))
        return [
            {
                **item,
                "title": item.get("title"),
                "body": item.get("discussion"),
                "replies": item.get("replies") or [],
                "created_at": item.get("created_at"),
                "url": item.get("url"),
                "evidence_id": f"manufacturer_forums:{item.get('thread_id')}",
            }
            for item in items
        ]

    def _fixture_map(self) -> dict[str, list[dict[str, Any]]]:
        return FORUM_FIXTURES
