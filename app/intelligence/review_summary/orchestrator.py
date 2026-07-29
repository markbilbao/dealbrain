"""Multi-model review analysis orchestrator (economy / balanced / maximum)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.entities.review_analysis import (
    MODE_RANK,
    AnalysisMode,
    ConsensusMetadata,
    OrchestratedAnalysis,
    ProviderAnalysis,
    ReviewAnalysisRequest,
)
from app.intelligence.review_summary.consensus import ConsensusService
from app.intelligence.review_summary.health import ProviderHealthService
from app.intelligence.review_summary.registry import AIProviderRegistry
from app.intelligence.review_summary.validator import ReviewAnalysisValidator


class MultiModelReviewOrchestrator:
    """Coordinate providers under server-side mode / cost restrictions."""

    def __init__(
        self,
        registry: AIProviderRegistry,
        validator: ReviewAnalysisValidator | None = None,
        consensus: ConsensusService | None = None,
        health: ProviderHealthService | None = None,
        *,
        ai_review_enabled: bool = False,
        configured_mode: AnalysisMode = "economy",
        allow_client_mode: bool = True,
        primary_provider: str = "openai",
        secondary_provider: str = "anthropic",
        max_estimated_cost: float = 0.05,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._registry = registry
        self._validator = validator or ReviewAnalysisValidator()
        self._consensus = consensus or ConsensusService()
        self._health = health or ProviderHealthService(registry.all())
        self._ai_review_enabled = ai_review_enabled
        self._configured_mode = configured_mode
        self._allow_client_mode = allow_client_mode
        self._primary = primary_provider
        self._secondary = secondary_provider
        self._max_cost = max_estimated_cost
        self._clock = clock or (lambda: datetime.now(UTC))

    def resolve_mode(self, requested: str | None) -> AnalysisMode:
        """Client mode may only downgrade/stay within server-configured mode."""
        configured = self._configured_mode
        if not self._ai_review_enabled:
            return "economy"
        if not requested or not self._allow_client_mode:
            return configured
        cleaned = requested.strip().lower()
        if cleaned not in MODE_RANK:
            raise ValueError(f"Unsupported analysis mode: {requested}")
        if MODE_RANK[cleaned] > MODE_RANK[configured]:
            # Do not allow bypassing server cost / mode ceiling.
            return configured
        return cleaned  # type: ignore[return-value]

    def analyze(
        self,
        request: ReviewAnalysisRequest,
        *,
        mode: str | None = None,
    ) -> OrchestratedAnalysis:
        resolved = self.resolve_mode(mode)
        if not self._ai_review_enabled:
            return self._deterministic_only(
                request,
                mode=resolved,
                fallback_used=True,
                fallback_reason="ai_review_disabled",
            )

        if resolved == "economy":
            return self._run_economy(request)
        if resolved == "balanced":
            return self._run_balanced(request)
        return self._run_maximum(request)

    def health_snapshot(self) -> list[dict]:
        return [item.to_dict() for item in self._health.snapshot()]

    def _run_economy(self, request: ReviewAnalysisRequest) -> OrchestratedAnalysis:
        order = [self._primary, *self._registry.fallback_order()]
        names: list[str] = []
        seen: set[str] = set()
        for name in order:
            if name not in seen:
                seen.add(name)
                names.append(name)
        attempted: list[ProviderAnalysis] = []
        for name in names:
            provider = self._registry.get(name)
            if provider is None:
                continue
            if name != "deterministic" and not provider.is_available():
                attempted.append(
                    ProviderAnalysis(
                        product_id=request.product_id,
                        overall_sentiment="mixed",
                        summary="",
                        pros=(),
                        cons=(),
                        warnings=(),
                        recommendation="consider_alternatives",
                        confidence=0.0,
                        provider=name,
                        model=provider.model_name,
                        status="unavailable",
                        error_code="unavailable",
                    )
                )
                continue
            raw = provider.analyze_reviews(request)
            validated = self._validator.validate(raw, request)
            attempted.append(validated)
            if validated.status == "ok":
                if self._exceeds_cost(validated):
                    continue
                fallback_used = name == "deterministic" and self._primary != "deterministic"
                merged, meta = self._consensus.build(
                    mode="economy",
                    analyses=attempted,
                    fallback_used=fallback_used,
                    fallback_reason="primary_unavailable" if fallback_used else None,
                )
                # Prefer the successful analysis itself for economy.
                return OrchestratedAnalysis(
                    analysis=validated if not fallback_used else merged,
                    consensus=meta,
                    generated_at=self._clock(),
                    providers_used=(validated.provider,),
                )

        return self._deterministic_only(
            request,
            mode="economy",
            fallback_used=True,
            fallback_reason="all_external_providers_failed",
            prior=attempted,
        )

    def _run_balanced(self, request: ReviewAnalysisRequest) -> OrchestratedAnalysis:
        primary = self._registry.get(self._primary)
        secondary = self._registry.get(self._secondary)
        results: list[ProviderAnalysis] = []

        if primary is None or not primary.is_available():
            return self._run_economy(request)

        primary_raw = primary.analyze_reviews(request)
        primary_ok = self._validator.validate(primary_raw, request)
        results.append(primary_ok)
        if primary_ok.status != "ok":
            return self._run_economy(request)

        if (
            secondary is not None
            and secondary.is_available()
            and secondary.provider_name != primary.provider_name
        ):
            critique_raw = secondary.analyze_reviews(request)
            critique_ok = self._validator.validate(critique_raw, request)
            results.append(critique_ok)
            if critique_ok.status == "ok":
                merged, meta = self._consensus.build(
                    mode="balanced",
                    analyses=[primary_ok, critique_ok],
                )
                return OrchestratedAnalysis(
                    analysis=merged,
                    consensus=meta,
                    generated_at=self._clock(),
                    providers_used=(primary_ok.provider, critique_ok.provider),
                )

        merged, meta = self._consensus.build(mode="balanced", analyses=results)
        return OrchestratedAnalysis(
            analysis=primary_ok,
            consensus=meta,
            generated_at=self._clock(),
            providers_used=(primary_ok.provider,),
        )

    def _run_maximum(self, request: ReviewAnalysisRequest) -> OrchestratedAnalysis:
        names = ["openai", "anthropic", "gemini"]
        results: list[ProviderAnalysis] = []
        for name in names:
            provider = self._registry.get(name)
            if provider is None:
                continue
            if not provider.is_available():
                results.append(
                    ProviderAnalysis(
                        product_id=request.product_id,
                        overall_sentiment="mixed",
                        summary="",
                        pros=(),
                        cons=(),
                        warnings=(),
                        recommendation="consider_alternatives",
                        confidence=0.0,
                        provider=name,
                        model=provider.model_name if provider else name,
                        status="unavailable",
                        error_code="unavailable",
                    )
                )
                continue
            raw = provider.analyze_reviews(request)
            results.append(self._validator.validate(raw, request))

        successful = [item for item in results if item.status == "ok"]
        if not successful:
            return self._deterministic_only(
                request,
                mode="maximum",
                fallback_used=True,
                fallback_reason="all_external_providers_failed",
                prior=results,
            )

        merged, meta = self._consensus.build(
            mode="maximum",
            analyses=results,
            fallback_used=False,
        )
        return OrchestratedAnalysis(
            analysis=merged,
            consensus=meta,
            generated_at=self._clock(),
            providers_used=tuple(item.provider for item in successful),
        )

    def _deterministic_only(
        self,
        request: ReviewAnalysisRequest,
        *,
        mode: AnalysisMode,
        fallback_used: bool,
        fallback_reason: str | None,
        prior: list[ProviderAnalysis] | None = None,
    ) -> OrchestratedAnalysis:
        provider = self._registry.require_deterministic()
        raw = provider.analyze_reviews(request)
        validated = self._validator.validate(raw, request)
        analyses = [*(prior or []), validated]
        merged, meta = self._consensus.build(
            mode=mode,
            analyses=analyses,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        # Surface deterministic analysis as the user-facing result.
        meta = ConsensusMetadata(
            mode=meta.mode,
            providers_requested=meta.providers_requested,
            providers_completed=meta.providers_completed,
            agreement_score=meta.agreement_score,
            consensus_confidence=validated.confidence,
            provider_results=meta.provider_results,
            disagreements=meta.disagreements,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        return OrchestratedAnalysis(
            analysis=validated,
            consensus=meta,
            generated_at=self._clock(),
            providers_used=(validated.provider,),
        )

    def _exceeds_cost(self, analysis: ProviderAnalysis) -> bool:
        if analysis.usage is None or analysis.usage.estimated_cost_usd is None:
            return False
        return analysis.usage.estimated_cost_usd > self._max_cost
