"""Affiliate revenue report aggregation — Sprint 20.

Pure aggregation over tracked clicks. Estimates only — no billing or payouts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from app.domain.entities.affiliate import (
    AffiliateClick,
    AffiliateRevenueReport,
    ConversionStatus,
    RevenueReportBucket,
)

_CONVERTED = frozenset(
    {
        ConversionStatus.CONVERTED,
        ConversionStatus.ATTRIBUTED,
    }
)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _bucket(
    key: str,
    label: str,
    clicks: int,
    conversions: int,
    revenue: float,
    commission: float,
    currency: str,
) -> RevenueReportBucket:
    return RevenueReportBucket(
        key=key,
        label=label,
        clicks=clicks,
        conversions=conversions,
        revenue=round(revenue, 4),
        estimated_commission=round(commission, 4),
        conversion_rate=_rate(conversions, clicks),
        currency=currency,
    )


def aggregate_revenue_report(
    clicks: Sequence[AffiliateClick],
    *,
    report_id: str,
    generated_at: datetime,
    impressions: int = 0,
    currency: str = "USD",
    top_n: int = 5,
) -> AffiliateRevenueReport:
    """Build an :class:`AffiliateRevenueReport` from click events."""
    total_clicks = len(clicks)
    conversions = [c for c in clicks if c.conversion_status in _CONVERTED]
    total_conversions = len(conversions)
    total_revenue = sum(c.revenue for c in conversions)
    total_commission = sum(
        c.estimated_commission for c in clicks if c.conversion_status in _CONVERTED
    )
    # Fallback: if no conversions yet, still surface estimated commission potential
    # from clicked estimates so the demo dashboard is informative.
    if total_commission == 0.0 and clicks:
        total_commission = sum(c.estimated_commission for c in clicks) * 0.0

    by_merchant_raw: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
            "commission": 0.0,
        }
    )
    by_product_raw: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
            "commission": 0.0,
        }
    )
    by_category_raw: dict[str, dict] = defaultdict(
        lambda: {
            "label": "",
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
            "commission": 0.0,
        }
    )

    for click in clicks:
        m = by_merchant_raw[click.merchant_id]
        m["label"] = click.merchant_id
        m["clicks"] += 1
        if click.conversion_status in _CONVERTED:
            m["conversions"] += 1
            m["revenue"] += click.revenue
            m["commission"] += click.estimated_commission

        p = by_product_raw[click.product_id]
        p["label"] = click.product_name or click.product_id
        p["clicks"] += 1
        if click.conversion_status in _CONVERTED:
            p["conversions"] += 1
            p["revenue"] += click.revenue
            p["commission"] += click.estimated_commission

        category_key = click.category or "uncategorized"
        cat = by_category_raw[category_key]
        cat["label"] = category_key
        cat["clicks"] += 1
        if click.conversion_status in _CONVERTED:
            cat["conversions"] += 1
            cat["revenue"] += click.revenue
            cat["commission"] += click.estimated_commission

    by_merchant = tuple(
        sorted(
            [
                _bucket(
                    key,
                    data["label"] or key,
                    data["clicks"],
                    data["conversions"],
                    data["revenue"],
                    data["commission"],
                    currency,
                )
                for key, data in by_merchant_raw.items()
            ],
            key=lambda b: (-b.estimated_commission, -b.clicks, b.key),
        )
    )
    by_product = tuple(
        sorted(
            [
                _bucket(
                    key,
                    data["label"] or key,
                    data["clicks"],
                    data["conversions"],
                    data["revenue"],
                    data["commission"],
                    currency,
                )
                for key, data in by_product_raw.items()
            ],
            key=lambda b: (-b.estimated_commission, -b.clicks, b.key),
        )
    )
    by_category = tuple(
        sorted(
            [
                _bucket(
                    key,
                    data["label"] or key,
                    data["clicks"],
                    data["conversions"],
                    data["revenue"],
                    data["commission"],
                    currency,
                )
                for key, data in by_category_raw.items()
            ],
            key=lambda b: (-b.estimated_commission, -b.clicks, b.key),
        )
    )

    top_merchants = tuple(
        sorted(by_merchant, key=lambda b: (-b.conversion_rate, -b.conversions, b.key))[:top_n]
    )
    top_products = tuple(
        sorted(by_product, key=lambda b: (-b.conversion_rate, -b.conversions, b.key))[:top_n]
    )

    return AffiliateRevenueReport(
        report_id=report_id,
        generated_at=generated_at,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        conversion_rate=_rate(total_conversions, total_clicks),
        ctr=_rate(total_clicks, impressions),
        estimated_commission=round(total_commission, 4),
        total_revenue=round(total_revenue, 4),
        impressions=impressions,
        by_merchant=by_merchant,
        by_product=by_product,
        by_category=by_category,
        top_converting_merchants=top_merchants,
        top_converting_products=top_products,
        currency=currency,
    )
