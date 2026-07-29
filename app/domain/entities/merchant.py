"""Merchant Platform domain entities — Sprint 21.

Organizations, memberships, product/offer submissions, promotions, sponsored
campaign drafts, analytics summaries, and audit events.

Hard rules:
- Merchant tools never directly manipulate organic DealScore or ranking.
- Sponsored campaigns are labeled and rendered separately from organic results.
- Merchant-submitted data uses provenance MERCHANT_SUBMITTED (not live/verified).
- Demo analytics are labeled as demo/simulated; no fabricated real sales.

Identifiers and timestamps are injected by callers — core types never generate
random UUIDs or wall-clock times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MerchantRole(StrEnum):
    """Roles within a merchant organization (least privilege)."""

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    EDITOR = "editor"
    VIEWER = "viewer"
    INTERNAL_ADMIN = "internal_admin"


class MerchantPermission(StrEnum):
    """Fine-grained permissions enforced by the merchant security layer."""

    ORGANIZATION_MANAGE = "organization_manage"
    USER_MANAGE = "user_manage"
    PRODUCT_SUBMIT = "product_submit"
    OFFER_SUBMIT = "offer_submit"
    PROMOTION_MANAGE = "promotion_manage"
    ANALYTICS_ACCESS = "analytics_access"
    CAMPAIGN_MANAGE = "campaign_manage"
    VERIFICATION_REVIEW = "verification_review"
    AUDIT_LOG_ACCESS = "audit_log_access"
    ADMIN_REVIEW = "admin_review"


class MerchantOrgStatus(StrEnum):
    """Lifecycle status for a merchant organization."""

    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class MerchantVerificationStatus(StrEnum):
    """Verification state — documents are reference-only in this sprint."""

    UNVERIFIED = "unverified"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class InvitationStatus(StrEnum):
    """Merchant invitation lifecycle."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SubmissionStatus(StrEnum):
    """Product / offer submission review lifecycle."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


class MerchantSourceMode(StrEnum):
    """Provenance for merchant-submitted marketplace data.

    Distinct from marketplace SourceMode — merchant submissions must never be
    labeled as verified live data unless independently validated.
    """

    MERCHANT_SUBMITTED = "merchant_submitted"


class PromotionType(StrEnum):
    """Kinds of merchant promotions (do not auto-boost DealScore)."""

    SALE_PRICE = "sale_price"
    VOUCHER = "voucher"
    COUPON_CODE = "coupon_code"
    FREE_SHIPPING = "free_shipping"
    BUNDLE_OFFER = "bundle_offer"
    LIMITED_TIME = "limited_time"
    SEASONAL = "seasonal"
    CASHBACK = "cashback"


class PromotionStatus(StrEnum):
    """Promotion lifecycle."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    EXPIRED = "expired"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class CampaignPlacementType(StrEnum):
    """Sponsored placement types — always labeled as sponsored."""

    SPONSORED_PRODUCT = "sponsored_product"
    FEATURED_OFFER = "featured_offer"
    SPONSORED_COLLECTION = "sponsored_collection"
    BANNER_PLACEMENT = "banner_placement"


