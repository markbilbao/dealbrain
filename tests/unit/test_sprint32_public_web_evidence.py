"""Sprint 32 public-web discovery: snippets are not prices; providers are not merchants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.domain.entities.public_web_shopping_evidence import (
    LEVEL_A,
    LEVEL_C,
    LEVEL_D,
    SEARCH_PROVIDER_IS_NOT_MERCHANT,
    SNIPPET_NOT_CANONICAL_PRICE,
    PublicWebProvenance,
    PublicWebShoppingResult,
    classify_search_hit_as_discovery,
    offer_promotion_reason,
    refuse_snippet_price_line,
    shipping_status_from_discovery_text,
    unknown_money_line,
)
from app.domain.entities.research_execution import ResearchCapability, ResearchProviderDescriptor
from app.research.certification import (
    make_research_provider_certification,
    research_provider_certification_catalog_for_tests,
)
from app.research.public_web_provider import (
    PublicWebResearchProvider,
    make_public_web_research_provider,
)
from app.research.registry import (
    production_research_provider_registry,
    research_provider_registry_for_tests,
)
from app.services.research_execution import execute_research_plan

from tests.unit.test_sprint31_research_execution_router import (
    _authorization,
    _plan,
    _scope,
)


def _discovery_hit(**overrides):
    payload = {
        "query_id": "ph-smartphones-001",
        "discovery_provider_id": "brave_search",
        "source_url": "https://shopee.ph/iphone-17-pro-max-i.1.2",
        "title": "iPhone 17 Pro Max",
        "snippet": "PHP 89990 with free shipping",
        "merchant_identity": "shopee.ph",
        "php_price_text": "PHP 89990",
        "test_fixture": True,
    }
    payload.update(overrides)
    return classify_search_hit_as_discovery(**payload)


def test_search_snippet_cannot_become_canonical_listing_price() -> None:
    result = _discovery_hit()
    assert result.evidence_tier == LEVEL_D
    assert result.role == "discovery_only"
    assert result.may_enter_evaluated_set is False
    assert offer_promotion_reason(result) == SNIPPET_NOT_CANONICAL_PRICE
    line = refuse_snippet_price_line(result)
    assert line.status == "unknown"
    assert line.amount_minor is None
    assert line.applied is False
    assert line.label == SNIPPET_NOT_CANONICAL_PRICE


def test_unknown_shipping_is_not_free_or_zero() -> None:
    assert shipping_status_from_discovery_text("Free shipping on selected items") == "unknown"
    shipping = unknown_money_line(kind="shipping")
    assert shipping.status == "unknown"
    assert shipping.amount_minor is None
    assert shipping.applied is False


def test_search_provider_cannot_be_labeled_as_the_merchant() -> None:
    with pytest.raises(ValueError, match=SEARCH_PROVIDER_IS_NOT_MERCHANT):
        PublicWebProvenance(
            discovery_provider_id="brave",
            source_url="https://shopee.ph/item",
            merchant_identity="brave",
        )


def test_level_d_cannot_be_constructed_as_offer_evidence() -> None:
    provenance = PublicWebProvenance(
        discovery_provider_id="brave_search",
        source_url="https://www.powermaccenter.com/products/iphone-17-pro-max",
        merchant_identity="powermaccenter.com",
    )
    with pytest.raises(ValueError, match=SNIPPET_NOT_CANONICAL_PRICE):
        PublicWebShoppingResult(
            query_id="ph-smartphones-001",
            provenance=provenance,
            evidence_tier=LEVEL_D,
            role="offer_evidence",
            test_fixture=True,
        )


def test_level_c_requires_explicit_sprint32_policy_permission() -> None:
    result = PublicWebShoppingResult(
        query_id="ph-smartphones-001",
        provenance=PublicWebProvenance(
            discovery_provider_id="brave_search",
            source_url="https://www.powermaccenter.com/products/iphone-17-pro-max",
            merchant_identity="powermaccenter.com",
            contractual_policy="allowed",
        ),
        evidence_tier=LEVEL_C,
        role="discovery_only",
        price_tied_to_source=True,
        freshness_evidence=True,
        snippet_only_price=False,
        search_result_not_product_page=False,
        level_c_policy_permitted=False,
        test_fixture=True,
    )
    assert offer_promotion_reason(result) == "level_c_not_policy_permitted"


def test_level_a_offer_requires_tied_price_freshness_and_allowed_policy() -> None:
    ready = PublicWebShoppingResult(
        query_id="ph-smartphones-001",
        provenance=PublicWebProvenance(
            discovery_provider_id="brave_search",
            source_url="https://www.powermaccenter.com/products/iphone-17-pro-max",
            merchant_identity="powermaccenter.com",
            retrieved_at=datetime(2026, 9, 18, tzinfo=UTC),
            contractual_policy="allowed",
        ),
        evidence_tier=LEVEL_A,
        role="offer_evidence",
        price_tied_to_source=True,
        freshness_evidence=True,
        snippet_only_price=False,
        search_result_not_product_page=False,
        test_fixture=True,
    )
    assert ready.may_enter_evaluated_set is True
    unknown_policy = PublicWebShoppingResult(
        query_id="ph-smartphones-001",
        provenance=PublicWebProvenance(
            discovery_provider_id="brave_search",
            source_url="https://www.powermaccenter.com/products/iphone-17-pro-max",
            merchant_identity="powermaccenter.com",
            contractual_policy="unknown",
        ),
        evidence_tier=LEVEL_A,
        role="discovery_only",
        price_tied_to_source=True,
        freshness_evidence=True,
        snippet_only_price=False,
        search_result_not_product_page=False,
        test_fixture=True,
    )
    assert offer_promotion_reason(unknown_policy) == "policy_not_allowed"


def test_public_web_provider_is_discovery_only_and_cannot_claim_pricing() -> None:
    provider = make_public_web_research_provider(
        provider_id="ph-brave-search",
        test_fixture=False,
    )
    assert provider.descriptor.provider_type == "public_web"
    assert provider.descriptor.supported_capabilities == (ResearchCapability.PRODUCT_DISCOVERY,)
    assert provider.descriptor.can_provide_pricing is False
    with pytest.raises(ValueError, match="pricing"):
        PublicWebResearchProvider(
            ResearchProviderDescriptor(
                provider_id="bad-public-web",
                provider_type="public_web",
                supported_markets=("PH",),
                supported_capabilities=(ResearchCapability.CURRENT_PRICING,),
                supported_sources=(),
                test_fixture=False,
                can_provide_pricing=True,
            )
        )


def test_public_web_discovery_can_plan_without_creating_offer_pricing() -> None:
    provider = make_public_web_research_provider(
        provider_id="test-public-web-ph",
        test_fixture=True,
    )
    cert = make_research_provider_certification(
        provider_id=provider.provider_id,
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        market="PH",
        certification_version="test-public-web-v1",
        source=None,
        source_scope="source_agnostic",
        test_fixture=True,
    )
    result = _plan(
        _authorization(_scope(reason="outside_evaluated_set")),
        registry=research_provider_registry_for_tests([provider]),
        catalog=research_provider_certification_catalog_for_tests((cert,)),
    )
    plan = result.plan
    assert plan is not None
    assert any(
        step.capability is ResearchCapability.PRODUCT_DISCOVERY
        and step.provider_id == "test-public-web-ph"
        for step in plan.eligible_steps
    )
    assert any(
        item.capability is ResearchCapability.OFFER_DISCOVERY for item in plan.blocked_requirements
    )
    assert all(
        step.capability is not ResearchCapability.CURRENT_PRICING for step in plan.eligible_steps
    )
    assert plan.source_checked is False
    assert plan.execution_implemented is False
    preparation = execute_research_plan(plan)
    assert preparation.connectors_invoked is False
    assert preparation.attempted is False
    assert preparation.source_checked is False
    assert preparation.trace.attempted_sources == ()


def test_production_registry_still_has_no_public_web_provider() -> None:
    assert len(production_research_provider_registry().list_providers()) == 1


def test_unknown_provider_type_fails_closed() -> None:
    with pytest.raises(ValueError, match="provider_type is unknown"):
        ResearchProviderDescriptor(
            provider_id="web-search-alias",
            provider_type="web_search",  # type: ignore[arg-type]
            supported_markets=("PH",),
            supported_capabilities=(ResearchCapability.PRODUCT_DISCOVERY,),
            supported_sources=(),
            test_fixture=False,
        )
