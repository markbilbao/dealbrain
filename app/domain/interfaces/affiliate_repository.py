"""Affiliate Revenue Engine persistence ports — Sprint 20."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.affiliate import (
    AffiliateClick,
    AffiliateDisclosure,
    AffiliateLink,
    AffiliateMerchant,
    AttributionResult,
)


class AffiliateMerchantRepository(ABC):
    """Persistence for the merchant registry."""

    @abstractmethod
    def save_merchant(self, merchant: AffiliateMerchant) -> AffiliateMerchant:
        """Create or replace a merchant registry entry."""

    @abstractmethod
    def get_merchant(self, merchant_id: str) -> AffiliateMerchant | None:
        """Return a merchant by id, or None."""

    @abstractmethod
    def list_merchants(
        self,
        *,
        status: str | None = None,
        marketplace: str | None = None,
        country: str | None = None,
    ) -> list[AffiliateMerchant]:
        """Return merchants in insertion order, optionally filtered."""

    @abstractmethod
    def delete_merchant(self, merchant_id: str) -> bool:
        """Delete a merchant. Returns False if missing."""


class AffiliateLinkRepository(ABC):
    """Persistence for generated affiliate links."""

    @abstractmethod
    def save_link(self, link: AffiliateLink) -> AffiliateLink:
        """Create or replace an affiliate link."""

    @abstractmethod
    def get_link(self, link_id: str) -> AffiliateLink | None:
        """Return a link by id, or None."""

    @abstractmethod
    def list_links(
        self,
        *,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 100,
    ) -> list[AffiliateLink]:
        """Return links newest-first, optionally filtered."""


class AffiliateClickRepository(ABC):
    """Persistence for tracked affiliate clicks."""

    @abstractmethod
    def save_click(self, click: AffiliateClick) -> AffiliateClick:
        """Create or replace a click event."""

    @abstractmethod
    def get_click(self, click_id: str) -> AffiliateClick | None:
        """Return a click by id, or None."""

    @abstractmethod
    def list_clicks(
        self,
        *,
        user_id: str | None = None,
        session_id: str | None = None,
        merchant_id: str | None = None,
        product_id: str | None = None,
        limit: int = 200,
    ) -> list[AffiliateClick]:
        """Return clicks newest-first, optionally filtered."""


class AffiliateAttributionRepository(ABC):
    """Persistence for attribution outcomes."""

    @abstractmethod
    def save_attribution(self, result: AttributionResult) -> AttributionResult:
        """Create or replace an attribution result."""

    @abstractmethod
    def list_attributions(self, *, limit: int = 100) -> list[AttributionResult]:
        """Return attribution results newest-first."""


class AffiliateDisclosureRepository(ABC):
    """Persistence for disclosure text records."""

    @abstractmethod
    def save_disclosure(self, disclosure: AffiliateDisclosure) -> AffiliateDisclosure:
        """Create or replace a disclosure record."""

    @abstractmethod
    def get_disclosure(self, disclosure_id: str) -> AffiliateDisclosure | None:
        """Return a disclosure by id, or None."""

    @abstractmethod
    def list_disclosures(
        self,
        *,
        region: str | None = None,
        merchant_id: str | None = None,
        disclosure_type: str | None = None,
        active_only: bool = True,
    ) -> list[AffiliateDisclosure]:
        """Return disclosures in insertion order, optionally filtered."""
