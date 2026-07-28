"""Mock TikTok Shop review collector — canned fixtures only."""

from __future__ import annotations

from app.intelligence.reviews.base import BaseMockReviewCollector
from app.intelligence.reviews.fixtures import MOCK_REVIEW_FIXTURES


class MockTikTokShopReviewCollector(BaseMockReviewCollector):
    """Development-only TikTok Shop review collector."""

    def __init__(self) -> None:
        super().__init__("TikTok Shop", MOCK_REVIEW_FIXTURES["TikTok Shop"])
