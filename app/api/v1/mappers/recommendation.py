"""Map shopping recommendation domain results to HTTP response schemas."""

from __future__ import annotations

from app.api.v1.mappers.dealscore import to_dealscore_search_response
from app.domain.entities.recommendation import Recommendation, ShoppingRecommendationResult
from app.schemas.recommendation import (
    AlternativeRecommendationPayload,
    RecommendationPayload,
    ShoppingRecommendationSearchResponse,
)


def to_shopping_recommendation_response(
    result: ShoppingRecommendationResult,
) -> ShoppingRecommendationSearchResponse:
    """Convert a shopping recommendation result into the public API response."""
    ranked = to_dealscore_search_response(result.ranking)
    return ShoppingRecommendationSearchResponse(
        query=result.query,
        currency=result.currency,
        recommendation=_to_recommendation_payload(result.recommendation),
        ranked_results=ranked.results,
    )


def _to_recommendation_payload(recommendation: Recommendation) -> RecommendationPayload:
    return RecommendationPayload(
        decision=recommendation.decision.value,
        recommended_listing_id=recommendation.recommended_listing_id,
        headline=recommendation.headline,
        summary=recommendation.summary,
        reasoning=[reason.text for reason in recommendation.reasoning],
        tradeoffs=[tradeoff.text for tradeoff in recommendation.tradeoffs],
        warnings=[warning.text for warning in recommendation.warnings],
        confidence=recommendation.confidence.value,
        alternatives=[
            AlternativeRecommendationPayload(
                listing_id=alt.listing_id,
                label=alt.label,
                reason=alt.reason,
            )
            for alt in recommendation.alternatives
        ],
    )
