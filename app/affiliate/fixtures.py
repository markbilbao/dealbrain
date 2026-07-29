"""Placeholder affiliate merchants and demo disclosure/click seeds — Sprint 20.

NO real credentials, affiliate tags, API keys, or network integrations.
All tracking templates use obvious DEMO_* placeholders.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.affiliate import (
    AffiliateDisclosure,
    AffiliateMerchant,
    AffiliateNetwork,
    CommissionType,
    MarketplacePlaceholder,
    MerchantHealthStatus,
    MerchantStatus,
)

# Fixed seed timestamp so demo data is deterministic across process restarts
# until the in-memory store is cleared.
SEED_NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)

# Template placeholders use curly-brace tokens applied by AffiliateLinkBuilder.
# Values like DEMO_TAG are never real affiliate credentials.
PLACEHOLDER_MERCHANTS: tuple[dict, ...] = (
    {
        "merchant_id": "merchant-amazon-us",
        "merchant_name": "Amazon",
        "marketplace": MarketplacePlaceholder.AMAZON,
        "country": "US",
        "affiliate_network": AffiliateNetwork.AMAZON_ASSOCIATES,
        "tracking_template": (
            "https://www.amazon.com/dp/{product_ref}"
            "?tag=DEMO_AMAZON_TAG"
            "&ascsubtag={sub_id}"
            "&camp={campaign_id}"
            "&clickid={click_id}"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 4.0,
        "cookie_days": 24,
        "status": MerchantStatus.ACTIVE,
        "priority": 10,
        "health_status": MerchantHealthStatus.HEALTHY,
        "allowed_countries": ("US", "CA", "GB"),
        "deep_link_supported": True,
    },
    {
        "merchant_id": "merchant-shopee-ph",
        "merchant_name": "Shopee",
        "marketplace": MarketplacePlaceholder.SHOPEE,
        "country": "PH",
        "affiliate_network": AffiliateNetwork.SHOPEE_AFFILIATE,
        "tracking_template": (
            "https://shopee.ph/product/{product_ref}"
            "?utm_source=dealbrain"
            "&utm_campaign={campaign_id}"
            "&sub_id={sub_id}"
            "&click_id={click_id}"
            "&aff_id=DEMO_SHOPEE_AFF"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 5.5,
        "cookie_days": 7,
        "status": MerchantStatus.ACTIVE,
        "priority": 20,
        "health_status": MerchantHealthStatus.HEALTHY,
        "allowed_countries": ("PH", "SG", "MY", "TH", "VN", "ID"),
        "deep_link_supported": True,
    },
    {
        "merchant_id": "merchant-lazada-ph",
        "merchant_name": "Lazada",
        "marketplace": MarketplacePlaceholder.LAZADA,
        "country": "PH",
        "affiliate_network": AffiliateNetwork.LAZADA_AFFILIATE,
        "tracking_template": (
            "https://www.lazada.com.ph/products/{product_ref}.html"
            "?spm=DEMO_LAZADA"
            "&exlaz=1"
            "&cid={campaign_id}"
            "&subid={sub_id}"
            "&clickid={click_id}"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 4.5,
        "cookie_days": 7,
        "status": MerchantStatus.ACTIVE,
        "priority": 30,
        "health_status": MerchantHealthStatus.HEALTHY,
        "allowed_countries": ("PH", "SG", "MY", "TH", "VN", "ID"),
        "deep_link_supported": True,
    },
    {
        "merchant_id": "merchant-tiktok-shop-us",
        "merchant_name": "TikTok Shop",
        "marketplace": MarketplacePlaceholder.TIKTOK_SHOP,
        "country": "US",
        "affiliate_network": AffiliateNetwork.TIKTOK_SHOP_AFFILIATE,
        "tracking_template": (
            "https://shop.tiktok.com/view/product/{product_ref}"
            "?affiliate_id=DEMO_TIKTOK_AFF"
            "&campaign_id={campaign_id}"
            "&sub_id={sub_id}"
            "&click_id={click_id}"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 8.0,
        "cookie_days": 14,
        "status": MerchantStatus.ACTIVE,
        "priority": 40,
        "health_status": MerchantHealthStatus.DEGRADED,
        "allowed_countries": ("US", "GB", "SG"),
        "deep_link_supported": True,
    },
    {
        "merchant_id": "merchant-ebay-us",
        "merchant_name": "eBay",
        "marketplace": MarketplacePlaceholder.EBAY,
        "country": "US",
        "affiliate_network": AffiliateNetwork.EBAY_PARTNER,
        "tracking_template": (
            "https://www.ebay.com/itm/{product_ref}"
            "?mkcid=1"
            "&mkrid=DEMO_EBAY_MK"
            "&campid={campaign_id}"
            "&customid={sub_id}"
            "&toolid={click_id}"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 3.0,
        "cookie_days": 24,
        "status": MerchantStatus.ACTIVE,
        "priority": 50,
        "health_status": MerchantHealthStatus.HEALTHY,
        "allowed_countries": ("US", "GB", "DE", "AU"),
        "deep_link_supported": True,
    },
    {
        "merchant_id": "merchant-aliexpress-global",
        "merchant_name": "AliExpress",
        "marketplace": MarketplacePlaceholder.ALIEXPRESS,
        "country": "GLOBAL",
        "affiliate_network": AffiliateNetwork.ALIEXPRESS_AFFILIATE,
        "tracking_template": (
            "https://www.aliexpress.com/item/{product_ref}.html"
            "?aff_fcid=DEMO_ALI_FCID"
            "&aff_fsk={sub_id}"
            "&aff_platform=dealbrain"
            "&sk={campaign_id}"
            "&af={click_id}"
        ),
        "commission_type": CommissionType.PERCENT,
        "commission_value": 6.0,
        "cookie_days": 30,
        "status": MerchantStatus.INACTIVE,
        "priority": 60,
        "health_status": MerchantHealthStatus.UNKNOWN,
        "allowed_countries": (),
        "deep_link_supported": True,
    },
)

DEFAULT_DISCLOSURES: tuple[dict, ...] = (
    {
        "disclosure_id": "disc-general-en",
        "disclosure_type": "affiliate_general",
        "text": (
            "DealBrain may earn a commission when you buy through links on this page. "
            "Commissions never change DealScore or product rankings."
        ),
        "region": None,
        "merchant_id": None,
        "locale": "en",
        "ftc_placeholder": True,
    },
    {
        "disclosure_id": "disc-ftc-us",
        "disclosure_type": "ftc",
        "text": (
            "[FTC DISCLOSURE PLACEHOLDER] This site contains affiliate links. "
            "We may receive compensation if you purchase through these links. "
            "This disclosure is a placeholder and is not legal advice."
        ),
        "region": "US",
        "merchant_id": None,
        "locale": "en-US",
        "ftc_placeholder": True,
    },
    {
        "disclosure_id": "disc-regional-ph",
        "disclosure_type": "regional",
        "text": (
            "Some product links are affiliate links for Philippine marketplaces "
            "(Shopee / Lazada placeholders). Rankings remain commission-independent."
        ),
        "region": "PH",
        "merchant_id": None,
        "locale": "en-PH",
        "ftc_placeholder": True,
    },
    {
        "disclosure_id": "disc-merchant-amazon",
        "disclosure_type": "merchant",
        "text": (
            "As an Amazon Associates placeholder participant, DealBrain may earn from "
            "qualifying purchases. No real Amazon credentials are configured."
        ),
        "region": "US",
        "merchant_id": "merchant-amazon-us",
        "locale": "en-US",
        "ftc_placeholder": True,
    },
)


def build_placeholder_merchants(
    *,
    now: datetime | None = None,
) -> list[AffiliateMerchant]:
    """Materialize frozen merchant entities from placeholder definitions."""
    stamp = now or SEED_NOW
    merchants: list[AffiliateMerchant] = []
    for raw in PLACEHOLDER_MERCHANTS:
        merchants.append(
            AffiliateMerchant(
                merchant_id=raw["merchant_id"],
                merchant_name=raw["merchant_name"],
                marketplace=raw["marketplace"],
                country=raw["country"],
                affiliate_network=raw["affiliate_network"],
                tracking_template=raw["tracking_template"],
                commission_type=raw["commission_type"],
                commission_value=float(raw["commission_value"]),
                cookie_days=int(raw["cookie_days"]),
                status=raw["status"],
                priority=int(raw["priority"]),
                created_at=stamp,
                updated_at=stamp,
                health_status=raw["health_status"],
                allowed_countries=tuple(raw["allowed_countries"]),
                deep_link_supported=bool(raw["deep_link_supported"]),
            )
        )
    return merchants


def build_default_disclosures(
    *,
    now: datetime | None = None,
) -> list[AffiliateDisclosure]:
    """Materialize default disclosure records (FTC / regional / merchant hooks)."""
    stamp = now or SEED_NOW
    items: list[AffiliateDisclosure] = []
    for raw in DEFAULT_DISCLOSURES:
        items.append(
            AffiliateDisclosure(
                disclosure_id=raw["disclosure_id"],
                disclosure_type=raw["disclosure_type"],
                text=raw["text"],
                region=raw["region"],
                merchant_id=raw["merchant_id"],
                locale=raw["locale"],
                created_at=stamp,
                updated_at=stamp,
                ftc_placeholder=bool(raw["ftc_placeholder"]),
                active=True,
            )
        )
    return items


# Demo product catalog snippets used by reporting / dashboard seeds only.
DEMO_PRODUCTS: tuple[dict[str, str], ...] = (
    {
        "product_id": "prod-iphone-17-pro",
        "product_name": "iPhone 17 Pro",
        "category": "smartphones",
        "marketplace": "shopee",
    },
    {
        "product_id": "prod-galaxy-s26",
        "product_name": "Samsung Galaxy S26",
        "category": "smartphones",
        "marketplace": "lazada",
    },
    {
        "product_id": "prod-airpods-pro-3",
        "product_name": "AirPods Pro 3",
        "category": "audio",
        "marketplace": "amazon",
    },
    {
        "product_id": "prod-nintendo-switch-2",
        "product_name": "Nintendo Switch 2",
        "category": "gaming",
        "marketplace": "ebay",
    },
    {
        "product_id": "prod-dyson-v16",
        "product_name": "Dyson V16 Absolute",
        "category": "home",
        "marketplace": "tiktok_shop",
    },
)
