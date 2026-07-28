"""Deal recommendation application service.

Searches marketplaces, evaluates every listing with the DealScore engine,
ranks best → worst, and preserves all alternatives.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.entities.deal_score import (
    DealListingAttributes,
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
    ) -> None:
        self._marketplace_service = marketplace_service
        self._deal_score_engine = deal_score_engine

    def recommend(self, query: str) -> RankingResult:
        """Search marketplaces and return ranked DealScore recommendations."""
        search = self._marketplace_service.search(query)
        scoreable = [to_scoreable_listing(listing) for listing in search.results]
        return self._deal_score_engine.rank(search.query, scoreable)

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
        return self._deal_score_engine.rank(query, scoreable)
