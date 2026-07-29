"""Affiliate Revenue Engine API request and response schemas — Sprint 20."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AffiliateMerchantCreateRequest(BaseModel):
    merchant_name: str = Field(..., min_length=1)
    marketplace: str = Field(..., min_length=1)
    country: str = Field(default="US", min_length=1)
    affiliate_network: str = Field(..., min_length=1)
    tracking_template: str = Field(..., min_length=1)
    commission_type: str = "percent"
    commission_value: float = Field(default=0.0, ge=0)
    cookie_days: int = Field(default=7, ge=0)
    status: str = "active"
    priority: int = 100
    health_status: str = "healthy"
    allowed_countries: list[str] = Field(default_factory=list)
    deep_link_supported: bool = True


class AffiliateMerchantUpdateRequest(BaseModel):
    merchant_name: str | None = None
    tracking_template: str | None = None
    commission_type: str | None = None
    commission_value: float | None = Field(default=None, ge=0)
    cookie_days: int | None = Field(default=None, ge=0)
    status: str | None = None
    priority: int | None = None
    health_status: str | None = None
    allowed_countries: list[str] | None = None
    deep_link_supported: bool | None = None
    country: str | None = None


class AffiliateCommissionUpdateRequest(BaseModel):
    commission_type: str = Field(..., min_length=1)
    commission_value: float = Field(..., ge=0)


class AffiliatePriorityUpdateRequest(BaseModel):
    priority: int


class AffiliateCountriesUpdateRequest(BaseModel):
    allowed_countries: list[str] = Field(default_factory=list)


class AffiliateHealthUpdateRequest(BaseModel):
    health_status: str = Field(..., min_length=1)


class AffiliateMerchantPayload(BaseModel):
    merchant_id: str
    merchant_name: str
    marketplace: str
    country: str
    affiliate_network: str
    tracking_template: str
    commission_type: str
    commission_value: float
    cookie_days: int
    status: str
    priority: int
    created_at: str
    updated_at: str
    health_status: str
    allowed_countries: list[str] = Field(default_factory=list)
    deep_link_supported: bool = True
    notes: str = ""
    simulated: bool = True


class AffiliateMerchantListResponse(BaseModel):
    merchants: list[AffiliateMerchantPayload] = Field(default_factory=list)
    disclaimer: str = (
        "Placeholder merchants only — no real affiliate credentials, APIs, or payouts."
    )


class AffiliateLinkGenerateRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1)
    marketplace: str | None = None
    merchant_id: str | None = None
    original_url: str | None = None
    product_ref: str | None = None
    campaign_id: str | None = None
    sub_id: str | None = None
    click_id: str | None = None
    country: str | None = None
    category: str | None = None
    order_value: float | None = Field(default=None, ge=0)
    deep_link: bool = False
    currency: str = "USD"


class AffiliateLinkPayload(BaseModel):
    link_id: str
    merchant_id: str
    product_id: str
    product_name: str
    original_url: str
    affiliate_url: str
    marketplace: str
    campaign_id: str | None = None
    sub_id: str | None = None
    click_id: str | None = None
    deep_link: bool = False
    created_at: str
    category: str | None = None
    estimated_commission: float | None = None
    currency: str = "USD"
    disclosure_required: bool = True
    simulated: bool = True
    disclaimer: str = (
        "Generated demo affiliate link — no real network tracking or commissions."
    )


class AffiliateLinkListResponse(BaseModel):
    links: list[AffiliateLinkPayload] = Field(default_factory=list)
    disclaimer: str = "Demo affiliate links only — no real network tracking."


class AffiliateClickTrackRequest(BaseModel):
    merchant_id: str | None = None
    product_id: str | None = None
    link_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    device: str | None = None
    country: str | None = None
    campaign_id: str | None = None
    source: str = "unknown"
    referrer: str | None = None
    product_name: str | None = None
    category: str | None = None
    revenue: float = Field(default=0.0, ge=0)
    estimated_commission: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AffiliateClickConversionRequest(BaseModel):
    conversion_status: str = Field(..., min_length=1)
    revenue: float | None = Field(default=None, ge=0)
    estimated_commission: float | None = Field(default=None, ge=0)


class AffiliateAttributeRequest(BaseModel):
    model: str = "last_click"
    user_id: str | None = None
    session_id: str | None = None
    product_id: str | None = None
    merchant_id: str | None = None
    revenue: float = Field(default=0.0, ge=0)
    estimated_commission: float = Field(default=0.0, ge=0)
    mark_click_converted: bool = True


class AffiliateClickPayload(BaseModel):
    click_id: str
    user_id: str | None = None
    session_id: str | None = None
    merchant_id: str
    product_id: str
    timestamp: str
    device: str | None = None
    country: str | None = None
    campaign_id: str | None = None
    source: str
    referrer: str | None = None
    conversion_status: str
    revenue: float = 0.0
    link_id: str | None = None
    product_name: str | None = None
    category: str | None = None
    marketplace: str | None = None
    attribution_model: str = "last_click"
    estimated_commission: float = 0.0
    currency: str = "USD"
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulated: bool = True


class AffiliateClickListResponse(BaseModel):
    clicks: list[AffiliateClickPayload] = Field(default_factory=list)
    disclaimer: str = "Demo click tracking only — no real conversion postbacks."


class AttributionResultPayload(BaseModel):
    attribution_id: str
    model: str
    click_id: str | None = None
    merchant_id: str | None = None
    product_id: str | None = None
    attributed_at: str
    revenue: float = 0.0
    estimated_commission: float = 0.0
    reason: str
    candidates_considered: int = 0
    currency: str = "USD"
    simulated: bool = True


class RevenueBucketPayload(BaseModel):
    key: str
    label: str
    clicks: int
    conversions: int
    revenue: float
    estimated_commission: float
    conversion_rate: float
    currency: str = "USD"


class AffiliateReportResponse(BaseModel):
    report_id: str
    generated_at: str
    total_clicks: int
    total_conversions: int
    conversion_rate: float
    ctr: float
    estimated_commission: float
    total_revenue: float
    impressions: int
    by_merchant: list[RevenueBucketPayload] = Field(default_factory=list)
    by_product: list[RevenueBucketPayload] = Field(default_factory=list)
    by_category: list[RevenueBucketPayload] = Field(default_factory=list)
    top_converting_merchants: list[RevenueBucketPayload] = Field(default_factory=list)
    top_converting_products: list[RevenueBucketPayload] = Field(default_factory=list)
    currency: str = "USD"
    disclaimer: str = (
        "Demo affiliate report — no real commissions, conversions, billing, or payouts."
    )
    simulated: bool = True


class AffiliateDisclosureCreateRequest(BaseModel):
    disclosure_type: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    region: str | None = None
    merchant_id: str | None = None
    locale: str = "en"
    ftc_placeholder: bool = True
    active: bool = True


class AffiliateDisclosurePayload(BaseModel):
    disclosure_id: str
    disclosure_type: str
    text: str
    region: str | None = None
    merchant_id: str | None = None
    locale: str
    created_at: str
    updated_at: str
    ftc_placeholder: bool = True
    active: bool = True


class AffiliateDisclosureResolveResponse(BaseModel):
    disclosures: list[AffiliateDisclosurePayload] = Field(default_factory=list)
    combined_text: str
    region: str | None = None
    merchant_id: str | None = None
    ftc_placeholder: bool = True
    disclaimer: str = (
        "Disclosure text is a demo placeholder and is not legal advice."
    )


class AffiliateDisclosureListResponse(BaseModel):
    disclosures: list[AffiliateDisclosurePayload] = Field(default_factory=list)
    disclaimer: str = "Demo disclosure copy only — not legal advice."
