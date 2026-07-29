"""Read-only adapters that project existing DealBrain modules into graph records.

Adapters never mutate protected modules.
"""

from __future__ import annotations

from typing import Any, Protocol


class CatalogAdapter(Protocol):
    def list_products(self) -> list[dict[str, Any]]: ...


class FixtureCatalogAdapter:
    """Adapter over shopping catalog fixtures."""

    def list_products(self) -> list[dict[str, Any]]:
        from app.intelligence.knowledge_graph.fixtures import build_fixture_records

        return list(build_fixture_records()["products"])


class ShoppingCatalogAdapter:
    """Read-only view of Shopping Assistant catalog fixtures."""

    def list_products(self) -> list[dict[str, Any]]:
        from app.intelligence.shopping_assistant.fixtures import get_catalog

        return [
            {
                "product_id": item["product_id"],
                "label": item["product_name"],
                "brand": item.get("brand"),
                "category": item.get("category"),
                "marketplace": item.get("marketplace"),
                "seller_name": item.get("seller_name"),
                "seller_trust_score": item.get("seller_trust_score"),
                "known_price": item.get("known_price"),
                "currency": item.get("currency", "PHP"),
                "deal_score": item.get("deal_score"),
                "rating": item.get("rating"),
                "review_count": item.get("review_count"),
                "complaints": list(item.get("complaints") or ()),
                "strengths": list(item.get("strengths") or ()),
                "data_status": item.get("data_status") or "mock",
                "topics": ["performance", "value"],
            }
            for item in get_catalog()
        ]


class CommunityEvidenceAdapter:
    """Optional read-only adapter for community intelligence evidence."""

    def __init__(self, community_service: Any | None = None) -> None:
        self._community = community_service

    def evidence_for(self, product_ids: list[str]) -> list[dict[str, Any]]:
        if self._community is None:
            return []
        try:
            items = self._community.shopping_assistant_evidence(product_ids)
        except Exception:  # noqa: BLE001
            return []
        mapped: list[dict[str, Any]] = []
        for item in items:
            mapped.append(
                {
                    "product_id": item.product_id or item.product,
                    "source": item.source,
                    "source_id": item.evidence_id,
                    "label": item.title or (item.body[:120] if item.body else item.evidence_id),
                    "topic": item.topic,
                    "confidence": float(item.confidence or 0.5),
                    "data_status": getattr(item, "data_status", "mock"),
                }
            )
        return mapped
