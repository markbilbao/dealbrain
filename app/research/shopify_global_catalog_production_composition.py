"""Server-owned production composition for the reduced Shopify PH path.

Provider registration, evidence, and certification stay distinct. This module
asks ``ResearchProviderCertificationDecisionService`` to write certifications.
It does not self-certify the provider, create routing, or perform HTTP.
"""

from __future__ import annotations

from datetime import date

from app.domain.entities.research_certification_decision import (
    CertificationDecisionRequest,
    CertificationDecisionResult,
)
from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import ResearchProviderCertificationCatalog
from app.research.certification_evidence import (
    production_research_provider_certification_evidence_catalog,
)
from app.research.registry import production_research_provider_registry
from app.research.shopify_global_catalog_capability_policy import (
    SHOPIFY_GLOBAL_CATALOG_MARKET,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_CAPABILITIES,
    SHOPIFY_EVIDENCE_REVIEWER,
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
    SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
)
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)

SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE = date(2026, 9, 25)


class ShopifyReducedCapabilityCertificationError(RuntimeError):
    """Trusted decision did not certify the exact reduced capability set."""


def shopify_reduced_capability_decision_request(
    capability: ResearchCapability,
) -> CertificationDecisionRequest:
    """Explicit server-owned review for one allowed capability."""

    return CertificationDecisionRequest(
        provider_id="ph-shopify-global-catalog",
        capability=capability,
        market=SHOPIFY_GLOBAL_CATALOG_MARKET,
        source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
        source_scope="exact",
        requested_status="certified",
        requested_policy="allowed",
        certification_version=SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
        reviewer=SHOPIFY_EVIDENCE_REVIEWER,
        decided_at=SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE,
    )


def compose_shopify_reduced_capability_certifications(
    catalog: ResearchProviderCertificationCatalog | None = None,
) -> ResearchProviderCertificationCatalog:
    """Build the production certification catalog through the decision service.

    Fails closed unless all four exact allowed targets are approved. Does not
    certify shipping, tax/import, promotion, or any other capability.
    """

    if catalog is None:
        catalog = ResearchProviderCertificationCatalog(allow_test_certifications=False)
    results = decide_shopify_reduced_capability_certifications(catalog)
    if len(results) != len(SHOPIFY_EVIDENCE_CAPABILITIES):
        raise ShopifyReducedCapabilityCertificationError(
            "reduced Shopify certification did not review every allowed target"
        )
    if any(not result.accepted or result.certification is None for result in results):
        raise ShopifyReducedCapabilityCertificationError(
            "reduced Shopify certification decision was not approved"
        )
    if len(catalog.list_records()) != len(SHOPIFY_EVIDENCE_CAPABILITIES):
        raise ShopifyReducedCapabilityCertificationError(
            "reduced Shopify certification catalog count is not the allowed set"
        )
    return catalog


def decide_shopify_reduced_capability_certifications(
    catalog: ResearchProviderCertificationCatalog,
) -> tuple[CertificationDecisionResult, ...]:
    """Run the existing decision service. Does not write routing."""

    service = ResearchProviderCertificationDecisionService(
        production_research_provider_certification_evidence_catalog(),
        catalog,
        production_research_provider_registry(),
    )
    results: list[CertificationDecisionResult] = []
    for capability in SHOPIFY_EVIDENCE_CAPABILITIES:
        result = service.decide(shopify_reduced_capability_decision_request(capability))
        results.append(result)
        if not result.accepted:
            raise ShopifyReducedCapabilityCertificationError(
                f"{capability.value} refused: {result.reason}"
            )
    return tuple(results)
