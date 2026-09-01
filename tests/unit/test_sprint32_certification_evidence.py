"""Sprint 32.1 certification evidence: sibling records do not authorize planning."""

from __future__ import annotations

from dataclasses import fields
from datetime import date, datetime

import pytest
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderCertificationEvidence,
)
from app.research.certification import (
    make_research_provider_certification,
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.certification_evidence import (
    make_research_provider_certification_evidence,
    production_research_provider_certification_evidence_catalog,
    research_provider_certification_evidence_catalog_for_tests,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.services.research_execution_router import plan_authorized_research

from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint31_certification_authority import (
    _exact_cert,
    _pricing_provider,
    _pricing_scope,
)
from tests.unit.test_sprint31_research_execution_router import (
    _authorization,
    _plan,
    _registry,
)


def _shopee_provider():
    return _pricing_provider(
        "test-shopee-ph",
        markets=("PH",),
        sources=("shopee",),
        capabilities=(
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.CURRENT_PRICING,
            ResearchCapability.SHIPPING,
        ),
    )


def _evidence(
    *,
    provider_id: str = "test-shopee-ph",
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str | None = "shopee",
    completeness: str = "recorded",
    certification_version: str = "",
    test_fixture: bool = True,
):
    return make_research_provider_certification_evidence(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        evidence_source="docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md",
        completeness=completeness,
        certification_version=certification_version,
        notes="Technical documentation exists; production rights remain unknown.",
        test_fixture=test_fixture,
    )


def test_shopee_technical_support_without_certification_is_not_eligible() -> None:
    provider = _shopee_provider()
    result = _plan(
        _authorization(_pricing_scope(source="shopee")),
        registry=_registry(provider),
        certify=False,
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False
    assert plan.support_status == "blocked_missing_certified_provider"
    assert any(item.reason == "certification_missing" for item in plan.blocked_requirements)


def test_evidence_record_does_not_authorize_planning() -> None:
    provider = _shopee_provider()
    catalog = research_provider_certification_evidence_catalog_for_tests((_evidence(),))
    stored = catalog.lookup(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="shopee",
    )
    assert stored is not None
    assert stored.grants_certification is False
    assert stored.grants_eligibility is False
    assert stored.completeness == "recorded"
    result = _plan(
        _authorization(_pricing_scope(source="shopee")),
        registry=_registry(provider),
        certify=False,
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "certification_missing" for item in plan.blocked_requirements)


def test_pending_certification_with_evidence_remains_blocked() -> None:
    provider = _shopee_provider()
    research_provider_certification_evidence_catalog_for_tests(
        (
            _evidence(capability=ResearchCapability.OFFER_DISCOVERY),
            _evidence(capability=ResearchCapability.CURRENT_PRICING),
        )
    )
    certs = (
        _exact_cert(
            provider,
            capability=ResearchCapability.OFFER_DISCOVERY,
            source="shopee",
            status="pending",
        ),
        _exact_cert(
            provider,
            capability=ResearchCapability.CURRENT_PRICING,
            source="shopee",
            status="pending",
        ),
    )
    result = _plan(
        _authorization(_pricing_scope(source="shopee")),
        registry=_registry(provider),
        catalog=research_provider_certification_catalog_for_tests(certs),
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "certification_pending" for item in plan.blocked_requirements)


def test_unknown_policy_with_evidence_remains_blocked() -> None:
    provider = _shopee_provider()
    research_provider_certification_evidence_catalog_for_tests(
        (
            _evidence(capability=ResearchCapability.OFFER_DISCOVERY),
            _evidence(capability=ResearchCapability.CURRENT_PRICING),
        )
    )
    certs = (
        _exact_cert(
            provider,
            capability=ResearchCapability.OFFER_DISCOVERY,
            source="shopee",
            policy="unknown",
        ),
        _exact_cert(
            provider,
            capability=ResearchCapability.CURRENT_PRICING,
            source="shopee",
            policy="unknown",
        ),
    )
    result = _plan(
        _authorization(_pricing_scope(source="shopee")),
        registry=_registry(provider),
        catalog=research_provider_certification_catalog_for_tests(certs),
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "policy_not_allowed" for item in plan.blocked_requirements)


def test_evidence_identity_is_exact_and_does_not_cross_source_market_or_capability() -> None:
    shopee_pricing = _evidence()
    catalog = research_provider_certification_evidence_catalog_for_tests((shopee_pricing,))
    assert (
        catalog.lookup(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="US",
            source="shopee",
        )
        is None
    )
    assert (
        catalog.lookup(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="lazada",
        )
        is None
    )
    assert (
        catalog.lookup(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="amazon",
        )
        is None
    )
    assert (
        catalog.lookup(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.SHIPPING,
            market="PH",
            source="shopee",
        )
        is None
    )
    amazon_cert = make_research_provider_certification(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="amazon",
        certification_version="v1",
        test_fixture=True,
    )
    assert shopee_pricing.binds_to(amazon_cert) is False
    matching = make_research_provider_certification(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="shopee",
        certification_version="v1",
        test_fixture=True,
    )
    assert shopee_pricing.binds_to(matching) is True


def test_us_shopee_evidence_does_not_authorize_philippines_planning() -> None:
    provider = _pricing_provider(
        "test-shopee-multi",
        markets=("US", "PH"),
        sources=("shopee",),
        capabilities=(
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.CURRENT_PRICING,
        ),
    )
    research_provider_certification_evidence_catalog_for_tests(
        (
            _evidence(
                provider_id="test-shopee-multi",
                capability=ResearchCapability.OFFER_DISCOVERY,
                market="US",
            ),
            _evidence(
                provider_id="test-shopee-multi",
                capability=ResearchCapability.CURRENT_PRICING,
                market="US",
            ),
        )
    )
    us_certs = (
        _exact_cert(
            provider,
            capability=ResearchCapability.OFFER_DISCOVERY,
            market="US",
            source="shopee",
        ),
        _exact_cert(
            provider,
            capability=ResearchCapability.CURRENT_PRICING,
            market="US",
            source="shopee",
        ),
    )
    result = _plan(
        _authorization(_pricing_scope(source="shopee")),
        registry=_registry(provider),
        catalog=research_provider_certification_catalog_for_tests(us_certs),
        market="PH",
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert any(item.reason == "certification_market_mismatch" for item in plan.blocked_requirements)


def test_test_evidence_cannot_enter_production_catalog() -> None:
    production = production_research_provider_certification_evidence_catalog()
    assert production.list_records() == ()
    with pytest.raises(ValueError, match="test evidence"):
        production.register(_evidence())


def test_sprint_32_1_does_not_populate_production_catalogs() -> None:
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    authorization = _authorization(_pricing_scope(source="shopee"))
    result = plan_authorized_research(
        authorization,
        owner=_owner(),
        conversation_id=authorization.conversation_id,
        decision_id=authorization.decision_id,
        canonical_context_version=authorization.canonical_context_version,
        registry=production_research_provider_registry(),
    )
    plan = result.plan
    assert plan is not None
    assert plan.eligible_steps == ()
    assert plan.plan_ready is False


def test_evidence_has_no_commission_or_price_authorization_fields() -> None:
    names = {item.name for item in fields(ResearchProviderCertificationEvidence)}
    forbidden = {
        "affiliate_commission_rate",
        "commission",
        "commission_rate",
        "commission_amount",
        "seller_commission",
        "price_min",
        "price_max",
        "discount_rate",
        "effective_cost",
        "landed_cost",
        "secret",
        "app_id",
        "appid",
        "token",
        "password",
    }
    assert names.isdisjoint(forbidden)
    dated = make_research_provider_certification_evidence(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="shopee",
        evidence_source="Sprint 32.1 inventory",
        review_date=date(2026, 9, 2),
        reviewer="Marketplace eng + legal",
        test_fixture=True,
    )
    assert "commission" not in dated.to_dict()
    assert "priceMin" not in dated.to_dict()
    assert "priceMax" not in dated.to_dict()


def test_evidence_rejects_source_wildcard_and_non_calendar_dates() -> None:
    with pytest.raises(ValueError, match="explicit source identity"):
        make_research_provider_certification_evidence(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            evidence_source="inventory",
            source=None,
            source_scope="exact",
        )
    source_agnostic = make_research_provider_certification_evidence(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        evidence_source="inventory",
        source=None,
        source_scope="source_agnostic",
        test_fixture=True,
    )
    catalog = research_provider_certification_evidence_catalog_for_tests((source_agnostic,))
    assert (
        catalog.lookup(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="shopee",
        )
        is None
    )
    with pytest.raises(ValueError, match="calendar date"):
        ResearchProviderCertificationEvidence(
            provider_id="test-shopee-ph",
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source="shopee",
            evidence_source="inventory",
            evidence_date=datetime(2026, 9, 2, 12, 0),
            test_fixture=True,
        )
