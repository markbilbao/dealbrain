"""Shared adapter helpers for external AI review providers."""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.domain.entities.review_analysis import (
    ProviderAnalysis,
    ProviderUsageMetadata,
    ReviewAnalysisRequest,
    ReviewEvidenceItem,
)
from app.domain.exceptions import (
    AIProviderMalformedResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.domain.interfaces.ai_review_provider import AIReviewProvider
from app.infrastructure.ai.review_providers.parsing import parse_provider_json
from app.infrastructure.ai.transports import ProviderTransport


def build_analysis_prompt(request: ReviewAnalysisRequest) -> tuple[str, str]:
    """Build system/user prompts. Never logged to API responses."""
    system = (
        "You are a shopping review analyst. Return ONLY valid JSON matching the "
        "DealBrain review analysis schema. Every pro/con/warning claim MUST cite "
        "evidence_review_ids from the supplied reviews. Do not invent facts, "
        "prices, or review IDs. Do not include secrets."
    )
    reviews_payload = [item.to_dict() for item in request.reviews]
    user = json.dumps(
        {
            "product_id": request.product_id,
            "product": request.product,
            "average_rating": request.average_rating,
            "total_review_count": request.total_review_count,
            "reviews": reviews_payload,
            "output_schema": {
                "product_id": "string",
                "overall_sentiment": "very_positive|positive|mixed|negative",
                "summary": "string",
                "pros": [{"claim": "string", "evidence_review_ids": ["string"], "confidence": 0.0}],
                "cons": [{"claim": "string", "evidence_review_ids": ["string"], "confidence": 0.0}],
                "warnings": [
                    {"claim": "string", "evidence_review_ids": ["string"], "confidence": 0.0}
                ],
                "recommendation": (
                    "highly_recommended|recommended|consider_alternatives|not_recommended"
                ),
                "confidence": 0.0,
            },
        },
        ensure_ascii=True,
    )
    return system, user


def failure_analysis(
    request: ReviewAnalysisRequest,
    *,
    provider: str,
    model: str,
    status: str,
    error_code: str,
) -> ProviderAnalysis:
    """Return a non-ok analysis shell for orchestrator bookkeeping."""
    return ProviderAnalysis(
        product_id=request.product_id,
        overall_sentiment="mixed",
        summary="",
        pros=(),
        cons=(),
        warnings=(),
        recommendation="consider_alternatives",
        confidence=0.0,
        provider=provider,
        model=model,
        status=status,  # type: ignore[arg-type]
        error_code=error_code,
    )


class TransportBackedReviewProvider(AIReviewProvider):
    """Base class for OpenAI / Claude / Gemini adapters using a transport."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: ProviderTransport,
        live_http_enabled: bool,
        ai_review_enabled: bool,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model
        self._transport = transport
        self._live_http_enabled = live_http_enabled
        self._ai_review_enabled = ai_review_enabled

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(
            self._ai_review_enabled
            and self._live_http_enabled
            and self._api_key
        )

    def analyze_reviews(self, request: ReviewAnalysisRequest) -> ProviderAnalysis:
        if not self._ai_review_enabled:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="unavailable",
                error_code="ai_disabled",
            )
        if not self._api_key:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="unavailable",
                error_code="missing_api_key",
            )
        if not self._live_http_enabled:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="unavailable",
                error_code="live_http_disabled",
            )

        system_prompt, user_prompt = build_analysis_prompt(request)
        try:
            response = self._transport.complete(
                provider=self.provider_name,
                model=self._model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                timeout_seconds=request.timeout_seconds,
            )
        except AIProviderTimeoutError:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="timeout",
                error_code="timeout",
            )
        except AIProviderRateLimitError:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="rate_limited",
                error_code="rate_limited",
            )
        except AIProviderMalformedResponseError:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="malformed",
                error_code="malformed",
            )
        except AIProviderUnavailableError as exc:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="unavailable",
                error_code=exc.error_code,
            )

        usage = ProviderUsageMetadata(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            estimated_cost_usd=response.estimated_cost_usd,
            latency_ms=response.latency_ms,
        )
        try:
            return parse_provider_json(
                response.content,
                provider=self.provider_name,
                model=self._model,
                product_id=request.product_id,
                usage=usage,
            )
        except AIProviderMalformedResponseError:
            return failure_analysis(
                request,
                provider=self.provider_name,
                model=self._model,
                status="malformed",
                error_code="malformed",
            )


def truncate_reviews(
    reviews: Sequence[ReviewEvidenceItem],
    max_items: int,
) -> tuple[ReviewEvidenceItem, ...]:
    return tuple(reviews[: max(1, max_items)])
