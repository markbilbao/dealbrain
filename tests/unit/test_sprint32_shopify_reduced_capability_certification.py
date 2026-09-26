"""Trusted reduced Shopify Global Catalog PH certification. No Shopify calls."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import httpx
import pytest
from app.domain.entities.connector_reliability import ConnectorOperationalStatus
from app.domain.entities.research_certification_decision import CertificationDecisionRequest
from app.domain.entities.research_execution import ResearchCapability, TrustedMarketContext
from app.research.certification import (
    ResearchProviderCertificationCatalog,
    production_research_provider_certification_catalog,
)
from app.research.certification_evidence import (
    ResearchProviderCertificationEvidenceCatalog,
    make_research_provider_certification_evidence,
    production_research_provider_certification_evidence_catalog,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_access_stage import (
    anonymous_global_catalog_access_stage,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_CAPABILITIES,
    SHOPIFY_EVIDENCE_REVIEWER,
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
    SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
)
from app.research.shopify_global_catalog_production_composition import (
    SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE,
    decide_shopify_reduced_capability_certifications,
    shopify_reduced_capability_decision_request,
)
from app.research.shopify_global_catalog_provider import (
    shopify_global_catalog_ph_provider,
    shopify_global_catalog_unsupported_capabilities,
)
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)
from app.services.research_execution_router import plan_authorized_research
from app.ucp.agent_profile import PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED

from tests.unit.test_phase_29_4b_refine_session_recommendation import _owner
from tests.unit.test_sprint31_certification_authority import _pricing_scope
from tests.unit.test_sprint31_research_execution_router import _authorization

ROOT = Path(__file__).resolve().parents[2]
SPRINT32 = ROOT / "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
SPRINT38 = ROOT / "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md"
SPRINT41 = ROOT / "docs/roadmap/sprints/SPRINT_41_PRODUCTION_ENVIRONMENT_DEPLOY.md"
ATTEMPT3 = (
    ROOT / "docs/roadmap/evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_NORMALIZATION_ATTEMPT_3.md"
)
HARNESS = ROOT / "scripts/shopify_global_catalog_normalization_validation.py"
_ALLOWED = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.AVAILABILITY,
)
_REFUSED = (
    ResearchCapability.SHIPPING,
    ResearchCapability.TAXES_IMPORT,
    ResearchCapability.PROMOTION_EVIDENCE,
)


def test_production_provider_identity_is_exact_and_disabled() -> None:
    provider = shopify_global_catalog_ph_provider()
    descriptor = provider.descriptor
    assert descriptor.provider_id == "ph-shopify-global-catalog"
    assert descriptor.test_fixture is False
    assert descriptor.provider_type == "merchant"
    assert descriptor.supported_markets == ("PH",)
    assert descriptor.supported_sources == ("shopify_global_catalog",)
    assert descriptor.supported_capabilities == _ALLOWED
    assert descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    assert descriptor.is_operationally_available is False
    assert descriptor.can_provide_pricing is True
    assert descriptor.can_provide_product_evidence is True
    assert descriptor.can_provide_shipping_taxes is False
    assert descriptor.can_provide_review_evidence is False
    assert descriptor.affiliate_commission_rate is None
    for capability in shopify_global_catalog_unsupported_capabilities():
        assert capability not in descriptor.supported_capabilities
    registered = production_research_provider_registry()
    assert [item.provider_id for item in registered.list_providers()] == [
        "ph-shopify-global-catalog"
    ]
    assert registered.get("ph-shopify-global-catalog") is not None
    stored = registered.get("ph-shopify-global-catalog")
    assert stored is not None
    assert stored.descriptor.operational_status is ConnectorOperationalStatus.DISABLED


def test_provider_execute_stays_unimplemented() -> None:
    provider = production_research_provider_registry().get("ph-shopify-global-catalog")
    assert provider is not None
    assert not hasattr(StaticResearchProvider, "certify_self")
    assert not hasattr(provider, "decide")
    with pytest.raises(NotImplementedError, match="cannot execute research"):
        provider.execute(None)  # type: ignore[arg-type]


def test_evidence_rows_record_attempt_three_as_fail_closed_ambiguity() -> None:
    records = production_research_provider_certification_evidence_catalog().list_records()
    assert len(records) == 4
    assert [record.capability for record in records] == list(SHOPIFY_EVIDENCE_CAPABILITIES)
    attempt = ATTEMPT3.read_text(encoding="utf-8")
    assert "attempt #3" in attempt.casefold()
    assert "attempts #1 and #2" in attempt.casefold()
    assert "ambiguous_or_insufficient_matches_count = 5" in attempt
    assert "not failed normalization" in attempt
    assert "fail-closed" in attempt
    assert "gid://shopify" not in attempt
    for record in records:
        assert record.provider_id == "ph-shopify-global-catalog"
        assert record.market == "PH"
        assert record.source == SHOPIFY_GLOBAL_CATALOG_SOURCE
        assert record.test_fixture is False
        assert record.evidence_date == date(2026, 9, 25)
        assert record.review_date == date(2026, 9, 25)
        assert record.reviewer == SHOPIFY_EVIDENCE_REVIEWER
        assert "not counsel approval" in record.reviewer
        assert "counsel approval" in record.reviewer
        assert record.restrictions == ()
        assert record.certification_version == SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION
        assert "ambiguous_or_insufficient_matches_count 5" in record.notes
        assert "fail-closed" in record.notes
        assert "exact match" in record.notes
        assert "2026-09-25" in record.notes
        assert record.grants_certification is False


def test_trusted_decision_certifies_only_the_four_allowed_capabilities() -> None:
    catalog = ResearchProviderCertificationCatalog(allow_test_certifications=False)
    results = decide_shopify_reduced_capability_certifications(catalog)
    assert len(results) == 4
    assert all(result.accepted is True and result.reason == "approved" for result in results)
    assert all(
        result.reviewer == SHOPIFY_EVIDENCE_REVIEWER and "not counsel approval" in result.reviewer
        for result in results
    )
    assert all(result.decided_at == SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE for result in results)
    assert {result.capability for result in results} == set(_ALLOWED)
    assert all(
        result.certification is not None
        and result.certification.certification_version
        == SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION
        and result.certification.provider_id == "ph-shopify-global-catalog"
        and result.certification.market == "PH"
        and result.certification.source == SHOPIFY_GLOBAL_CATALOG_SOURCE
        and result.certification.policy == "allowed"
        and result.certification.status == "certified"
        and result.certification.test_fixture is False
        for result in results
    )
    production = production_research_provider_certification_catalog()
    assert len(production.list_records()) == 4
    assert len(production_research_provider_certification_evidence_catalog().list_records()) == 4
    assert len(production_research_provider_registry().list_providers()) == 1
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    for capability in _REFUSED:
        assert (
            production.lookup(
                provider_id="ph-shopify-global-catalog",
                capability=capability,
                market="PH",
                source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
            )
            is None
        )


def test_exact_bindings_are_required_and_uncertified_capabilities_are_refused() -> None:
    production = production_research_provider_certification_catalog()
    evidence = production_research_provider_certification_evidence_catalog()
    registry = production_research_provider_registry()
    service = ResearchProviderCertificationDecisionService(evidence, production, registry)
    wrong_provider = service.decide(
        _request(provider_id="other-provider", capability=ResearchCapability.PRODUCT_DISCOVERY)
    )
    wrong_market = service.decide(
        _request(market="US", capability=ResearchCapability.PRODUCT_DISCOVERY)
    )
    wrong_source = service.decide(
        _request(source="other-source", capability=ResearchCapability.PRODUCT_DISCOVERY)
    )
    wrong_capability = service.decide(_request(capability=ResearchCapability.SHIPPING))
    assert wrong_provider.accepted is False
    assert wrong_provider.reason == "evidence_missing"
    assert wrong_market.accepted is False
    assert wrong_market.reason == "identity_mismatch"
    assert wrong_source.accepted is False
    assert wrong_source.reason == "identity_mismatch"
    assert wrong_capability.accepted is False
    assert wrong_capability.reason == "identity_mismatch"
    isolated = ResearchProviderCertificationCatalog(allow_test_certifications=False)
    binding = ResearchProviderCertificationDecisionService(
        _shipping_evidence_catalog(),
        isolated,
        registry,
    )
    shipping = binding.decide(_request(capability=ResearchCapability.SHIPPING))
    tax = binding.decide(_request(capability=ResearchCapability.TAXES_IMPORT))
    promotion = binding.decide(_request(capability=ResearchCapability.PROMOTION_EVIDENCE))
    assert shipping.reason == "provider_capability_mismatch"
    assert tax.reason == "provider_capability_mismatch"
    assert promotion.reason == "provider_capability_mismatch"
    assert isolated.list_records() == ()
    market_binding = ResearchProviderCertificationDecisionService(
        _copied_evidence_catalog(market="US"),
        ResearchProviderCertificationCatalog(allow_test_certifications=False),
        registry,
    )
    assert (
        market_binding.decide(
            _request(market="US", capability=ResearchCapability.CURRENT_PRICING)
        ).reason
        == "provider_market_mismatch"
    )
    source_binding = ResearchProviderCertificationDecisionService(
        _copied_evidence_catalog(source="other-source"),
        ResearchProviderCertificationCatalog(allow_test_certifications=False),
        registry,
    )
    assert (
        source_binding.decide(
            _request(source="other-source", capability=ResearchCapability.CURRENT_PRICING)
        ).reason
        == "provider_source_mismatch"
    )


def test_disabled_provider_keeps_planning_fail_closed_without_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Shopify must not be called")

    monkeypatch.setattr(httpx, "post", _boom)
    monkeypatch.setattr(httpx, "Client", _boom)
    authorization = _authorization(_pricing_scope(source=SHOPIFY_GLOBAL_CATALOG_SOURCE))
    planned = plan_authorized_research(
        authorization,
        owner=_owner(),
        conversation_id=authorization.conversation_id,
        decision_id=authorization.decision_id,
        canonical_context_version=authorization.canonical_context_version,
        registry=production_research_provider_registry(),
        catalog=production_research_provider_certification_catalog(),
        routing_policy=production_research_provider_routing_policy_catalog(),
        trusted_market=TrustedMarketContext(country_code="PH"),
    )
    assert planned.plan is not None
    assert planned.plan.eligible_steps == ()
    assert planned.plan.plan_ready is False
    assert planned.plan.execution_available is False
    assert planned.plan.execution_implemented is False
    assert any(item.reason == "provider_unavailable" for item in planned.plan.blocked_requirements)
    assert production_research_provider_routing_policy_catalog().list_records() == ()
    request = shopify_reduced_capability_decision_request(ResearchCapability.CURRENT_PRICING)
    assert not hasattr(request, "affiliate_commission_rate")
    for record in production_research_provider_certification_catalog().list_records():
        assert "affiliate" not in record.to_dict()


def test_sprint_gates_and_harness_stay_unchanged() -> None:
    stage = anonymous_global_catalog_access_stage()
    sprint32 = SPRINT32.read_text(encoding="utf-8")
    sprint38 = SPRINT38.read_text(encoding="utf-8")
    sprint41 = SPRINT41.read_text(encoding="utf-8")
    assert PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED is False
    assert stage.production_profile_deployed is False
    assert stage.production_ready is False
    assert stage.production_certified is False
    assert stage.executable_production_certification is False
    assert stage.production_provider_registered is True
    assert stage.sprint_32_status == "COMPLETE / CLOSED"
    assert stage.sprint_38_status == "IN PROGRESS"
    assert stage.sprint_38_live_execution_status == "NOT OPERATIONAL"
    assert stage.sprint_41_status == "UNSTARTED"
    assert "Sprint 32 remains open." in sprint32
    assert "COMPLETE / CLOSED" in next(
        line for line in sprint32.splitlines() if line.startswith("**Status:**")
    )
    sprint38_status = sprint38.split("**Status:**", 1)[1].splitlines()[0].strip()
    assert sprint38_status.startswith("IN PROGRESS")
    assert not sprint38_status.startswith("COMPLETE")
    sprint41_status = sprint41.split("**Status:**", 1)[1].splitlines()[0].strip()
    assert sprint41_status.startswith("Planned")
    assert "not started" in sprint41_status.casefold()
    harness = HARNESS.read_text(encoding="utf-8")
    assert "attempt #4" not in harness
    for path in (
        ROOT / "app/research/shopify_global_catalog_provider.py",
        ROOT / "app/research/shopify_global_catalog_production_composition.py",
        ROOT / "app/research/registry.py",
        ROOT / "app/research/certification.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert imported.isdisjoint({"httpx", "requests", "urllib", "socket", "aiohttp"})


def _request(
    *,
    provider_id: str = "ph-shopify-global-catalog",
    capability: ResearchCapability = ResearchCapability.PRODUCT_DISCOVERY,
    market: str = "PH",
    source: str = SHOPIFY_GLOBAL_CATALOG_SOURCE,
) -> CertificationDecisionRequest:
    return CertificationDecisionRequest(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        requested_status="certified",
        requested_policy="allowed",
        certification_version=SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
        reviewer=SHOPIFY_EVIDENCE_REVIEWER,
        decided_at=SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE,
    )


def _shipping_evidence_catalog() -> ResearchProviderCertificationEvidenceCatalog:
    catalog = ResearchProviderCertificationEvidenceCatalog(allow_test_evidence=False)
    for capability in _REFUSED:
        catalog.register(_nonfixture_evidence(capability))
    return catalog


def _copied_evidence_catalog(
    *,
    market: str = "PH",
    source: str = SHOPIFY_GLOBAL_CATALOG_SOURCE,
) -> ResearchProviderCertificationEvidenceCatalog:
    catalog = ResearchProviderCertificationEvidenceCatalog(allow_test_evidence=False)
    catalog.register(
        _nonfixture_evidence(
            ResearchCapability.CURRENT_PRICING,
            market=market,
            source=source,
        )
    )
    return catalog


def _nonfixture_evidence(
    capability: ResearchCapability,
    *,
    market: str = "PH",
    source: str = SHOPIFY_GLOBAL_CATALOG_SOURCE,
):
    return make_research_provider_certification_evidence(
        provider_id="ph-shopify-global-catalog",
        capability=capability,
        market=market,
        source=source,
        evidence_source="tests/unit/test_sprint32_shopify_reduced_capability_certification.py",
        certification_version=SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
        evidence_date=date(2026, 9, 25),
        review_date=date(2026, 9, 25),
        reviewer=SHOPIFY_EVIDENCE_REVIEWER,
        completeness="recorded",
        notes="Binding test evidence. Not a production grant for this capability.",
        test_fixture=False,
    )
