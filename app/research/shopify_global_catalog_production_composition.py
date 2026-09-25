"""Server-owned production composition for the reduced Shopify PH path.

Provider registration, evidence, and certification stay distinct. This module
asks ``ResearchProviderCertificationDecisionService`` to write certifications
only after the provider, evidence, and Shopify capability-policy map agree.
It does not self-certify the provider, create routing, or perform HTTP.
"""

from __future__ import annotations

from collections.abc import Sequence
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
    SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_MARKET,
    ShopifyCapabilityPolicyRow,
    shopify_global_catalog_capability_policy_rows,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_REVIEWER,
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
    SHOPIFY_REDUCED_CAPABILITY_CERTIFICATION_VERSION,
)
from app.services.research_certification_decision import (
    ResearchProviderCertificationDecisionService,
)

SHOPIFY_REDUCED_CAPABILITY_DECISION_DATE = date(2026, 9, 25)


class ShopifyReducedCapabilityCertificationError(RuntimeError):
    """Provider, evidence, and capability policy did not agree."""


def require_shopify_reduced_capability_agreement(
    *,
    provider_capabilities: Sequence[ResearchCapability],
    evidence_capabilities: Sequence[ResearchCapability],
    policy_rows: Sequence[ShopifyCapabilityPolicyRow],
) -> tuple[ResearchCapability, ...]:
    """Return the exact reduced set, or raise before any certification write.

    The three sets must be identical. Disagreement does not fall back to their
    intersection.
    """

    provider_set = _capability_set(provider_capabilities, "provider")
    evidence_set = _capability_set(evidence_capabilities, "evidence")
    if provider_set != evidence_set:
        unsupported = evidence_set - provider_set
        if unsupported:
            names = ", ".join(sorted(item.value for item in unsupported))
            raise ShopifyReducedCapabilityCertificationError(
                "evidence capability is not supported by the provider: " + names
            )
        extra = provider_set - evidence_set
        names = ", ".join(sorted(item.value for item in extra))
        raise ShopifyReducedCapabilityCertificationError(
            "provider capability set contains an extra capability: " + names
        )

    policy_by_capability = _unique_policy_rows(policy_rows)
    for capability in provider_capabilities:
        row = policy_by_capability.get(capability)
        if row is None:
            raise ShopifyReducedCapabilityCertificationError(
                f"missing Shopify capability-policy row for {capability.value}"
            )
        if row.policy != "allowed":
            raise ShopifyReducedCapabilityCertificationError(
                f"Shopify capability-policy for {capability.value} is {row.policy}"
            )

    allowed = frozenset(
        capability for capability, row in policy_by_capability.items() if row.policy == "allowed"
    )
    if allowed != provider_set:
        raise ShopifyReducedCapabilityCertificationError(
            "allowed capability-policy set disagrees with the provider and evidence sets"
        )
    return tuple(provider_capabilities)


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
    if any(not result.accepted or result.certification is None for result in results):
        raise ShopifyReducedCapabilityCertificationError(
            "reduced Shopify certification decision was not approved"
        )
    if len(catalog.list_records()) != len(results):
        raise ShopifyReducedCapabilityCertificationError(
            "reduced Shopify certification catalog count is not the allowed set"
        )
    return catalog


def decide_shopify_reduced_capability_certifications(
    catalog: ResearchProviderCertificationCatalog,
    *,
    provider_capabilities: Sequence[ResearchCapability] | None = None,
    evidence_capabilities: Sequence[ResearchCapability] | None = None,
    policy_rows: Sequence[ShopifyCapabilityPolicyRow] | None = None,
) -> tuple[CertificationDecisionResult, ...]:
    """Run the existing decision service after the three-way gate.

    Overrides exist so tests can prove drift fails closed. They do not change
    production constants. No certification is written when the gate refuses.
    """

    targets = require_shopify_reduced_capability_agreement(
        provider_capabilities=(
            _production_provider_capabilities()
            if provider_capabilities is None
            else provider_capabilities
        ),
        evidence_capabilities=(
            _production_evidence_capabilities()
            if evidence_capabilities is None
            else evidence_capabilities
        ),
        policy_rows=(
            shopify_global_catalog_capability_policy_rows() if policy_rows is None else policy_rows
        ),
    )
    service = ResearchProviderCertificationDecisionService(
        production_research_provider_certification_evidence_catalog(),
        catalog,
        production_research_provider_registry(),
    )
    results: list[CertificationDecisionResult] = []
    for capability in targets:
        result = service.decide(shopify_reduced_capability_decision_request(capability))
        results.append(result)
        if not result.accepted:
            raise ShopifyReducedCapabilityCertificationError(
                f"{capability.value} refused: {result.reason}"
            )
    return tuple(results)


def _production_provider_capabilities() -> tuple[ResearchCapability, ...]:
    provider = production_research_provider_registry().get(
        SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID
    )
    if provider is None:
        raise ShopifyReducedCapabilityCertificationError(
            "production Shopify provider is not registered"
        )
    return provider.descriptor.supported_capabilities


def _production_evidence_capabilities() -> tuple[ResearchCapability, ...]:
    records = production_research_provider_certification_evidence_catalog().list_records()
    matched = tuple(
        record.capability
        for record in records
        if record.provider_id == SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID
        and record.market == SHOPIFY_GLOBAL_CATALOG_MARKET
        and record.source == SHOPIFY_GLOBAL_CATALOG_SOURCE
        and record.completeness == "recorded"
        and record.test_fixture is False
    )
    if len(matched) != len(records):
        raise ShopifyReducedCapabilityCertificationError(
            "production evidence is not exactly the reduced Shopify identity"
        )
    return matched


def _capability_set(
    capabilities: Sequence[ResearchCapability],
    label: str,
) -> frozenset[ResearchCapability]:
    values = tuple(capabilities)
    if len(values) != len(set(values)):
        raise ShopifyReducedCapabilityCertificationError(
            f"{label} capability set contains a duplicate"
        )
    return frozenset(values)


def _unique_policy_rows(
    policy_rows: Sequence[ShopifyCapabilityPolicyRow],
) -> dict[ResearchCapability, ShopifyCapabilityPolicyRow]:
    grouped: dict[ResearchCapability, list[ShopifyCapabilityPolicyRow]] = {}
    for row in policy_rows:
        if row.research_capability is None:
            continue
        grouped.setdefault(row.research_capability, []).append(row)
    unique: dict[ResearchCapability, ShopifyCapabilityPolicyRow] = {}
    for capability, matches in grouped.items():
        if len(matches) != 1:
            raise ShopifyReducedCapabilityCertificationError(
                f"duplicate Shopify capability-policy rows for {capability.value}"
            )
        unique[capability] = matches[0]
    return unique
