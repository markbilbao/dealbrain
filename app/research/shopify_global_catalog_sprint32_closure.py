"""Sprint 32 closure record for the reduced Shopify Global Catalog PH path.

This module records staging-certification closure, the effective-cost
acceptance table, and the engineering kill-switch check. It does not enable
the provider, create routing, deploy a profile, call Shopify, or start
Sprint 38 or Sprint 41.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from app.domain.entities.connector_reliability import (
    ConnectorOperationalStatus,
    KillSwitch,
)
from app.domain.entities.research_execution import ResearchCapability, ResearchProviderDescriptor
from app.market.coverage import PH_PREPARING_COVERAGE_DISCLOSURE
from app.research.providers import StaticResearchProvider
from app.research.shopify_global_catalog_capability_policy import (
    shopify_capability_policy_index,
)
from app.research.shopify_global_catalog_certification_evidence import (
    SHOPIFY_GLOBAL_CATALOG_SOURCE,
)
from app.research.shopify_global_catalog_provider import shopify_global_catalog_ph_provider

SPRINT_32_STATUS = "COMPLETE / CLOSED"
SPRINT_32_CLOSURE_DATE = date(2026, 9, 25)
SPRINT_38_STATUS = "IN PROGRESS"
SPRINT_38_LIVE_EXECUTION_STATUS = "NOT OPERATIONAL"
SPRINT_41_STATUS = "UNSTARTED"
STAGING_CERTIFICATION = "PASSED"
STAGING_CERTIFICATION_SCOPE = "REDUCED CAPABILITY SET ONLY"
NOT_PRODUCTION_DEPLOYMENT_READY = "NOT PRODUCTION DEPLOYMENT READY"
SELECTED_PATH = "Shopify Global Catalog Anonymous reduced capability path"
PUBLIC_PH_COVERAGE_DISCLOSURE = PH_PREPARING_COVERAGE_DISCLOSURE
DEPLOYED_KILL_SWITCH_DRILL = "DEFERRED TO SPRINT 38/41"
ENGINEERING_KILL_SWITCH_VALIDATION = "PASSED"
PROVIDER_ID = "ph-shopify-global-catalog"

CERTIFIED_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.AVAILABILITY,
)
UNCERTIFIED_CAPABILITIES = (
    ResearchCapability.SHIPPING,
    ResearchCapability.TAXES_IMPORT,
    ResearchCapability.PROMOTION_EVIDENCE,
    ResearchCapability.REVIEW_COMMUNITY_EVIDENCE,
)

# Monitoring must not use these words for the disabled production provider.
FORBIDDEN_MONITORING_LABELS = ("healthy", "live", "available", "production-ready")
MONITORING_STATUS = "disabled"


@dataclass(frozen=True, slots=True)
class EffectiveCostAcceptance:
    """One Sprint 32 effective-cost component. Unknown is not zero."""

    component: str
    policy_row_id: str
    technical: str
    policy: str
    shopper_applicability: str
    included_in_effective_cost: bool


def shopify_reduced_path_effective_cost_table() -> tuple[EffectiveCostAcceptance, ...]:
    """Required effective-cost evidence for the reduced Shopify path.

    Current listing price maps the existing ``current_price`` policy row.
    ``observed`` is the technical-exposure word for exposed listing price.
    Shopper applicability stays the Sprint 31 enum ``not_applicable``: the
    amount is usable only as the observed current listing price, not as a
    shopper-specific adjustment. Unknown components stay excluded.
    """

    index = shopify_capability_policy_index()
    listing = index["current_price"]
    if listing.technical_exposure != "observed" or listing.policy != "allowed":
        raise ValueError("current listing price evidence drifted")
    if listing.shopper_applicability != "not_applicable":
        raise ValueError("listing price must not become a shopper-specific adjustment")
    rows = (
        EffectiveCostAcceptance(
            component="current_listing_price",
            policy_row_id="current_price",
            technical="exposed",
            policy="allowed",
            shopper_applicability="usable only as observed current listing price",
            included_in_effective_cost=True,
        ),
        EffectiveCostAcceptance(
            component="seller_discount",
            policy_row_id="seller_discount",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="platform_discount",
            policy_row_id="platform_discount",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="voucher_promotion",
            policy_row_id="voucher_promotion",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="voucher_eligibility",
            policy_row_id="voucher_eligibility",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="destination_shipping",
            policy_row_id="destination_shipping_amount",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="free_shipping",
            policy_row_id="free_shipping",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="checkout_other_costs",
            policy_row_id="checkout_other_costs",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
        EffectiveCostAcceptance(
            component="tax_import",
            policy_row_id="uncertified_taxes_import",
            technical="unknown",
            policy="unknown",
            shopper_applicability="unknown",
            included_in_effective_cost=False,
        ),
    )
    for row in rows:
        if row.component in {"current_listing_price", "tax_import"}:
            if row.component == "tax_import" and row.included_in_effective_cost:
                raise ValueError("tax/import must stay excluded from effective cost")
            continue
        policy_row = index[row.policy_row_id]
        if policy_row.technical_exposure != "unknown" or policy_row.policy != "unknown":
            raise ValueError(f"{row.component} must stay unknown")
        if policy_row.shopper_applicability != "unknown":
            raise ValueError(f"{row.component} must not be treated as applicable")
        if row.included_in_effective_cost:
            raise ValueError(f"{row.component} must stay excluded from effective cost")
    freshness = index["freshness_timestamp"]
    if freshness.shopper_applicability != "unknown":
        raise ValueError("retained shopper-facing freshness is not established")
    return rows


def real_provider_descriptor_for_kill_switch_check(
    *,
    operational_status: ConnectorOperationalStatus,
    kill_switch: KillSwitch,
) -> ResearchProviderDescriptor:
    """In-memory copy of the real non-fixture provider descriptor.

    The production factory is not mutated. This copy is not registered and
    does not perform HTTP.
    """

    source = shopify_global_catalog_ph_provider().descriptor
    if source.provider_id != PROVIDER_ID or source.test_fixture:
        raise ValueError("kill-switch check requires the real non-fixture descriptor")
    if source.supported_sources != (SHOPIFY_GLOBAL_CATALOG_SOURCE,):
        raise ValueError("kill-switch check must keep the real source identity")
    return replace(
        source,
        operational_status=operational_status,
        kill_switch=kill_switch,
    )


def real_provider_is_operationally_available(
    descriptor: ResearchProviderDescriptor,
    *,
    browser_disengage_kill_switch: bool = False,
    request_disengage_kill_switch: bool = False,
    shopper_disengage_kill_switch: bool = False,
) -> bool:
    """Server-owned predicate. Caller input cannot disengage a kill switch."""

    del browser_disengage_kill_switch, request_disengage_kill_switch, shopper_disengage_kill_switch
    return descriptor.is_operationally_available


def real_provider_eligibility_reasons(
    descriptor: ResearchProviderDescriptor,
) -> tuple[str, ...]:
    """Technical eligibility reasons. Does not route or execute."""

    eligibility = StaticResearchProvider(descriptor).supports(
        ResearchCapability.CURRENT_PRICING,
        "PH",
        SHOPIFY_GLOBAL_CATALOG_SOURCE,
    )
    return () if eligibility.eligible else eligibility.reasons
