"""Real Shopify Global Catalog PH technical provider identity.

Registration is not permission to execute. ``operational_status`` stays
DISABLED until Sprint 38 / production deployment gates. ``execute`` remains
unimplemented on ``StaticResearchProvider``. Affiliate commission is absent
and is not part of this identity.
"""

from __future__ import annotations

from app.domain.entities.connector_reliability import ConnectorOperationalStatus
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.providers import StaticResearchProvider
from app.research.shopify_global_catalog_capability_policy import (
    SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_MARKET,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
)

SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID = SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID
# Technical support is an authority of its own. It must not grow because the
# evidence tuple grows. Production composition checks this set against evidence
# and the capability-policy map before any certification write.
SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.AVAILABILITY,
)


def shopify_global_catalog_ph_provider() -> StaticResearchProvider:
    """Non-fixture PH merchant descriptor. Operationally disabled."""

    descriptor = ResearchProviderDescriptor(
        provider_id=SHOPIFY_GLOBAL_CATALOG_PROVIDER_ID,
        provider_type="merchant",
        supported_markets=(SHOPIFY_GLOBAL_CATALOG_MARKET,),
        supported_capabilities=SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
        supported_sources=(SHOPIFY_GLOBAL_CATALOG_SOURCE,),
        operational_status=ConnectorOperationalStatus.DISABLED,
        test_fixture=False,
        affiliate_commission_rate=None,
        may_expand_evaluated_set=False,
        can_provide_pricing=True,
        can_provide_shipping_taxes=False,
        can_provide_product_evidence=True,
        can_provide_review_evidence=False,
    )
    return StaticResearchProvider(descriptor)


def shopify_global_catalog_unsupported_capabilities() -> tuple[ResearchCapability, ...]:
    """Capabilities this provider must not claim."""

    return (
        ResearchCapability.SHIPPING,
        ResearchCapability.TAXES_IMPORT,
        ResearchCapability.PROMOTION_EVIDENCE,
        ResearchCapability.REVIEW_COMMUNITY_EVIDENCE,
    )
