"""Public-web discovery provider — technical descriptor only.

Search/retrieval implementations declare PRODUCT_DISCOVERY support. They
are not merchants and cannot provide canonical pricing. ``execute`` remains
unimplemented until Sprint 38 after certification.
"""

from __future__ import annotations

from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.providers import StaticResearchProvider

PUBLIC_WEB_PROVIDER_TYPE = "public_web"
_FORBIDDEN_PRICING_CAPABILITIES = frozenset(
    {
        ResearchCapability.CURRENT_PRICING,
        ResearchCapability.AVAILABILITY,
        ResearchCapability.SHIPPING,
        ResearchCapability.TAXES_IMPORT,
        ResearchCapability.PROMOTION_EVIDENCE,
    }
)


class PublicWebResearchProvider(StaticResearchProvider):
    """Technical public-web discovery adapter.

    Registers through the existing ``ResearchProviderRegistry``. Does not
    create a parallel registry or router. Does not perform HTTP.
    """

    def __init__(self, descriptor: ResearchProviderDescriptor) -> None:
        _validate_public_web_descriptor(descriptor)
        super().__init__(descriptor)


def make_public_web_research_provider(
    *,
    provider_id: str,
    markets: tuple[str, ...] = ("PH",),
    supported_sources: tuple[str, ...] = (),
    test_fixture: bool = True,
) -> PublicWebResearchProvider:
    """Build a discovery-only public-web provider. Not a certification."""

    provider_type = "test" if test_fixture else PUBLIC_WEB_PROVIDER_TYPE
    descriptor = ResearchProviderDescriptor(
        provider_id=provider_id,
        provider_type=provider_type,
        supported_markets=markets,
        supported_capabilities=(ResearchCapability.PRODUCT_DISCOVERY,),
        supported_sources=supported_sources,
        test_fixture=test_fixture,
        may_expand_evaluated_set=False,
        can_provide_pricing=False,
        can_provide_shipping_taxes=False,
        can_provide_product_evidence=True,
        can_provide_review_evidence=False,
    )
    return PublicWebResearchProvider(descriptor)


def _validate_public_web_descriptor(descriptor: ResearchProviderDescriptor) -> None:
    if descriptor.test_fixture:
        if descriptor.provider_type != "test":
            raise ValueError("test fixtures must use provider_type='test'")
    elif descriptor.provider_type != PUBLIC_WEB_PROVIDER_TYPE:
        raise ValueError("non-fixture public-web providers must use provider_type='public_web'")
    forbidden = _FORBIDDEN_PRICING_CAPABILITIES.intersection(descriptor.supported_capabilities)
    if forbidden:
        names = ", ".join(sorted(item.value for item in forbidden))
        raise ValueError(
            "public-web discovery providers cannot declare pricing capabilities: " + names
        )
    if descriptor.can_provide_pricing or descriptor.can_provide_shipping_taxes:
        raise ValueError("public-web discovery providers cannot claim pricing or shipping")
    extra = [
        item
        for item in descriptor.supported_capabilities
        if item is not ResearchCapability.PRODUCT_DISCOVERY
    ]
    if extra:
        raise ValueError("public-web discovery is limited to product_discovery")
