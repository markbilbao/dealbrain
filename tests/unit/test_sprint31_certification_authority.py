"""Sprint 31 certification-authority boundary.

Technical provider support is not PiqSavi production certification.
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from app.domain.entities.connector_reliability import (
    CircuitBreakerSnapshot,
    CircuitBreakerState,
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_execution import (
    CapabilityPolicyState,
    ProviderCertificationStatus,
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.certification import (
    make_research_provider_certification,
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import production_research_provider_registry
from app.services.research_execution import execute_research_plan

from tests.unit.test_sprint31_research_execution_router import (
    _authorization,
    _catalog_for_registry,
    _plan,
    _provider,
    _registry,
    _scope,
)


def _pricing_scope(*, source: str = "amazon"):
    return _scope(
        reason="freshness_required",
        freshness_required=True,
        requested_sources=(source,),
        outside_set_product_names=(),
    )


def _pricing_provider(
    provider_id: str = "test-merchant-a",
    *,
    markets: tuple[str, ...] = ("PH",),
    sources: tuple[str, ...] = ("amazon",),
    capabilities: tuple[ResearchCapability, ...] = (
        ResearchCapability.OFFER_DISCOVERY,
        ResearchCapability.CURRENT_PRICING,
        ResearchCapability.SHIPPING,
    ),
    commission: float | None = None,
) -> StaticResearchProvider:
    return _provider(
        provider_id,
        markets=markets,
        sources=sources,
        capabilities=capabilities,
        commission=commission,
    )


def _exact_cert(
    provider: StaticResearchProvider,
    *,
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str = "amazon",
    status: ProviderCertificationStatus = "certified",
    policy: CapabilityPolicyState = "allowed",
    version: str = "cert-v1",
):
    return make_research_provider_certification(
        provider_id=provider.provider_id,
        capability=capability,
        market=market,
        source=source,
        certification_version=version,
        status=status,
        policy=policy,
        test_fixture=True,
    )


def test_provider_descriptor_has_no_certification_authority_fields() -> None:
    names = {item.name for item in fields(ResearchProviderDescriptor)}
    assert "certification_status" not in names
    assert "certification_version" not in names
    assert "capability_certifications" not in names
    assert "is_certified" not in names
    assert "policy" not in names
    with pytest.raises(TypeError):
        payload = {
            "provider_id": "test-self-cert",
            "provider_type": "test",
            "supported_markets": ("PH",),
            "supported_capabilities": (ResearchCapability.CURRENT_PRICING,),
            "supported_sources": ("amazon",),
            "test_fixture": True,
            "certification_status": "certified",
        }
        ResearchProviderDescriptor(**payload)


def test_provider_self_declaration_cannot_certify_without_catalog_record() -> None:
    provider = _pricing_provider()
    descriptor = provider.descriptor
    assert descriptor.supported_markets == ("PH",)
    assert ResearchCapability.CURRENT_PRICING in descriptor.supported_capabilities
    assert "amazon" in descriptor.supported_sources
    assert descriptor.is_operationally_available is True
    result = _plan(
        _authorization(_pricing_scope()),
        registry=_registry(provider),
        certify=False,
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False
    assert plan.support_status == "blocked_missing_certified_provider"
    assert any(item.reason == "certification_missing" for item in plan.blocked_requirements)


def test_no_certification_record_blocks_technically_complete_provider() -> None:
    provider = _pricing_provider()
    catalog = research_provider_certification_catalog_for_tests(())
    result = _plan(
        _authorization(_pricing_scope()),
        registry=_registry(provider),
        catalog=catalog,
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False
    assert any(item.reason == "certification_missing" for item in plan.blocked_requirements)
    with pytest.raises(NotImplementedError):
        execute_research_plan(plan)


def test_us_certification_does_not_certify_philippines() -> None:
    provider = _pricing_provider(markets=("US", "PH"))
    catalog = research_provider_certification_catalog_for_tests(
        (
            _exact_cert(provider, capability=ResearchCapability.OFFER_DISCOVERY, market="US"),
            _exact_cert(provider, capability=ResearchCapability.CURRENT_PRICING, market="US"),
        )
    )
    result = _plan(
        _authorization(_pricing_scope()),
        registry=_registry(provider),
        catalog=catalog,
        market="PH",
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False
    assert any(item.reason == "certification_market_mismatch" for item in plan.blocked_requirements)


def test_pricing_certification_does_not_certify_shipping() -> None:
    provider = _pricing_provider()
    catalog = research_provider_certification_catalog_for_tests(
        (
            _exact_cert(provider, capability=ResearchCapability.OFFER_DISCOVERY),
            _exact_cert(provider, capability=ResearchCapability.CURRENT_PRICING),
        )
    )
    scope = _scope(
        reason="freshness_required",
        freshness_required=True,
        requested_evidence_topics=("shipping",),
        requested_sources=("amazon",),
        outside_set_product_names=(),
    )
    result = _plan(_authorization(scope), registry=_registry(provider), catalog=catalog)
    plan = result.plan
    assert plan is not None
    assert any(
        step.capability is ResearchCapability.CURRENT_PRICING for step in plan.eligible_steps
    )
    shipping = next(
        item for item in plan.blocked_requirements if item.capability is ResearchCapability.SHIPPING
    )
    assert shipping.reason == "certification_capability_mismatch"
    assert plan.support_status == "partially_supported"


def test_shopee_certification_does_not_certify_amazon() -> None:
    provider = _pricing_provider(sources=("amazon", "shopee"))
    catalog = research_provider_certification_catalog_for_tests(
        (
            _exact_cert(
                provider,
                capability=ResearchCapability.OFFER_DISCOVERY,
                source="shopee",
            ),
            _exact_cert(
                provider,
                capability=ResearchCapability.CURRENT_PRICING,
                source="shopee",
            ),
        )
    )
    result = _plan(
        _authorization(_pricing_scope(source="amazon")),
        registry=_registry(provider),
        catalog=catalog,
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "certification_source_mismatch" for item in plan.blocked_requirements)


def test_revoked_and_disabled_certifications_are_ineligible() -> None:
    provider = _pricing_provider()
    statuses: tuple[ProviderCertificationStatus, ...] = (
        "revoked",
        "disabled",
        "pending",
        "expired",
    )
    for status in statuses:
        catalog = research_provider_certification_catalog_for_tests(
            (
                _exact_cert(
                    provider,
                    capability=ResearchCapability.OFFER_DISCOVERY,
                    status=status,
                ),
                _exact_cert(
                    provider,
                    capability=ResearchCapability.CURRENT_PRICING,
                    status=status,
                ),
            )
        )
        result = _plan(
            _authorization(_pricing_scope()),
            registry=_registry(provider),
            catalog=catalog,
        )
        plan = result.plan
        assert plan is not None
        assert plan.eligible_steps == ()
        assert plan.plan_ready is False
        assert any(item.reason == f"certification_{status}" for item in plan.blocked_requirements)


def test_certification_version_changes_fingerprint_and_plan_digest() -> None:
    provider = _pricing_provider()
    registry = _registry(provider)
    catalog_v1 = _catalog_for_registry(registry, version="v1")
    catalog_v2 = _catalog_for_registry(registry, version="v2")
    first = _plan(_authorization(_pricing_scope()), registry=registry, catalog=catalog_v1)
    repeat = _plan(_authorization(_pricing_scope()), registry=registry, catalog=catalog_v1)
    second = _plan(_authorization(_pricing_scope()), registry=registry, catalog=catalog_v2)
    assert first.plan is not None and repeat.plan is not None and second.plan is not None
    assert first.plan.plan_ready is True
    assert second.plan.plan_ready is True
    assert catalog_v1.fingerprint() != catalog_v2.fingerprint()
    assert first.plan.plan_digest == repeat.plan.plan_digest
    assert first.plan.plan_digest != second.plan.plan_digest
    assert {step.certification_version for step in first.plan.eligible_steps} == {"v1"}
    assert {step.certification_version for step in second.plan.eligible_steps} == {"v2"}


def test_test_certifications_cannot_enter_production_catalog() -> None:
    provider = _pricing_provider()
    registry = _registry(provider)
    test_catalog = _catalog_for_registry(registry)
    ready = _plan(_authorization(_pricing_scope()), registry=registry, catalog=test_catalog)
    assert ready.plan is not None
    assert ready.plan.plan_ready is True

    production_registry = production_research_provider_registry()
    production_catalog = production_research_provider_certification_catalog()
    assert production_registry.list_providers() == ()
    assert production_catalog.list_records() == ()
    assert all(record.test_fixture for record in test_catalog.list_records())
    with pytest.raises(ValueError, match="test certifications"):
        production_catalog.register(_exact_cert(provider))
    blocked = _plan(
        _authorization(_pricing_scope()),
        registry=production_registry,
        catalog=production_catalog,
    )
    assert blocked.plan is not None
    assert blocked.plan.eligible_steps == ()
    assert blocked.plan.plan_ready is False


def test_affiliate_metadata_cannot_create_or_alter_certification() -> None:
    high = _pricing_provider("test-aaa", commission=0.99)
    low = _pricing_provider("test-bbb", commission=0.01)
    registry = _registry(high, low)
    empty = research_provider_certification_catalog_for_tests(())
    uncertified = _plan(
        _authorization(_pricing_scope()),
        registry=registry,
        catalog=empty,
    )
    assert uncertified.plan is not None
    assert uncertified.plan.eligible_steps == ()

    certified = _catalog_for_registry(registry)
    first = _plan(_authorization(_pricing_scope()), registry=registry, catalog=certified)
    swapped = _plan(
        _authorization(_pricing_scope()),
        registry=_registry(
            _pricing_provider("test-aaa", commission=0.01),
            _pricing_provider("test-bbb", commission=0.99),
        ),
        catalog=certified,
    )
    assert first.plan is not None and swapped.plan is not None
    assert first.plan.plan_ready is True
    assert {step.provider_id for step in first.plan.eligible_steps} == {"test-aaa"}
    assert {step.provider_id for step in swapped.plan.eligible_steps} == {"test-aaa"}
    assert first.plan.plan_digest == swapped.plan.plan_digest
    assert certified.fingerprint() == _catalog_for_registry(registry).fingerprint()


def test_trusted_policy_authority_cannot_be_overridden_by_provider() -> None:
    provider = _pricing_provider()
    registry = _registry(provider)
    policies: tuple[CapabilityPolicyState, ...] = ("restricted", "prohibited", "unknown")
    for policy in policies:
        catalog = _catalog_for_registry(registry, policy=policy)
        result = _plan(
            _authorization(_pricing_scope()),
            registry=registry,
            catalog=catalog,
        )
        plan = result.plan
        assert plan is not None
        assert plan.eligible_steps == ()
        assert any(item.reason == "policy_not_allowed" for item in plan.blocked_requirements)


def test_kill_switch_does_not_rewrite_certification_status() -> None:
    provider = _provider(
        capabilities=(
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.CURRENT_PRICING,
        ),
        kill_switch=KillSwitch(engaged=True, reason="off"),
    )
    registry = _registry(provider)
    catalog = _catalog_for_registry(registry)
    assert all(record.status == "certified" for record in catalog.list_records())
    result = _plan(_authorization(_pricing_scope()), registry=registry, catalog=catalog)
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "kill_switch" for item in plan.blocked_requirements)
    assert all(record.status == "certified" for record in catalog.list_records())


def test_open_circuit_blocks_planning_without_revoking_certification() -> None:
    provider = _provider(
        capabilities=(
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.CURRENT_PRICING,
        ),
        circuit=CircuitBreakerSnapshot(state=CircuitBreakerState.OPEN),
        operational_status=ConnectorOperationalStatus.AVAILABLE,
    )
    registry = _registry(provider)
    catalog = _catalog_for_registry(registry)
    result = _plan(_authorization(_pricing_scope()), registry=registry, catalog=catalog)
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "circuit_open" for item in plan.blocked_requirements)
    assert all(record.status == "certified" for record in catalog.list_records())


def test_missing_source_on_certification_is_not_a_wildcard() -> None:
    with pytest.raises(ValueError, match="explicit source identity"):
        make_research_provider_certification(
            provider_id="test-merchant-a",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            certification_version="v1",
            source=None,
            source_scope="exact",
        )
    record = make_research_provider_certification(
        provider_id="test-merchant-a",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        certification_version="v1",
        source=None,
        source_scope="source_agnostic",
        test_fixture=True,
    )
    catalog = research_provider_certification_catalog_for_tests((record,))
    assert (
        catalog.lookup(
            provider_id="test-merchant-a",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="amazon",
        )
        is None
    )
    assert (
        catalog.lookup(
            provider_id="test-merchant-a",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source=None,
        )
        is record
    )