class MerchantCampaignStatus(StrEnum):
    """Sponsored campaign lifecycle (draft framework — no real billing)."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    REJECTED = "rejected"


class MerchantAuditAction(StrEnum):
    """Audit action vocabulary for merchant platform events."""

    ORGANIZATION_CREATED = "organization_created"
    PROFILE_UPDATED = "profile_updated"
    ORGANIZATION_ACTIVATED = "organization_activated"
    ORGANIZATION_DEACTIVATED = "organization_deactivated"
    ORGANIZATION_ARCHIVED = "organization_archived"
    ORGANIZATION_SUSPENDED = "organization_suspended"
    USER_INVITED = "user_invited"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_REJECTED = "invitation_rejected"
    MEMBERSHIP_ADDED = "membership_added"
    MEMBERSHIP_REMOVED = "membership_removed"
    ROLE_CHANGED = "role_changed"
    PRODUCT_SUBMITTED = "product_submitted"
    PRODUCT_UPDATED = "product_updated"
    PRODUCT_WITHDRAWN = "product_withdrawn"
    SUBMISSION_APPROVED = "submission_approved"
    SUBMISSION_REJECTED = "submission_rejected"
    OFFER_SUBMITTED = "offer_submitted"
    OFFER_UPDATED = "offer_updated"
    OFFER_DEACTIVATED = "offer_deactivated"
    PROMOTION_CREATED = "promotion_created"
    PROMOTION_UPDATED = "promotion_updated"
    PROMOTION_PAUSED = "promotion_paused"
    CAMPAIGN_CREATED = "campaign_created"
    CAMPAIGN_UPDATED = "campaign_updated"
    CAMPAIGN_PAUSED = "campaign_paused"
    CAMPAIGN_RESUMED = "campaign_resumed"
    CAMPAIGN_CANCELLED = "campaign_cancelled"
    VERIFICATION_UPDATED = "verification_updated"
    MATCH_REVIEW_CREATED = "match_review_created"


MERCHANT_SOURCE_LABEL = "Merchant-submitted data — not independently verified live data"
DEMO_ANALYTICS_LABEL = "Demo analytics — simulated, not live sales reporting"
SPONSORED_LABEL = "Sponsored — not an organic recommendation"


# Role → permission matrix (least privilege). INTERNAL_ADMIN has all.
ROLE_PERMISSIONS: dict[MerchantRole, frozenset[MerchantPermission]] = {
    MerchantRole.OWNER: frozenset(MerchantPermission),
    MerchantRole.ADMIN: frozenset(
        {
            MerchantPermission.ORGANIZATION_MANAGE,
            MerchantPermission.USER_MANAGE,
            MerchantPermission.PRODUCT_SUBMIT,
            MerchantPermission.OFFER_SUBMIT,
            MerchantPermission.PROMOTION_MANAGE,
            MerchantPermission.ANALYTICS_ACCESS,
            MerchantPermission.CAMPAIGN_MANAGE,
            MerchantPermission.AUDIT_LOG_ACCESS,
        }
    ),
    MerchantRole.MANAGER: frozenset(
        {
            MerchantPermission.PRODUCT_SUBMIT,
            MerchantPermission.OFFER_SUBMIT,
            MerchantPermission.PROMOTION_MANAGE,
            MerchantPermission.ANALYTICS_ACCESS,
            MerchantPermission.CAMPAIGN_MANAGE,
        }
    ),
    MerchantRole.ANALYST: frozenset(
        {
            MerchantPermission.ANALYTICS_ACCESS,
            MerchantPermission.AUDIT_LOG_ACCESS,
        }
    ),
    MerchantRole.EDITOR: frozenset(
        {
            MerchantPermission.PRODUCT_SUBMIT,
            MerchantPermission.OFFER_SUBMIT,
            MerchantPermission.PROMOTION_MANAGE,
        }
    ),
    MerchantRole.VIEWER: frozenset(
        {
            MerchantPermission.ANALYTICS_ACCESS,
        }
    ),
    MerchantRole.INTERNAL_ADMIN: frozenset(MerchantPermission),
}


# ---------------------------------------------------------------------------
# Value objects / entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MerchantProfile:
    """Public/business profile for a merchant organization."""

    business_name: str
    legal_name: str
    display_name: str
    country: str
    business_category: str
    website: str | None = None
    support_email: str | None = None
    marketplace_presence: tuple[str, ...] = ()
    business_description: str = ""
    logo_reference: str | None = None
    contact_references: tuple[str, ...] = ()
    verification_status: MerchantVerificationStatus = MerchantVerificationStatus.UNVERIFIED
    terms_accepted_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_name": self.business_name,
            "legal_name": self.legal_name,
            "display_name": self.display_name,
            "country": self.country,
            "business_category": self.business_category,
            "website": self.website,
            "support_email": self.support_email,
            "marketplace_presence": list(self.marketplace_presence),
            "business_description": self.business_description,
            "logo_reference": self.logo_reference,
            "contact_references": list(self.contact_references),
            "verification_status": self.verification_status.value,
            "terms_accepted_at": (
                self.terms_accepted_at.isoformat() if self.terms_accepted_at else None
            ),
        }


@dataclass(frozen=True, slots=True)
class MerchantVerification:
    """Verification record — document refs only (no identity docs stored)."""

    verification_id: str
    organization_id: str
    status: MerchantVerificationStatus
    created_at: datetime
    updated_at: datetime
    reviewed_by: str | None = None
    notes: str = ""
    # Future architecture only — opaque document references, never raw contents.
    document_references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "organization_id": self.organization_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reviewed_by": self.reviewed_by,
            "notes": self.notes,
            "document_references": list(self.document_references),
            "limitation": "Verification documents are reference architecture only — not stored.",
        }


@dataclass(frozen=True, slots=True)
class MerchantOrganization:
    """A merchant organization (tenant) on the Merchant Platform."""

    organization_id: str
    profile: MerchantProfile
    status: MerchantOrgStatus
    owner_account_id: str
    created_at: datetime
    updated_at: datetime
    affiliate_merchant_id: str | None = None
    archived_at: datetime | None = None
    notes: str = "Demo merchant organization — in-memory only."

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "profile": self.profile.to_dict(),
            "status": self.status.value,
            "owner_account_id": self.owner_account_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "affiliate_merchant_id": self.affiliate_merchant_id,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class MerchantAccount:
    """Login identity for a merchant user or internal admin (demo tokens)."""

    account_id: str
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    is_internal_admin: bool = False
    # Demo opaque session token — not a production credential.
    demo_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "is_internal_admin": self.is_internal_admin,
            # demo_token intentionally omitted from public serialization
        }


@dataclass(frozen=True, slots=True)
class MerchantUser:
    """Person record linked to a merchant account (display / contact)."""

    user_id: str
    account_id: str
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "account_id": self.account_id,
            "email": self.email,
            "display_name": self.display_name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MerchantMembership:
    """Membership of an account in an organization with a role."""

    membership_id: str
    organization_id: str
    account_id: str
    role: MerchantRole
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "membership_id": self.membership_id,
            "organization_id": self.organization_id,
            "account_id": self.account_id,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "permissions": [p.value for p in ROLE_PERMISSIONS.get(self.role, frozenset())],
        }


@dataclass(frozen=True, slots=True)
class MerchantInvitation:
    """Invitation for an email to join an organization."""

    invitation_id: str
    organization_id: str
    email: str
    role: MerchantRole
    invited_by_account_id: str
    status: InvitationStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invitation_id": self.invitation_id,
            "organization_id": self.organization_id,
            "email": self.email,
            "role": self.role.value,
            "invited_by_account_id": self.invited_by_account_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass(frozen=True, slots=True)
class MerchantMarketplaceAccount:
    """Link between a merchant org and a marketplace seller presence."""

    marketplace_account_id: str
    organization_id: str
    marketplace: str
    seller_name: str
    external_seller_id: str | None = None
    country: str = "US"
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "marketplace_account_id": self.marketplace_account_id,
            "organization_id": self.organization_id,
            "marketplace": self.marketplace,
            "seller_name": self.seller_name,
            "external_seller_id": self.external_seller_id,
            "country": self.country,
            "is_active": self.is_active,
        }


@dataclass(frozen=True, slots=True)
class MerchantNotificationPreference:
    """Notification preferences for a merchant account (in-app only)."""

    preference_id: str
    account_id: str
    organization_id: str
    submission_updates: bool = True
    campaign_updates: bool = True
    analytics_digest: bool = False
    # No external email sending in this sprint.
    email_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "preference_id": self.preference_id,
            "account_id": self.account_id,
            "organization_id": self.organization_id,
            "submission_updates": self.submission_updates,
            "campaign_updates": self.campaign_updates,
            "analytics_digest": self.analytics_digest,
            "email_enabled": self.email_enabled,
            "limitation": "No external email sending in Sprint 21.",
        }


@dataclass(frozen=True, slots=True)
class MerchantMatchResult:
    """Product matching outcome for a merchant submission."""

    matched_product_id: str | None
    confidence: float
    reasons: tuple[str, ...]
    ambiguity: str
    candidate_ids: tuple[str, ...] = ()
    review_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_product_id": self.matched_product_id,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "ambiguity": self.ambiguity,
            "candidate_ids": list(self.candidate_ids),
            "review_required": self.review_required,
        }


@dataclass(frozen=True, slots=True)
class MerchantProductSubmission:
    """Merchant-submitted product pending validation / review."""

    submission_id: str
    organization_id: str
    submitted_by_account_id: str
    status: SubmissionStatus
    title: str
    brand: str | None
    model: str | None
    created_at: datetime
    updated_at: datetime
    category: str | None = None
    description: str = ""
    sku: str | None = None
    upc: str | None = None
    ean: str | None = None
    gtin: str | None = None
    merchant_product_id: str | None = None
    image_urls: tuple[str, ...] = ()
    identifiers: dict[str, str] = field(default_factory=dict)
    warranty: str | None = None
    seller_info: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    validation_errors: tuple[str, ...] = ()
    match_result: MerchantMatchResult | None = None
    source_mode: MerchantSourceMode = MerchantSourceMode.MERCHANT_SUBMITTED
    matched_product_id: str | None = None
    review_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "organization_id": self.organization_id,
            "submitted_by_account_id": self.submitted_by_account_id,
            "status": self.status.value,
            "title": self.title,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "description": self.description,
            "sku": self.sku,
            "upc": self.upc,
            "ean": self.ean,
            "gtin": self.gtin,
            "merchant_product_id": self.merchant_product_id,
            "image_urls": list(self.image_urls),
            "identifiers": dict(self.identifiers),
            "warranty": self.warranty,
            "seller_info": self.seller_info,
            "raw_payload": dict(self.raw_payload),
            "validation_errors": list(self.validation_errors),
            "match_result": self.match_result.to_dict() if self.match_result else None,
            "source_mode": self.source_mode.value,
            "source_label": MERCHANT_SOURCE_LABEL,
            "matched_product_id": self.matched_product_id,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MerchantOfferSubmission:
    """Merchant-submitted offer for an existing or pending product."""

    offer_id: str
    organization_id: str
    submitted_by_account_id: str
    status: SubmissionStatus
    title: str
    currency: str
    price: float
    created_at: datetime
    updated_at: datetime
    product_submission_id: str | None = None
    matched_product_id: str | None = None
    sale_price: float | None = None
    shipping_cost: float = 0.0
    inventory_quantity: int | None = None
    availability: str = "in_stock"
    marketplace_url: str | None = None
    warranty: str | None = None
    seller_details: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    validation_errors: tuple[str, ...] = ()
    source_mode: MerchantSourceMode = MerchantSourceMode.MERCHANT_SUBMITTED
    is_active: bool = True
    review_notes: str = ""

    @property
    def total_price(self) -> float:
        base = self.sale_price if self.sale_price is not None else self.price
        return float(base) + float(self.shipping_cost)

    def to_dict(self) -> dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "organization_id": self.organization_id,
            "submitted_by_account_id": self.submitted_by_account_id,
            "status": self.status.value,
            "title": self.title,
            "currency": self.currency,
            "price": self.price,
            "sale_price": self.sale_price,
            "shipping_cost": self.shipping_cost,
            "total_price": self.total_price,
            "inventory_quantity": self.inventory_quantity,
            "availability": self.availability,
            "marketplace_url": self.marketplace_url,
            "warranty": self.warranty,
            "seller_details": self.seller_details,
            "product_submission_id": self.product_submission_id,
            "matched_product_id": self.matched_product_id,
            "raw_payload": dict(self.raw_payload),
            "validation_errors": list(self.validation_errors),
            "source_mode": self.source_mode.value,
            "source_label": MERCHANT_SOURCE_LABEL,
            "is_active": self.is_active,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class MerchantPromotion:
    """Merchant promotion — does not automatically increase DealScore."""

    promotion_id: str
    organization_id: str
    created_by_account_id: str
    promotion_type: PromotionType
    status: PromotionStatus
    title: str
    created_at: datetime
    updated_at: datetime
    description: str = ""
    coupon_code: str | None = None
    sale_price: float | None = None
    currency: str = "USD"
    terms: str = ""
    product_ids: tuple[str, ...] = ()
    offer_ids: tuple[str, ...] = ()
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    cashback_description: str | None = None
    dealscore_independent: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "organization_id": self.organization_id,
            "created_by_account_id": self.created_by_account_id,
            "promotion_type": self.promotion_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "coupon_code": self.coupon_code,
            "sale_price": self.sale_price,
            "currency": self.currency,
            "terms": self.terms,
            "product_ids": list(self.product_ids),
            "offer_ids": list(self.offer_ids),
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "cashback_description": self.cashback_description,
            "dealscore_independent": self.dealscore_independent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "note": "Promotions do not automatically increase DealScore.",
        }


@dataclass(frozen=True, slots=True)
class MerchantCampaignBudget:
    """Budget metadata for a sponsored campaign (no real billing)."""

    currency: str
    daily_budget: float | None = None
    total_budget: float | None = None
    notes: str = "Budget metadata only — no real billing or payment collection."

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "daily_budget": self.daily_budget,
            "total_budget": self.total_budget,
            "notes": self.notes,
            "billing": "not_implemented",
        }


@dataclass(frozen=True, slots=True)
class MerchantCampaignPlacement:
    """A placement slot within a sponsored campaign."""

    placement_id: str
    placement_type: CampaignPlacementType
    product_ids: tuple[str, ...] = ()
    offer_ids: tuple[str, ...] = ()
    targeting_metadata: dict[str, Any] = field(default_factory=dict)
    sponsored_label: str = SPONSORED_LABEL

    def to_dict(self) -> dict[str, Any]:
        return {
            "placement_id": self.placement_id,
            "placement_type": self.placement_type.value,
            "product_ids": list(self.product_ids),
            "offer_ids": list(self.offer_ids),
            "targeting_metadata": dict(self.targeting_metadata),
            "sponsored_label": self.sponsored_label,
            "organic_ranking_independent": True,
        }


@dataclass(frozen=True, slots=True)
class MerchantCampaign:
    """Sponsored campaign draft framework — never alters organic rankings."""

    campaign_id: str
    organization_id: str
    created_by_account_id: str
    name: str
    status: MerchantCampaignStatus
    placements: tuple[MerchantCampaignPlacement, ...]
    budget: MerchantCampaignBudget
    created_at: datetime
    updated_at: datetime
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    targeting_metadata: dict[str, Any] = field(default_factory=dict)
    sponsored_label: str = SPONSORED_LABEL
    organic_ranking_independent: bool = True
    review_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "organization_id": self.organization_id,
            "created_by_account_id": self.created_by_account_id,
            "name": self.name,
            "status": self.status.value,
            "placements": [p.to_dict() for p in self.placements],
            "budget": self.budget.to_dict(),
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "targeting_metadata": dict(self.targeting_metadata),
            "sponsored_label": self.sponsored_label,
            "organic_ranking_independent": self.organic_ranking_independent,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "billing": "not_implemented",
        }


@dataclass(frozen=True, slots=True)
class MerchantProductPerformance:
    """Per-product performance row for merchant analytics (demo-labeled)."""

    product_id: str
    organization_id: str
    title: str
    product_views: int = 0
    offer_views: int = 0
    affiliate_clicks: int = 0
    click_through_rate: float = 0.0
    attributed_conversions: int = 0
    estimated_commission: float | None = None
    watchlist_additions: int = 0
    alert_activity: int = 0
    comparison_appearances: int = 0
    recommendation_appearances: int = 0
    dealscore: float | None = None
    data_freshness: str = "unknown"
    price_competitiveness: str = "unknown"
    seller_quality: str = "unknown"
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "organization_id": self.organization_id,
            "title": self.title,
            "product_views": self.product_views,
            "offer_views": self.offer_views,
            "affiliate_clicks": self.affiliate_clicks,
            "click_through_rate": self.click_through_rate,
            "attributed_conversions": self.attributed_conversions,
            "estimated_commission": self.estimated_commission,
            "watchlist_additions": self.watchlist_additions,
            "alert_activity": self.alert_activity,
            "comparison_appearances": self.comparison_appearances,
            "recommendation_appearances": self.recommendation_appearances,
            "dealscore": self.dealscore,
            "data_freshness": self.data_freshness,
            "price_competitiveness": self.price_competitiveness,
            "seller_quality": self.seller_quality,
            "simulated": self.simulated,
            "label": DEMO_ANALYTICS_LABEL if self.simulated else "analytics",
        }


@dataclass(frozen=True, slots=True)
class MerchantAffiliatePerformance:
    """Affiliate performance summary for a merchant org (read-only)."""

    organization_id: str
    affiliate_merchant_id: str | None
    affiliate_eligible: bool
    link_available: bool
    clicks: int = 0
    attributed_conversions: int = 0
    estimated_revenue: float | None = None
    conversion_status_summary: dict[str, int] = field(default_factory=dict)
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "affiliate_merchant_id": self.affiliate_merchant_id,
            "affiliate_eligible": self.affiliate_eligible,
            "link_available": self.link_available,
            "clicks": self.clicks,
            "attributed_conversions": self.attributed_conversions,
            "estimated_revenue": self.estimated_revenue,
            "conversion_status_summary": dict(self.conversion_status_summary),
            "simulated": self.simulated,
            "label": DEMO_ANALYTICS_LABEL if self.simulated else "affiliate_performance",
            "read_only": True,
        }


@dataclass(frozen=True, slots=True)
class RankingExplanationFactor:
    """A safe ranking explanation factor (no private/proprietary data)."""

    factor: str
    contribution: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor": self.factor,
            "contribution": self.contribution,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class RankingExplanation:
    """Safe explanation of why a product/offer ranks as it does."""

    product_id: str
    organization_id: str
    dealscore: float | None
    factors: tuple[RankingExplanationFactor, ...]
    organic_ranking_independent: bool = True
    note: str = "Explanations are informational only — merchants cannot alter organic ranking."

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "organization_id": self.organization_id,
            "dealscore": self.dealscore,
            "factors": [f.to_dict() for f in self.factors],
            "organic_ranking_independent": self.organic_ranking_independent,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class MerchantAnalyticsSummary:
    """Organization-level analytics rollup (demo-labeled)."""

    organization_id: str
    generated_at: datetime
    product_views: int = 0
    offer_views: int = 0
    affiliate_clicks: int = 0
    click_through_rate: float = 0.0
    attributed_conversions: int = 0
    estimated_commission: float | None = None
    watchlist_additions: int = 0
    alert_activity: int = 0
    comparison_appearances: int = 0
    recommendation_appearances: int = 0
    active_promotions: int = 0
    active_campaigns: int = 0
    products: tuple[MerchantProductPerformance, ...] = ()
    affiliate: MerchantAffiliatePerformance | None = None
    simulated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": self.organization_id,
            "generated_at": self.generated_at.isoformat(),
            "product_views": self.product_views,
            "offer_views": self.offer_views,
            "affiliate_clicks": self.affiliate_clicks,
            "click_through_rate": self.click_through_rate,
            "attributed_conversions": self.attributed_conversions,
            "estimated_commission": self.estimated_commission,
            "watchlist_additions": self.watchlist_additions,
            "alert_activity": self.alert_activity,
            "comparison_appearances": self.comparison_appearances,
            "recommendation_appearances": self.recommendation_appearances,
            "active_promotions": self.active_promotions,
            "active_campaigns": self.active_campaigns,
            "products": [p.to_dict() for p in self.products],
            "affiliate": self.affiliate.to_dict() if self.affiliate else None,
            "simulated": self.simulated,
            "label": DEMO_ANALYTICS_LABEL if self.simulated else "analytics",
        }


@dataclass(frozen=True, slots=True)
class MerchantAuditEvent:
    """Audit log entry for merchant platform actions."""

    event_id: str
    actor_account_id: str
    organization_id: str | None
    action: MerchantAuditAction
    target_type: str
    target_id: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "actor_account_id": self.actor_account_id,
            "organization_id": self.organization_id,
            "action": self.action.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MerchantMatchReview:
    """Review record for ambiguous product matching."""

    review_id: str
    organization_id: str
    submission_id: str
    ambiguity: str
    confidence: float
    candidate_ids: tuple[str, ...]
    created_at: datetime
    status: str = "open"
    resolved_product_id: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "organization_id": self.organization_id,
            "submission_id": self.submission_id,
            "ambiguity": self.ambiguity,
            "confidence": self.confidence,
            "candidate_ids": list(self.candidate_ids),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "resolved_product_id": self.resolved_product_id,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class MerchantActor:
    """Resolved authenticated actor for authorization checks."""

    account: MerchantAccount
    membership: MerchantMembership | None = None
    organization_id: str | None = None

    @property
    def account_id(self) -> str:
        return self.account.account_id

    @property
    def is_internal_admin(self) -> bool:
        return self.account.is_internal_admin

    @property
    def role(self) -> MerchantRole | None:
        if self.is_internal_admin:
            return MerchantRole.INTERNAL_ADMIN
        if self.membership is not None:
            return self.membership.role
        return None

    def has_permission(self, permission: MerchantPermission) -> bool:
        if self.is_internal_admin:
            return True
        role = self.role
        if role is None:
            return False
        return permission in ROLE_PERMISSIONS.get(role, frozenset())

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "email": self.account.email,
            "display_name": self.account.display_name,
            "is_internal_admin": self.is_internal_admin,
            "organization_id": self.organization_id,
            "role": self.role.value if self.role else None,
            "permissions": (
                [p.value for p in ROLE_PERMISSIONS.get(self.role, frozenset())] if self.role else []
            ),
        }
