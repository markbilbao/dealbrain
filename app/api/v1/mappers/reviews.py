"""Map Review Intelligence domain objects to HTTP schemas."""

from __future__ import annotations

from app.domain.entities.review import (
    MarketplaceReviewComparison,
    MarketplaceReviewSummary,
    ReviewCollectionResult,
    ReviewSnapshot,
)
from app.schemas.reviews import (
    MarketplaceReviewPayload,
    ReviewCollectResponse,
    ReviewCompareResponse,
    ReviewHistoryResponse,
    ReviewLatestResponse,
    ReviewSnapshotPayload,
)


def to_snapshot_payload(snapshot: ReviewSnapshot) -> ReviewSnapshotPayload:
    return ReviewSnapshotPayload(
        snapshot_id=snapshot.snapshot_id,
        product_id=snapshot.product_id,
        product_label=snapshot.product_label,
        marketplace=snapshot.marketplace,
        average_rating=snapshot.average_rating,
        review_count=snapshot.review_count,
        five_star_count=snapshot.five_star_count,
        four_star_count=snapshot.four_star_count,
        three_star_count=snapshot.three_star_count,
        two_star_count=snapshot.two_star_count,
        one_star_count=snapshot.one_star_count,
        seller_rating=snapshot.seller_rating,
        seller_followers=snapshot.seller_followers,
        seller_products=snapshot.seller_products,
        collected_at=snapshot.collected_at.isoformat(),
    )


def to_marketplace_payload(summary: MarketplaceReviewSummary) -> MarketplaceReviewPayload:
    return MarketplaceReviewPayload(
        marketplace=summary.marketplace,
        rating=summary.rating,
        reviews=summary.reviews,
        seller_rating=summary.seller_rating,
        seller_followers=summary.seller_followers,
        seller_products=summary.seller_products,
        five_star_count=summary.five_star_count,
        four_star_count=summary.four_star_count,
        three_star_count=summary.three_star_count,
        two_star_count=summary.two_star_count,
        one_star_count=summary.one_star_count,
        collected_at=summary.collected_at.isoformat() if summary.collected_at else None,
        snapshot_id=summary.snapshot_id,
    )


def to_collect_response(
    result: ReviewCollectionResult,
    *,
    overall_rating: float | None,
    total_review_count: int,
) -> ReviewCollectResponse:
    return ReviewCollectResponse(
        product_id=result.product_id,
        product=result.product,
        snapshots=[to_snapshot_payload(snap) for snap in result.snapshots],
        collected_count=len(result.snapshots),
        collected_at=result.collected_at.isoformat(),
        overall_rating=overall_rating,
        total_review_count=total_review_count,
    )


def to_latest_response(
    product_id: str,
    product: str,
    summaries: list[MarketplaceReviewSummary],
    *,
    overall_rating: float | None,
    total_review_count: int,
) -> ReviewLatestResponse:
    return ReviewLatestResponse(
        product_id=product_id,
        product=product,
        overall_rating=overall_rating,
        total_review_count=total_review_count,
        marketplaces=[to_marketplace_payload(item) for item in summaries],
    )


def to_history_response(
    product_id: str,
    product: str,
    snapshots: list[ReviewSnapshot],
) -> ReviewHistoryResponse:
    return ReviewHistoryResponse(
        product_id=product_id,
        product=product,
        snapshots=[to_snapshot_payload(snap) for snap in snapshots],
        count=len(snapshots),
    )


def to_compare_response(comparison: MarketplaceReviewComparison) -> ReviewCompareResponse:
    return ReviewCompareResponse(
        product=comparison.product,
        product_id=comparison.product_id,
        overall_rating=comparison.overall_rating,
        total_review_count=comparison.total_review_count,
        marketplaces=[to_marketplace_payload(item) for item in comparison.marketplaces],
    )
