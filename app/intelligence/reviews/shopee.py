"""Mock Shopee review collector — canned fixtures only."""

from __future__ import annotations

from app.intelligence.reviews.base import BaseMockReviewCollector
from app.intelligence.reviews.fixtures import MOCK_REVIEW_FIXTURES


class MockShopeeReviewCollector(BaseMockReviewCollector):
    """Development-only Shopee review collector."""

    def __init__(self) -> None:
        super().__init__("Shopee", MOCK_REVIEW_FIXTURES["Shopee"])
