"""Recommendation Engine port — deterministic buying advice from DealScore rankings."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.deal_score import RankingResult
from app.domain.entities.recommendation import Recommendation


class RecommendationEngine(ABC):
    """Abstract contract for explainable purchase recommendations.

    Implementations must be deterministic and must not depend on LLMs,
    live marketplace APIs, or invented price-history claims.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Human-readable engine identifier."""

    @abstractmethod
    def recommend(self, ranking: RankingResult) -> Recommendation:
        """Convert a DealScore ranking into a purchase recommendation."""
