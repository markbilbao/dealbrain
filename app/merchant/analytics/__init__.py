"""Merchant analytics aggregation — demo/simulated labels only."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.entities.merchant import (
    DEMO_ANALYTICS_LABEL,
    MerchantAffiliatePerformance,
    MerchantAnalyticsSummary,
    MerchantCampaign,
    MerchantCampaignStatus,
    MerchantOfferSubmission,
    MerchantProductPerformance,
    MerchantProductSubmission,
    MerchantPromotion,
    PromotionStatus,
    RankingExplanation,
    RankingExplanationFactor,
)


def aggregate_analytics(
    *,
    organization_id: str,
    generated_at: datetime,
    products: list[MerchantProductSubmission],
    offers: list[MerchantOfferSubmission],
    promotions: list[MerchantPromotion],
    campaigns: list[MerchantCampaign],
    affiliate_stats: dict[str, Any] | None = None,
    demo_seed: dict[str, Any] | None = None,
) -> MerchantAnalyticsSummary:
    """Build an org-level analytics summary from stored data + optional demo seed.

    Never fabricates real sales. Demo seed values are always labeled simulated.
    """
    seed = demo_seed or {}
    aff = affiliate_stats or {}

    product_rows: list[MerchantProductPerformance] = []
    for idx, product in enumerate(products):
        pid = product.matched_product_id or product.submission_id
        per_product = seed.get("products", {}).get(pid, {})
        views = int(per_product.get("product_views", seed.get("product_views_base", 12) + idx))
        offer_views = int(per_product.get("offer_views", max(1, views // 2)))
        clicks = int(
            per_product.get("affiliate_clicks", aff.get("clicks_by_product", {}).get(pid, 0))
        )
        ctr = round(clicks / views, 4) if views else 0.0
        product_rows.append(
            MerchantProductPerformance(
                product_id=pid,
                organization_id=organization_id,
                title=product.title,
                product_views=views,
                offer_views=offer_views,
                affiliate_clicks=clicks,
                click_through_rate=ctr,
                attributed_conversions=int(per_product.get("attributed_conversions", 0)),
                estimated_commission=per_product.get("estimated_commission"),
                watchlist_additions=int(per_product.get("watchlist_additions", 0)),
                alert_activity=int(per_product.get("alert_activity", 0)),
                comparison_appearances=int(per_product.get("comparison_appearances", 0)),
                recommendation_appearances=int(per_product.get("recommendation_appearances", 0)),
                dealscore=per_product.get("dealscore"),
                data_freshness=str(per_product.get("data_freshness", "demo")),
                price_competitiveness=str(per_product.get("price_competitiveness", "demo")),
                seller_quality=str(per_product.get("seller_quality", "demo")),
                simulated=True,
            )
        )

    total_views = sum(p.product_views for p in product_rows) or int(seed.get("product_views", 0))
    total_offer_views = sum(p.offer_views for p in product_rows) or int(seed.get("offer_views", 0))
    total_clicks = sum(p.affiliate_clicks for p in product_rows) or int(aff.get("clicks", 0))
    total_conversions = sum(p.attributed_conversions for p in product_rows) or int(
        aff.get("attributed_conversions", 0)
    )
    ctr = round(total_clicks / total_views, 4) if total_views else 0.0

    affiliate = MerchantAffiliatePerformance(
        organization_id=organization_id,
        affiliate_merchant_id=aff.get("affiliate_merchant_id"),
        affiliate_eligible=bool(aff.get("affiliate_eligible", False)),
        link_available=bool(aff.get("link_available", False)),
        clicks=int(aff.get("clicks", total_clicks)),
        attributed_conversions=int(aff.get("attributed_conversions", total_conversions)),
        estimated_revenue=aff.get("estimated_revenue"),
        conversion_status_summary=dict(aff.get("conversion_status_summary", {})),
        simulated=True,
    )

    active_promos = sum(1 for p in promotions if p.status == PromotionStatus.ACTIVE)
    active_campaigns = sum(
        1
        for c in campaigns
        if c.status in (MerchantCampaignStatus.ACTIVE, MerchantCampaignStatus.PAUSED)
    )

    return MerchantAnalyticsSummary(
        organization_id=organization_id,
        generated_at=generated_at,
        product_views=total_views,
        offer_views=total_offer_views,
        affiliate_clicks=total_clicks,
        click_through_rate=ctr,
        attributed_conversions=total_conversions,
        estimated_commission=aff.get("estimated_commission") or seed.get("estimated_commission"),
        watchlist_additions=int(seed.get("watchlist_additions", 0)),
        alert_activity=int(seed.get("alert_activity", 0)),
        comparison_appearances=int(seed.get("comparison_appearances", 0)),
        recommendation_appearances=int(seed.get("recommendation_appearances", 0)),
        active_promotions=active_promos,
        active_campaigns=active_campaigns,
        products=tuple(product_rows),
        affiliate=affiliate,
        simulated=True,
    )


def build_ranking_explanation(
    *,
    product_id: str,
    organization_id: str,
    dealscore: float | None,
    offer: MerchantOfferSubmission | None = None,
    extras: dict[str, Any] | None = None,
) -> RankingExplanation:
    """Build a safe ranking explanation — no private or proprietary data."""
    meta = extras or {}
    factors: list[RankingExplanationFactor] = []

    if offer is not None:
        factors.append(
            RankingExplanationFactor(
                factor="total_price",
                contribution="primary",
                detail=f"Total price {offer.currency} {offer.total_price:.2f} (item + shipping).",
            )
        )
        factors.append(
            RankingExplanationFactor(
                factor="shipping_cost",
                contribution="secondary",
                detail=f"Shipping cost {offer.currency} {offer.shipping_cost:.2f}.",
            )
        )
        factors.append(
            RankingExplanationFactor(
                factor="availability",
                contribution="secondary",
                detail=f"Availability reported as {offer.availability}.",
            )
        )
        if offer.warranty:
            factors.append(
                RankingExplanationFactor(
                    factor="warranty",
                    contribution="minor",
                    detail=f"Warranty: {offer.warranty}",
                )
            )

    factors.append(
        RankingExplanationFactor(
            factor="freshness",
            contribution="secondary",
            detail=str(
                meta.get(
                    "freshness", "Merchant-submitted — freshness pending independent validation."
                )
            ),
        )
    )
    factors.append(
        RankingExplanationFactor(
            factor="seller_reliability",
            contribution="secondary",
            detail=str(
                meta.get("seller_reliability", "Seller quality indicators are demo estimates only.")
            ),
        )
    )
    if "review_sentiment" in meta:
        factors.append(
            RankingExplanationFactor(
                factor="review_sentiment",
                contribution="minor",
                detail=str(meta["review_sentiment"]),
            )
        )
    if "community_evidence" in meta:
        factors.append(
            RankingExplanationFactor(
                factor="community_evidence",
                contribution="minor",
                detail=str(meta["community_evidence"]),
            )
        )
    factors.append(
        RankingExplanationFactor(
            factor="dealscore_factors",
            contribution="informational",
            detail=(
                f"PiqScore {dealscore}"
                if dealscore is not None
                else "PiqScore not yet computed for this submission."
            ),
        )
    )
    factors.append(
        RankingExplanationFactor(
            factor="user_preference_relevance",
            contribution="informational",
            detail=str(
                meta.get(
                    "preference_relevance",
                    "Preference relevance is computed per shopper — "
                    "not exposed as private user data.",
                )
            ),
        )
    )

    return RankingExplanation(
        product_id=product_id,
        organization_id=organization_id,
        dealscore=dealscore,
        factors=tuple(factors),
    )


def analytics_disclaimer() -> str:
    return DEMO_ANALYTICS_LABEL
