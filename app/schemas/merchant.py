"""Merchant Platform API request/response schemas — Sprint 21."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MerchantProfilePayload(BaseModel):
    business_name: str
    legal_name: str
    display_name: str
    country: str
    business_category: str
    website: str | None = None
    support_email: str | None = None
    marketplace_presence: list[str] = Field(default_factory=list)
    business_description: str = ""
    logo_reference: str | None = None
    contact_references: list[str] = Field(default_factory=list)
    verification_status: str
    terms_accepted_at: str | None = None


class MerchantOrganizationPayload(BaseModel):
    organization_id: str
    profile: MerchantProfilePayload
    status: str
    owner_account_id: str
    created_at: str
    updated_at: str
    affiliate_merchant_id: str | None = None
    archived_at: str | None = None
    notes: str = ""


class MerchantOrganizationListResponse(BaseModel):
    items: list[MerchantOrganizationPayload]
    disclaimer: str = "Demo merchants only — in-memory persistence."


class MerchantOrganizationCreateRequest(BaseModel):
    business_name: str
    legal_name: str
    display_name: str
    country: str
    business_category: str
    website: str | None = None
    support_email: str | None = None
    marketplace_presence: list[str] = Field(default_factory=list)
    business_description: str = ""
    logo_reference: str | None = None
    contact_references: list[str] = Field(default_factory=list)
    affiliate_merchant_id: str | None = None
    accept_terms: bool = False


class MerchantOrganizationUpdateRequest(BaseModel):
    business_name: str | None = None
    legal_name: str | None = None
    display_name: str | None = None
    country: str | None = None
    business_category: str | None = None
    website: str | None = None
    support_email: str | None = None
    marketplace_presence: list[str] | None = None
    business_description: str | None = None
    logo_reference: str | None = None
    contact_references: list[str] | None = None


class MerchantMembershipPayload(BaseModel):
    membership_id: str
    organization_id: str
    account_id: str
    role: str
    created_at: str
    updated_at: str
    is_active: bool
    permissions: list[str] = Field(default_factory=list)


class MerchantMembershipListResponse(BaseModel):
    items: list[MerchantMembershipPayload]


class MerchantInvitationCreateRequest(BaseModel):
    email: str
    role: str = "viewer"


class MerchantInvitationPayload(BaseModel):
    invitation_id: str
    organization_id: str
    email: str
    role: str
    invited_by_account_id: str
    status: str
    created_at: str
    updated_at: str
    expires_at: str | None = None


class MerchantRoleUpdateRequest(BaseModel):
    role: str


class MerchantProductCreateRequest(BaseModel):
    title: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    description: str = ""
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    merchant_product_id: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)
    warranty: str | None = None
    seller_info: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class MerchantProductUpdateRequest(BaseModel):
    title: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    description: str | None = None
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    merchant_product_id: str | None = None
    image_urls: list[str] | None = None
    identifiers: dict[str, str] | None = None
    warranty: str | None = None
    seller_info: str | None = None
    raw_payload: dict[str, Any] | None = None


class MerchantMatchResultPayload(BaseModel):
    matched_product_id: str | None
    confidence: float
    reasons: list[str]
    ambiguity: str
    candidate_ids: list[str] = Field(default_factory=list)
    review_required: bool = False


class MerchantProductPayload(BaseModel):
    submission_id: str
    organization_id: str
    submitted_by_account_id: str
    status: str
    title: str
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    description: str = ""
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    merchant_product_id: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    identifiers: dict[str, str] = Field(default_factory=dict)
    warranty: str | None = None
    seller_info: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    match_result: MerchantMatchResultPayload | None = None
    source_mode: str
    source_label: str
    matched_product_id: str | None = None
    review_notes: str = ""
    created_at: str
    updated_at: str


class MerchantProductListResponse(BaseModel):
    items: list[MerchantProductPayload]
    disclaimer: str = "Merchant-submitted data — not independently verified live data"


class MerchantOfferCreateRequest(BaseModel):
    title: str
    currency: str
    price: float
    sale_price: float | None = None
    shipping_cost: float = 0.0
    inventory_quantity: int | None = None
    availability: str = "in_stock"
    marketplace_url: str | None = None
    warranty: str | None = None
    seller_details: str | None = None
    product_submission_id: str | None = None
    matched_product_id: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class MerchantOfferUpdateRequest(BaseModel):
    title: str | None = None
    currency: str | None = None
    price: float | None = None
    sale_price: float | None = None
    shipping_cost: float | None = None
    inventory_quantity: int | None = None
    availability: str | None = None
    marketplace_url: str | None = None
    warranty: str | None = None
    seller_details: str | None = None
    raw_payload: dict[str, Any] | None = None


class MerchantOfferPayload(BaseModel):
    offer_id: str
    organization_id: str
    submitted_by_account_id: str
    status: str
    title: str
    currency: str
    price: float
    sale_price: float | None = None
    shipping_cost: float
    total_price: float
    inventory_quantity: int | None = None
    availability: str
    marketplace_url: str | None = None
    warranty: str | None = None
    seller_details: str | None = None
    product_submission_id: str | None = None
    matched_product_id: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    source_mode: str
    source_label: str
    is_active: bool
    review_notes: str = ""
    created_at: str
    updated_at: str


class MerchantOfferListResponse(BaseModel):
    items: list[MerchantOfferPayload]
    disclaimer: str = "Merchant-submitted data — not independently verified live data"


class MerchantPromotionCreateRequest(BaseModel):
    promotion_type: str
    title: str
    description: str = ""
    coupon_code: str | None = None
    sale_price: float | None = None
    currency: str = "USD"
    terms: str = ""
    product_ids: list[str] = Field(default_factory=list)
    offer_ids: list[str] = Field(default_factory=list)
    starts_at: str | None = None
    ends_at: str | None = None
    cashback_description: str | None = None
    status: str = "draft"


class MerchantPromotionUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    coupon_code: str | None = None
    sale_price: float | None = None
    currency: str | None = None
    terms: str | None = None
    product_ids: list[str] | None = None
    offer_ids: list[str] | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    cashback_description: str | None = None


class MerchantPromotionPayload(BaseModel):
    promotion_id: str
    organization_id: str
    created_by_account_id: str
    promotion_type: str
    status: str
    title: str
    description: str = ""
    coupon_code: str | None = None
    sale_price: float | None = None
    currency: str
    terms: str = ""
    product_ids: list[str] = Field(default_factory=list)
    offer_ids: list[str] = Field(default_factory=list)
    starts_at: str | None = None
    ends_at: str | None = None
    cashback_description: str | None = None
    dealscore_independent: bool = True
    created_at: str
    updated_at: str
    note: str = ""


class MerchantPromotionListResponse(BaseModel):
    items: list[MerchantPromotionPayload]
    disclaimer: str = "Promotions do not automatically increase DealScore."


class MerchantCampaignCreateRequest(BaseModel):
    name: str
    product_ids: list[str] = Field(default_factory=list)
    placement_types: list[str] = Field(default_factory=lambda: ["sponsored_product"])
    currency: str = "USD"
    daily_budget: float | None = None
    total_budget: float | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    targeting_metadata: dict[str, Any] = Field(default_factory=dict)
    placements: list[dict[str, Any]] | None = None


class MerchantCampaignUpdateRequest(BaseModel):
    name: str | None = None
    product_ids: list[str] | None = None
    placement_types: list[str] | None = None
    currency: str | None = None
    daily_budget: float | None = None
    total_budget: float | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    targeting_metadata: dict[str, Any] | None = None
    placements: list[dict[str, Any]] | None = None


class MerchantCampaignPayload(BaseModel):
    campaign_id: str
    organization_id: str
    created_by_account_id: str
    name: str
    status: str
    placements: list[dict[str, Any]]
    budget: dict[str, Any]
    starts_at: str | None = None
    ends_at: str | None = None
    targeting_metadata: dict[str, Any] = Field(default_factory=dict)
    sponsored_label: str
    organic_ranking_independent: bool = True
    review_notes: str = ""
    created_at: str
    updated_at: str
    billing: str = "not_implemented"


class MerchantCampaignListResponse(BaseModel):
    items: list[MerchantCampaignPayload]
    disclaimer: str = "Draft sponsored campaigns — no real billing; never alter organic rankings."


class MerchantAnalyticsResponse(BaseModel):
    organization_id: str
    generated_at: str
    product_views: int
    offer_views: int
    affiliate_clicks: int
    click_through_rate: float
    attributed_conversions: int
    estimated_commission: float | None = None
    watchlist_additions: int = 0
    alert_activity: int = 0
    comparison_appearances: int = 0
    recommendation_appearances: int = 0
    active_promotions: int = 0
    active_campaigns: int = 0
    products: list[dict[str, Any]] = Field(default_factory=list)
    affiliate: dict[str, Any] | None = None
    simulated: bool = True
    label: str = "Demo analytics — simulated, not live sales reporting"


class MerchantAuditLogResponse(BaseModel):
    items: list[dict[str, Any]]


class MerchantRankingExplanationResponse(BaseModel):
    product_id: str
    organization_id: str
    dealscore: float | None = None
    factors: list[dict[str, Any]]
    organic_ranking_independent: bool = True
    note: str = ""


class MerchantAdminRejectRequest(BaseModel):
    notes: str = ""
    needs_changes: bool = False


class MerchantAdminNotesRequest(BaseModel):
    notes: str = ""


class MerchantVerificationUpdateRequest(BaseModel):
    status: str
    notes: str = ""


class MerchantDemoMetaResponse(BaseModel):
    demo_accounts: list[dict[str, Any]]
    limitations: list[str]
    roles: list[str]
