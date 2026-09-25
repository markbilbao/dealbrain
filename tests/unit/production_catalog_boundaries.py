"""Production catalog boundaries after the Shopify Global Catalog evidence slice."""

from __future__ import annotations

from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import production_research_provider_certification_catalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.routing import production_research_provider_routing_policy_catalog
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_CAPABILITIES,
    shopify_global_catalog_certification_evidence_records,
)


def assert_production_shopify_evidence_only() -> None:
    """Shopify evidence grants nothing. Production catalogs match the reduced set."""

    from app.domain.entities.connector_reliability import ConnectorOperationalStatus

    records = production_research_provider_certification_evidence_catalog().list_records()
    assert records == shopify_global_catalog_certification_evidence_records()
    assert {record.capability for record in records} == set(SHOPIFY_EVIDENCE_CAPABILITIES)
    assert ResearchCapability.SHIPPING not in {record.capability for record in records}
    assert ResearchCapability.PROMOTION_EVIDENCE not in {record.capability for record in records}
    assert all(record.grants_certification is False for record in records)
    assert all(record.grants_eligibility is False for record in records)
    assert all(record.test_fixture is False for record in records)
    providers = production_research_provider_registry().list_providers()
    assert len(providers) == 1
    assert providers[0].provider_id == "ph-shopify-global-catalog"
    assert providers[0].descriptor.operational_status is ConnectorOperationalStatus.DISABLED
    certifications = production_research_provider_certification_catalog().list_records()
    assert len(certifications) == 4
    assert {record.capability for record in certifications} == set(SHOPIFY_EVIDENCE_CAPABILITIES)
    assert production_research_provider_routing_policy_catalog().list_records() == ()
