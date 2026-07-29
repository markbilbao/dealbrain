"""Mock review text fixtures for AI Review Summary demos.

DEVELOPMENT MOCK DATA — NOT LIVE MARKETPLACE REVIEWS
====================================================

Canned buyer comments only. Never contacts marketplaces or external AI.
"""

from __future__ import annotations

from app.intelligence.reviews.fixtures import (
    DEMO_PRODUCT_LABELS,
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
    resolve_product_label,
)

# Re-export demo identity constants for summary callers.
__all__ = [
    "DEMO_PRODUCT_LABELS",
    "IPHONE_DEMO_PRODUCT_ID",
    "IPHONE_DEMO_PRODUCT_LABEL",
    "MOCK_REVIEW_TEXTS",
    "THEME_LEXICON",
    "get_mock_review_texts",
    "resolve_product_label",
]

# Example buyer comments used for keyword frequency ranking.
MOCK_REVIEW_TEXTS: dict[str, tuple[str, ...]] = {
    IPHONE_DEMO_PRODUCT_ID: (
        "Battery lasts all day.",
        "Camera is excellent.",
        "Packaging was poor.",
        "Heats during gaming.",
        "Very fast delivery.",
        "Authentic product.",
        "Premium build quality feels solid.",
        "Camera is excellent in low light.",
        "Battery lasts all day with heavy use.",
        "Heats during gaming and video calls.",
        "Very fast delivery from the seller.",
        "Expensive but worth the camera quality.",
        "Accessories in the box felt cheap.",
        "Authentic product with sealed packaging.",
        "Build quality is premium.",
        "Some complaints about accessories online match mine.",
        "Warms under heavy gaming sessions.",
        "Long battery life is impressive.",
        "Excellent camera for photos and video.",
        "Price is expensive compared to last gen.",
        "Premium build and finish.",
        "Fast delivery again on a second order.",
    ),
    "iphone-17-pro-max": (
        "Battery lasts all day.",
        "Camera is excellent.",
        "Packaging was poor.",
        "Heats during gaming.",
        "Very fast delivery.",
        "Authentic product.",
        "Premium build quality feels solid.",
        "Expensive but worth it.",
        "Accessories in the box felt cheap.",
        "Long battery life is impressive.",
    ),
}

# Default fixture used when a product_id has no dedicated texts.
DEFAULT_MOCK_REVIEW_TEXTS: tuple[str, ...] = (
    "Battery lasts all day.",
    "Camera is excellent.",
    "Packaging was poor.",
    "Heats during gaming.",
    "Very fast delivery.",
    "Authentic product.",
    "Premium build quality.",
    "Expensive compared to rivals.",
    "Accessories feel incomplete.",
    "Warms under heavy gaming.",
)

# Keyword → (polarity, display label). Matching is case-insensitive substring.
THEME_LEXICON: dict[str, tuple[str, str]] = {
    "camera": ("pro", "Excellent camera"),
    "battery": ("pro", "Long battery life"),
    "build": ("pro", "Premium build"),
    "delivery": ("pro", "Fast delivery"),
    "authentic": ("pro", "Authentic product"),
    "heat": ("con", "Warms under heavy gaming"),
    "heats": ("con", "Warms under heavy gaming"),
    "warm": ("con", "Warms under heavy gaming"),
    "expensive": ("con", "Expensive"),
    "price": ("con", "Expensive"),
    "packaging": ("con", "Poor packaging"),
    "accessories": ("warning", "Some complaints about accessories"),
}


def get_mock_review_texts(product_id: str) -> tuple[str, ...]:
    """Return canned review texts for ``product_id`` (demo soft-lookup)."""
    cleaned = product_id.strip()
    if cleaned in MOCK_REVIEW_TEXTS:
        return MOCK_REVIEW_TEXTS[cleaned]
    lowered = cleaned.lower()
    if lowered in MOCK_REVIEW_TEXTS:
        return MOCK_REVIEW_TEXTS[lowered]
    return DEFAULT_MOCK_REVIEW_TEXTS
