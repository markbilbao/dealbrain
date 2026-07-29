"""Deal recommendation application service.

Searches marketplaces, evaluates every listing with the DealScore engine,
ranks best → worst, and preserves all alternatives.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.entities.deal_score import (
    DealListingAttributes,
    DealScore,
    ListingEvaluation,
    RankingResult,
    ScoreableListing,
)
from app.domain.entities.marketplace_listing import MarketplaceListing
from app.domain.interfaces.deal_score_engine import DealScoreEngine
from app.intelligence.dealscore.enrichment import resolve_deal_attributes, to_scoreable_listing
from app.services.marketplace_intelligence_service import MarketplaceIntelligenceService


class DealRecommendationService:
    """Use-case orchestration for DealScore search and ranking."""

    def __init__(
        self,
        marketplace_service: MarketplaceIntelligenceService,
        deal_score_engine: DealScoreEngine,
        marketplace_data_service: Any | None = None,
    ) -> None:
        self._marketplace_service = marketplace_service
        self._deal_score_engine = deal_score_engine
        self._marketplace_data = marketplace_data_service

    def recommend(self, query: str) -> RankingResult:
        """Search marketplaces and return ranked DealScore recommendations."""
        search = self._marketplace_service.search(query)
        scoreable = [to_scoreable_listing(listing) for listing in search.results]
        result = self._deal_score_engine.rank(search.query, scoreable)
        return self._annotate_provenance(result)

    def evaluate_listings(
        self,
        query: str,
        listings: Sequence[MarketplaceListing],
        attributes_by_id: dict[str, DealListingAttributes] | None = None,
    ) -> RankingResult:
        """Evaluate an explicit listing set (useful for tests and offline ranking)."""
        overrides = attributes_by_id or {}
        scoreable: list[ScoreableListing] = []
        for listing in listings:
            attrs = overrides.get(listing.product_id, resolve_deal_attributes(listing))
            scoreable.append(to_scoreable_listing(listing, attrs))
        result = self._deal_score_engine.rank(query, scoreable)
        return self._annotate_provenance(result)

    def _annotate_provenance(self, result: RankingResult) -> RankingResult:
        """Append honest source-mode / freshness notes without changing scores."""
        evaluations: list[ListingEvaluation] = []
        for evaluation in result.evaluations:
            notes = [
                (
                    "DealScore listing source: mock marketplace connector — "
                    "not live pricing unless a live connector is configured."
                ),
            ]
            if self._marketplace_data is not None:
                try:
                    for offer in self._marketplace_data.list_offers(limit=50):
                        if offer.title.lower() in evaluation.listing.title.lower() or (
                            evaluation.listing.title.lower() in offer.title.lower()
                        ):
                            notes.extend(
                                self._marketplace_data.provenance_notes_for_offer(offer)[:2]
                            )
                            break
                except Exception:  # noqa: BLE001
                    pass
            score = evaluation.deal_score
            annotated = DealScore(
                listing_id=score.listing_id,
                marketplace=score.marketplace,
                score=score.score,
                rating=score.rating,
                rank=score.rank,
                total_cost=score.total_cost,
                components=score.components,
                explanation=tuple([*score.explanation, *notes]),
                warnings=score.warnings,
                applied_weights=dict(score.applied_weights),
            )
            evaluations.append(
                ListingEvaluation(
                    listing=evaluation.listing,
                    attributes=evaluation.attributes,
                    deal_score=annotated,
                )
            )
        return RankingResult(
            query=result.query,
            currency=result.currency,
            market_average_total_cost=result.market_average_total_cost,
            recommended_listing_id=result.recommended_listing_id,
            evaluations=tuple(evaluations),
        )
