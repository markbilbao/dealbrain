"""In-memory Affiliate Revenue Engine repository — Sprint 20.

Implements merchant, link, click, attribution, and disclosure ports in a
single process-local store. Demo only — no database, no real affiliate APIs.
"""

from __future__ import annotations

from app.affiliate.fixtures import build_default_disclosures, build_placeholder_merchants
from app.domain.entities.affiliate import (
    AffiliateClick,
    AffiliateDisclosure,
    AffiliateLink,
    AffiliateMerchant,
    AttributionResult,
)
from app.domain.interfaces.affiliate_repository import (
    AffiliateAttributionRepository,
    AffiliateClickRepository,
    AffiliateDisclosureRepository,
    AffiliateLinkRepository,
    AffiliateMerchantRepository,
)


class InMemoryAffiliateRepository(
    AffiliateMerchantRepository,
    AffiliateLinkRepository,
    AffiliateClickRepository,
    AffiliateAttributionRepository,
    AffiliateDisclosureRepository,
):
    """Process-local store for the Affiliate Revenue Engine."""

    def __init__(self, *, seed: bool = True) -> None:
        self._merchants: dict[str, AffiliateMerchant] = {}
        self._merchant_order: list[str] = []
        self._links: dict[str, AffiliateLink] = {}
        self._link_order: list[str] = []
        self._clicks: dict[str, AffiliateClick] = {}
        self._click_order: list[str] = []
        self._attributions: dict[str, AttributionResult] = {}
        self._attribution_order: list[str] = []
        self._disclosures: dict[str, AffiliateDisclosure] = {}
        self._disclosure_order: list[str] = []
        self._impression_count: int = 0
        if seed:
            self.seed_placeholders()
            self.seed_demo_activity()

    # ---------------------------------------------------------------- merchants
    def save_merchant(self, merchant: AffiliateMerchant) -> AffiliateMerchant:
        if merchant.merchant_id not in self._merchants:
            self._merchant_order.append(merchant.merchant_id)
        self._merchants[merchant.merchant_id] = merchant
        return merchant

    def get_merchant(self, merchant_id: str) -> AffiliateMerchant | None:
        return self._merchants.get(merchant_id)

    def list_merchants(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        country: str | None = None,
    ) -> list[AffiliateMerchant]:
        items = [self._merchants[mid] for mid in self._merchant_order if mid in self._merchants]
        if status is not None:
            items = [m for m in items if m.status.value == status]
        if marketplace is not None:
            items = [m for m in items if m.marketplace.value == marketplace]
        if country is not None:
            country_upper = country.upper()
            items = [
                m
                for m in items
                if m.country.upper() == country_upper
                or country_upper in {c.upper() for c in m.allowed_countries}
                or m.country.upper() == "GLOBAL"
            ]
        return items

    def delete_merchant(self, merchant_id: str) -> bool:
        if merchant_id not in self._merchants:
            return False
        del self._merchants[merchant_id]
        self._merchant_order = [mid for mid in self._merchant_order if mid != merchant_id]
        return True

    # -------------------------------------------------------------------- links
    def save_link(self, link: AffiliateLink) -> AffiliateLink:
        if link.link_id not in self._links:
            self._link_order.append(link.link_id)
        self._links[link.link_id] = link
        return link

    def get_link(self, link_id: str) -> AffiliateLink | None:
        return self._links.get(link_id)

    def list_links(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[AffiliateLink]:
        ordered = [self._links[lid] for lid in reversed(self._link_order) if lid in self._links]
        if merchant_id is not None:
            ordered = [link for link in ordered if link.merchant_id == merchant_id]
        if product_id is not None:
            ordered = [link for link in ordered if link.product_id == product_id]
        return ordered[: max(0, limit)]

    # ------------------------------------------------------------------- clicks
    def save_click(self, click: AffiliateClick) -> AffiliateClick:
        if click.click_id not in self._clicks:
            self._click_order.append(click.click_id)
        self._clicks[click.click_id] = click
        return click

    def get_click(self, click_id: str) -> AffiliateClick | None:
        return self._clicks.get(click_id)

    def list_clicks(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 200,
    ) -> list[AffiliateClick]:
        ordered = [self._clicks[cid] for cid in reversed(self._click_order) if cid in self._clicks]
        if user_id is not None:
            ordered = [c for c in ordered if c.user_id == user_id]
        if session_id is not None:
            ordered = [c for c in ordered if c.session_id == session_id]
        if merchant_id is not None:
            ordered = [c for c in ordered if c.merchant_id == merchant_id]
        if product_id is not None:
            ordered = [c for c in ordered if c.product_id == product_id]
        return ordered[: max(0, limit)]

    # ------------------------------------------------------------ attributions
    def save_attribution(self, result: AttributionResult) -> AttributionResult:
        if result.attribution_id not in self._attributions:
            self._attribution_order.append(result.attribution_id)
        self._attributions[result.attribution_id] = result
        return result

    def list_attributions(self, *, limit: int = 100) -> list[AttributionResult]:
        ordered = [
            self._attributions[aid]
            for aid in reversed(self._attribution_order)
            if aid in self._attributions
        ]
        return ordered[: max(0, limit)]

    # ------------------------------------------------------------- disclosures
    def save_disclosure(self, disclosure: AffiliateDisclosure) -> AffiliateDisclosure:
        if disclosure.disclosure_id not in self._disclosures:
            self._disclosure_order.append(disclosure.disclosure_id)
        self._disclosures[disclosure.disclosure_id] = disclosure
        return disclosure

    def get_disclosure(self, disclosure_id: str) -> AffiliateDisclosure | None:
        return self._disclosures.get(disclosure_id)

    def list_disclosures(
        self,
        *,
        region: str | None = None,
        merchant_id: str | None = None,
        disclosure_type: str | None = None,
        active_only: bool = True,
    ) -> list[AffiliateDisclosure]:
        items = [
            self._disclosures[did] for did in self._disclosure_order if did in self._disclosures
        ]
        if active_only:
            items = [d for d in items if d.active]
        if region is not None:
            items = [d for d in items if d.region is None or d.region.upper() == region.upper()]
        if merchant_id is not None:
            items = [d for d in items if d.merchant_id is None or d.merchant_id == merchant_id]
        if disclosure_type is not None:
            items = [d for d in items if d.disclosure_type == disclosure_type]
        return items

    # -------------------------------------------------------------------- misc
    def record_impression(self, count: int = 1) -> int:
        """Increment synthetic impression counter used for CTR demos."""
        self._impression_count += max(0, count)
        return self._impression_count

    @property
    def impression_count(self) -> int:
        return self._impression_count

    def seed_placeholders(self) -> None:
        """Load placeholder merchants and default disclosures."""
        for merchant in build_placeholder_merchants():
            self.save_merchant(merchant)
        for disclosure in build_default_disclosures():
            self.save_disclosure(disclosure)
        # Seed a non-zero impression baseline so CTR demos are non-zero.
        self._impression_count = 250

    def seed_demo_activity(self) -> None:
        """Seed a handful of simulated clicks/links for the Affiliate Dashboard."""
        from app.affiliate.fixtures import DEMO_PRODUCTS, SEED_NOW
        from app.domain.entities.affiliate import (
            AffiliateClick,
            AffiliateLink,
            ClickSource,
            ConversionStatus,
            MarketplacePlaceholder,
        )

        merchant_by_marketplace = {
            m.marketplace.value: m for m in self.list_merchants(status="active")
        }
        demo_rows = (
            (
                "shopee",
                0,
                ClickSource.SHOPPING_ASSISTANT,
                ConversionStatus.CONVERTED,
                899.0,
                49.45,
            ),
            (
                "lazada",
                1,
                ClickSource.RECOMMENDATION_API,
                ConversionStatus.ATTRIBUTED,
                750.0,
                33.75,
            ),
            ("amazon", 2, ClickSource.AFFILIATE_DASHBOARD, ConversionStatus.CLICKED, 0.0, 9.96),
            ("ebay", 3, ClickSource.DIRECT_LINK, ConversionStatus.CLICKED, 0.0, 12.0),
            ("tiktok_shop", 4, ClickSource.EXTERNAL_CAMPAIGN, ConversionStatus.PENDING, 0.0, 24.0),
            ("shopee", 0, ClickSource.SHOPPING_ASSISTANT, ConversionStatus.CLICKED, 0.0, 49.45),
            ("lazada", 1, ClickSource.ORGANIC, ConversionStatus.REJECTED, 0.0, 0.0),
            ("amazon", 2, ClickSource.SHOPPING_ASSISTANT, ConversionStatus.CONVERTED, 249.0, 9.96),
        )
        for index, (marketplace, product_idx, source, status, revenue, commission) in enumerate(
            demo_rows
        ):
            merchant = merchant_by_marketplace.get(marketplace)
            if merchant is None:
                continue
            product = DEMO_PRODUCTS[product_idx]
            link_id = f"link-demo-{index + 1}"
            click_id = f"clk-demo-{index + 1}"
            self.save_link(
                AffiliateLink(
                    link_id=link_id,
                    merchant_id=merchant.merchant_id,
                    product_id=product["product_id"],
                    product_name=product["product_name"],
                    original_url=f"https://dealbrain.demo/product/{product['product_id']}",
                    affiliate_url=merchant.tracking_template.format(
                        product_ref=product["product_id"],
                        campaign_id="demo-seed",
                        sub_id="demo-sub",
                        click_id=click_id,
                    ),
                    marketplace=MarketplacePlaceholder(marketplace),
                    campaign_id="demo-seed",
                    sub_id="demo-sub",
                    click_id=click_id,
                    deep_link=False,
                    created_at=SEED_NOW,
                    category=product["category"],
                    estimated_commission=commission,
                    currency="USD",
                )
            )
            self.save_click(
                AffiliateClick(
                    click_id=click_id,
                    user_id="demo-user",
                    session_id=f"sess-demo-{index + 1}",
                    merchant_id=merchant.merchant_id,
                    product_id=product["product_id"],
                    timestamp=SEED_NOW,
                    device="desktop",
                    country=merchant.country if merchant.country != "GLOBAL" else "US",
                    campaign_id="demo-seed",
                    source=source,
                    referrer="https://dealbrain.demo/assistant",
                    conversion_status=status,
                    revenue=revenue,
                    link_id=link_id,
                    product_name=product["product_name"],
                    category=product["category"],
                    marketplace=MarketplacePlaceholder(marketplace),
                    estimated_commission=commission,
                    currency="USD",
                )
            )

    def clear(self) -> None:
        """Reset all stored affiliate state (tests)."""
        self._merchants.clear()
        self._merchant_order.clear()
        self._links.clear()
        self._link_order.clear()
        self._clicks.clear()
        self._click_order.clear()
        self._attributions.clear()
        self._attribution_order.clear()
        self._disclosures.clear()
        self._disclosure_order.clear()
        self._impression_count = 0
