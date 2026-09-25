"""Three-way Shopify certification gate. No Shopify calls."""

from __future__ import annotations

from dataclasses import replace

import pytest
from app.domain.entities.research_execution import ResearchCapability
from app.research.certification import ResearchProviderCertificationCatalog
from app.research.shopify_global_catalog_capability_policy import (
    shopify_global_catalog_capability_policy_rows,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_EVIDENCE_CAPABILITIES,
)
from app.research.shopify_global_catalog_production_composition import (
    ShopifyReducedCapabilityCertificationError,
    decide_shopify_reduced_capability_certifications,
    require_shopify_reduced_capability_agreement,
)
from app.research.shopify_global_catalog_provider import (
    SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES,
)

_FOUR = SHOPIFY_GLOBAL_CATALOG_SUPPORTED_CAPABILITIES


def test_production_sets_agree_before_certification() -> None:
    catalog = ResearchProviderCertificationCatalog(allow_test_certifications=False)
    results = decide_shopify_reduced_capability_certifications(catalog)
    assert tuple(result.capability for result in results) == _FOUR
    assert SHOPIFY_EVIDENCE_CAPABILITIES == _FOUR
    assert len(catalog.list_records()) == 4
    agreed = require_shopify_reduced_capability_agreement(
        provider_capabilities=_FOUR,
        evidence_capabilities=SHOPIFY_EVIDENCE_CAPABILITIES,
        policy_rows=shopify_global_catalog_capability_policy_rows(),
    )
    assert agreed == _FOUR


@pytest.mark.parametrize(
    ("evidence_extra", "message"),
    [
        (ResearchCapability.SHIPPING, "not supported by the provider"),
        (ResearchCapability.WARRANTY_EVIDENCE, "not supported by the provider"),
    ],
)
def test_evidence_capability_missing_from_provider_fails_closed(
    evidence_extra: ResearchCapability,
    message: str,
) -> None:
    _assert_refused(
        evidence_capabilities=_FOUR + (evidence_extra,),
        message=message,
    )


def test_extra_provider_capability_fails_closed() -> None:
    _assert_refused(
        provider_capabilities=_FOUR + (ResearchCapability.REVIEW_COMMUNITY_EVIDENCE,),
        message="provider capability set contains an extra capability",
    )


def test_extra_evidence_capability_fails_closed() -> None:
    _assert_refused(
        evidence_capabilities=_FOUR + (ResearchCapability.PRODUCT_SPECIFICATION,),
        message="evidence capability is not supported by the provider",
    )


def test_missing_policy_row_fails_closed() -> None:
    rows = tuple(
        row
        for row in shopify_global_catalog_capability_policy_rows()
        if row.research_capability is not ResearchCapability.PRODUCT_DISCOVERY
    )
    _assert_refused(policy_rows=rows, message="missing Shopify capability-policy row")


def test_duplicate_policy_rows_fail_closed() -> None:
    rows = shopify_global_catalog_capability_policy_rows()
    original = next(
        row for row in rows if row.research_capability is ResearchCapability.CURRENT_PRICING
    )
    _assert_refused(
        policy_rows=rows + (replace(original, row_id="current_pricing_duplicate"),),
        message="duplicate Shopify capability-policy rows for current_pricing",
    )


@pytest.mark.parametrize("policy", ["restricted", "prohibited", "unknown"])
def test_non_allowed_policy_fails_closed(policy: str) -> None:
    rows = _with_policy(ResearchCapability.AVAILABILITY, policy)
    _assert_refused(
        policy_rows=rows,
        message=f"Shopify capability-policy for availability is {policy}",
    )


def test_shipping_evidence_cannot_certify_shipping() -> None:
    _assert_blocked_capability(
        ResearchCapability.SHIPPING,
        "Shopify capability-policy for shipping is unknown",
    )


def test_promotion_evidence_cannot_certify_promotion() -> None:
    _assert_blocked_capability(
        ResearchCapability.PROMOTION_EVIDENCE,
        "Shopify capability-policy for promotion_evidence is unknown",
    )


def test_taxes_import_evidence_cannot_certify_taxes() -> None:
    _assert_blocked_capability(
        ResearchCapability.TAXES_IMPORT,
        "missing Shopify capability-policy row for taxes_import",
    )


def _assert_blocked_capability(capability: ResearchCapability, message: str) -> None:
    """Provider and evidence both name the capability. Policy still refuses it."""

    _assert_refused(
        provider_capabilities=_FOUR + (capability,),
        evidence_capabilities=_FOUR + (capability,),
        message=message,
    )


def _assert_refused(
    *,
    message: str,
    provider_capabilities: tuple[ResearchCapability, ...] = _FOUR,
    evidence_capabilities: tuple[ResearchCapability, ...] = _FOUR,
    policy_rows=None,
) -> None:
    catalog = ResearchProviderCertificationCatalog(allow_test_certifications=False)
    with pytest.raises(ShopifyReducedCapabilityCertificationError, match=message):
        decide_shopify_reduced_capability_certifications(
            catalog,
            provider_capabilities=provider_capabilities,
            evidence_capabilities=evidence_capabilities,
            policy_rows=policy_rows
            if policy_rows is not None
            else shopify_global_catalog_capability_policy_rows(),
        )
    assert catalog.list_records() == ()


def _with_policy(capability: ResearchCapability, policy: str):
    rows = []
    for row in shopify_global_catalog_capability_policy_rows():
        if row.research_capability is capability:
            rows.append(replace(row, policy=policy))
        else:
            rows.append(row)
    return tuple(rows)
