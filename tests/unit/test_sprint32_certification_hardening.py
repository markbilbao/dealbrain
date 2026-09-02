"""Sprint 32.4: close remaining certification-boundary gaps."""

from __future__ import annotations

from dataclasses import fields
from datetime import date
from pathlib import Path

from app.domain.entities.connector_reliability import KillSwitch
from app.domain.entities.research_certification_decision import (
    CertificationDecisionRequest,
    CertificationDecisionResult,
)
from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderDescriptor,
)
from app.research.certification import (
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.certification_evidence import (
    make_research_provider_certification_evidence,
    production_research_provider_certification_evidence_catalog,
    research_provider_certification_evidence_catalog_for_tests,
)
from app.research.philippines_certification_evidence import (
    philippines_merchant_certification_evidence_catalog,
    philippines_merchant_certification_evidence_records,
    philippines_merchant_provider_ids,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import (
    ResearchProviderRegistry,
    production_research_provider_registry,
)
from app.research.routing import production_research_provider_routing_policy_catalog
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)

ROOT = Path(__file__).resolve().parents[2]
_AS_OF = date(2026, 9, 2)
_REVIEWER = "Sprint 32.4 reviewer"
_PRODUCTION_FACTORY_SOURCES = (
    ROOT / "app/research/certification.py",
    ROOT / "app/research/certification_evidence.py",
    ROOT / "app/research/registry.py",
    ROOT / "app/research/routing.py",
    ROOT / "app/research/__init__.py",
    ROOT / "app/research/eligibility.py",
    ROOT / "app/research/providers.py",
    ROOT / "app/services/research_execution_router.py",
    ROOT / "app/core/dependencies.py",
    ROOT / "app/main.py",
)
_RUNTIME_MUTATION_SOURCES = (
    ROOT / "app/research/providers.py",
    ROOT / "app/research/eligibility.py",
    ROOT / "app/research/registry.py",
    ROOT / "app/research/routing.py",
    ROOT / "app/services/research_execution_router.py",
    ROOT / "app/core/dependencies.py",
    ROOT / "app/main.py",
)


def _request(
    *,
    provider_id: str = "bound-merchant",
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str | None = "catalog-source",
    status: str = "certified",
    policy: str = "allowed",
) -> CertificationDecisionRequest:
    return CertificationDecisionRequest(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        requested_status=status,
        requested_policy=policy,
        certification_version="cert-v1",
        reviewer=_REVIEWER,
        decided_at=_AS_OF,
    )


def _recorded_evidence(
    *,
    provider_id: str = "bound-merchant",
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str | None = "catalog-source",
    completeness: str = "recorded",
    restrictions: tuple[str, ...] = (),
    test_fixture: bool = False,
):
    return make_research_provider_certification_evidence(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        evidence_source="tests/unit/test_sprint32_certification_hardening.py",
        completeness=completeness,
        review_date=_AS_OF,
        reviewer=_REVIEWER,
        restrictions=restrictions,
        review_after=date(2026, 12, 31),
        notes="Synthetic binding-test evidence. Not a production merchant grant.",
        test_fixture=test_fixture,
    )


def _production_provider(
    provider_id: str = "bound-merchant",
    *,
    markets: tuple[str, ...] = ("PH",),
    capabilities: tuple[ResearchCapability, ...] = (ResearchCapability.CURRENT_PRICING,),
    sources: tuple[str, ...] = ("catalog-source",),
    test_fixture: bool = False,
    kill_switch: KillSwitch | None = None,
) -> StaticResearchProvider:
    return StaticResearchProvider(
        ResearchProviderDescriptor(
            provider_id=provider_id,
            provider_type="test" if test_fixture else "merchant",
            supported_markets=markets,
            supported_capabilities=capabilities,
            supported_sources=sources,
            test_fixture=test_fixture,
            kill_switch=kill_switch or KillSwitch(),
        )
    )


def _production_service(
    evidence,
    *,
    registry: ResearchProviderRegistry | None = None,
    certs=None,
):
    evidence_catalog = production_research_provider_certification_evidence_catalog()
    evidence_catalog.register(evidence)
    return ResearchProviderCertificationDecisionService(
        evidence_catalog,
        certs or production_research_provider_certification_catalog(),
        provider_registry=registry,
    )


def test_documentary_ph_id_cannot_certify_without_registered_provider() -> None:
    evidence = _recorded_evidence(provider_id="ph-shopee", source="shopee")
    result = _production_service(evidence).decide(
        _request(provider_id="ph-shopee", source="shopee")
    )
    assert result.accepted is False
    assert result.reason == "provider_missing"
    assert result.certification is None
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()


def test_empty_production_registry_cannot_bind_documentary_identity() -> None:
    evidence = _recorded_evidence(provider_id="ph-lazada", source="lazada")
    result = _production_service(
        evidence,
        registry=production_research_provider_registry(),
    ).decide(_request(provider_id="ph-lazada", source="lazada"))
    assert result.accepted is False
    assert result.reason == "provider_missing"
    assert result.certification is None


def test_evidence_cannot_bind_to_a_different_registered_provider() -> None:
    evidence = _recorded_evidence(provider_id="ph-shopee", source="shopee")
    registry = ResearchProviderRegistry(
        [_production_provider("shopee-affiliate-open-api", sources=("shopee",))],
        allow_test_providers=False,
    )
    result = _production_service(evidence, registry=registry).decide(
        _request(provider_id="ph-shopee", source="shopee")
    )
    assert result.accepted is False
    assert result.reason == "provider_missing"
    assert result.certification is None


def test_production_certified_allowed_requires_exact_provider_support() -> None:
    evidence = _recorded_evidence()
    capability_mismatch = ResearchProviderRegistry(
        [_production_provider(capabilities=(ResearchCapability.PRODUCT_DISCOVERY,))],
        allow_test_providers=False,
    )
    market_mismatch = ResearchProviderRegistry(
        [_production_provider(markets=("US",))],
        allow_test_providers=False,
    )
    source_mismatch = ResearchProviderRegistry(
        [_production_provider(sources=("other-source",))],
        allow_test_providers=False,
    )
    assert (
        _production_service(evidence, registry=capability_mismatch).decide(_request()).reason
        == "provider_capability_mismatch"
    )
    assert (
        _production_service(evidence, registry=market_mismatch).decide(_request()).reason
        == "provider_market_mismatch"
    )
    assert (
        _production_service(evidence, registry=source_mismatch).decide(_request()).reason
        == "provider_source_mismatch"
    )


def test_test_provider_cannot_satisfy_production_certification() -> None:
    evidence = _recorded_evidence()
    registry = ResearchProviderRegistry(
        [_production_provider(test_fixture=True)],
        allow_test_providers=True,
    )
    result = _production_service(evidence, registry=registry).decide(_request())
    assert result.accepted is False
    assert result.reason == "provider_fixture_forbidden"
    assert result.certification is None


def test_test_catalog_does_not_require_a_production_provider() -> None:
    evidence = _recorded_evidence(
        provider_id="test-merchant-a",
        test_fixture=True,
    )
    service = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests((evidence,)),
        research_provider_certification_catalog_for_tests(()),
    )
    result = service.decide(_request(provider_id="test-merchant-a"))
    assert result.accepted is True
    assert result.reason == "approved"
    assert result.certification is not None
    assert result.certification.test_fixture is True
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_certification_catalog().list_records() == ()


