"""Sprint 32.2 trusted certification decision: evidence never self-authorizes."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

from app.domain.entities.research_certification_decision import (
    CertificationDecisionRequest,
    CertificationDecisionResult,
)
from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import (
    production_research_provider_certification_catalog,
    research_provider_certification_catalog_for_tests,
)
from app.research.certification_evidence import (
    make_research_provider_certification_evidence,
    production_research_provider_certification_evidence_catalog,
    research_provider_certification_evidence_catalog_for_tests,
)
from app.research.providers import StaticResearchProvider
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)

from tests.unit.test_sprint31_certification_authority import (
    _pricing_provider,
    _pricing_scope,
)
from tests.unit.test_sprint31_research_execution_router import _authorization, _plan, _registry

_AS_OF = date(2026, 9, 2)
_REVIEWER = "Sprint 32.2 test reviewer"


def _request(
    *,
    provider_id: str = "test-merchant-a",
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str | None = "catalog-source",
    status: str = "certified",
    policy: str = "allowed",
    version: str = "cert-v1",
) -> CertificationDecisionRequest:
    return CertificationDecisionRequest(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        requested_status=status,
        requested_policy=policy,
        certification_version=version,
        reviewer=_REVIEWER,
        decided_at=_AS_OF,
    )


def _ready_evidence(
    *,
    provider_id: str = "test-merchant-a",
    capability: ResearchCapability = ResearchCapability.CURRENT_PRICING,
    market: str = "PH",
    source: str | None = "catalog-source",
    completeness: str = "recorded",
    restrictions: tuple[str, ...] = (),
    review_after: date | None = date(2026, 12, 31),
    certification_version: str = "",
    test_fixture: bool = True,
):
    return make_research_provider_certification_evidence(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        evidence_source="tests/unit/test_sprint32_certification_decision.py",
        completeness=completeness,
        review_date=_AS_OF,
        reviewer=_REVIEWER,
        restrictions=restrictions,
        review_after=review_after,
        certification_version=certification_version,
        notes="Synthetic test evidence. Not a production merchant claim.",
        test_fixture=test_fixture,
    )


def _service(evidence_records=(), cert_records=()):
    return ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests(evidence_records),
        research_provider_certification_catalog_for_tests(cert_records),
    )


def test_complete_test_evidence_can_produce_certification() -> None:
    evidence = _ready_evidence()
    service = _service((evidence,))
    result = service.decide(_request())
    assert result.accepted is True
    assert result.reason == "approved"
    assert result.certification is not None
    assert result.certification.status == "certified"
    assert result.certification.policy == "allowed"
    assert result.certification.test_fixture is True
    assert result.evidence_ids == (evidence.evidence_id,)
    assert result.reviewer == _REVIEWER
    assert evidence.is_decision_ready(as_of=_AS_OF) is True


def test_missing_evidence_is_refused() -> None:
    result = _service().decide(_request())
    assert result.accepted is False
    assert result.reason == "evidence_missing"
    assert result.certification is None


def test_incomplete_evidence_is_refused() -> None:
    evidence = _ready_evidence(completeness="incomplete")
    result = _service((evidence,)).decide(_request())
    assert result.accepted is False
    assert result.reason == "evidence_incomplete"
    assert result.certification is None
    assert evidence.is_decision_ready(as_of=_AS_OF) is False


def test_identity_mismatch_is_refused() -> None:
    evidence = _ready_evidence(source="catalog-source")
    result = _service((evidence,)).decide(_request(source="other-source"))
    assert result.accepted is False
    assert result.reason == "identity_mismatch"
    assert result.certification is None


def test_stale_evidence_is_refused() -> None:
    evidence = _ready_evidence(review_after=date(2026, 8, 1))
    result = _service((evidence,)).decide(_request())
    assert result.accepted is False
    assert result.reason == "evidence_stale"
    assert result.certification is None


def test_test_evidence_cannot_enter_production_certification() -> None:
    evidence = _ready_evidence()
    service = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests((evidence,)),
        production_research_provider_certification_catalog(),
    )
    result = service.decide(_request())
    assert result.accepted is False
    assert result.reason == "fixture_forbidden"
    assert production_research_provider_certification_catalog().list_records() == ()


def test_evidence_does_not_infer_allowed_policy() -> None:
    evidence = _ready_evidence()
    result = _service((evidence,)).decide(_request(policy="unknown"))
    assert result.accepted is False
    assert result.reason == "denied"
    assert result.certification is None
    assert evidence.grants_certification is False


def test_restrictions_block_certified_allowed() -> None:
    evidence = _ready_evidence(restrictions=("sandbox only",))
    result = _service((evidence,)).decide(_request(policy="allowed"))
    assert result.accepted is False
    assert result.reason == "restrictions_unresolved"
    restricted = _service((evidence,)).decide(_request(policy="restricted"))
    assert restricted.accepted is True
    assert restricted.certification is not None
    assert restricted.certification.policy == "restricted"
    assert restricted.certification.is_production_eligible is False


def test_provider_cannot_self_certify() -> None:
    provider = _pricing_provider(
        "test-merchant-a",
        sources=("catalog-source",),
        commission=0.99,
    )
    assert not hasattr(StaticResearchProvider, "certify_self")
    assert not hasattr(StaticResearchProvider, "set_certification")
    assert not hasattr(StaticResearchProvider, "set_policy_allowed")
    assert not hasattr(provider, "certify_self")
    registry = production_research_provider_registry()
    assert registry.list_providers() == ()
    certs = production_research_provider_certification_catalog()
    assert certs.list_records() == ()
    assert provider.descriptor.affiliate_commission_rate == 0.99


def test_certification_decision_does_not_create_routing_policy() -> None:
    service = _service((_ready_evidence(),))
    result = service.decide(_request())
    assert result.accepted is True
    routing = production_research_provider_routing_policy_catalog()
    assert routing.list_records() == ()
    assert routing.lookup("test-merchant-a") is None


def test_sprint_32_2_production_catalogs_remain_empty() -> None:
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()


def test_commission_fields_cannot_influence_decision() -> None:
    names = {item.name for item in fields(CertificationDecisionRequest)}
    names |= {item.name for item in fields(CertificationDecisionResult)}
    assert names.isdisjoint(
        {
            "affiliate_commission_rate",
            "commission",
            "commission_rate",
            "payout",
            "expected_revenue",
            "affiliate_priority",
        }
    )
    first = _service((_ready_evidence(),)).decide(_request())
    second = _service((_ready_evidence(),)).decide(_request())
    assert first.accepted is second.accepted is True
    assert first.reason == second.reason == "approved"
    assert first.to_dict()["status"] == second.to_dict()["status"]
    assert first.to_dict()["policy"] == second.to_dict()["policy"]


def test_shopee_current_evidence_cannot_be_approved() -> None:
    shopee = make_research_provider_certification_evidence(
        provider_id="test-shopee-ph",
        capability=ResearchCapability.CURRENT_PRICING,
        market="PH",
        source="shopee",
        evidence_source="docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md",
        completeness="incomplete",
        notes="Counsel-cleared to apply; API access and rights remain unknown.",
        test_fixture=True,
    )
    result = _service((shopee,)).decide(_request(provider_id="test-shopee-ph", source="shopee"))
    assert result.accepted is False
    assert result.reason == "evidence_incomplete"
    assert result.certification is None
    assert production_research_provider_certification_catalog().list_records() == ()


def test_evidence_registration_does_not_populate_certification_or_plans() -> None:
    evidence = _ready_evidence()
    research_provider_certification_evidence_catalog_for_tests((evidence,))
    assert production_research_provider_certification_catalog().list_records() == ()
    provider = _pricing_provider(sources=("catalog-source",))
    planned = _plan(
        _authorization(_pricing_scope(source="catalog-source")),
        registry=_registry(provider),
        certify=False,
    )
    assert planned.plan is not None
    assert planned.plan.eligible_steps == ()
    assert any(item.reason == "certification_missing" for item in planned.plan.blocked_requirements)


def test_revoked_certification_no_longer_authorizes_planning() -> None:
    provider = _pricing_provider(
        sources=("catalog-source",),
        capabilities=(
            ResearchCapability.OFFER_DISCOVERY,
            ResearchCapability.CURRENT_PRICING,
        ),
    )
    evidence_rows = (
        _ready_evidence(capability=ResearchCapability.OFFER_DISCOVERY),
        _ready_evidence(capability=ResearchCapability.CURRENT_PRICING),
    )
    catalog = research_provider_certification_catalog_for_tests(())
    service = ResearchProviderCertificationDecisionService(
        research_provider_certification_evidence_catalog_for_tests(evidence_rows),
        catalog,
    )
    assert service.decide(_request(capability=ResearchCapability.OFFER_DISCOVERY)).accepted
    approved = service.decide(_request())
    assert approved.accepted is True
    ready = _plan(
        _authorization(_pricing_scope(source="catalog-source")),
        registry=_registry(provider),
        catalog=catalog,
    )
    assert ready.plan is not None
    assert ready.plan.plan_ready is True
    for capability in (
        ResearchCapability.OFFER_DISCOVERY,
        ResearchCapability.CURRENT_PRICING,
    ):
        revoked = service.decide(
            _request(capability=capability, status="revoked", policy="unknown")
        )
        assert revoked.accepted is True
        assert revoked.reason == "revoked"
        assert revoked.certification is not None
        assert revoked.certification.status == "revoked"
    blocked = _plan(
        _authorization(_pricing_scope(source="catalog-source")),
        registry=_registry(provider),
        catalog=catalog,
    )
    assert blocked.plan is not None
    assert blocked.plan.eligible_steps == ()
    assert blocked.plan.plan_ready is False
    assert any(item.reason == "certification_revoked" for item in blocked.plan.blocked_requirements)


def test_us_evidence_cannot_approve_philippines() -> None:
    evidence = _ready_evidence(market="US")
    result = _service((evidence,)).decide(_request(market="PH"))
    assert result.accepted is False
    assert result.reason == "identity_mismatch"


def test_pricing_evidence_cannot_approve_shipping() -> None:
    evidence = _ready_evidence(capability=ResearchCapability.CURRENT_PRICING)
    result = _service((evidence,)).decide(_request(capability=ResearchCapability.SHIPPING))
    assert result.accepted is False
    assert result.reason == "identity_mismatch"
