"""Shopify Global Catalog PH capability-policy map — Sprint 32 certification prep.

This is documentary evidence against the existing Sprint 31 model. It does
not create a second policy system, a ``ResearchProviderCertification``, or a
production provider/routing record.

Policy uses only ``CapabilityPolicyState``: ``allowed``, ``restricted``,
``prohibited``, ``unknown``. Technical exposure and shopper/offer
applicability are separate facts. Technical availability does not grant
permission. Unknown permission is not marked allowed.

The reduced query-time comparison path from the 2026-09-18 rights audit is
``restricted``, not unrestricted ``allowed``. ``restricted`` does not make a
provider production-eligible. Production catalogs stay empty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.domain.entities.research_execution import CapabilityPolicyState, ResearchCapability

TechnicalExposure = Literal["observed", "documented_not_observed", "not_exposed", "unknown"]
ShopperApplicability = Literal["applicable", "not_applicable", "unknown"]
POLICY_STATES: frozenset[str] = frozenset({"allowed", "restricted", "prohibited", "unknown"})
TECHNICAL_EXPOSURE_STATES: frozenset[str] = frozenset(
    {"observed", "documented_not_observed", "not_exposed", "unknown"}
)
SHOPPER_APPLICABILITY_STATES: frozenset[str] = frozenset(
    {"applicable", "not_applicable", "unknown"}
)

# Documentary identity only. Not registered in the production provider registry.
SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID = "ph-shopify-global-catalog"
SHOPIFY_GLOBAL_CATALOG_MARKET = "PH"
CERTIFICATION_PREP_ONLY = True
PRODUCTION_CERTIFIED = False


@dataclass(frozen=True, slots=True)
class ShopifyCapabilityPolicyRow:
    """One field or use, with the three Sprint 31 evidence layers kept apart."""

    row_id: str
    label: str
    research_capability: ResearchCapability | None
    technical_exposure: TechnicalExposure
    policy: CapabilityPolicyState
    shopper_applicability: ShopperApplicability
    evidence_note: str

    def __post_init__(self) -> None:
        if not self.row_id.strip():
            raise ValueError("row_id is required")
        if self.policy not in POLICY_STATES:
            raise ValueError("policy must be an existing Sprint 31 state")
        if self.technical_exposure not in TECHNICAL_EXPOSURE_STATES:
            raise ValueError("technical exposure is not a policy state")
        if self.shopper_applicability not in SHOPPER_APPLICABILITY_STATES:
            raise ValueError("shopper applicability is not a policy state")
        if self.technical_exposure == "observed" and self.policy == "allowed":
            raise ValueError("technical availability must not be recorded as allowed")
        if self.policy == "unknown" and self.shopper_applicability == "applicable":
            raise ValueError("unknown permission must not be shopper-applicable")
        object.__setattr__(self, "evidence_note", self.evidence_note.strip())

    @property
    def production_eligible(self) -> bool:
        return False

    def to_dict(self) -> dict[str, str | None]:
        capability = self.research_capability.value if self.research_capability else None
        return {
            "row_id": self.row_id,
            "label": self.label,
            "research_capability": capability,
            "technical_exposure": self.technical_exposure,
            "policy": self.policy,
            "shopper_applicability": self.shopper_applicability,
            "evidence_note": self.evidence_note,
            "production_eligible": "false",
        }


def _row(
    row_id: str,
    label: str,
    technical_exposure: TechnicalExposure,
    policy: CapabilityPolicyState,
    shopper_applicability: ShopperApplicability,
    evidence_note: str,
    research_capability: ResearchCapability | None = None,
) -> ShopifyCapabilityPolicyRow:
    return ShopifyCapabilityPolicyRow(
        row_id=row_id,
        label=label,
        research_capability=research_capability,
        technical_exposure=technical_exposure,
        policy=policy,
        shopper_applicability=shopper_applicability,
        evidence_note=evidence_note,
    )


def shopify_global_catalog_capability_policy_rows() -> tuple[ShopifyCapabilityPolicyRow, ...]:
    """Certification-prep map. Not a production certification catalog."""

    restricted_query = (
        "2026-09-18 rights audit Outcome A: query-time comparison is a reduced "
        "mode under Shopify Global Catalog docs and API Terms. Sprint 31 state "
        "is restricted. This row does not certify production."
    )
    return (
        _row(
            "product_discovery",
            "PRODUCT_DISCOVERY",
            "observed",
            "restricted",
            "not_applicable",
            "12/12 PH search queries were USEFUL_PH_OFFER. Staging search_catalog "
            "retry returned HTTP 200 and product_count 3. " + restricted_query,
            ResearchCapability.PRODUCT_DISCOVERY,
        ),
        _row(
            "current_pricing",
            "CURRENT_PRICING",
            "observed",
            "restricted",
            "not_applicable",
            "Live probe summaries record usable current price evidence. Do not "
            "cache search results. Re-query for freshness. " + restricted_query,
            ResearchCapability.CURRENT_PRICING,
        ),
        _row(
            "current_price",
            "current price",
            "observed",
            "restricted",
            "not_applicable",
            "Same price evidence as CURRENT_PRICING. Returned amount is not a "
            "canonical shopper price. " + restricted_query,
        ),
        _row(
            "product_identity",
            "product identity",
            "observed",
            "restricted",
            "not_applicable",
            "Useful PH offers required an identifiable product id. Identity is "
            "query-time only and is not a persistent index. " + restricted_query,
        ),
        _row(
            "variant_identity",
            "variant identity",
            "observed",
            "restricted",
            "not_applicable",
            "Diversified get_product and multi-variant offer counts exposed "
            "variant identity. Not a stored catalog. " + restricted_query,
        ),
        _row(
            "seller_identity",
            "seller identity",
            "observed",
            "restricted",
            "not_applicable",
            "Useful PH offers required seller identity. Attribution stays with "
            "the response. " + restricted_query,
        ),
        _row(
            "seller_url",
            "seller URL",
            "observed",
            "restricted",
            "not_applicable",
            "Coverage required a seller URL or domain for a useful offer. "
            "Ordinary outbound link only. Promoted placement stays off.",
        ),
        _row(
            "product_url",
            "product URL",
            "observed",
            "restricted",
            "not_applicable",
            "Destination evidence in the live probe includes product URL when "
            "the response exposed it. Not a canonical checkout.",
        ),
        _row(
            "checkout_url",
            "checkout URL",
            "observed",
            "restricted",
            "not_applicable",
            "Destination evidence includes checkout URL when exposed. Affiliate "
            "parameters stay off.",
        ),
        _row(
            "availability",
            "availability",
            "observed",
            "restricted",
            "not_applicable",
            "Owner live summaries say availability evidence remained usable. "
            "That is not a canonical availability claim. " + restricted_query,
            ResearchCapability.AVAILABILITY,
        ),
        _row(
            "ships_to_ph",
            "destination / ships_to PH",
            "observed",
            "restricted",
            "unknown",
            "The probe sent ships_to.country=PH with the useful-offer searches. "
            "That shows the documented filter was used. It does not prove each "
            "offer ships to a specific shopper. This is not a shipping-price "
            "capability.",
        ),
        _row(
            "currency",
            "currency",
            "observed",
            "restricted",
            "not_applicable",
            "Currencies were returned. PHP context does not rewrite mixed "
            "returned currencies. Preserve the returned currency.",
        ),
        _row(
            "query_time_comparison",
            "query-time comparison",
            "observed",
            "restricted",
            "not_applicable",
            "Probe classification usable_for_comparison is technical. Docs "
            "describe comparison shopping with view=offer. Not a canonical "
            "evaluated offer. " + restricted_query,
            ResearchCapability.OFFER_DISCOVERY,
        ),
        _row(
            "normalization_within_piqsavi",
            "normalization within PiqSavi",
            "unknown",
            "restricted",
            "not_applicable",
            "API Terms limit transformation to application functionality and "
            "do not transfer content ownership. Production normalization and "
            "matching evidence are still absent. Probe minimization is not that "
            "evidence.",
        ),
        _row(
            "short_lived_retention",
            "short-lived retention",
            "observed",
            "restricted",
            "not_applicable",
            "Harness and owner retries process then discard. Raw Shopify "
            "product payloads are not stored. Retention is request-scoped.",
        ),
        _row(
            "caching_search_results",
            "caching search results or images",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "API Terms prohibit caching search results and images. This probe does not cache them.",
        ),
        _row(
            "persistent_product_index",
            "persistent product index",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "API Terms §2.3.14 prohibit a product index. The harness is not a "
            "Shopify product index.",
        ),
        _row(
            "ai_training",
            "AI training or model improvement",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "API Terms §2.3.24 prohibit training or model improvement from "
            "Shopify-derived data without the required consent.",
        ),
        _row(
            "promoted_placement",
            "promoted placement",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "Promoted placement stays disabled. Program existence is not "
            "permission. Organic results are not affiliate-ranked.",
        ),
        _row(
            "affiliate_neutrality",
            "affiliate neutrality",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "Affiliate parameters are off. Affiliate status must not include, "
            "exclude, or rank a source. Affiliate approval is not product-data "
            "permission.",
        ),
        _row(
            "get_product",
            "get_product use",
            "observed",
            "restricted",
            "not_applicable",
            "Anonymous diversified validation was 5/5 across five categories. "
            "The later staging negotiation retry did not call get_product. "
            "Bounded get_product is not bulk lookup.",
        ),
        _row(
            "lookup_catalog",
            "lookup_catalog in this Sprint 32 probe",
            "documented_not_observed",
            "prohibited",
            "not_applicable",
            "Shopify documents lookup_catalog. This Sprint 32 probe forbids it: "
            "call budget 0. Declaring catalog.lookup for get_product is not "
            "permission to run lookup_catalog.",
        ),
        _row(
            "raw_response_persistence",
            "raw response persistence",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "Owner evidence and the harness prohibit storing the raw Shopify product payload.",
        ),
        _row(
            "seller_discount",
            "seller discount",
            "unknown",
            "unknown",
            "unknown",
            "No evidence that seller-discount fields were exposed or permitted "
            "for shopper effective cost.",
        ),
        _row(
            "platform_discount",
            "platform discount",
            "unknown",
            "unknown",
            "unknown",
            "No evidence that platform-discount fields were exposed or permitted.",
        ),
        _row(
            "voucher_promotion",
            "voucher or promotion information",
            "unknown",
            "unknown",
            "unknown",
            "Promotion evidence is not established for this path.",
            ResearchCapability.PROMOTION_EVIDENCE,
        ),
        _row(
            "voucher_eligibility",
            "voucher eligibility",
            "unknown",
            "unknown",
            "unknown",
            "Voucher availability would not by itself prove shopper applicability. "
            "Neither fact is established.",
        ),
        _row(
            "destination_shipping_amount",
            "destination-dependent shipping amount",
            "unknown",
            "unknown",
            "unknown",
            "ships_to PH is a request filter, not a shipping-price grant. "
            "Shipping amount policy remains unknown.",
            ResearchCapability.SHIPPING,
        ),
        _row(
            "free_shipping",
            "free-shipping status",
            "unknown",
            "unknown",
            "unknown",
            "Free-shipping status was not established. Unknown shipping is not free.",
        ),
        _row(
            "checkout_other_costs",
            "unavoidable checkout or other costs",
            "unknown",
            "unknown",
            "unknown",
            "Checkout-cost exposure and permission are both unknown.",
        ),
        _row(
            "freshness_timestamp",
            "timestamp / freshness",
            "unknown",
            "restricted",
            "unknown",
            "Live responses were current at request time, and raw payloads were "
            "not retained. A shopper-facing freshness record is not established. "
            "Cached prices stay prohibited.",
        ),
    )


def shopify_capability_policy_index() -> dict[str, ShopifyCapabilityPolicyRow]:
    rows = shopify_global_catalog_capability_policy_rows()
    index = {row.row_id: row for row in rows}
    if len(index) != len(rows):
        raise ValueError("duplicate Shopify capability-policy row_id")
    return index


def shopify_policies_by_state() -> dict[CapabilityPolicyState, tuple[str, ...]]:
    grouped: dict[CapabilityPolicyState, list[str]] = {
        "allowed": [],
        "restricted": [],
        "prohibited": [],
        "unknown": [],
    }
    for row in shopify_global_catalog_capability_policy_rows():
        grouped[row.policy].append(row.row_id)
    return {state: tuple(row_ids) for state, row_ids in grouped.items()}


def shopify_capability_policy_grants_production() -> bool:
    """Prep map never authorizes production certification or routing."""

    if not CERTIFICATION_PREP_ONLY or PRODUCTION_CERTIFIED:
        return True
    return any(
        row.policy == "allowed"
        or row.production_eligible
        or row.shopper_applicability == "applicable"
        for row in shopify_global_catalog_capability_policy_rows()
    )