def test_bound_production_provider_can_be_certified_in_isolated_catalogs() -> None:
    evidence = _recorded_evidence()
    certs = production_research_provider_certification_catalog()
    registry = ResearchProviderRegistry(
        [_production_provider()],
        allow_test_providers=False,
    )
    result = _production_service(evidence, registry=registry, certs=certs).decide(_request())
    assert result.accepted is True
    assert result.reason == "approved"
    assert result.certification is not None
    assert result.certification.provider_id == "bound-merchant"
    assert result.certification.test_fixture is False
    assert certs.list_records() == (result.certification,)
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()


def test_kill_switch_does_not_block_structural_certification() -> None:
    evidence = _recorded_evidence()
    registry = ResearchProviderRegistry(
        [_production_provider(kill_switch=KillSwitch(engaged=True, reason="off"))],
        allow_test_providers=False,
    )
    result = _production_service(evidence, registry=registry).decide(_request())
    assert result.accepted is True
    assert result.certification is not None
    assert result.certification.status == "certified"
    assert production_research_provider_certification_catalog().list_records() == ()


def test_current_ph_documentary_records_remain_incomplete() -> None:
    service = ResearchProviderCertificationDecisionService(
        philippines_merchant_certification_evidence_catalog(),
        production_research_provider_certification_catalog(),
        provider_registry=production_research_provider_registry(),
    )
    for provider_id, source in (
        ("ph-shopee", "shopee"),
        ("ph-lazada", "lazada"),
        ("ph-tiktok-shop", "tiktok_shop"),
        ("ph-amazon", "amazon"),
        ("ph-temu", "temu"),
    ):
        result = service.decide(
            _request(
                provider_id=provider_id,
                source=source,
                capability=ResearchCapability.CURRENT_PRICING,
            )
        )
        assert result.accepted is False
        assert result.reason == "evidence_incomplete"
        assert result.certification is None
    assert set(philippines_merchant_provider_ids()) == {
        "ph-shopee",
        "ph-lazada",
        "ph-tiktok-shop",
        "ph-amazon",
        "ph-temu",
    }


