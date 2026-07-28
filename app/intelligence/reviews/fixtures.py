"""Mock review fixtures for Review Intelligence demos.

DEVELOPMENT MOCK DATA — NOT LIVE MARKETPLACE REVIEWS
====================================================

Canned rating / review counts only. Never contacts marketplaces.
"""

from __future__ import annotations

from typing import Any

# Fixed demo product id (aligned with Price History / Watchlists iPhone demo).
IPHONE_DEMO_PRODUCT_ID = "00000000-0000-4000-8000-000000000017"
IPHONE_DEMO_PRODUCT_LABEL = "iPhone 17 Pro Max"

# Known product labels keyed by product_id (demo soft-lookup).
DEMO_PRODUCT_LABELS: dict[str, str] = {
    IPHONE_DEMO_PRODUCT_ID: IPHONE_DEMO_PRODUCT_LABEL,
    "iphone-17-pro-max": IPHONE_DEMO_PRODUCT_LABEL,
    IPHONE_DEMO_PRODUCT_LABEL.lower(): IPHONE_DEMO_PRODUCT_LABEL,
}

# Per-marketplace canned review payloads.
# Star counts are approximate distributions that sum to review_count.
MOCK_REVIEW_FIXTURES: dict[str, dict[str, Any]] = {
    "Shopee": {
        "average_rating": 4.8,
        "review_count": 12431,
        "five_star_count": 9870,
        "four_star_count": 1865,
        "three_star_count": 435,
        "two_star_count": 161,
        "one_star_count": 100,
        "seller_rating": 4.9,
        "seller_followers": 18000,
        "seller_products": 342,
    },
    "Lazada": {
        "average_rating": 4.7,
        "review_count": 9821,
        "five_star_count": 7420,
        "four_star_count": 1670,
        "three_star_count": 491,
        "two_star_count": 147,
        "one_star_count": 93,
        "seller_rating": 4.8,
        "seller_followers": 12500,
        "seller_products": 218,
    },
    "TikTok Shop": {
        "average_rating": 4.6,
        "review_count": 5432,
        "five_star_count": 3890,
        "four_star_count": 980,
        "three_star_count": 325,
        "two_star_count": 140,
        "one_star_count": 97,
        "seller_rating": 4.7,
        "seller_followers": 92000,
        "seller_products": 87,
    },
    "Amazon": {
        "average_rating": 4.5,
        "review_count": 15680,
        "five_star_count": 10976,
        "four_star_count": 2822,
        "three_star_count": 1098,
        "two_star_count": 470,
        "one_star_count": 314,
        "seller_rating": 4.6,
        "seller_followers": None,
        "seller_products": 1250,
    },
}


def resolve_product_label(product_id: str, product_label: str | None = None) -> str:
    """Return a display label for demos; fall back to the product_id."""
    if product_label and product_label.strip():
        return product_label.strip()
    cleaned = product_id.strip()
    return DEMO_PRODUCT_LABELS.get(cleaned, DEMO_PRODUCT_LABELS.get(cleaned.lower(), cleaned))


# Historical mock deltas applied when seeding demo history (older → newer).
# Each entry is (days_ago, rating_delta, review_count_delta_fraction).
DEMO_HISTORY_WAVES: tuple[tuple[int, float, float], ...] = (
    (21, -0.15, -0.18),
    (14, -0.08, -0.10),
    (7, -0.03, -0.04),
)
