"""Mock shopping catalog for AI Shopping Assistant v1.

Uses DealBrain-style mock / imported demo data only. Does not claim live
marketplace access or scraping.
"""

from __future__ import annotations

from typing import Any

from app.intelligence.reviews.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)

# Re-export demo anchors for cross-panel consistency.
__all__ = [
    "IPHONE_DEMO_PRODUCT_ID",
    "IPHONE_DEMO_PRODUCT_LABEL",
    "SHOPPING_CATALOG",
    "DEMO_QUERIES",
    "get_catalog",
    "get_product_by_id",
    "get_product_by_name",
]

SHOPPING_CATALOG: list[dict[str, Any]] = [
    {
        "product_id": "sa-laptop-tuf-a15",
        "product_name": "ASUS TUF Gaming A15 Ryzen 7 RTX 4050",
        "category": "laptop",
        "brand": "ASUS",
        "known_price": 54999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 88.5,
        "rating": 4.6,
        "review_count": 1842,
        "use_cases": ("gaming", "productivity"),
        "features": ("rtx 4050", "16gb ram", "512gb ssd", "144hz"),
        "seller_name": "ASUS Official Store PH",
        "seller_trust_score": 0.92,
        "price_near_low": True,
        "recent_price_direction": "down",
        "complaints": ("Fans can be loud under load", "Average webcam"),
        "strengths": (
            "Strong 1080p gaming",
            "Good DealScore under ₱60k",
            "Solid battery for a gaming laptop",
        ),
        "data_status": "mock",
    },
    {
        "product_id": "sa-laptop-nitro-v15",
        "product_name": "Acer Nitro V 15 i5 RTX 4050",
        "category": "laptop",
        "brand": "Acer",
        "known_price": 52999.0,
        "currency": "PHP",
        "marketplace": "Lazada",
        "deal_score": 84.0,
        "rating": 4.4,
        "review_count": 963,
        "use_cases": ("gaming",),
        "features": ("rtx 4050", "16gb ram", "512gb ssd"),
        "seller_name": "Acer LazMall",
        "seller_trust_score": 0.88,
        "price_near_low": False,
        "recent_price_direction": "stable",
        "complaints": ("Build feels plasticky", "Screen brightness is average"),
        "strengths": ("Lower known price", "Capable for esports and AAA at medium"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-laptop-loq-15",
        "product_name": "Lenovo LOQ 15 RTX 4060",
        "category": "laptop",
        "brand": "Lenovo",
        "known_price": 59999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 90.2,
        "rating": 4.7,
        "review_count": 1210,
        "use_cases": ("gaming", "content_creation"),
        "features": ("rtx 4060", "16gb ram", "512gb ssd", "mux switch"),
        "seller_name": "Lenovo Official PH",
        "seller_trust_score": 0.94,
        "price_near_low": True,
        "recent_price_direction": "down",
        "complaints": ("Heavier than ultraportables",),
        "strengths": ("Stronger GPU in budget", "Highest DealScore under ₱60k"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-laptop-macbook-air-m3",
        "product_name": "Apple MacBook Air M3 256GB Midnight",
        "category": "laptop",
        "brand": "Apple",
        "known_price": 62999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 82.0,
        "rating": 4.9,
        "review_count": 540,
        "use_cases": ("productivity", "photography", "battery_life"),
        "features": ("m3", "fanless", "retina", "long battery"),
        "seller_name": "Apple Authorized PH",
        "seller_trust_score": 0.97,
        "price_near_low": False,
        "recent_price_direction": "stable",
        "complaints": ("Not ideal for AAA gaming", "Base storage fills quickly"),
        "strengths": ("Excellent battery", "Quiet and light", "Strong photo editing"),
        "data_status": "mock",
    },
    {
        "product_id": IPHONE_DEMO_PRODUCT_ID,
        "product_name": IPHONE_DEMO_PRODUCT_LABEL,
        "category": "phone",
        "brand": "Apple",
        "known_price": 74999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 79.5,
        "rating": 4.64,
        "review_count": 43364,
        "use_cases": ("photography", "premium", "battery_life"),
        "features": ("camera", "battery", "a19", "titanium"),
        "seller_name": "Apple Authorized PH",
        "seller_trust_score": 0.97,
        "price_near_low": False,
        "recent_price_direction": "up",
        "complaints": ("Expensive", "Warms under heavy gaming"),
        "strengths": ("Excellent camera", "Long battery life", "Premium build"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-phone-galaxy-s25-ultra",
        "product_name": "Samsung Galaxy S25 Ultra 512GB",
        "category": "phone",
        "brand": "Samsung",
        "known_price": 64999.0,
        "currency": "PHP",
        "marketplace": "Lazada",
        "deal_score": 85.0,
        "rating": 4.6,
        "review_count": 8120,
        "use_cases": ("photography", "productivity", "gaming"),
        "features": ("camera", "s-pen", "battery", "zoom"),
        "seller_name": "Samsung Official Store",
        "seller_trust_score": 0.95,
        "price_near_low": True,
        "recent_price_direction": "down",
        "complaints": ("Large and heavy", "Accessories priced high"),
        "strengths": ("Versatile zoom camera", "S Pen productivity", "Strong DealScore"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-phone-iphone-16-pro",
        "product_name": "Apple iPhone 16 Pro 128GB White Titanium",
        "category": "phone",
        "brand": "Apple",
        "known_price": 58999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 83.0,
        "rating": 4.7,
        "review_count": 9200,
        "use_cases": ("photography", "premium"),
        "features": ("camera", "battery", "pro motion"),
        "seller_name": "GadgetHub Official",
        "seller_trust_score": 0.86,
        "price_near_low": False,
        "recent_price_direction": "stable",
        "complaints": ("128GB fills fast", "Price still premium"),
        "strengths": ("Strong camera", "Smooth performance"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-phone-pixel-9",
        "product_name": "Google Pixel 9 128GB",
        "category": "phone",
        "brand": "Google",
        "known_price": 42990.0,
        "currency": "PHP",
        "marketplace": "Lazada",
        "deal_score": 87.0,
        "rating": 4.5,
        "review_count": 2104,
        "use_cases": ("photography", "battery_life"),
        "features": ("camera", "computational photography", "clean android"),
        "seller_name": "MobileZone Official",
        "seller_trust_score": 0.81,
        "price_near_low": True,
        "recent_price_direction": "down",
        "complaints": ("Limited local service centers", "Average zoom"),
        "strengths": ("Excellent still photography", "Clean software", "Value DealScore"),
        "data_status": "mock",
    },
    {
        "product_id": "sa-earbuds-airpods-pro-2",
        "product_name": "Apple AirPods Pro 2 USB-C",
        "category": "earbuds",
        "brand": "Apple",
        "known_price": 12999.0,
        "currency": "PHP",
        "marketplace": "Shopee",
        "deal_score": 80.0,
        "rating": 4.8,
        "review_count": 6400,
        "use_cases": ("audio", "commute"),
        "features": ("anc", "usb-c", "spatial audio"),
        "seller_name": "AudioWorld Store",
        "seller_trust_score": 0.84,
        "price_near_low": False,
        "recent_price_direction": "stable",
        "complaints": ("Tips fit varies", "Pricey for earbuds"),
        "strengths": ("Strong ANC", "Convenient Apple ecosystem"),
        "data_status": "mock",
    },
]

DEMO_QUERIES: tuple[str, ...] = (
    "What is the best gaming laptop under ₱60,000?",
    "Compare iPhone 17 Pro Max and Galaxy S25 Ultra for camera and battery",
    "Is the ASUS TUF Gaming A15 worth buying?",
    "Which marketplace has the best offer for MacBook Air M3?",
    "What are the main complaints about Galaxy S25 Ultra?",
    "Should I buy the Lenovo LOQ 15 now or wait?",
    "Which product is better for gaming under 60000 PHP?",
    "Which product is best for photography under ₱50,000?",
    "Is the cheapest seller trustworthy for AirPods Pro 2?",
    "Recommend a laptop for my budget and needs under ₱60,000 for gaming",
)


def get_catalog() -> list[dict[str, Any]]:
    """Return a shallow copy of the mock shopping catalog."""
    return [dict(item) for item in SHOPPING_CATALOG]


def get_product_by_id(product_id: str) -> dict[str, Any] | None:
    cleaned = product_id.strip()
    for item in SHOPPING_CATALOG:
        if item["product_id"] == cleaned:
            return dict(item)
    return None


def get_product_by_name(name: str) -> dict[str, Any] | None:
    needle = name.strip().lower()
    if not needle:
        return None
    for item in SHOPPING_CATALOG:
        product_name = str(item["product_name"]).lower()
        if needle == product_name or needle in product_name:
            return dict(item)
    return None
