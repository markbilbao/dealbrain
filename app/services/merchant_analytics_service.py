"""Merchant analytics and ranking explanations — Sprint 21.

Demo analytics are labeled simulated. Merchants cannot alter organic ranking.
Affiliate data is read-only — never mutated from the merchant portal.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.merchant import (
    MerchantActor,
    MerchantAnalyticsSummary,
    MerchantPermission,
    RankingExplanation,
)
from app.domain.exceptions import MerchantValidationError
from app.domain.interfaces.merchant_repository import (
    MerchantAuditRepository,
    MerchantCampaignRepository,
    MerchantOrganizationRepository,
    MerchantPromotionRepository,
    MerchantSubmissionRepository,
)
from app.merchant.analytics import aggregate_analytics, build_ranking_explanation
from app.merchant.fixtures import demo_analytics_seed
from app.merchant.security.permissions import require_membership, require_permission
from app.merchant.security.redaction import redact_secrets


class MerchantAnalyticsService:
    """Merchant-facing analytics, affiliate summaries, and ranking explanations."""

    def __init__(
        self,
        organizations: MerchantOrganizationRepository,
        submissions: MerchantSubmissionRepository,
        promotions: MerchantPromotionRepository,
        campaigns: MerchantCampaignRepository,
        audit: MerchantAuditRepository,
        *,
        affiliate_click_lister: Callable[..., list[Any]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._organizations = organizations
        self._submissions = submissions
        self._promotions = promotions
        self._campaigns = campaigns
        self._audit = audit
        self._affiliate_click_lister = affiliate_click_lister
        self._clock = clock or (lambda: datetime.now(UTC))

    def get_analytics(self, actor: MerchantActor, organization_id: str) -> MerchantAnalyticsSummary:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ANALYTICS_ACCESS)
        org = self._organizations.get_organization(organization_id)
        if org is None:
            raise MerchantValidationError(f"Organization not found: {organization_id}")

        products = self._submissions.list_product_submissions(
            organization_id=organization_id, limit=200
        )
        offers = self._submissions.list_offer_submissions(
            organization_id=organization_id, limit=200
        )
        promotions = self._promotions.list_promotions(organization_id=organization_id, limit=200)
        campaigns = self._campaigns.list_campaigns(organization_id=organization_id, limit=200)
        affiliate_stats = self._affiliate_stats(org.affiliate_merchant_id)
        return aggregate_analytics(
            organization_id=organization_id,
            generated_at=self._clock(),
            products=products,
            offers=offers,
            promotions=promotions,
            campaigns=campaigns,
            affiliate_stats=affiliate_stats,
            demo_seed=demo_analytics_seed(),
        )

    def get_product_performance(
        self, actor: MerchantActor, organization_id: str, product_id: str
    ) -> dict[str, Any]:
        summary = self.get_analytics(actor, organization_id)
        for row in summary.products:
            if row.product_id == product_id:
                return row.to_dict()
        # Fallback demo row when product not yet in submissions seed map.
        seed = demo_analytics_seed().get("products", {}).get(product_id)
        if seed:
            return {
                "product_id": product_id,
                "organization_id": organization_id,
                **seed,
                "simulated": True,
                "label": "Demo analytics — simulated, not live sales reporting",
            }
        raise MerchantValidationError(f"No performance data for product {product_id}.")

    def get_ranking_explanation(
        self, actor: MerchantActor, organization_id: str, product_id: str
    ) -> RankingExplanation:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.ANALYTICS_ACCESS)
        offers = self._submissions.list_offer_submissions(
            organization_id=organization_id, limit=200
        )
        offer = next((o for o in offers if o.matched_product_id == product_id), None)
        if offer is None:
            offer = next((o for o in offers if o.offer_id == product_id), None)
        perf = demo_analytics_seed().get("products", {}).get(product_id, {})
        return build_ranking_explanation(
            product_id=product_id,
            organization_id=organization_id,
            dealscore=perf.get("dealscore"),
            offer=offer,
            extras={
                "freshness": perf.get("data_freshness", "demo"),
                "seller_reliability": perf.get("seller_quality", "demo"),
                "review_sentiment": "Demo review sentiment — not private user data.",
                "community_evidence": "Community evidence summaries only — no private posts.",
            },
        )

    def list_audit_log(
        self, actor: MerchantActor, organization_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        require_membership(actor, organization_id)
        require_permission(actor, MerchantPermission.AUDIT_LOG_ACCESS)
        events = self._audit.list_audit_events(organization_id=organization_id, limit=limit)
        return [redact_secrets(e.to_dict()) for e in events]

    def _affiliate_stats(self, affiliate_merchant_id: str | None) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "affiliate_merchant_id": affiliate_merchant_id,
            "affiliate_eligible": bool(affiliate_merchant_id),
            "link_available": bool(affiliate_merchant_id),
            "clicks": 0,
            "attributed_conversions": 0,
            "estimated_revenue": None,
            "conversion_status_summary": {},
            "clicks_by_product": {},
        }
        if not affiliate_merchant_id or self._affiliate_click_lister is None:
            return stats
        try:
            clicks = self._affiliate_click_lister(merchant_id=affiliate_merchant_id, limit=500)
        except Exception:  # noqa: BLE001 — affiliate integration is best-effort
            return stats
        status_counts: dict[str, int] = {}
        by_product: dict[str, int] = {}
        conversions = 0
        estimated = 0.0
        for click in clicks:
            status = getattr(click, "conversion_status", None)
            status_value = status.value if hasattr(status, "value") else str(status or "clicked")
            status_counts[status_value] = status_counts.get(status_value, 0) + 1
            if status_value in {"converted", "attributed"}:
                conversions += 1
            product_id = getattr(click, "product_id", None)
            if product_id:
                by_product[product_id] = by_product.get(product_id, 0) + 1
            commission = getattr(click, "estimated_commission", None)
            if commission is not None:
                estimated += float(commission)
        stats.update(
            {
                "clicks": len(clicks),
                "attributed_conversions": conversions,
                "estimated_revenue": round(estimated, 2) if estimated else None,
                "estimated_commission": round(estimated, 2) if estimated else None,
                "conversion_status_summary": status_counts,
                "clicks_by_product": by_product,
            }
        )
        return stats
