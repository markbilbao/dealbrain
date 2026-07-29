"""Affiliate link generation application service — Sprint 20.

Generates affiliate URLs **after** a product has already been selected by the
recommendation / Shopping Assistant pipeline. Never alters DealScore.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.affiliate.linking.builder import AffiliateLinkBuilder
from app.domain.entities.affiliate import AffiliateLink, AffiliateMerchant, MerchantStatus
from app.domain.exceptions import (
    AffiliateLinkNotFoundError,
    AffiliateMerchantNotFoundError,
    AffiliateValidationError,
)
from app.domain.interfaces.affiliate_repository import (
    AffiliateLinkRepository,
    AffiliateMerchantRepository,
)
from app.services.affiliate_merchant_service import AffiliateMerchantService


class AffiliateLinkService:
    """Generate, validate, and persist affiliate links for selected products."""

    def __init__(
        self,
        repository: AffiliateLinkRepository,
        merchant_repository: AffiliateMerchantRepository,
        *,
        merchant_service: AffiliateMerchantService | None = None,
        builder: AffiliateLinkBuilder | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._merchants = merchant_repository
        self._merchant_service = merchant_service or AffiliateMerchantService(merchant_repository)
        self._builder = builder or AffiliateLinkBuilder()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def generate_link(
        self,
        *,
        product_id: str,
        product_name: str,
        marketplace: str | None = None,
        merchant_id: str | None = None,
        original_url: str | None = None,
        product_ref: str | None = None,
        campaign_id: str | None = None,
        sub_id: str | None = None,
        click_id: str | None = None,
        country: str | None = None,
        category: str | None = None,
        order_value: float | None = None,
        deep_link: bool = False,
        currency: str = "USD",
        link_id: str | None = None,
    ) -> AffiliateLink:
        """Build an affiliate link for an already-selected product.

        Commission estimates are attached for reporting only and must never be
        fed back into DealScore or ranking.
        """
        cleaned_product_id = (product_id or "").strip()
        cleaned_name = (product_name or "").strip()
        if not cleaned_product_id:
            raise AffiliateValidationError("product_id is required.")
        if not cleaned_name:
            raise AffiliateValidationError("product_name is required.")

        merchant = self._resolve_merchant(
            merchant_id=merchant_id, marketplace=marketplace, country=country
        )
        if merchant.status is not MerchantStatus.ACTIVE:
            raise AffiliateValidationError(
                f"Merchant {merchant.merchant_id} is not active (status={merchant.status.value})."
            )
        if country and merchant.allowed_countries:
            allowed = {c.upper() for c in merchant.allowed_countries}
            if (
                country.upper() not in allowed
                and merchant.country.upper() not in {"GLOBAL", country.upper()}
            ):
                raise AffiliateValidationError(
                    f"Merchant {merchant.merchant_id} is not available in country {country!r}."
                )

        ref = (product_ref or cleaned_product_id).strip()
        resolved_click_id = click_id or f"clk-{self._id_factory()}"
        stamp = self._clock()

        if deep_link:
            if not original_url:
                raise AffiliateValidationError("original_url is required for deep links.")
            affiliate_url = self._builder.build_deep_link(
                merchant,
                destination_url=original_url,
                campaign_id=campaign_id,
                sub_id=sub_id,
                click_id=resolved_click_id,
            )
            source_url = self._builder.validate_url(original_url)
        else:
            affiliate_url = self._builder.apply_template(
                merchant,
                product_ref=ref,
                campaign_id=campaign_id,
                sub_id=sub_id,
                click_id=resolved_click_id,
            )
            if original_url:
                source_url = self._builder.validate_url(original_url)
            else:
                source_url = f"https://dealbrain.demo/product/{cleaned_product_id}"

        estimated = self._builder.estimate_commission(merchant, order_value=order_value)
        link = AffiliateLink(
            link_id=link_id or f"link-{self._id_factory()}",
            merchant_id=merchant.merchant_id,
            product_id=cleaned_product_id,
            product_name=cleaned_name,
            original_url=source_url,
            affiliate_url=affiliate_url,
            marketplace=merchant.marketplace,
            campaign_id=campaign_id,
            sub_id=sub_id,
            click_id=resolved_click_id,
            deep_link=deep_link,
            created_at=stamp,
            category=category,
            estimated_commission=estimated,
            currency=currency,
            disclosure_required=True,
            simulated=True,
        )
        return self._repository.save_link(link)

    def generate_for_recommendation(
        self,
        recommendation: Any,
        *,
        campaign_id: str | None = "shopping-assistant",
        sub_id: str | None = None,
        user_id: str | None = None,
        country: str | None = None,
    ) -> AffiliateLink | None:
        """Post-rank helper: decorate a selected recommendation with an affiliate link.

        Accepts a ``ShoppingRecommendation`` (or duck-typed object / dict) and
        returns ``None`` when no active merchant matches — never raises into the
        ranking path.
        """
        if recommendation is None:
            return None
        if isinstance(recommendation, dict):
            product_id = str(recommendation.get("product_id") or "")
            product_name = str(recommendation.get("product_name") or "")
            marketplace = recommendation.get("marketplace")
            known_price = recommendation.get("known_price")
            category = recommendation.get("category")
        else:
            product_id = str(getattr(recommendation, "product_id", "") or "")
            product_name = str(getattr(recommendation, "product_name", "") or "")
            marketplace = getattr(recommendation, "marketplace", None)
            known_price = getattr(recommendation, "known_price", None)
            category = getattr(recommendation, "category", None)

        if not product_id or not product_name:
            return None
        if not marketplace:
            return None

        try:
            return self.generate_link(
                product_id=product_id,
                product_name=product_name,
                marketplace=str(marketplace),
                campaign_id=campaign_id,
                sub_id=sub_id or (f"user-{user_id}" if user_id else "sa-anon"),
                country=country,
                category=str(category) if category else None,
                order_value=float(known_price) if known_price is not None else None,
            )
        except (AffiliateValidationError, AffiliateMerchantNotFoundError):
            return None

    def get_link(self, link_id: str) -> AffiliateLink:
        link = self._repository.get_link(link_id)
        if link is None:
            raise AffiliateLinkNotFoundError(link_id)
        return link

    def list_links(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[AffiliateLink]:
        return self._repository.list_links(
            merchant_id=merchant_id, product_id=product_id, limit=limit
        )

    def validate_url(self, url: str) -> str:
        return self._builder.validate_url(url)

    def _resolve_merchant(
        self,
        *,
        merchant_id: str | None,
        marketplace: str | None,
        country: str | None,
    ) -> AffiliateMerchant:
        if merchant_id:
            merchant = self._merchants.get_merchant(merchant_id)
            if merchant is None:
                raise AffiliateMerchantNotFoundError(merchant_id)
            return merchant
        if not marketplace:
            raise AffiliateValidationError("merchant_id or marketplace is required.")
        resolved = self._merchant_service.resolve_for_marketplace(
            marketplace, country=country
        )
        if resolved is None:
            raise AffiliateValidationError(
                f"No active affiliate merchant for marketplace {marketplace!r}."
            )
        return resolved
