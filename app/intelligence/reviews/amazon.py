"""Mock Amazon review collector — canned fixtures only."""

from __future__ import annotations

from app.intelligence.reviews.base import BaseMockReviewCollector
from app.intelligence.reviews.fixtures import MOCK_REVIEW_FIXTURES


class MockAmazonReviewCollector(BaseMockReviewCollector):
    """Development-only Amazon review collector."""

    def __init__(self) -> None:
        super().__init__("Amazon", MOCK_REVIEW_FIXTURES["Amazon"])
