"""Launch-readiness guard: aggregate rating vs written-summary polarity."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.review_analysis import (
    ConsensusMetadata,
    EvidenceClaim,
    OrchestratedAnalysis,
    ProviderAnalysis,
)
from app.intelligence.review_summary import (
    DeterministicMockReviewSummarizer,
    InMemoryReviewSummaryRepository,
)
from app.intelligence.review_summary.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
)
from app.intelligence.reviews import (
    InMemoryReviewRepository,
    MockAmazonReviewCollector,
    MockLazadaReviewCollector,
    MockShopeeReviewCollector,
    MockTikTokShopReviewCollector,
)
from app.services.review_service import ReviewService
from app.services.review_summary_service import (
    CAUTIOUS_RECOMMENDATION_LABEL,
    SUMMARY_RATING_CONFLICT_WARNING,
    ReviewSummaryService,
    broad_sentiment_polarity,
    rating_polarity,
)

FIXED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


class _ScriptedReviewOrchestrator:
    def __init__(self, analysis: ProviderAnalysis, *, confidence: float = 0.88) -> None:
        self._analysis = analysis
        self._confidence = confidence

    def analyze(self, request, mode=None) -> OrchestratedAnalysis:
        consensus = ConsensusMetadata(
            mode="economy",
            providers_requested=1,
            providers_completed=1,
            agreement_score=1.0,
            consensus_confidence=self._confidence,
            provider_results=(self._analysis,),
            disagreements=(),
            fallback_used=False,
        )
        return OrchestratedAnalysis(
            analysis=self._analysis,
            consensus=consensus,
            generated_at=FIXED_NOW,
            providers_used=(self._analysis.provider,),
        )


def _review_service() -> ReviewService:
    counter = {"n": 0}

    def next_id() -> str:
        counter["n"] += 1
        return f"rv-conflict-{counter['n']}"

    return ReviewService(
        InMemoryReviewRepository(),
        [
            MockShopeeReviewCollector(),
            MockLazadaReviewCollector(),
            MockTikTokShopReviewCollector(),
            MockAmazonReviewCollector(),
        ],
        clock=lambda: FIXED_NOW,
        id_factory=next_id,
        seed_demo_history=False,
    )


def _service(orchestrator) -> ReviewSummaryService:
    return ReviewSummaryService(
        InMemoryReviewSummaryRepository(),
        DeterministicMockReviewSummarizer(),
        _review_service(),
        orchestrator=orchestrator,
        clock=lambda: FIXED_NOW,
        id_factory=lambda: "summary-conflict",
        auto_collect=True,
    )


def _analysis(*, sentiment: str, recommendation: str) -> ProviderAnalysis:
    return ProviderAnalysis(
        product_id=IPHONE_DEMO_PRODUCT_ID,
        overall_sentiment=sentiment,  # type: ignore[arg-type]
        summary="Buyers describe overheating and disappointing battery life.",
        pros=(),
        cons=(
            EvidenceClaim(
                claim="Warms under heavy gaming",
                evidence_review_ids=("rv-004",),
                confidence=0.8,
            ),
        ),
        warnings=(),
        recommendation=recommendation,  # type: ignore[arg-type]
        confidence=0.88,
        provider="scripted",
        model="scripted-v1",
    )


def test_broad_polarity_collapses_positive_variants() -> None:
    assert broad_sentiment_polarity("positive") == "positive"
    assert broad_sentiment_polarity("very_positive") == "positive"
    assert broad_sentiment_polarity("Very Positive") == "positive"
    assert broad_sentiment_polarity("mixed") == "mixed"
    assert broad_sentiment_polarity("Negative") == "negative"
    assert rating_polarity(4.7) == "positive"
    assert rating_polarity(4.2) == "positive"
    assert rating_polarity(4.0) == "mixed"
    assert rating_polarity(3.2) == "negative"
    assert rating_polarity(None) is None


def test_high_rating_negative_written_summary_is_surfaced() -> None:
    service = _service(
        _ScriptedReviewOrchestrator(
            _analysis(sentiment="negative", recommendation="not_recommended")
        )
    )
    summary = service.summarize(IPHONE_DEMO_PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)
    assert summary.average_rating is not None
    assert rating_polarity(summary.average_rating) == "positive"
    assert summary.overall_sentiment == "Negative"
    assert summary.processing.get("summary_rating_conflict") is True
    assert any(item.field == "summary_rating" for item in summary.disagreements)
    conflict = next(item for item in summary.disagreements if item.field == "summary_rating")
    assert "Negative" in conflict.values
    assert any(value.startswith("4.") for value in conflict.values)
    assert "neither signal is automatically treated as correct" in conflict.detail.lower()
    assert any(item.message == SUMMARY_RATING_CONFLICT_WARNING for item in summary.warnings)
    assert summary.recommendation.label == CAUTIOUS_RECOMMENDATION_LABEL
    assert summary.consensus_confidence is not None
    assert summary.consensus_confidence <= 0.60
    blob = str(summary.to_dict()).lower()
    assert "fake review" not in blob
    assert "fake reviews" not in blob


def test_aligned_high_rating_positive_summary_is_unchanged() -> None:
    service = _service(
        _ScriptedReviewOrchestrator(
            _analysis(sentiment="very_positive", recommendation="highly_recommended")
        )
    )
    summary = service.summarize(IPHONE_DEMO_PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)
    assert summary.average_rating is not None
    assert rating_polarity(summary.average_rating) == "positive"
    assert summary.overall_sentiment == "Very Positive"
    assert summary.processing.get("summary_rating_conflict") is False
    assert all(item.field != "summary_rating" for item in summary.disagreements)
    assert all(item.message != SUMMARY_RATING_CONFLICT_WARNING for item in summary.warnings)
    assert summary.recommendation.label == "Highly Recommended"
    assert summary.consensus_confidence == 0.88


def test_positive_versus_very_positive_is_not_a_conflict() -> None:
    service = _service(
        _ScriptedReviewOrchestrator(_analysis(sentiment="positive", recommendation="recommended"))
    )
    summary = service.summarize(IPHONE_DEMO_PRODUCT_ID, product_label=IPHONE_DEMO_PRODUCT_LABEL)
    assert summary.processing.get("summary_rating_conflict") is False
    assert summary.overall_sentiment == "Positive"
    assert summary.recommendation.label == "Recommended"
    assert summary.consensus_confidence == 0.88
