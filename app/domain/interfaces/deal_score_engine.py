"""DealScore Engine port — deterministic deal evaluation and ranking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.entities.deal_score import RankingResult, ScoreableListing


class DealScoreEngine(ABC):
    """Abstract contract for explainable DealScore evaluation.

    Implementations must be deterministic and must not depend on LLMs.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Human-readable engine identifier."""

    @abstractmethod
    def rank(self, query: str, listings: Sequence[ScoreableListing]) -> RankingResult:
        """Evaluate every listing and return rankings from best to worst."""
