"""Mock Lazada review collector — canned fixtures only."""

from __future__ import annotations

from app.intelligence.reviews.base import BaseMockReviewCollector
from app.intelligence.reviews.fixtures import MOCK_REVIEW_FIXTURES


class MockLazadaReviewCollector(BaseMockReviewCollector):
    """Development-only Lazada review collector."""

    def __init__(self) -> None:
        super().__init__("Lazada", MOCK_REVIEW_FIXTURES["Lazada"])
