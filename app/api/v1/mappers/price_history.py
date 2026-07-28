"""Map Price History domain results to HTTP response schemas."""

from __future__ import annotations

from app.domain.entities.price_history import (
    MarketplacePriceSummary,
    PriceHistory,
    PriceHistorySearchResult,
    PriceSnapshot,
    PriceStatistics,
)
from app.schemas.price_history import (
    MarketplacePriceSummaryPayload,
    PriceHistoryResponse,
    PriceHistorySearchResponse,
    PriceSnapshotPayload,
    PriceStatisticsPayload,
)

_DISCLAIMER = (
    "Lowest recorded price in the available DealBrain history. "
    "Statistics use only stored observations."
)
_MOCK_NOTE = "Development history uses mocked observations."


def to_snapshot_payload(snapshot: PriceSnapshot) -> PriceSnapshotPayload:
    return PriceSnapshotPayload(
        snapshot_id=str(snapshot.snapshot_id),
        canonical_product_id=snapshot.canonical_product_id,
        marketplace=snapshot.marketplace,
        listing_id=snapshot.listing_id,
        seller_name=snapshot.seller_name,
        currency=snapshot.currency,
        item_price=snapshot.item_price,
        shipping_cost=snapshot.shipping_cost,
        total_cost=snapshot.total_cost,
        availability=snapshot.availability.value,
        observed_at=snapshot.observed_at,
    )


def to_statistics_payload(stats: PriceStatistics) -> PriceStatisticsPayload:
    return PriceStatisticsPayload(
        current_total_cost=stats.current_total_cost,
        lowest_recorded_total_cost=stats.lowest_recorded_total_cost,
        highest_recorded_total_cost=stats.highest_recorded_total_cost,
        average_total_cost=stats.average_total_cost,
        median_total_cost=stats.median_total_cost,
        observation_count=stats.observation_count,
        first_observed=stats.first_observed,
        last_observed=stats.last_observed,
        absolute_change=stats.absolute_change,
        percentage_change=stats.percentage_change,
        trend=stats.trend.value,
    )


def to_marketplace_summary_payload(
    summary: MarketplacePriceSummary,
) -> MarketplacePriceSummaryPayload:
    return MarketplacePriceSummaryPayload(
        marketplace=summary.marketplace,
        latest_total_cost=summary.latest_total_cost,
        lowest_recorded_total_cost=summary.lowest_recorded_total_cost,
        average_total_cost=summary.average_total_cost,
        observation_count=summary.observation_count,
        latest_availability=summary.latest_availability.value,
        last_observed=summary.last_observed,
    )


def to_history_response(history: PriceHistory) -> PriceHistoryResponse:
    return PriceHistoryResponse(
        canonical_product_id=history.canonical_product_id,
        listing_id=history.listing_id,
        currency=history.currency,
        statistics=(
            to_statistics_payload(history.statistics) if history.statistics else None
        ),
        history=[to_snapshot_payload(s) for s in history.snapshots],
        marketplace_summaries=[
            to_marketplace_summary_payload(s) for s in history.marketplace_summaries
        ],
        disclaimer=_DISCLAIMER,
    )


def to_search_response(result: PriceHistorySearchResult) -> PriceHistorySearchResponse:
    return PriceHistorySearchResponse(
        query=result.query,
        currency=result.currency,
        statistics=(
            to_statistics_payload(result.statistics) if result.statistics else None
        ),
        history=[to_snapshot_payload(s) for s in result.history],
        marketplace_summaries=[
            to_marketplace_summary_payload(s) for s in result.marketplace_summaries
        ],
        canonical_product_id=result.canonical_product_id,
        disclaimer=_DISCLAIMER,
        development_note=_MOCK_NOTE if result.is_mock_history else None,
    )
