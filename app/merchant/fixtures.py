"""Deterministic demo merchants for Merchant Platform v1 — Sprint 21.

Demo accounts only. In-memory persistence. No production verification documents,
real billing, or external email.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain.entities.merchant import (
    CampaignPlacementType,
    InvitationStatus,
    MerchantAccount,
    MerchantCampaign,
    MerchantCampaignBudget,
    MerchantCampaignPlacement,
    MerchantCampaignStatus,
    MerchantInvitation,
    MerchantMarketplaceAccount,
    MerchantMembership,
    MerchantOfferSubmission,
    MerchantOrganization,
    MerchantOrgStatus,
    MerchantProductSubmission,
    MerchantProfile,
    MerchantPromotion,
    MerchantRole,
    MerchantUser,
    MerchantVerification,
    MerchantVerificationStatus,
    PromotionStatus,
    PromotionType,
    SubmissionStatus,
)
from app.marketplace.matching.matcher import CatalogEntry

SEED_NOW = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)

LIMITATIONS: tuple[str, ...] = (
    "Demo merchants only — not a public merchant self-service launch.",
    "In-memory persistence only — data resets on process restart.",
    "No production merchant verification documents.",
    "No real sponsored billing or payment processing.",
    "No merchant payouts.",
    "No live sales reporting unless supported by affiliate demo data.",
    "No ranking manipulation — merchants cannot alter organic PiqScore.",
    "No production database.",
    "No subscription billing.",
    "No external email sending.",
)

# Deterministic demo tokens (opaque demo session keys — not production secrets).
DEMO_TOKENS = {
    "acct-techhaven-owner": "demo-token-techhaven-owner",
    "acct-techhaven-editor": "demo-token-techhaven-editor",
    "acct-gadgetgrove-owner": "demo-token-gadgetgrove-owner",
    "acct-internal-admin": "demo-token-internal-admin",
}


def _dt(offset_hours: int = 0) -> datetime:
    return SEED_NOW + timedelta(hours=offset_hours)


DEMO_CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        product_id="prod-laptop-x1",
        brand="NovaTech",
        model="X1 Pro",
        title="NovaTech X1 Pro 14-inch Laptop",
        sku="NT-X1PRO-14",
        upc="012345678901",
        ean="5012345678900",
        gtin="0123456789012",
        aliases=("novatech x1", "x1 pro laptop"),
        marketplace_product_ids=("mp-x1-001",),
    ),
    CatalogEntry(
        product_id="prod-phone-z5",
        brand="PulseMobile",
        model="Z5",
        title="PulseMobile Z5 Smartphone",
        sku="PM-Z5-128",
        upc="098765432109",
        aliases=("pulse z5", "z5 phone"),
        marketplace_product_ids=("mp-z5-001",),
    ),
    CatalogEntry(
        product_id="prod-headphones-a9",
        brand="AudioWave",
        model="A9",
        title="AudioWave A9 Wireless Headphones",
        sku="AW-A9-BLK",
        aliases=("audiowave a9", "a9 headphones"),
        marketplace_product_ids=("mp-a9-001",),
    ),
)


def build_demo_accounts() -> list[MerchantAccount]:
    return [
        MerchantAccount(
            account_id="acct-techhaven-owner",
            email="owner@techhaven.demo",
            display_name="TechHaven Owner",
            created_at=_dt(-720),
            updated_at=_dt(-24),
            is_active=True,
            is_internal_admin=False,
            demo_token=DEMO_TOKENS["acct-techhaven-owner"],
        ),
        MerchantAccount(
            account_id="acct-techhaven-editor",
            email="editor@techhaven.demo",
            display_name="TechHaven Editor",
            created_at=_dt(-700),
            updated_at=_dt(-24),
            is_active=True,
            is_internal_admin=False,
            demo_token=DEMO_TOKENS["acct-techhaven-editor"],
        ),
        MerchantAccount(
            account_id="acct-gadgetgrove-owner",
            email="owner@gadgetgrove.demo",
            display_name="GadgetGrove Owner",
            created_at=_dt(-600),
            updated_at=_dt(-12),
            is_active=True,
            is_internal_admin=False,
            demo_token=DEMO_TOKENS["acct-gadgetgrove-owner"],
        ),
        MerchantAccount(
            account_id="acct-internal-admin",
            email="admin@dealbrain.demo",
            display_name="PiqSavi Internal Admin",
            created_at=_dt(-1000),
            updated_at=_dt(-1),
            is_active=True,
            is_internal_admin=True,
            demo_token=DEMO_TOKENS["acct-internal-admin"],
        ),
    ]


def build_demo_users() -> list[MerchantUser]:
    return [
        MerchantUser(
            user_id="muser-techhaven-owner",
            account_id="acct-techhaven-owner",
            email="owner@techhaven.demo",
            display_name="TechHaven Owner",
            created_at=_dt(-720),
            updated_at=_dt(-24),
        ),
        MerchantUser(
            user_id="muser-techhaven-editor",
            account_id="acct-techhaven-editor",
            email="editor@techhaven.demo",
            display_name="TechHaven Editor",
            created_at=_dt(-700),
            updated_at=_dt(-24),
        ),
        MerchantUser(
            user_id="muser-gadgetgrove-owner",
            account_id="acct-gadgetgrove-owner",
            email="owner@gadgetgrove.demo",
            display_name="GadgetGrove Owner",
            created_at=_dt(-600),
            updated_at=_dt(-12),
        ),
        MerchantUser(
            user_id="muser-internal-admin",
            account_id="acct-internal-admin",
            email="admin@dealbrain.demo",
            display_name="PiqSavi Internal Admin",
            created_at=_dt(-1000),
            updated_at=_dt(-1),
        ),
    ]


def build_demo_organizations() -> list[MerchantOrganization]:
    return [
        MerchantOrganization(
            organization_id="org-techhaven",
            profile=MerchantProfile(
                business_name="TechHaven Retail LLC",
                legal_name="TechHaven Retail Limited Liability Company",
                display_name="TechHaven",
                country="US",
                business_category="consumer_electronics",
                website="https://techhaven.demo",
                support_email="support@techhaven.demo",
                marketplace_presence=("amazon", "ebay"),
                business_description="Demo electronics retailer for PiqSavi Merchant Platform.",
                logo_reference="https://cdn.techhaven.demo/logo.png",
                contact_references=("support@techhaven.demo",),
                verification_status=MerchantVerificationStatus.VERIFIED,
                terms_accepted_at=_dt(-700),
            ),
            status=MerchantOrgStatus.ACTIVE,
            owner_account_id="acct-techhaven-owner",
            created_at=_dt(-720),
            updated_at=_dt(-24),
            affiliate_merchant_id="merchant-amazon-us",
        ),
        MerchantOrganization(
            organization_id="org-gadgetgrove",
            profile=MerchantProfile(
                business_name="GadgetGrove PH",
                legal_name="GadgetGrove Philippines Inc.",
                display_name="GadgetGrove",
                country="PH",
                business_category="consumer_electronics",
                website="https://gadgetgrove.demo",
                support_email="support@gadgetgrove.demo",
                marketplace_presence=("shopee", "lazada"),
                business_description="Demo PH marketplace seller for Merchant Platform.",
                logo_reference="https://cdn.gadgetgrove.demo/logo.png",
                contact_references=("support@gadgetgrove.demo",),
                verification_status=MerchantVerificationStatus.PENDING_REVIEW,
                terms_accepted_at=_dt(-500),
            ),
            status=MerchantOrgStatus.ACTIVE,
            owner_account_id="acct-gadgetgrove-owner",
            created_at=_dt(-600),
            updated_at=_dt(-12),
            affiliate_merchant_id="merchant-shopee-ph",
        ),
    ]


def build_demo_memberships() -> list[MerchantMembership]:
    return [
        MerchantMembership(
            membership_id="mem-techhaven-owner",
            organization_id="org-techhaven",
            account_id="acct-techhaven-owner",
            role=MerchantRole.OWNER,
            created_at=_dt(-720),
            updated_at=_dt(-24),
        ),
        MerchantMembership(
            membership_id="mem-techhaven-editor",
            organization_id="org-techhaven",
            account_id="acct-techhaven-editor",
            role=MerchantRole.EDITOR,
            created_at=_dt(-700),
            updated_at=_dt(-24),
        ),
        MerchantMembership(
            membership_id="mem-gadgetgrove-owner",
            organization_id="org-gadgetgrove",
            account_id="acct-gadgetgrove-owner",
            role=MerchantRole.OWNER,
            created_at=_dt(-600),
            updated_at=_dt(-12),
        ),
    ]


def build_demo_invitations() -> list[MerchantInvitation]:
    return [
        MerchantInvitation(
            invitation_id="inv-techhaven-analyst",
            organization_id="org-techhaven",
            email="analyst@techhaven.demo",
            role=MerchantRole.ANALYST,
            invited_by_account_id="acct-techhaven-owner",
            status=InvitationStatus.PENDING,
            created_at=_dt(-48),
            updated_at=_dt(-48),
            expires_at=_dt(24 * 14),
        ),
    ]


def build_demo_verifications() -> list[MerchantVerification]:
    return [
        MerchantVerification(
            verification_id="ver-techhaven",
            organization_id="org-techhaven",
            status=MerchantVerificationStatus.VERIFIED,
            created_at=_dt(-700),
            updated_at=_dt(-600),
            reviewed_by="acct-internal-admin",
            notes="Demo verification — no identity documents stored.",
            document_references=("docref-techhaven-business-license",),
        ),
        MerchantVerification(
            verification_id="ver-gadgetgrove",
            organization_id="org-gadgetgrove",
            status=MerchantVerificationStatus.PENDING_REVIEW,
            created_at=_dt(-400),
            updated_at=_dt(-400),
            notes="Awaiting internal review — document refs only.",
            document_references=("docref-gadgetgrove-dti",),
        ),
    ]


def build_demo_marketplace_accounts() -> list[MerchantMarketplaceAccount]:
    return [
        MerchantMarketplaceAccount(
            marketplace_account_id="mkt-techhaven-amazon",
            organization_id="org-techhaven",
            marketplace="amazon",
            seller_name="TechHaven Official",
            external_seller_id="AMZ-TECHHAVEN",
            country="US",
        ),
        MerchantMarketplaceAccount(
            marketplace_account_id="mkt-gadgetgrove-shopee",
            organization_id="org-gadgetgrove",
            marketplace="shopee",
            seller_name="GadgetGrove PH Store",
            external_seller_id="SHOPEE-GADGETGROVE",
            country="PH",
        ),
    ]


def build_demo_product_submissions() -> list[MerchantProductSubmission]:
    return [
        MerchantProductSubmission(
            submission_id="psub-techhaven-x1",
            organization_id="org-techhaven",
            submitted_by_account_id="acct-techhaven-owner",
            status=SubmissionStatus.APPROVED,
            title="NovaTech X1 Pro 14-inch Laptop",
            brand="NovaTech",
            model="X1 Pro",
            category="laptop",
            description="Demo approved product submission matched to catalog.",
            sku="NT-X1PRO-14",
            upc="012345678901",
            merchant_product_id="mp-x1-001",
            image_urls=("https://cdn.techhaven.demo/products/x1.png",),
            warranty="1 year limited",
            seller_info="TechHaven Official",
            matched_product_id="prod-laptop-x1",
            created_at=_dt(-200),
            updated_at=_dt(-100),
            raw_payload={"demo": True},
        ),
        MerchantProductSubmission(
            submission_id="psub-techhaven-draft",
            organization_id="org-techhaven",
            submitted_by_account_id="acct-techhaven-editor",
            status=SubmissionStatus.DRAFT,
            title="AudioWave A9 Wireless Headphones — Merchant Draft",
            brand="AudioWave",
            model="A9",
            category="headphones",
            description="Draft submission awaiting merchant submit.",
            sku="AW-A9-BLK",
            image_urls=("https://cdn.techhaven.demo/products/a9.png",),
            created_at=_dt(-10),
            updated_at=_dt(-10),
            raw_payload={"demo": True},
        ),
        MerchantProductSubmission(
            submission_id="psub-gadgetgrove-z5",
            organization_id="org-gadgetgrove",
            submitted_by_account_id="acct-gadgetgrove-owner",
            status=SubmissionStatus.UNDER_REVIEW,
            title="PulseMobile Z5 Smartphone",
            brand="PulseMobile",
            model="Z5",
            category="phone",
            description="Under review — merchant-submitted, not live verified.",
            sku="PM-Z5-128",
            upc="098765432109",
            image_urls=("https://cdn.gadgetgrove.demo/products/z5.png",),
            matched_product_id="prod-phone-z5",
            created_at=_dt(-50),
            updated_at=_dt(-20),
            raw_payload={"demo": True},
        ),
    ]


def build_demo_offer_submissions() -> list[MerchantOfferSubmission]:
    return [
        MerchantOfferSubmission(
            offer_id="osub-techhaven-x1",
            organization_id="org-techhaven",
            submitted_by_account_id="acct-techhaven-owner",
            status=SubmissionStatus.APPROVED,
            title="NovaTech X1 Pro — TechHaven Offer",
            currency="USD",
            price=1299.0,
            sale_price=1199.0,
            shipping_cost=0.0,
            inventory_quantity=25,
            availability="in_stock",
            marketplace_url="https://techhaven.demo/products/x1-pro",
            warranty="1 year limited",
            seller_details="TechHaven Official",
            product_submission_id="psub-techhaven-x1",
            matched_product_id="prod-laptop-x1",
            created_at=_dt(-180),
            updated_at=_dt(-90),
            raw_payload={"demo": True},
        ),
        MerchantOfferSubmission(
            offer_id="osub-gadgetgrove-z5",
            organization_id="org-gadgetgrove",
            submitted_by_account_id="acct-gadgetgrove-owner",
            status=SubmissionStatus.SUBMITTED,
            title="PulseMobile Z5 — GadgetGrove Offer",
            currency="PHP",
            price=24990.0,
            shipping_cost=120.0,
            inventory_quantity=40,
            availability="in_stock",
            marketplace_url="https://gadgetgrove.demo/products/z5",
            product_submission_id="psub-gadgetgrove-z5",
            matched_product_id="prod-phone-z5",
            created_at=_dt(-40),
            updated_at=_dt(-40),
            raw_payload={"demo": True},
        ),
    ]


def build_demo_promotions() -> list[MerchantPromotion]:
    return [
        MerchantPromotion(
            promotion_id="promo-techhaven-x1-sale",
            organization_id="org-techhaven",
            created_by_account_id="acct-techhaven-owner",
            promotion_type=PromotionType.SALE_PRICE,
            status=PromotionStatus.ACTIVE,
            title="X1 Pro Summer Sale",
            description="Demo limited-time sale — does not auto-boost PiqScore.",
            sale_price=1199.0,
            currency="USD",
            terms="Demo promotion terms only.",
            product_ids=("prod-laptop-x1",),
            offer_ids=("osub-techhaven-x1",),
            starts_at=_dt(-72),
            ends_at=_dt(72),
            created_at=_dt(-80),
            updated_at=_dt(-70),
        ),
        MerchantPromotion(
            promotion_id="promo-gadgetgrove-free-ship",
            organization_id="org-gadgetgrove",
            created_by_account_id="acct-gadgetgrove-owner",
            promotion_type=PromotionType.FREE_SHIPPING,
            status=PromotionStatus.SCHEDULED,
            title="Free Shipping Weekend",
            description="Scheduled free shipping promo.",
            terms="Demo only.",
            product_ids=("prod-phone-z5",),
            starts_at=_dt(24),
            ends_at=_dt(96),
            created_at=_dt(-5),
            updated_at=_dt(-5),
        ),
    ]


def build_demo_campaigns() -> list[MerchantCampaign]:
    return [
        MerchantCampaign(
            campaign_id="camp-techhaven-sponsored-x1",
            organization_id="org-techhaven",
            created_by_account_id="acct-techhaven-owner",
            name="X1 Pro Sponsored Draft",
            status=MerchantCampaignStatus.DRAFT,
            placements=(
                MerchantCampaignPlacement(
                    placement_id="place-x1-sponsored",
                    placement_type=CampaignPlacementType.SPONSORED_PRODUCT,
                    product_ids=("prod-laptop-x1",),
                    offer_ids=("osub-techhaven-x1",),
                    targeting_metadata={"category": "laptop", "country": "US"},
                ),
            ),
            budget=MerchantCampaignBudget(
                currency="USD",
                daily_budget=50.0,
                total_budget=500.0,
            ),
            starts_at=_dt(48),
            ends_at=_dt(48 + 24 * 14),
            targeting_metadata={"demo": True},
            created_at=_dt(-8),
            updated_at=_dt(-8),
            review_notes="Draft sponsored campaign — no real billing.",
        ),
    ]


def demo_analytics_seed() -> dict[str, Any]:
    """Deterministic demo analytics seed — always labeled simulated."""
    return {
        "product_views": 1280,
        "offer_views": 640,
        "watchlist_additions": 42,
        "alert_activity": 11,
        "comparison_appearances": 87,
        "recommendation_appearances": 54,
        "estimated_commission": 96.5,
        "product_views_base": 200,
        "products": {
            "prod-laptop-x1": {
                "product_views": 820,
                "offer_views": 410,
                "affiliate_clicks": 95,
                "attributed_conversions": 7,
                "estimated_commission": 72.0,
                "watchlist_additions": 28,
                "alert_activity": 6,
                "comparison_appearances": 55,
                "recommendation_appearances": 33,
                "dealscore": 82.5,
                "data_freshness": "demo",
                "price_competitiveness": "competitive",
                "seller_quality": "good",
            },
            "prod-phone-z5": {
                "product_views": 460,
                "offer_views": 230,
                "affiliate_clicks": 40,
                "attributed_conversions": 2,
                "estimated_commission": 24.5,
                "watchlist_additions": 14,
                "alert_activity": 5,
                "comparison_appearances": 32,
                "recommendation_appearances": 21,
                "dealscore": 76.0,
                "data_freshness": "demo",
                "price_competitiveness": "average",
                "seller_quality": "good",
            },
        },
    }
