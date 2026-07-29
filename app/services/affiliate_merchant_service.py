"""Affiliate merchant management application service — Sprint 20.

Activate/deactivate merchants, update commission/priority, country
restrictions, and health status. Placeholder merchants only — no real
affiliate network credentials or payouts.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.entities.affiliate import (
    AffiliateMerchant,
    AffiliateNetwork,
    CommissionType,
    MarketplacePlaceholder,
    MerchantHealthStatus,
    MerchantStatus,
)
from app.domain.exceptions import AffiliateMerchantNotFoundError, AffiliateValidationError
from app.domain.interfaces.affiliate_repository import AffiliateMerchantRepository

_UNSET = object()


class AffiliateMerchantService:
    """CRUD and lifecycle management for the merchant registry."""

    def __init__(
        self,
        repository: AffiliateMerchantRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))

    def list_merchants(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        country: str | None = None,
        active_only: bool = False,
    ) -> list[AffiliateMerchant]:
        effective_status = status
        if active_only and effective_status is None:
            effective_status = MerchantStatus.ACTIVE.value
        merchants = self._repository.list_merchants(
            status=effective_status, marketplace=marketplace, country=country
        )
        return sorted(merchants, key=lambda m: (m.priority, m.merchant_name))

    def get_merchant(self, merchant_id: str) -> AffiliateMerchant:
        merchant = self._repository.get_merchant(merchant_id)
        if merchant is None:
            raise AffiliateMerchantNotFoundError(merchant_id)
        return merchant

    def create_merchant(
        self,
        *,
        merchant_name: str,
        marketplace: str,
        country: str,
        affiliate_network: str,
        tracking_template: str,
        commission_type: str = "percent",
        commission_value: float = 0.0,
        cookie_days: int = 7,
        status: str = "active",
        priority: int = 100,
        health_status: str = "healthy",
        allowed_countries: list[str] | tuple[str, ...] | None = None,
        deep_link_supported: bool = True,
        merchant_id: str | None = None,
    ) -> AffiliateMerchant:
        name = self._require_name(merchant_name)
        if cookie_days < 0:
            raise AffiliateValidationError("cookie_days must be non-negative.")
        if commission_value < 0:
            raise AffiliateValidationError("commission_value must be non-negative.")
        if not tracking_template.strip():
            raise AffiliateValidationError("tracking_template is required.")
        stamp = self._clock()
        merchant = AffiliateMerchant(
            merchant_id=merchant_id or f"merchant-{self._id_factory()}",
            merchant_name=name,
            marketplace=self._marketplace(marketplace),
            country=country.strip().upper() or "US",
            affiliate_network=self._network(affiliate_network),
            tracking_template=tracking_template.strip(),
            commission_type=self._commission_type(commission_type),
            commission_value=float(commission_value),
            cookie_days=int(cookie_days),
            status=self._status(status),
            priority=int(priority),
            created_at=stamp,
            updated_at=stamp,
            health_status=self._health(health_status),
            allowed_countries=tuple(c.upper() for c in (allowed_countries or ())),
            deep_link_supported=deep_link_supported,
        )
        return self._repository.save_merchant(merchant)

    def update_merchant(
        self,
        merchant_id: str,
        *,
        merchant_name: str | None = None,
        tracking_template: str | None = None,
        commission_type: str | None = None,
        commission_value: float | None = None,
        cookie_days: int | None = None,
        status: str | None = None,
        priority: int | None = None,
        health_status: str | None = None,
        allowed_countries: object = _UNSET,
        deep_link_supported: bool | None = None,
        country: str | None = None,
    ) -> AffiliateMerchant:
        merchant = self.get_merchant(merchant_id)
        updates: dict[str, Any] = {"updated_at": self._clock()}
        if merchant_name is not None:
            updates["merchant_name"] = self._require_name(merchant_name)
        if tracking_template is not None:
            if not tracking_template.strip():
                raise AffiliateValidationError("tracking_template is required.")
            updates["tracking_template"] = tracking_template.strip()
        if commission_type is not None:
            updates["commission_type"] = self._commission_type(commission_type)
        if commission_value is not None:
            if commission_value < 0:
                raise AffiliateValidationError("commission_value must be non-negative.")
            updates["commission_value"] = float(commission_value)
        if cookie_days is not None:
            if cookie_days < 0:
                raise AffiliateValidationError("cookie_days must be non-negative.")
            updates["cookie_days"] = int(cookie_days)
        if status is not None:
            updates["status"] = self._status(status)
        if priority is not None:
            updates["priority"] = int(priority)
        if health_status is not None:
            updates["health_status"] = self._health(health_status)
        if allowed_countries is not _UNSET:
            updates["allowed_countries"] = tuple(
                c.upper() for c in (allowed_countries or ())  # type: ignore[union-attr]
            )
        if deep_link_supported is not None:
            updates["deep_link_supported"] = deep_link_supported
        if country is not None:
            updates["country"] = country.strip().upper() or merchant.country
        return self._repository.save_merchant(replace(merchant, **updates))

    def activate_merchant(self, merchant_id: str) -> AffiliateMerchant:
        return self.update_merchant(merchant_id, status=MerchantStatus.ACTIVE.value)

    def deactivate_merchant(self, merchant_id: str) -> AffiliateMerchant:
        return self.update_merchant(merchant_id, status=MerchantStatus.INACTIVE.value)

    def update_commission(
        self,
        merchant_id: str,
        *,
        commission_type: str,
        commission_value: float,
    ) -> AffiliateMerchant:
        return self.update_merchant(
            merchant_id,
            commission_type=commission_type,
            commission_value=commission_value,
        )

    def set_priority(self, merchant_id: str, priority: int) -> AffiliateMerchant:
        return self.update_merchant(merchant_id, priority=priority)

    def set_country_restrictions(
        self, merchant_id: str, countries: list[str] | tuple[str, ...]
    ) -> AffiliateMerchant:
        return self.update_merchant(merchant_id, allowed_countries=countries)

    def set_health_status(self, merchant_id: str, health_status: str) -> AffiliateMerchant:
        return self.update_merchant(merchant_id, health_status=health_status)

    def resolve_for_marketplace(
        self,
        marketplace: str,
        *,
        country: str | None = None,
    ) -> AffiliateMerchant | None:
        """Pick the highest-priority active merchant for a marketplace."""
        marketplace_key = marketplace.strip().lower().replace(" ", "_").replace("-", "_")
        # Normalize common aliases from shopping assistant catalog.
        aliases = {
            "tiktok": MarketplacePlaceholder.TIKTOK_SHOP.value,
            "tiktokshop": MarketplacePlaceholder.TIKTOK_SHOP.value,
        }
        marketplace_key = aliases.get(marketplace_key, marketplace_key)
        candidates = self.list_merchants(
            status=MerchantStatus.ACTIVE.value,
            marketplace=marketplace_key,
            country=country,
        )
        if not candidates:
            # Fallback: any active merchant matching marketplace ignoring country filter.
            candidates = self.list_merchants(
                status=MerchantStatus.ACTIVE.value, marketplace=marketplace_key
            )
        return candidates[0] if candidates else None

    @staticmethod
    def _require_name(name: str) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            raise AffiliateValidationError("merchant_name is required.")
        return cleaned

    @staticmethod
    def _marketplace(value: str) -> MarketplacePlaceholder:
        try:
            return MarketplacePlaceholder(value.strip().lower().replace(" ", "_").replace("-", "_"))
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported marketplace: {value!r}") from exc

    @staticmethod
    def _network(value: str) -> AffiliateNetwork:
        try:
            return AffiliateNetwork(value.strip().lower().replace(" ", "_").replace("-", "_"))
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported affiliate_network: {value!r}") from exc

    @staticmethod
    def _commission_type(value: str) -> CommissionType:
        try:
            return CommissionType(value.strip().lower())
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported commission_type: {value!r}") from exc

    @staticmethod
    def _status(value: str) -> MerchantStatus:
        try:
            return MerchantStatus(value.strip().lower())
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported status: {value!r}") from exc

    @staticmethod
    def _health(value: str) -> MerchantHealthStatus:
        try:
            return MerchantHealthStatus(value.strip().lower())
        except ValueError as exc:
            raise AffiliateValidationError(f"Unsupported health_status: {value!r}") from exc
