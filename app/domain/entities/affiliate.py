"""Affiliate Revenue Engine domain entities — Sprint 20.

Merchant registry, generated affiliate links, click tracking, attribution,
and disclosure records. Affiliate data is applied **after** recommendation
selection only — never as a DealScore or ranking input.

Identifiers and timestamps are injected by callers — core types never
generate random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MarketplacePlaceholder(StrEnum):
    """Supported merchant marketplace placeholders (demo only — no real APIs)."""

    AMAZON = "amazon"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    TIKTOK_SHOP = "tiktok_shop"
    EBAY = "ebay"
    ALIEXPRESS = "aliexpress"


class AffiliateNetwork(StrEnum):
    """Placeholder affiliate network labels (no real network credentials)."""

    AMAZON_ASSOCIATES = "amazon_associates"
    SHOPEE_AFFILIATE = "shopee_affiliate"
    LAZADA_AFFILIATE = "lazada_affiliate"
    TIKTOK_SHOP_AFFILIATE = "tiktok_shop_affiliate"
    EBAY_PARTNER = "ebay_partner"
    ALIEXPRESS_AFFILIATE = "aliexpress_affiliate"
    DEMO_NETWORK = "demo_network"


class CommissionType(StrEnum):
    """How estimated commission is expressed (demo estimates only)."""

    PERCENT = "percent"
    FIXED = "fixed"


class MerchantStatus(StrEnum):
    """Administrative lifecycle for a merchant registry entry."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"


