"""Shopping recommendation application service.

Searches marketplaces, obtains DealScore rankings, and converts them into
explainable purchase recommendations via the RecommendationEngine.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.deal_score import DealListingAttributes, RankingResult
from app.domain.entities.marketplace_listing import MarketplaceListing
from app.domain.entities.recommendation import (
    PurchaseDecision,
    Recommendation,
    RecommendationConfidence,
    RecommendationReason,
    RecommendationWarning,
    ShoppingRecommendationResult,
)
from app.domain.exceptions import DealScoreValidationError
from app.domain.interfaces.recommendation_engine import RecommendationEngine
from app.services.deal_recommendation_service import DealRecommendationService


class ShoppingRecommendationService:
    """Use-case orchestration for shopping recommendations."""

    def __init__(
        self,
        deal_recommendation_service: DealRecommendationService,
        recommendation_engine: RecommendationEngine,
    ) -> None:
        self._deal_recommendation_service = deal_recommendation_service
        self._recommendation_engine = recommendation_engine

    def recommend(self, query: str) -> ShoppingRecommendationResult:
        """Search marketplaces, rank by DealScore, and explain a purchase decision."""
        cleaned = query.strip()
        try:
            ranking = self._deal_recommendation_service.recommend(cleaned)
        except DealScoreValidationError as exc:
            return self._validation_fallback(cleaned, exc.message)

        recommendation = self._recommendation_engine.recommend(ranking)
        return ShoppingRecommendationResult(
            query=ranking.query,
            currency=ranking.currency,
            recommendation=recommendation,
            ranking=ranking,
        )

    def recommend_from_listings(
        self,
        query: str,
        listings: Sequence[MarketplaceListing],
        attributes_by_id: dict[str, DealListingAttributes] | None = None,
    ) -> ShoppingRecommendationResult:
        """Recommend from an explicit listing set (tests / offline evaluation)."""
        cleaned = query.strip()
        try:
            ranking = self._deal_recommendation_service.evaluate_listings(
                cleaned, listings, attributes_by_id
            )
        except DealScoreValidationError as exc:
            return self._validation_fallback(cleaned, exc.message)

        recommendation = self._recommendation_engine.recommend(ranking)
        return ShoppingRecommendationResult(
            query=ranking.query,
            currency=ranking.currency,
            recommendation=recommendation,
            ranking=ranking,
        )

    def recommend_from_ranking(self, ranking: RankingResult) -> ShoppingRecommendationResult:
        """Apply the recommendation engine to an existing DealScore ranking."""
        recommendation = self._recommendation_engine.recommend(ranking)
        return ShoppingRecommendationResult(
            query=ranking.query,
            currency=ranking.currency,
            recommendation=recommendation,
            ranking=ranking,
        )

    @staticmethod
    def _validation_fallback(query: str, message: str) -> ShoppingRecommendationResult:
        """Map DealScore validation failures to insufficient_information advice."""
        lowered = message.lower()
        if "mixed currencies" in lowered:
            headline = "Mixed currencies cannot be compared"
            summary = (
                "Listings use more than one currency, so DealBrain cannot produce "
                "a reliable purchase recommendation without conversion."
            )
            reason = (
                "Comparable DealScore ranking requires a single currency; "
                "mixed currencies were rejected."
            )
        else:
            headline = "Not enough information to recommend"
            summary = (
                "DealScore validation failed, so DealBrain cannot produce "
                "trustworthy buying advice for this query."
            )
            reason = message

        recommendation = Recommendation(
            decision=PurchaseDecision.INSUFFICIENT_INFORMATION,
            recommended_listing_id=None,
            headline=headline,
            summary=summary,
            reasoning=(RecommendationReason(text=reason, rank=1),),
            tradeoffs=(),
            warnings=(
                RecommendationWarning(text=message),
                RecommendationWarning(
                    text=(
                        "Marketplace results are based on mocked connector data, "
                        "not live marketplace APIs."
                    )
                ),
            ),
            confidence=RecommendationConfidence(
                value=0.2,
                factors=("dealscore_validation_error",),
            ),
            alternatives=(),
        )
        empty_ranking = RankingResult(
            query=query,
            currency="",
            market_average_total_cost=0.0,
            recommended_listing_id=None,
            evaluations=(),
        )
        return ShoppingRecommendationResult(
            query=query,
            currency="",
            recommendation=recommendation,
            ranking=empty_ranking,
        )
