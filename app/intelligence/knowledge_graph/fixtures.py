"""Fixture graph data for Knowledge Graph demos and tests.

Uses mock/imported DealBrain-style data only. No live scraping.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.intelligence.reviews.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.intelligence.shopping_assistant.fixtures import SHOPPING_CATALOG

DEMO_PRODUCT_ID = "sa-laptop-tuf-a15"
DEMO_PRODUCT_LABEL = "ASUS TUF Gaming A15 Ryzen 7 RTX 4050"

# Anchor shared with Shopping / Community / Reviews demos.
__all__ = [
    "DEMO_PRODUCT_ID",
    "DEMO_PRODUCT_LABEL",
    "IPHONE_DEMO_PRODUCT_ID",
    "IPHONE_DEMO_PRODUCT_LABEL",
    "build_fixture_records",
    "list_demo_product_ids",
]


def list_demo_product_ids() -> list[str]:
    ids = [str(item["product_id"]) for item in SHOPPING_CATALOG]
    if IPHONE_DEMO_PRODUCT_ID not in ids:
        ids.append(IPHONE_DEMO_PRODUCT_ID)
    return ids


def build_fixture_records() -> dict[str, Any]:
    """Return structured records used by the aggregator to seed the graph."""
    now = datetime.now(UTC).isoformat()
    products: list[dict[str, Any]] = []
    for item in SHOPPING_CATALOG:
        products.append(
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
                "topics": ["battery", "performance", "value"]
                if item.get("category") == "laptop"
                else ["camera", "battery"],
            }
        )

    # Cross-marketplace duplicate of the demo laptop (same brand+label → one canonical).
    products.append(
        {
            "product_id": "lazada-tuf-a15-mirror",
            "label": DEMO_PRODUCT_LABEL,
            "brand": "ASUS",
            "category": "laptop",
            "marketplace": "Lazada",
            "seller_name": "ASUS LazMall",
            "seller_trust_score": 0.9,
            "known_price": 55999.0,
            "currency": "PHP",
            "deal_score": 86.0,
            "rating": 4.5,
            "review_count": 640,
            "complaints": ["Fans can be loud under load"],
            "strengths": ["Good DealScore under ₱60k"],
            "data_status": "mock",
            "topics": ["battery", "performance", "value"],
        }
    )

    similar_pairs = [
        ("sa-laptop-tuf-a15", "sa-laptop-nitro-v15", 0.82),
        ("sa-laptop-tuf-a15", "sa-laptop-loq-15", 0.78),
        ("sa-laptop-nitro-v15", "sa-laptop-loq-15", 0.8),
    ]

    contradictions = [
        {
            "product_id": DEMO_PRODUCT_ID,
            "topic": "battery",
            "left": {
                "source": "community",
                "source_id": "reddit-battery-good",
                "label": "Battery lasts a full workday",
                "confidence": 0.72,
            },
            "right": {
                "source": "review",
                "source_id": "review-battery-poor",
                "label": "Battery drains under gaming load",
                "confidence": 0.8,
            },
        }
    ]

    community_evidence = [
        {
            "product_id": DEMO_PRODUCT_ID,
            "source": "reddit",
            "source_id": "reddit-tuf-thread-1",
            "label": "r/ASUS: TUF A15 value discussion",
            "topic": "value",
            "confidence": 0.74,
            "data_status": "mock",
        },
        {
            "product_id": DEMO_PRODUCT_ID,
            "source": "reddit",
            "source_id": "reddit-tuf-thread-1",  # intentional duplicate source
            "label": "r/ASUS: TUF A15 value discussion",
            "topic": "value",
            "confidence": 0.74,
            "data_status": "mock",
        },
        {
            "product_id": "sa-laptop-loq-15",
            "source": "youtube",
            "source_id": "yt-loq-review",
            "label": "LOQ 15 budget gaming overview",
            "topic": "performance",
            "confidence": 0.7,
            "data_status": "mock",
        },
    ]

    return {
        "generated_at": now,
        "data_status": "mock",
        "products": products,
        "similar_pairs": similar_pairs,
        "contradictions": contradictions,
        "community_evidence": community_evidence,
        "warnings": [
            "Fixture data only — not live marketplace coverage.",
            "Similar/recommended relationships are not purchase guarantees.",
        ],
    }
