"""Affiliate click tracking & attribution application service — Sprint 20.

Stores click events and runs the attribution engine. Simulated only —
no real conversion postbacks or network callbacks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.affiliate.attribution.engine import AttributionEngine
from app.affiliate.linking.builder import AffiliateLinkBuilder
from app.domain.entities.affiliate import (
    AffiliateClick,
    AttributionModel,
    AttributionResult,
    ClickSource,
    ConversionStatus,
    MarketplacePlaceholder,
)
from app.domain.exceptions import (
    AffiliateClickNotFoundError,
    AffiliateLinkNotFoundError,
    AffiliateMerchantNotFoundError,
    AffiliateValidationError,
)
from app.domain.interfaces.affiliate_repository import (
    AffiliateAttributionRepository,
    AffiliateClickRepository,
    AffiliateLinkRepository,
    AffiliateMerchantRepository,
)


class AffiliateTrackingService:
    """Record clicks, update conversion status, and attribute conversions."""

    def __init__(
        self,
        click_repository: AffiliateClickRepository,
        *,
        link_repository: AffiliateLinkRepository | None = None,
        merchant_repository: AffiliateMerchantRepository | None = None,
        attribution_repository: AffiliateAttributionRepository | None = None,
        attribution_engine: AttributionEngine | None = None,
        link_builder: AffiliateLinkBuilder | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._clicks = click_repository
        self._links = link_repository
        self._merchants = merchant_repository
        self._attributions = attribution_repository
        self._engine = attribution_engine or AttributionEngine()
        self._builder = link_builder or AffiliateLinkBuilder()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def track_click(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        link_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        device: str | None = None,
        country: str | None = None,
        campaign_id: str | None = None,
        source: str = "unknown",
        referrer: str | None = None,
        product_name: str | None = None,
        category: str | None = None,
        revenue: float = 0.0,
        estimated_commission: float | None = None,
        currency: str = "USD",
        click_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AffiliateClick:
        """Persist a tracked click. Optionally hydrate from a prior affiliate link."""
        resolved_merchant = merchant_id
        resolved_product = product_id
        resolved_name = product_name
        resolved_category = category
        resolved_campaign = campaign_id
        resolved_commission = estimated_commission
        marketplace: MarketplacePlaceholder | None = None
        link_ref = link_id

        if link_id:
            if self._links is None:
                raise AffiliateValidationError("link_repository is required to resolve link_id.")
            link = self._links.get_link(link_id)
            if link is None:
                raise AffiliateLinkNotFoundError(link_id)
            resolved_merchant = resolved_merchant or link.merchant_id
            resolved_product = resolved_product or link.product_id
            resolved_name = resolved_name or link.product_name
            resolved_category = resolved_category or link.category
            resolved_campaign = resolved_campaign or link.campaign_id
            if resolved_commission is None:
                resolved_commission = link.estimated_commission
            marketplace = link.marketplace
            if link.click_id and not click_id:
                click_id = link.click_id

        if not resolved_merchant:
            raise AffiliateValidationError("merchant_id (or link_id) is required.")
        if not resolved_product:
            raise AffiliateValidationError("product_id (or link_id) is required.")

        if self._merchants is not None:
            merchant = self._merchants.get_merchant(resolved_merchant)
            if merchant is None:
                raise AffiliateMerchantNotFoundError(resolved_merchant)
            marketplace = marketplace or merchant.marketplace
            if resolved_commission is None:
                resolved_commission = self._builder.estimate_commission(merchant)

        stamp = self._clock()
        click = AffiliateClick(
            click_id=click_id or f"clk-{self._id_factory()}",
            user_id=user_id,
            session_id=session_id,
            merchant_id=resolved_merchant,
            product_id=resolved_product,
            timestamp=stamp,
            device=device,
            country=country.upper() if country else None,
            campaign_id=resolved_campaign,
            source=self._source(source),
            referrer=referrer,
            conversion_status=ConversionStatus.CLICKED,
            revenue=float(revenue or 0.0),
            link_id=link_ref,
            product_name=resolved_name,
            category=resolved_category,
            marketplace=marketplace,
            attribution_model=AttributionModel.LAST_CLICK,
            estimated_commission=float(resolved_commission or 0.0),
            currency=currency,
            metadata=dict(metadata or {}),
            simulated=True,
        )
        return self._clicks.save_click(click)

    def get_click(self, click_id: str) -> AffiliateClick:
        click = self._clicks.get_click(click_id)
        if click is None:
            raise AffiliateClickNotFoundError(click_id)
        return click

    def list_clicks(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 200,
    ) -> list[AffiliateClick]:
        return self._clicks.list_clicks(
            user_id=user_id,
            session_id=session_id,
            merchant_id=merchant_id,
            product_id=product_id,
            limit=limit,
        )

    def update_conversion_status(
        self,
        click_id: str,
        *,
        conversion_status: str,
        revenue: float | None = None,
        estimated_commission: float | None = None,
    ) -> AffiliateClick:
        click = self.get_click(click_id)
        status = self._conversion_status(conversion_status)
        updates: dict[str, Any] = {"conversion_status": status}
        if revenue is not None:
            if revenue < 0:
                raise AffiliateValidationError("revenue must be non-negative.")
            updates["revenue"] = float(revenue)
        if estimated_commission is not None:
            if estimated_commission < 0:
                raise AffiliateValidationError("estimated_commission must be non-negative.")
            updates["estimated_commission"] = float(estimated_commission)
        return self._clicks.save_click(replace(click, **updates))

    def attribute(
        self,
        *,
        model: str = "last_click",
        user_id: str | None = None,
        session_id: str | None = None,
        product_id: str | None = None,
        merchant_id: str | None = None,
        revenue: float = 0.0,
        estimated_commission: float = 0.0,
        mark_click_converted: bool = True,
    ) -> AttributionResult:
        """Run attribution over matching clicks and optionally mark the winner converted."""
        attribution_model = self._attribution_model(model)
        candidates = self._clicks.list_clicks(
            user_id=user_id,
            session_id=session_id,
            merchant_id=merchant_id,
            product_id=product_id,
            limit=500,
        )
        result = self._engine.attribute(
            candidates,
            model=attribution_model,
            attribution_id=f"attr-{self._id_factory()}",
            attributed_at=self._clock(),
            revenue=revenue,
            estimated_commission=estimated_commission,
            product_id=product_id,
            merchant_id=merchant_id,
        )
        if self._attributions is not None:
            self._attributions.save_attribution(result)

        if mark_click_converted and result.click_id:
            self.update_conversion_status(
                result.click_id,
                conversion_status=ConversionStatus.ATTRIBUTED.value,
                revenue=result.revenue,
                estimated_commission=result.estimated_commission,
            )
        return result

    def list_attributions(self, *, limit: int = 100) -> list[AttributionResult]:
        if self._attributions is None:
            return []
        return self._attributions.list_attributions(limit=limit)

    @staticmethod
    def _source(value: str) -> ClickSource:
        try:
            return ClickSource(value.strip().lower().replace(" ", "_").replace("-", "_"))
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported click source: {value!r}") from exc

    @staticmethod
    def _conversion_status(value: str) -> ConversionStatus:
        try:
            return ConversionStatus(value.strip().lower())
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported conversion_status: {value!r}") from exc

    @staticmethod
    def _attribution_model(value: str) -> AttributionModel:
        try:
            return AttributionModel(value.strip().lower().replace(" ", "_").replace("-", "_"))
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported attribution model: {value!r}") from exc
