"""AI Review Summary application service.

Reads Sprint 11 Review Intelligence outputs and runs multi-model review
analysis (deterministic fallback by default). External AI calls remain off
unless explicitly enabled in server configuration.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.entities.review_analysis import (
    RECOMMENDATION_DISPLAY,
    SENTIMENT_DISPLAY,
    OrchestratedAnalysis,
    ReviewAnalysisRequest,
)
from app.domain.entities.review_summary import (
    Cons,
    Pros,
    Recommendation,
    ReviewInsight,
    ReviewSummary,
    Warning,
)
from app.domain.exceptions import (
    ReviewNotFoundError,
    ReviewSummaryNotFoundError,
    ReviewSummaryValidationError,
)
from app.domain.interfaces.review_summary_repository import (
    ReviewSummarizer,
    ReviewSummaryRepository,
)
from app.intelligence.review_summary.fixtures import (
    IPHONE_DEMO_PRODUCT_ID,
    IPHONE_DEMO_PRODUCT_LABEL,
    get_mock_review_texts,
    resolve_product_label,
)
from app.intelligence.review_summary.orchestrator import MultiModelReviewOrchestrator
from app.intelligence.review_summary.validator import build_review_evidence
from app.services.review_service import ReviewService


class ReviewSummaryService:
    """Orchestrate review summarization with optional multi-model providers."""

    def __init__(
        self,
        repository: ReviewSummaryRepository,
        summarizer: ReviewSummarizer,
        review_service: ReviewService,
        *,
        orchestrator: MultiModelReviewOrchestrator | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        auto_collect: bool = True,
        max_review_input: int = 40,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._repository = repository
        self._summarizer = summarizer
        self._review_service = review_service
        self._orchestrator = orchestrator
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._auto_collect = auto_collect
        self._max_review_input = max_review_input
        self._timeout_seconds = timeout_seconds

    def summarize(
        self,
        product_id: str,
        *,
        product_label: str | None = None,
        force_refresh: bool = True,
        mode: str | None = None,
    ) -> ReviewSummary:
        cleaned = self._require_product_id(product_id)
        label = resolve_product_label(cleaned, product_label)

        if not force_refresh and mode is None:
            cached = self._repository.get_by_product_id(cleaned)
            if cached is not None:
                return cached

        average_rating, total_reviews, label = self._load_review_stats(
            cleaned,
            label=label,
        )
        texts = list(get_mock_review_texts(cleaned)[: self._max_review_input])

        if self._orchestrator is not None:
            evidence = build_review_evidence(texts)
            request = ReviewAnalysisRequest(
                product_id=cleaned,
                product=label,
                reviews=evidence,
                average_rating=average_rating,
                total_review_count=total_reviews,
                timeout_seconds=self._timeout_seconds,
            )
            try:
                orchestrated = self._orchestrator.analyze(request, mode=mode)
            except ValueError as exc:
                raise ReviewSummaryValidationError(str(exc)) from exc
            summary = self._from_orchestration(
                orchestrated,
                product=label,
                average_rating=average_rating,
                total_review_count=total_reviews,
            )
            return self._repository.save(summary)

        # Legacy deterministic path (no orchestrator injected).
        summary = self._summarizer.summarize(
            product_id=cleaned,
            product=label,
            review_texts=texts,
            average_rating=average_rating,
            total_review_count=total_reviews,
            summary_id=self._id_factory(),
            generated_at=self._clock(),
        )
        enriched = ReviewSummary(
            summary_id=summary.summary_id,
            product_id=summary.product_id,
            product=summary.product,
            overall_sentiment=summary.overall_sentiment,
            summary=summary.summary,
            pros=summary.pros,
            cons=summary.cons,
            warnings=summary.warnings,
            recommendation=summary.recommendation,
            insights=summary.insights,
            average_rating=summary.average_rating,
            total_review_count=summary.total_review_count,
            provider=summary.provider,
            generated_at=summary.generated_at,
            mode="economy",
            providers_used=(summary.provider,),
            models_used=("deterministic-mock-v1",),
            fallback_used=True,
            fallback_reason="orchestrator_not_configured",
            consensus_confidence=0.72,
            processing={"ai_review_enabled": False},
        )
        return self._repository.save(enriched)

    def get_summary(self, product_id: str, *, mode: str | None = None) -> ReviewSummary:
        cleaned = self._require_product_id(product_id)
        if mode is None:
            cached = self._repository.get_by_product_id(cleaned)
            if cached is not None:
                return cached
        return self.summarize(cleaned, force_refresh=True, mode=mode)

    def demo_summary(self, *, mode: str | None = None) -> ReviewSummary:
        """Return the canned iPhone demo summary (auto-collects ratings)."""
        return self.summarize(
            IPHONE_DEMO_PRODUCT_ID,
            product_label=IPHONE_DEMO_PRODUCT_LABEL,
            force_refresh=True,
            mode=mode,
        )

    def _from_orchestration(
        self,
        orchestrated: OrchestratedAnalysis,
        *,
        product: str,
        average_rating: float | None,
        total_review_count: int,
    ) -> ReviewSummary:
        analysis = orchestrated.analysis
        consensus = orchestrated.consensus
        sentiment = SENTIMENT_DISPLAY.get(
            analysis.overall_sentiment,
            analysis.overall_sentiment.replace("_", " ").title(),
        )
        recommendation = RECOMMENDATION_DISPLAY.get(
            analysis.recommendation,
            analysis.recommendation.replace("_", " ").title(),
        )
        insights = tuple(
            ReviewInsight(
                theme=claim.claim,
                label=claim.claim,
                polarity=polarity,
                frequency=len(claim.evidence_review_ids),
            )
            for polarity, claims in (
                ("pro", analysis.pros),
                ("con", analysis.cons),
                ("warning", analysis.warnings),
            )
            for claim in claims
        )
        models = tuple(
            dict.fromkeys(
                item.model
                for item in consensus.provider_results
                if item.status == "ok" and item.model
            )
        )
        processing = {
            "providers_requested": consensus.providers_requested,
            "providers_completed": consensus.providers_completed,
            "fallback_reason": consensus.fallback_reason,
            # Explicitly exclude prompts, API keys, and raw provider errors.
            "secrets_included": False,
            "prompts_included": False,
        }
        return ReviewSummary(
            summary_id=self._id_factory(),
            product_id=analysis.product_id,
            product=product,
            overall_sentiment=sentiment,
            summary=analysis.summary,
            pros=Pros(items=tuple(claim.claim for claim in analysis.pros)),
            cons=Cons(items=tuple(claim.claim for claim in analysis.cons)),
            warnings=tuple(Warning(message=claim.claim) for claim in analysis.warnings),
            recommendation=Recommendation(label=recommendation),
            insights=insights,
            average_rating=average_rating,
            total_review_count=total_review_count,
            provider=analysis.provider,
            generated_at=orchestrated.generated_at,
            mode=consensus.mode,
            providers_used=orchestrated.providers_used,
            models_used=models,
            fallback_used=consensus.fallback_used,
            fallback_reason=consensus.fallback_reason,
            agreement_score=(
                consensus.agreement_score
                if consensus.mode in {"balanced", "maximum"}
                else None
            ),
            consensus_confidence=consensus.consensus_confidence,
            disagreements=consensus.disagreements,
            evidence_pros=analysis.pros,
            evidence_cons=analysis.cons,
            evidence_warnings=analysis.warnings,
            processing=processing,
        )

    def _load_review_stats(
        self,
        product_id: str,
        *,
        label: str,
    ) -> tuple[float | None, int, str]:
        try:
            comparison = self._review_service.compare_marketplaces(product_id)
        except ReviewNotFoundError:
            if not self._auto_collect:
                raise ReviewSummaryNotFoundError(product_id) from None
            collected = self._review_service.collect_reviews(
                product_id,
                product_label=label,
            )
            comparison = self._review_service.compare_marketplaces(collected.product_id)
            label = collected.product

        if comparison.product:
            label = comparison.product
        return comparison.overall_rating, comparison.total_review_count, label

    def _require_product_id(self, product_id: str) -> str:
        cleaned = product_id.strip()
        if not cleaned:
            raise ReviewSummaryValidationError("product_id must not be blank.")
        return cleaned
