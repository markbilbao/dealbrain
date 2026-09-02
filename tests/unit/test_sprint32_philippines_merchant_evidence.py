"""Sprint 32.3 PH merchant evidence snapshots: documentary only, not certification."""

from __future__ import annotations

from datetime import date

from app.domain.entities.research_certification_decision import CertificationDecisionRequest
from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.philippines_certification_evidence import (
    philippines_merchant_certification_evidence_catalog,
    philippines_merchant_certification_evidence_records,
    philippines_merchant_provider_ids,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)

_AS_OF = date(2026, 9, 2)
_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
)
_MERCHANTS = (
    ("ph-shopee", "shopee"),
    ("ph-lazada", "lazada"),
    ("ph-tiktok-shop", "tiktok_shop"),
    ("ph-amazon", "amazon"),
    ("ph-temu", "temu"),
)


def _decision_service():
    return ResearchProviderCertificationDecisionService(
        philippines_merchant_certification_evidence_catalog(),
        production_research_provider_certification_catalog(),
    )


def _request(provider_id: str, source: str, capability: ResearchCapability, market: str = "PH"):
    return CertificationDecisionRequest(
        provider_id=provider_id,
        capability=capability,
        market=market,
        source=source,
        requested_status="certified",
        requested_policy="allowed",
        certification_version="ph-v1",
        reviewer="Sprint 32.3 reviewer",
        decided_at=_AS_OF,
    )


def test_philippines_merchant_snapshots_load_without_entering_production() -> None:
    records = philippines_merchant_certification_evidence_records()
    catalog = philippines_merchant_certification_evidence_catalog()
    assert len(records) == 15
    assert catalog.list_records() == records
    assert set(philippines_merchant_provider_ids()) == {item[0] for item in _MERCHANTS}
    assert all(record.test_fixture is False for record in records)
    assert all(record.market == "PH" for record in records)
    assert all(record.completeness == "incomplete" for record in records)
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_certification_catalog().list_records() == ()


def test_unknown_api_rights_do_not_become_permitted() -> None:
    for record in philippines_merchant_certification_evidence_records():
        assert "API/data permission unknown" in record.restrictions
        assert "unknown" in record.notes.lower()
        assert "allowed" not in record.notes.lower()
        assert record.grants_certification is False
        assert record.grants_eligibility is False
        assert record.is_decision_ready(as_of=_AS_OF) is False


def test_counsel_clearance_does_not_make_product_data_decision_ready() -> None:
    catalog = philippines_merchant_certification_evidence_catalog()
    for provider_id, source in _MERCHANTS:
        record = catalog.lookup(
            provider_id=provider_id,
            capability=ResearchCapability.CURRENT_PRICING,
            market="PH",
            source=source,
        )
        assert record is not None
        assert "Counsel-cleared to apply" in record.notes
        assert record.completeness == "incomplete"
        assert record.review_date is None
        assert record.is_decision_ready(as_of=_AS_OF) is False


def test_shopee_public_documentation_is_not_a_rights_grant() -> None:
    shopee = [
        record
        for record in philippines_merchant_certification_evidence_records()
        if record.source == "shopee"
    ]
    assert shopee
    joined = " ".join(record.notes + record.program_reference for record in shopee)
    assert "Public merchant documentation is not a PiqSavi access grant" in joined
    assert "productOfferV2" not in joined
    assert "AppID" not in joined
    assert "8000" not in joined
    assert "Affiliate Program is separate from Shopee Seller/ISV Open Platform" in joined


def test_cross_program_distinctions_are_preserved() -> None:
    catalog = philippines_merchant_certification_evidence_catalog()
    shopee = catalog.lookup(
        provider_id="ph-shopee",
        capability=ResearchCapability.OFFER_DISCOVERY,
        market="PH",
        source="shopee",
    )
    amazon = catalog.lookup(
        provider_id="ph-amazon",
        capability=ResearchCapability.PRODUCT_DISCOVERY,
        market="PH",
        source="amazon",
    )
    tiktok = catalog.lookup(
        provider_id="ph-tiktok-shop",
        capability=ResearchCapability.OFFER_DISCOVERY,
        market="PH",
        source="tiktok_shop",
    )
    assert shopee is not None
    assert amazon is not None
    assert tiktok is not None
    assert "Affiliate Program is separate from Shopee Seller/ISV Open Platform" in (
        shopee.program_reference
    )
    assert "Associates is separate from Creators API and from PA-API / SP-API" in (
        amazon.program_reference
    )
    assert "Creator affiliate, Partner Center, and developer API are separate" in (
        tiktok.program_reference
    )
    assert "US/GB/SG, not PH" in tiktok.notes


def test_non_ph_placeholders_cannot_satisfy_philippines() -> None:
    service = _decision_service()
    amazon_us = service.decide(
        _request("ph-amazon", "amazon", ResearchCapability.CURRENT_PRICING, market="US")
    )
    tiktok_us = service.decide(
        _request("ph-tiktok-shop", "tiktok_shop", ResearchCapability.OFFER_DISCOVERY, market="US")
    )
    assert amazon_us.accepted is False
    assert amazon_us.reason == "identity_mismatch"
    assert tiktok_us.accepted is False
    assert tiktok_us.reason == "identity_mismatch"
    catalog = philippines_merchant_certification_evidence_catalog()
    assert (
        catalog.lookup(
            provider_id="ph-amazon",
            capability=ResearchCapability.CURRENT_PRICING,
            market="US",
            source="amazon",
        )
        is None
    )


def test_current_ph_merchants_cannot_be_certified_allowed() -> None:
    service = _decision_service()
    for provider_id, source in _MERCHANTS:
        for capability in _CAPABILITIES:
            result = service.decide(_request(provider_id, source, capability))
            assert result.accepted is False
            assert result.reason == "evidence_incomplete"
            assert result.certification is None


def test_sprint_32_3_production_catalogs_remain_empty() -> None:
    philippines_merchant_certification_evidence_records()
    philippines_merchant_certification_evidence_catalog()
    assert production_research_provider_certification_catalog().list_records() == ()
    assert production_research_provider_certification_evidence_catalog().list_records() == ()
    assert production_research_provider_registry().list_providers() == ()
    assert production_research_provider_routing_policy_catalog().list_records() == ()