def test_evidence_catalog_has_no_implicit_completeness_promotion() -> None:
    catalog = philippines_merchant_certification_evidence_catalog()
    assert not hasattr(catalog, "replace")
    assert not hasattr(catalog, "promote")
    assert not hasattr(catalog, "complete")
    assert not hasattr(catalog, "mark_recorded")
    record = catalog.lookup(
        provider_id="ph-shopee",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="shopee",
    )
    assert record is not None
    assert record.completeness == "incomplete"
    assert record.is_decision_ready(as_of=_AS_OF) is False


def test_production_factories_do_not_import_documentary_or_decision_mutation() -> None:
    for path in _PRODUCTION_FACTORY_SOURCES:
        source = path.read_text(encoding="utf-8")
        assert "philippines_certification_evidence" not in source
        assert "philippines_merchant_certification" not in source
    for path in _RUNTIME_MUTATION_SOURCES:
        source = path.read_text(encoding="utf-8")
        assert "research_certification_decision" not in source
        assert "ResearchProviderCertificationDecisionService" not in source


def test_provider_module_cannot_self_certify_or_write_catalogs() -> None:
    source = (ROOT / "app/research/providers.py").read_text(encoding="utf-8")
    assert "certify_self" not in source
    assert "set_certification" not in source
    assert ".register(" not in source
    assert ".replace(" not in source
    assert not hasattr(StaticResearchProvider, "certify_self")
    assert not hasattr(StaticResearchProvider, "decide")


def test_certification_and_evidence_do_not_create_routing() -> None:
    evidence = _recorded_evidence()
    registry = ResearchProviderRegistry(
        [_production_provider()],
        allow_test_providers=False,
    )
    _production_service(evidence, registry=registry).decide(_request())
    philippines_merchant_certification_evidence_catalog()
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_commercial_fields_cannot_bind_or_decide() -> None:
    names = {item.name for item in fields(CertificationDecisionRequest)}
    names |= {item.name for item in fields(CertificationDecisionResult)}
    assert names.isdisjoint(
        {
            "affiliate_commission_rate",
            "affiliate_status",
            "commission",
            "payout",
            "tracking_readiness",
        }
    )


def test_fixture_and_documentary_combinations_stay_isolated() -> None:
    fixture_evidence = _recorded_evidence(test_fixture=True)
    production_certs = production_research_provider_certification_catalog()
    fixture_service = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests((fixture_evidence,)),
        production_certs,
    )
    assert fixture_service.decide(_request()).reason == "fixture_forbidden"
    documentary = philippines_merchant_certification_evidence_catalog()
    production_evidence = production_research_provider_certification_evidence_catalog()
    assert documentary.list_records()
    assert production_evidence.list_records() == ()
    assert production_research_provider_certification_catalog().list_records() == ()


def test_sprint_32_4_production_defaults_remain_empty() -> None:
    assert len(philippines_merchant_certification_evidence_records()) == 15
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
