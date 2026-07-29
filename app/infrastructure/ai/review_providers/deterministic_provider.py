"""Deterministic review provider — always-available fallback (no external AI)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.review_analysis import (
    DISPLAY_TO_RECOMMENDATION,
    DISPLAY_TO_SENTIMENT,
    EvidenceClaim,
    ProviderAnalysis,
    ReviewAnalysisRequest,
)
from app.domain.interfaces.ai_review_provider import AIReviewProvider
from app.intelligence.review_summary.deterministic import DeterministicMockReviewSummarizer
from app.intelligence.review_summary.fixtures import THEME_LEXICON


class DeterministicReviewProvider(AIReviewProvider):
    """Wraps Sprint 12 deterministic summarizer into the multi-model schema."""

    def __init__(self, summarizer: DeterministicMockReviewSummarizer | None = None) -> None:
        self._summarizer = summarizer or DeterministicMockReviewSummarizer()

    @property
    def provider_name(self) -> str:
        return "deterministic"

    @property
    def model_name(self) -> str:
        return "deterministic-mock-v1"

    def is_available(self) -> bool:
        return True

    def analyze_reviews(self, request: ReviewAnalysisRequest) -> ProviderAnalysis:
        texts = [item.text for item in request.reviews]
        summary = self._summarizer.summarize(
            product_id=request.product_id,
            product=request.product,
            review_texts=texts,
            average_rating=request.average_rating,
            total_review_count=request.total_review_count,
            summary_id="deterministic",
            generated_at=datetime.now(UTC),
        )
        id_by_text = {item.text: item.review_id for item in request.reviews}

        def claims_for(labels: list[str], polarity: str) -> tuple[EvidenceClaim, ...]:
            built: list[EvidenceClaim] = []
            for label in labels:
                evidence_ids = self._evidence_ids_for_label(label, polarity, request, id_by_text)
                if not evidence_ids:
                    continue
                built.append(
                    EvidenceClaim(
                        claim=label,
                        evidence_review_ids=tuple(evidence_ids),
                        confidence=min(0.95, 0.55 + 0.08 * len(evidence_ids)),
                    )
                )
            return tuple(built)

        sentiment = DISPLAY_TO_SENTIMENT.get(
            summary.overall_sentiment,
            "mixed",
        )
        recommendation = DISPLAY_TO_RECOMMENDATION.get(
            summary.recommendation.label,
            "consider_alternatives",
        )
        return ProviderAnalysis(
            product_id=request.product_id,
            overall_sentiment=sentiment,  # type: ignore[arg-type]
            summary=summary.summary,
            pros=claims_for(list(summary.pros.items), "pro"),
            cons=claims_for(list(summary.cons.items), "con"),
            warnings=claims_for([w.message for w in summary.warnings], "warning"),
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=0.72 if sentiment == "very_positive" else 0.65,
            provider=self.provider_name,
            model=self.model_name,
            status="ok",
        )

    def _evidence_ids_for_label(
        self,
        label: str,
        polarity: str,
        request: ReviewAnalysisRequest,
        id_by_text: dict[str, str],
    ) -> list[str]:
        keywords = [
            keyword
            for keyword, (pol, lbl) in THEME_LEXICON.items()
            if pol == polarity and lbl == label
        ]
        hits: list[str] = []
        for item in request.reviews:
            lowered = item.text.lower()
            if any(keyword in lowered for keyword in keywords) or label.lower() in lowered:
                hits.append(id_by_text[item.text])
        return hits[:5]
