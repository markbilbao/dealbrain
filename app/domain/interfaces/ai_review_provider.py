"""Provider-neutral port for multi-model review analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.review_analysis import ProviderAnalysis, ReviewAnalysisRequest


class AIReviewProvider(ABC):
    """Abstract contract for OpenAI / Claude / Gemini / deterministic adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider id: openai | anthropic | gemini | deterministic."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model identifier (never a secret)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider can accept work (keys, config, health)."""

    @abstractmethod
    def analyze_reviews(self, request: ReviewAnalysisRequest) -> ProviderAnalysis:
        """Analyze reviews and return normalized structured output.

        Implementations must not fabricate review facts. Claims must cite
        ``evidence_review_ids`` present in ``request.reviews``.
        """
