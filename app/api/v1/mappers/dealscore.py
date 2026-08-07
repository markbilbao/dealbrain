"""Map DealScore domain results to HTTP response schemas."""

from __future__ import annotations

from app.core.public_brand import present_consumer_text
from app.domain.entities.deal_score import DealScore, ListingEvaluation, RankingResult
from app.schemas.dealscore import (
    DealScoreComponentsPayload,
    DealScoreListingPayload,
    DealScorePayload,
    DealScoreResultItem,
    DealScoreSearchResponse,
)


def to_dealscore_search_response(result: RankingResult) -> DealScoreSearchResponse:
    """Convert a ranking result into the public DealScore search response."""
    return DealScoreSearchResponse(
        query=result.query,
        currency=result.currency,
        market_average_total_cost=result.market_average_total_cost,
        recommended_listing_id=result.recommended_listing_id,
        results=[_to_result_item(evaluation) for evaluation in result.evaluations],
    )


def _to_result_item(evaluation: ListingEvaluation) -> DealScoreResultItem:
    listing = evaluation.listing
    attrs = evaluation.attributes
    total_cost = evaluation.deal_score.total_cost
    return DealScoreResultItem(
        rank=evaluation.deal_score.rank,
        listing=DealScoreListingPayload(
            marketplace=listing.marketplace,
            product_id=listing.product_id,
            title=listing.title,
            price=listing.price,
            currency=listing.currency,
            seller=listing.seller,
            rating=listing.rating,
            url=listing.url,
            availability=listing.availability.value,
            shipping_cost=attrs.shipping_cost,
            is_official_store=attrs.is_official_store,
            warranty_months=attrs.warranty_months,
            return_policy_days=attrs.return_policy_days,
            total_cost=total_cost,
        ),
        deal_score=_to_deal_score_payload(evaluation.deal_score),
    )


def _to_deal_score_payload(score: DealScore) -> DealScorePayload:
    components = score.components
    return DealScorePayload(
        listing_id=score.listing_id,
        marketplace=score.marketplace,
        score=score.score,
        rating=score.rating.value,
        rank=score.rank,
        total_cost=score.total_cost,
        components=DealScoreComponentsPayload(
            price_score=components.price_score,
            seller_score=components.seller_score,
            shipping_score=components.shipping_score,
            availability_score=components.availability_score,
            official_store_score=components.official_store_score,
            warranty_score=components.warranty_score,
            return_policy_score=components.return_policy_score,
        ),
        explanation=[present_consumer_text(item) for item in score.explanation],
        warnings=[present_consumer_text(item) for item in score.warnings],
        applied_weights=dict(score.applied_weights),
    )
