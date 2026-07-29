"""Deterministic community fixtures for Community Intelligence Platform v1.

DEVELOPMENT MOCK DATA — NOT LIVE COMMUNITY CONTENT
==================================================

Canned Reddit / YouTube / Q&A / forum discussions only.
Never contacts external networks unless a live transport is explicitly wired.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.intelligence.reviews.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.intelligence.shopping_assistant.fixtures import SHOPPING_CATALOG

__all__ = [
    "IPHONE_DEMO_PRODUCT_ID",
    "IPHONE_DEMO_PRODUCT_LABEL",
    "DEMO_PRODUCT_ID",
    "DEMO_PRODUCT_LABEL",
    "COMMUNITY_PRODUCTS",
    "REDDIT_FIXTURES",
    "YOUTUBE_FIXTURES",
    "AMAZON_QA_FIXTURES",
    "MARKETPLACE_QA_FIXTURES",
    "FORUM_FIXTURES",
    "DISCORD_FIXTURES",
    "get_product_meta",
    "list_demo_product_ids",
    "fixture_timestamp",
]

DEMO_PRODUCT_ID = "sa-laptop-tuf-a15"
DEMO_PRODUCT_LABEL = "ASUS TUF Gaming A15 Ryzen 7 RTX 4050"

_BASE = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


def fixture_timestamp(days_ago: int = 0, hours_ago: int = 0) -> datetime:
    return _BASE - timedelta(days=days_ago, hours=hours_ago)


COMMUNITY_PRODUCTS: dict[str, dict[str, str]] = {
    DEMO_PRODUCT_ID: {
        "product_id": DEMO_PRODUCT_ID,
        "product_name": DEMO_PRODUCT_LABEL,
    },
    "sa-laptop-nitro-v15": {
        "product_id": "sa-laptop-nitro-v15",
        "product_name": "Acer Nitro V 15 i5 RTX 4050",
    },
    "sa-laptop-loq-15": {
        "product_id": "sa-laptop-loq-15",
        "product_name": "Lenovo LOQ 15 RTX 4060",
    },
    IPHONE_DEMO_PRODUCT_ID: {
        "product_id": IPHONE_DEMO_PRODUCT_ID,
        "product_name": IPHONE_DEMO_PRODUCT_LABEL,
    },
    "iphone-17-pro-max": {
        "product_id": IPHONE_DEMO_PRODUCT_ID,
        "product_name": IPHONE_DEMO_PRODUCT_LABEL,
    },
}

for item in SHOPPING_CATALOG:
    pid = str(item["product_id"])
    COMMUNITY_PRODUCTS.setdefault(
        pid,
        {"product_id": pid, "product_name": str(item["product_name"])},
    )


def get_product_meta(product_id: str, product_label: str | None = None) -> dict[str, str]:
    cleaned = product_id.strip()
    if cleaned in COMMUNITY_PRODUCTS:
        return dict(COMMUNITY_PRODUCTS[cleaned])
    if product_label:
        return {"product_id": cleaned, "product_name": product_label}
    return {"product_id": cleaned, "product_name": cleaned}


def list_demo_product_ids() -> list[str]:
    return [DEMO_PRODUCT_ID, "sa-laptop-nitro-v15", "sa-laptop-loq-15", IPHONE_DEMO_PRODUCT_ID]


# ---------------------------------------------------------------------------
# Reddit (full connector fixtures)
# ---------------------------------------------------------------------------

REDDIT_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "thread_id": "r_tuf_battery_1",
            "title": "TUF A15 battery life after 3 months?",
            "body": (
                "Battery lasts about 6 hours for browsing and light work. "
                "Gaming drains it fast but that is expected. Overall battery is solid for a gaming laptop."
            ),
            "subreddit": "ASUS",
            "author": "gamer_ph",
            "upvotes": 142,
            "comment_count": 38,
            "permalink": "https://reddit.com/r/ASUS/comments/tuf_battery_1",
            "url": "https://reddit.com/r/ASUS/comments/tuf_battery_1",
            "created_utc": fixture_timestamp(12).timestamp(),
            "comments": [
                {
                    "comment_id": "r_tuf_battery_1_c1",
                    "author": "battery_fan",
                    "body": "Agreed — battery is surprisingly good for RTX 4050 class.",
                    "upvotes": 44,
                    "created_utc": fixture_timestamp(11).timestamp(),
                },
                {
                    "comment_id": "r_tuf_battery_1_c2",
                    "author": "skeptic_user",
                    "body": "Mine gets warm on the keyboard deck under load.",
                    "upvotes": 19,
                    "created_utc": fixture_timestamp(10).timestamp(),
                },
            ],
        },
        {
            "thread_id": "r_tuf_gaming_1",
            "title": "ASUS TUF A15 for 1080p gaming — worth it?",
            "body": (
                "Performance is excellent at 1080p. RTX 4050 handles modern titles well. "
                "Fans get loud (noise) during long sessions. Display is decent 144Hz."
            ),
            "subreddit": "GamingLaptops",
            "author": "fps_hunter",
            "upvotes": 210,
            "comment_count": 67,
            "permalink": "https://reddit.com/r/GamingLaptops/comments/tuf_gaming_1",
            "url": "https://reddit.com/r/GamingLaptops/comments/tuf_gaming_1",
            "created_utc": fixture_timestamp(20).timestamp(),
            "comments": [
                {
                    "comment_id": "r_tuf_gaming_1_c1",
                    "author": "value_buyer",
                    "body": "Great value under 60k PHP. Price is hard to beat.",
                    "upvotes": 55,
                    "created_utc": fixture_timestamp(19).timestamp(),
                },
            ],
        },
        {
            "thread_id": "r_tuf_heat_1",
            "title": "Heat and thermals on TUF A15",
            "body": (
                "Heat is manageable with a cooling pad. Without one the chassis gets hot. "
                "Performance stays consistent though — no major throttling."
            ),
            "subreddit": "ASUS",
            "author": "thermal_nerd",
            "upvotes": 88,
            "comment_count": 24,
            "permalink": "https://reddit.com/r/ASUS/comments/tuf_heat_1",
            "url": "https://reddit.com/r/ASUS/comments/tuf_heat_1",
            "created_utc": fixture_timestamp(5).timestamp(),
            "comments": [],
        },
        {
            "thread_id": "r_tuf_warranty_1",
            "title": "Warranty experience with ASUS PH",
            "body": (
                "Customer service took two weeks for an RMA. Warranty coverage was honored "
                "but shipping back and forth was slow."
            ),
            "subreddit": "Philippines",
            "author": "support_seeker",
            "upvotes": 36,
            "comment_count": 12,
            "permalink": "https://reddit.com/r/Philippines/comments/tuf_warranty_1",
            "url": "https://reddit.com/r/Philippines/comments/tuf_warranty_1",
            "created_utc": fixture_timestamp(30).timestamp(),
            "comments": [],
        },
        {
            "thread_id": "r_tuf_software_1",
            "title": "Armoury Crate / software bloat on TUF",
            "body": (
                "Software is the weak point. Armoury Crate is heavy. Firmware updates fixed "
                "a few fan curve issues. Compatibility with Linux is mixed."
            ),
            "subreddit": "ASUS",
            "author": "linux_try",
            "upvotes": 71,
            "comment_count": 29,
            "permalink": "https://reddit.com/r/ASUS/comments/tuf_software_1",
            "url": "https://reddit.com/r/ASUS/comments/tuf_software_1",
            "created_utc": fixture_timestamp(8).timestamp(),
            "comments": [],
        },
    ],
    "sa-laptop-nitro-v15": [
        {
            "thread_id": "r_nitro_value_1",
            "title": "Acer Nitro V15 vs TUF — value?",
            "body": "Lower price, plasticky build, average display brightness. Gaming performance is close.",
            "subreddit": "GamingLaptops",
            "author": "budget_gamer",
            "upvotes": 95,
            "comment_count": 41,
            "permalink": "https://reddit.com/r/GamingLaptops/comments/nitro_value_1",
            "url": "https://reddit.com/r/GamingLaptops/comments/nitro_value_1",
            "created_utc": fixture_timestamp(15).timestamp(),
            "comments": [],
        },
    ],
    "sa-laptop-loq-15": [
        {
            "thread_id": "r_loq_perf_1",
            "title": "Lenovo LOQ 15 RTX 4060 performance",
            "body": "Performance headroom with 4060 is great. Battery is weaker. Durability feels solid.",
            "subreddit": "Lenovo",
            "author": "loq_owner",
            "upvotes": 120,
            "comment_count": 33,
            "permalink": "https://reddit.com/r/Lenovo/comments/loq_perf_1",
            "url": "https://reddit.com/r/Lenovo/comments/loq_perf_1",
            "created_utc": fixture_timestamp(9).timestamp(),
            "comments": [],
        },
    ],
    IPHONE_DEMO_PRODUCT_ID: [
        {
            "thread_id": "r_iphone_camera_1",
            "title": "iPhone 17 Pro Max camera impressions",
            "body": "Camera is excellent in low light. Battery easily lasts a full day. Price is steep but value for creators.",
            "subreddit": "iphone",
            "author": "photo_phile",
            "upvotes": 420,
            "comment_count": 110,
            "permalink": "https://reddit.com/r/iphone/comments/iphone_camera_1",
            "url": "https://reddit.com/r/iphone/comments/iphone_camera_1",
            "created_utc": fixture_timestamp(3).timestamp(),
            "comments": [
                {
                    "comment_id": "r_iphone_camera_1_c1",
                    "author": "creator_x",
                    "body": "Display and camera combo is best in class.",
                    "upvotes": 88,
                    "created_utc": fixture_timestamp(2).timestamp(),
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# YouTube (mock adapter fixtures)
# ---------------------------------------------------------------------------

YOUTUBE_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "video_id": "yt_tuf_review_8",
            "title": "ASUS TUF A15 Full Review — Gaming & Battery",
            "creator": "TechBench PH",
            "likes": 3200,
            "views": 185000,
            "publish_date": fixture_timestamp(40).isoformat(),
            "summary": "Praises gaming performance and battery for the class; notes fan noise and heat.",
            "transcript_excerpt": (
                "The battery surprised me for a gaming laptop. Performance is strong at 1080p. "
                "Noise under load is the main complaint."
            ),
            "url": "https://youtube.com/watch?v=yt_tuf_review_8",
        },
        {
            "video_id": "yt_tuf_thermals_2",
            "title": "TUF A15 Thermal Test",
            "creator": "CoolLab",
            "likes": 980,
            "views": 42000,
            "publish_date": fixture_timestamp(18).isoformat(),
            "summary": "Heat is acceptable with undervolt; packaging accessories are basic.",
            "transcript_excerpt": "Heat peaks near 90C GPU. Accessories in the box are minimal.",
            "url": "https://youtube.com/watch?v=yt_tuf_thermals_2",
        },
    ],
    IPHONE_DEMO_PRODUCT_ID: [
        {
            "video_id": "yt_iphone_cam_1",
            "title": "iPhone 17 Pro Max Camera Test",
            "creator": "LensDaily",
            "likes": 12000,
            "views": 900000,
            "publish_date": fixture_timestamp(7).isoformat(),
            "summary": "Camera and display excellence; discusses price and value.",
            "transcript_excerpt": "Camera is excellent. Price remains the barrier for many buyers.",
            "url": "https://youtube.com/watch?v=yt_iphone_cam_1",
        },
    ],
}

# ---------------------------------------------------------------------------
# Amazon Q&A
# ---------------------------------------------------------------------------

AMAZON_QA_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "qa_id": "amz_q_15",
            "question": "How is the battery for school use?",
            "answer": "Battery lasts a full class day for notes and browsing. Gaming needs the charger.",
            "helpful_votes": 64,
            "asked_at": fixture_timestamp(25).isoformat(),
            "url": "https://amazon.example/qa/amz_q_15",
        },
        {
            "qa_id": "amz_q_22",
            "question": "Is shipping packaging secure?",
            "answer": "Packaging was solid; no damage. Shipping took 4 days.",
            "helpful_votes": 21,
            "asked_at": fixture_timestamp(14).isoformat(),
            "url": "https://amazon.example/qa/amz_q_22",
        },
    ],
}

# ---------------------------------------------------------------------------
# Marketplace questions
# ---------------------------------------------------------------------------

MARKETPLACE_QA_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "question_id": "mp_q_1",
            "question": "Does this include warranty for PH buyers?",
            "seller_response": "Yes, 2-year local warranty via official store.",
            "community_responses": [
                "Warranty claim was honored but slow.",
                "Seller confirmed international adapters not included.",
            ],
            "asked_at": fixture_timestamp(6).isoformat(),
            "url": "https://marketplace.example/q/mp_q_1",
        },
        {
            "question_id": "mp_q_2",
            "question": "Compatibility with external monitors?",
            "seller_response": "HDMI and USB-C DP supported.",
            "community_responses": ["Compatibility with 144Hz monitors works over HDMI."],
            "asked_at": fixture_timestamp(4).isoformat(),
            "url": "https://marketplace.example/q/mp_q_2",
        },
    ],
}

# ---------------------------------------------------------------------------
# Manufacturer forums
# ---------------------------------------------------------------------------

FORUM_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "thread_id": "forum_fw_1",
            "title": "Firmware 3.2 fan curve update",
            "discussion": "Firmware update improved noise under light load. Accepted answer confirms reboot required.",
            "replies": [
                {"author": "mod_asus", "body": "Accepted: install firmware then reboot.", "accepted": True},
                {"author": "user_a", "body": "Noise is better after firmware update.", "accepted": False},
            ],
            "created_at": fixture_timestamp(16).isoformat(),
            "url": "https://forum.asus.example/t/forum_fw_1",
        },
    ],
}

# ---------------------------------------------------------------------------
# Discord (architecture only — disabled fixtures exist for tests)
# ---------------------------------------------------------------------------

DISCORD_FIXTURES: dict[str, list[dict[str, Any]]] = {
    DEMO_PRODUCT_ID: [
        {
            "message_id": "dc_msg_1",
            "channel": "laptop-advice",
            "author": "helper_bot",
            "body": "TUF A15 is fine for gaming; watch heat and noise.",
            "created_at": fixture_timestamp(2).isoformat(),
            "url": "https://discord.example/channels/laptop-advice/dc_msg_1",
        },
    ],
}
