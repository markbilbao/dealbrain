"""SQLAlchemy Affiliate Revenue Engine repository — Sprint 23."""

from __future__ import annotations

from dataclasses import dataclass

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
from app.infrastructure.persistence.session_bound import SessionBound
from app.infrastructure.persistence.stores import (
    AFF_ATTRIBUTIONS,
    AFF_CLICKS,
    AFF_DISCLOSURES,
    AFF_LINKS,
    AFF_MERCHANTS,
    AFF_META,
    AFFILIATE_STORES,
)

_IMPRESSION_ENTITY_ID = "impression_count"


@dataclass(frozen=True, slots=True)
class _ImpressionMeta:
    count: int


class SqlAlchemyAffiliateRepository(
    AffiliateMerchantRepository,
    AffiliateLinkRepository,
    AffiliateClickRepository,
    AffiliateAttributionRepository,
    AffiliateDisclosureRepository,
    SessionBound,
):
    """SQLAlchemy-backed affiliate store mirroring InMemoryAffiliateRepository."""

    def __init__(self, *, seed: bool = False, session_factory=None, session=None) -> None:
        super().__init__(session_factory=session_factory, session=session)
        if seed:
            self.seed_placeholders()
            self.seed_demo_activity()

    # ---------------------------------------------------------------- merchants
    def save_merchant(self, merchant: AffiliateMerchant) -> AffiliateMerchant:
        with self._ops() as ops:
            return ops.upsert(AFF_MERCHANTS, merchant.merchant_id, merchant)

    def get_merchant(self, merchant_id: str) -> AffiliateMerchant | None:
        with self._ops() as ops:
            return ops.get(AFF_MERCHANTS, merchant_id, AffiliateMerchant)

    def list_merchants(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        country: str | None = None,
    ) -> list[AffiliateMerchant]:
        def _matches(merchant: AffiliateMerchant) -> bool:
            if status is not None and merchant.status.value != status:
                return False
            if marketplace is not None and merchant.marketplace.value != marketplace:
                return False
            if country is not None:
                country_upper = country.upper()
                allowed = {c.upper() for c in merchant.allowed_countries}
                if not (
                    merchant.country.upper() == country_upper
                    or country_upper in allowed
                    or merchant.country.upper() == "GLOBAL"
                ):
                    return False
            return True

        with self._ops() as ops:
            return ops.list(AFF_MERCHANTS, AffiliateMerchant, predicate=_matches)

    def delete_merchant(self, merchant_id: str) -> bool:
        with self._ops() as ops:
            return ops.delete(AFF_MERCHANTS, merchant_id)

    # -------------------------------------------------------------------- links
    def save_link(self, link: AffiliateLink) -> AffiliateLink:
        with self._ops() as ops:
            return ops.upsert(AFF_LINKS, link.link_id, link, owner_id=link.merchant_id)

    def get_link(self, link_id: str) -> AffiliateLink | None:
        with self._ops() as ops:
            return ops.get(AFF_LINKS, link_id, AffiliateLink)

    def list_links(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[AffiliateLink]:
        def _matches(link: AffiliateLink) -> bool:
            if merchant_id is not None and link.merchant_id != merchant_id:
                return False
            if product_id is not None and link.product_id != product_id:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                AFF_LINKS,
                AffiliateLink,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # ------------------------------------------------------------------- clicks
    def save_click(self, click: AffiliateClick) -> AffiliateClick:
        with self._ops() as ops:
            return ops.upsert(AFF_CLICKS, click.click_id, click, owner_id=click.merchant_id)

    def get_click(self, click_id: str) -> AffiliateClick | None:
        with self._ops() as ops:
            return ops.get(AFF_CLICKS, click_id, AffiliateClick)

    def list_clicks(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 200,
    ) -> list[AffiliateClick]:
        def _matches(click: AffiliateClick) -> bool:
            if user_id is not None and click.user_id != user_id:
                return False
            if session_id is not None and click.session_id != session_id:
                return False
            if merchant_id is not None and click.merchant_id != merchant_id:
                return False
            if product_id is not None and click.product_id != product_id:
                return False
            return True

        with self._ops() as ops:
            return ops.list(
                AFF_CLICKS,
                AffiliateClick,
                reverse=True,
                limit=limit,
                predicate=_matches,
            )

    # ------------------------------------------------------------ attributions
    def save_attribution(self, result: AttributionResult) -> AttributionResult:
        with self._ops() as ops:
            return ops.upsert(AFF_ATTRIBUTIONS, result.attribution_id, result)

    def list_attributions(self, *, limit: int = 100) -> list[AttributionResult]:
        with self._ops() as ops:
            return ops.list(AFF_ATTRIBUTIONS, AttributionResult, reverse=True, limit=limit)

    # ------------------------------------------------------------- disclosures
    def save_disclosure(self, disclosure: AffiliateDisclosure) -> AffiliateDisclosure:
        with self._ops() as ops:
            return ops.upsert(AFF_DISCLOSURES, disclosure.disclosure_id, disclosure)

    def get_disclosure(self, disclosure_id: str) -> AffiliateDisclosure | None:
        with self._ops() as ops:
            return ops.get(AFF_DISCLOSURES, disclosure_id, AffiliateDisclosure)

    def list_disclosures(
        self,
        *,
        region: str | None = None,
        merchant_id: str | None = None,
        disclosure_type: str | None = None,
        active_only: bool = True,
    ) -> list[AffiliateDisclosure]:
        def _matches(disclosure: AffiliateDisclosure) -> bool:
            if active_only and not disclosure.active:
                return False
            if region is not None and disclosure.region is not None:
                if disclosure.region.upper() != region.upper():
                    return False
            if merchant_id is not None and disclosure.merchant_id is not None:
                if disclosure.merchant_id != merchant_id:
                    return False
            if disclosure_type is not None and disclosure.disclosure_type != disclosure_type:
                return False
            return True

        with self._ops() as ops:
            return ops.list(AFF_DISCLOSURES, AffiliateDisclosure, predicate=_matches)

    # -------------------------------------------------------------------- misc
    def record_impression(self, count: int = 1) -> int:
        with self._ops() as ops:
            meta = ops.get(AFF_META, _IMPRESSION_ENTITY_ID, _ImpressionMeta)
            new_count = (meta.count if meta else 0) + max(0, count)
            ops.upsert(AFF_META, _IMPRESSION_ENTITY_ID, _ImpressionMeta(count=new_count))
            return new_count

    @property
    def impression_count(self) -> int:
        with self._ops() as ops:
            meta = ops.get(AFF_META, _IMPRESSION_ENTITY_ID, _ImpressionMeta)
            return meta.count if meta else 0

    def seed_placeholders(self) -> None:
        for merchant in build_placeholder_merchants():
            self.save_merchant(merchant)
        for disclosure in build_default_disclosures():
            self.save_disclosure(disclosure)
        with self._ops() as ops:
            ops.upsert(AFF_META, _IMPRESSION_ENTITY_ID, _ImpressionMeta(count=250))

    def seed_demo_activity(self) -> None:
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
        with self._ops() as ops:
            ops.clear_stores(AFFILIATE_STORES)