class MerchantHealthStatus(StrEnum):
    """Synthetic health signal for demo dashboards (no real ping)."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    DOWN = "down"


class ConversionStatus(StrEnum):
    """Click → conversion lifecycle (simulated; no real conversions)."""

    CLICKED = "clicked"
    PENDING = "pending"
    ATTRIBUTED = "attributed"
    CONVERTED = "converted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AttributionModel(StrEnum):
    """Supported attribution models for the demo attribution engine."""

    LAST_CLICK = "last_click"
    FIRST_CLICK = "first_click"
    DIRECT = "direct"
    ORGANIC = "organic"
    INTERNAL_RECOMMENDATION = "internal_recommendation"
    EXTERNAL_CAMPAIGN = "external_campaign"


class ClickSource(StrEnum):
    """Where a tracked click originated."""

    SHOPPING_ASSISTANT = "shopping_assistant"
    RECOMMENDATION_API = "recommendation_api"
    AFFILIATE_DASHBOARD = "affiliate_dashboard"
    DIRECT_LINK = "direct_link"
    EXTERNAL_CAMPAIGN = "external_campaign"
    ORGANIC = "organic"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AffiliateMerchant:
    """Merchant registry entry with placeholder commission / tracking config."""

    merchant_id: str
    merchant_name: str
    marketplace: MarketplacePlaceholder
    country: str
    affiliate_network: AffiliateNetwork
    tracking_template: str
    commission_type: CommissionType
    commission_value: float
    cookie_days: int
    status: MerchantStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    health_status: MerchantHealthStatus = MerchantHealthStatus.HEALTHY
    allowed_countries: tuple[str, ...] = ()
    deep_link_supported: bool = True
    notes: str = "Placeholder merchant — no real credentials or payouts."

    def to_dict(self) -> dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "marketplace": self.marketplace.value,
            "country": self.country,
            "affiliate_network": self.affiliate_network.value,
            "tracking_template": self.tracking_template,
            "commission_type": self.commission_type.value,
            "commission_value": self.commission_value,
            "cookie_days": self.cookie_days,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "health_status": self.health_status.value,
            "allowed_countries": list(self.allowed_countries),
            "deep_link_supported": self.deep_link_supported,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class AffiliateLink:
    """A generated affiliate URL for a product after recommendation selection."""

    link_id: str
    merchant_id: str
    product_id: str
    product_name: str
    original_url: str
    affiliate_url: str
    marketplace: MarketplacePlaceholder
    campaign_id: str | None
    sub_id: str | None
    click_id: str | None
    deep_link: bool
    created_at: datetime
    category: str | None = None
    estimated_commission: float | None = None
    currency: str = "USD"
    disclosure_required: bool = True
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "merchant_id": self.merchant_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "original_url": self.original_url,
            "affiliate_url": self.affiliate_url,
            "marketplace": self.marketplace.value,
            "campaign_id": self.campaign_id,
            "sub_id": self.sub_id,
            "click_id": self.click_id,
            "deep_link": self.deep_link,
            "created_at": self.created_at.isoformat(),
            "category": self.category,
            "estimated_commission": self.estimated_commission,
            "currency": self.currency,
            "disclosure_required": self.disclosure_required,
            "simulated": self.simulated,
        }


@dataclass(frozen=True, slots=True)
class AffiliateClick:
    """Tracked affiliate click event (demo store — no real network callbacks)."""

    click_id: str
    user_id: str | None
    session_id: str | None
    merchant_id: str
    product_id: str
    timestamp: datetime
    device: str | None
    country: str | None
    campaign_id: str | None
    source: ClickSource
    referrer: str | None
    conversion_status: ConversionStatus
    revenue: float
    link_id: str | None = None
    product_name: str | None = None
    category: str | None = None
    marketplace: MarketplacePlaceholder | None = None
    attribution_model: AttributionModel = AttributionModel.LAST_CLICK
    estimated_commission: float = 0.0
    currency: str = "USD"
    metadata: dict[str, Any] = field(default_factory=dict)
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "click_id": self.click_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "merchant_id": self.merchant_id,
            "product_id": self.product_id,
            "timestamp": self.timestamp.isoformat(),
            "device": self.device,
            "country": self.country,
            "campaign_id": self.campaign_id,
            "source": self.source.value,
            "referrer": self.referrer,
            "conversion_status": self.conversion_status.value,
            "revenue": self.revenue,
            "link_id": self.link_id,
            "product_name": self.product_name,
            "category": self.category,
            "marketplace": self.marketplace.value if self.marketplace else None,
            "attribution_model": self.attribution_model.value,
            "estimated_commission": self.estimated_commission,
            "currency": self.currency,
            "metadata": dict(self.metadata),
            "simulated": self.simulated,
        }


@dataclass(frozen=True, slots=True)
class AttributionResult:
    """Outcome of attributing a conversion (or simulated conversion) to a click."""

    attribution_id: str
    model: AttributionModel
    click_id: str | None
    merchant_id: str | None
    product_id: str | None
    attributed_at: datetime
    revenue: float
    estimated_commission: float
    reason: str
    candidates_considered: int = 0
    currency: str = "USD"
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "attribution_id": self.attribution_id,
            "model": self.model.value,
            "click_id": self.click_id,
            "merchant_id": self.merchant_id,
            "product_id": self.product_id,
            "attributed_at": self.attributed_at.isoformat(),
            "revenue": self.revenue,
            "estimated_commission": self.estimated_commission,
            "reason": self.reason,
            "candidates_considered": self.candidates_considered,
            "currency": self.currency,
            "simulated": self.simulated,
        }


@dataclass(frozen=True, slots=True)
class AffiliateDisclosure:
    """Affiliate / FTC disclosure text for a region or merchant context."""

    disclosure_id: str
    disclosure_type: str
    text: str
    region: str | None
    merchant_id: str | None
    locale: str
    created_at: datetime
    updated_at: datetime
    ftc_placeholder: bool = True
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "disclosure_id": self.disclosure_id,
            "disclosure_type": self.disclosure_type,
            "text": self.text,
            "region": self.region,
            "merchant_id": self.merchant_id,
            "locale": self.locale,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ftc_placeholder": self.ftc_placeholder,
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class RevenueReportBucket:
    """A single aggregation bucket for revenue reporting."""

    key: str
    label: str
    clicks: int
    conversions: int
    revenue: float
    estimated_commission: float
    conversion_rate: float
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "revenue": self.revenue,
            "estimated_commission": self.estimated_commission,
            "conversion_rate": self.conversion_rate,
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class AffiliateRevenueReport:
    """Dashboard aggregation over tracked clicks (demo estimates only)."""

    report_id: str
    generated_at: datetime
    total_clicks: int
    total_conversions: int
    conversion_rate: float
    ctr: float
    estimated_commission: float
    total_revenue: float
    impressions: int
    by_merchant: tuple[RevenueReportBucket, ...]
    by_product: tuple[RevenueReportBucket, ...]
    by_category: tuple[RevenueReportBucket, ...]
    top_converting_merchants: tuple[RevenueReportBucket, ...]
    top_converting_products: tuple[RevenueReportBucket, ...]
    currency: str = "USD"
    disclaimer: str = (
        "Demo affiliate report — no real commissions, conversions, billing, or payouts."
    )
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "total_clicks": self.total_clicks,
            "total_conversions": self.total_conversions,
            "conversion_rate": self.conversion_rate,
            "ctr": self.ctr,
            "estimated_commission": self.estimated_commission,
            "total_revenue": self.total_revenue,
            "impressions": self.impressions,
            "by_merchant": [b.to_dict() for b in self.by_merchant],
            "by_product": [b.to_dict() for b in self.by_product],
            "by_category": [b.to_dict() for b in self.by_category],
            "top_converting_merchants": [b.to_dict() for b in self.top_converting_merchants],
            "top_converting_products": [b.to_dict() for b in self.top_converting_products],
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "simulated": self.simulated,
        }
