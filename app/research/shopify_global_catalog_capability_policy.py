"""Shopify Global Catalog PH capability-policy map — Sprint 32 certification prep.

Documentary evidence against the existing Sprint 31 model. It does not create
a second policy system, a ``ResearchProviderCertification``, or a production
provider, evidence, or routing record.

``policy`` is only ``CapabilityPolicyState``: ``allowed``, ``restricted``,
``prohibited``, ``unknown``. It records source/provider authorization.
Technical exposure and shopper applicability are separate facts. Technical
observation neither grants nor prohibits authorization. Operational
restrictions are notes on a row; they do not replace an ``allowed`` grant.
Unknown permission stays fail-closed.

PiqSavi probe and ranking rules live on ``PiqSaviInternalOperatingRule``.
They are not Shopify policy states.

``ResearchProviderCertification.is_production_eligible`` still requires
``status == certified`` and ``policy == allowed``. This map does not create
that record. An allowed documentary row does not certify Shopify and does not
make a later certification impossible.
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

_NOT_CERTIFIED = (
    "2026-09-18 rights audit Outcome A. Restrictions are operating limits on "
    "the stated Sprint 31 policy. This row is not a production certification."
)


@dataclass(frozen=True, slots=True)
class ShopifyCapabilityPolicyRow:
    """Provider authorization, technical exposure, and shopper applicability."""

    row_id: str
    label: str
    research_capability: ResearchCapability | None
    technical_exposure: TechnicalExposure
    policy: CapabilityPolicyState
    shopper_applicability: ShopperApplicability
    evidence_note: str
    restrictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.row_id.strip():
            raise ValueError("row_id is required")
        if self.policy not in POLICY_STATES:
            raise ValueError("policy must be an existing Sprint 31 state")
        if self.technical_exposure not in TECHNICAL_EXPOSURE_STATES:
            raise ValueError("technical exposure is not a policy state")
        if self.shopper_applicability not in SHOPPER_APPLICABILITY_STATES:
            raise ValueError("shopper applicability is not a policy state")
        if self.policy == "unknown" and self.shopper_applicability == "applicable":
            raise ValueError("unknown permission must not be shopper-applicable")
        object.__setattr__(self, "evidence_note", self.evidence_note.strip())
        object.__setattr__(self, "restrictions", tuple(item.strip() for item in self.restrictions))
        if any(not item for item in self.restrictions):
            raise ValueError("restrictions must be non-empty strings")

    @property
    def production_eligible(self) -> bool:
        """Prep rows are not certifications, even when policy is allowed."""

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
            "restrictions": "; ".join(self.restrictions),
            "evidence_note": self.evidence_note,
            "production_eligible": "false",
        }


@dataclass(frozen=True, slots=True)
class PiqSaviInternalOperatingRule:
    """PiqSavi behavior. Not a Shopify contractual policy state."""

    rule_id: str
    mode: str
    summary: str

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or not self.mode.strip():
            raise ValueError("internal operating rule requires an id and mode")
        object.__setattr__(self, "summary", self.summary.strip())


def _row(
    row_id: str,
    label: str,
    technical_exposure: TechnicalExposure,
    policy: CapabilityPolicyState,
    shopper_applicability: ShopperApplicability,
    evidence_note: str,
    restrictions: tuple[str, ...] = (),
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
        restrictions=restrictions,
    )


def shopify_global_catalog_capability_policy_rows() -> tuple[ShopifyCapabilityPolicyRow, ...]:
    """Certification-prep map. Not a production certification catalog."""

    return (
        _row(
            "product_discovery",
            "PRODUCT_DISCOVERY",
            "observed",
            "allowed",
            "not_applicable",
            "12/12 PH searches were USEFUL_PH_OFFER. Staging search_catalog "
            "returned HTTP 200 and product_count 3. " + _NOT_CERTIFIED,
            ("query-time", "minimum data", "rate limits"),
            ResearchCapability.PRODUCT_DISCOVERY,
        ),
        _row(
            "current_pricing",
            "CURRENT_PRICING",
            "observed",
            "allowed",
            "not_applicable",
            "Live probe summaries record usable current price evidence. " + _NOT_CERTIFIED,
            ("do not cache search results", "re-query for freshness"),
            ResearchCapability.CURRENT_PRICING,
        ),
        _row(
            "current_price",
            "current price",
            "observed",
            "allowed",
            "not_applicable",
            "Same price evidence as CURRENT_PRICING. Not yet a canonical "
            "shopper price. " + _NOT_CERTIFIED,
            ("do not cache search results", "re-query for freshness"),
        ),
        _row(
            "product_identity",
            "product identity",
            "observed",
            "allowed",
            "not_applicable",
            "Useful PH offers required an identifiable product id. " + _NOT_CERTIFIED,
            ("query-time",),
        ),
        _row(
            "variant_identity",
            "variant identity",
            "observed",
            "allowed",
            "not_applicable",
            "Diversified get_product exposed variant identity. " + _NOT_CERTIFIED,
            ("query-time",),
        ),
        _row(
            "seller_identity",
            "seller identity",
            "observed",
            "allowed",
            "not_applicable",
            "Useful PH offers required seller identity. " + _NOT_CERTIFIED,
            ("retain attribution",),
        ),
        _row(
            "seller_url",
            "seller URL",
            "observed",
            "allowed",
            "not_applicable",
            "Useful offers included a seller URL or domain. " + _NOT_CERTIFIED,
            ("ordinary outbound merchant link",),
        ),
        _row(
            "product_url",
            "product URL",
            "observed",
            "allowed",
            "not_applicable",
            "Destination evidence includes product URL when the response "
            "exposes it. " + _NOT_CERTIFIED,
            ("ordinary outbound merchant link",),
        ),
        _row(
            "checkout_url",
            "checkout URL",
            "observed",
            "allowed",
            "not_applicable",
            "Destination evidence includes checkout URL when exposed. " + _NOT_CERTIFIED,
            ("ordinary outbound checkout link",),
        ),
        _row(
            "availability",
            "availability",
            "observed",
            "allowed",
            "not_applicable",
            "Owner live summaries say availability evidence remained usable. " + _NOT_CERTIFIED,
            ("query-time",),
            ResearchCapability.AVAILABILITY,
        ),
        _row(
            "ships_to_ph",
            "destination / ships_to PH",
            "observed",
            "allowed",
            "unknown",
            "The probe sent ships_to.country=PH with the useful searches. "
            "That authorizes the documented filter. It does not prove each "
            "offer ships to a specific shopper.",
            ("documented ISO country filter", "not a shipping-price grant"),
        ),
        _row(
            "currency",
            "currency",
            "observed",
            "allowed",
            "not_applicable",
            "Currencies were returned. PHP context does not rewrite mixed returned currencies.",
            ("documented localization", "preserve returned currency"),
        ),
        _row(
            "query_time_comparison",
            "query-time comparison",
            "observed",
            "allowed",
            "not_applicable",
            "Docs describe comparison shopping with view=offer. Probe "
            "usable_for_comparison is technical exposure, not a canonical "
            "evaluated offer. " + _NOT_CERTIFIED,
            ("query-time only", "not a persistent index"),
            ResearchCapability.OFFER_DISCOVERY,
        ),
        _row(
            "get_product",
            "get_product",
            "observed",
            "allowed",
            "not_applicable",
            "Anonymous diversified validation was 5/5 across five categories. "
            "The later staging negotiation retry did not call get_product. " + _NOT_CERTIFIED,
            ("bounded product read", "not a product index"),
        ),
        _row(
            "lookup_catalog",
            "lookup_catalog",
            "documented_not_observed",
            "restricted",
            "not_applicable",
            "Shopify documents lookup_catalog as a Global Catalog tool. API "
            "Terms still forbid using catalog access to build a product index "
            "or bulk-copy the catalog. This restricted state is not a finding "
            "that Shopify prohibits the tool. The Sprint 32 probe disables it "
            "separately and does not call it.",
            ("documented catalog tool", "not a product index or bulk catalog copy"),
        ),
        _row(
            "normalization_within_piqsavi",
            "normalization within PiqSavi",
            "unknown",
            "restricted",
            "not_applicable",
            "API Terms limit transformation to application functionality and "
            "do not transfer content ownership. Production normalization "
            "evidence is still absent.",
            ("application functionality only", "no content ownership"),
        ),
        _row(
            "short_lived_retention",
            "short-lived retention",
            "observed",
            "restricted",
            "not_applicable",
            "Rights audit: process then discard; do not keep a Shopify catalog. "
            "PiqSavi's probe also stores no raw payload. That stricter probe "
            "rule is internal and is not this policy state.",
            ("request lifecycle", "do not keep a Shopify catalog"),
        ),
        _row(
            "freshness_timestamp",
            "timestamp / freshness",
            "unknown",
            "allowed",
            "unknown",
            "Current responses were fresh at request time. A retained "
            "shopper-facing freshness record is not established. Re-query "
            "instead of caching search results.",
            ("re-query for freshness", "do not cache search results"),
        ),
        _row(
            "caching_search_results",
            "caching Shopify Catalog search results or images",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "Shopify Catalog terms prohibit caching search results and images. "
            "Render images in real time. This prohibition is evidence-backed.",
        ),
        _row(
            "persistent_product_index",
            "persistent commerce/product index",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "API Terms §2.3.14 prohibit a persistent product index. The harness "
            "is not a Shopify product index.",
        ),
        _row(
            "ai_training",
            "AI training or model improvement",
            "not_exposed",
            "prohibited",
            "not_applicable",
            "API Terms §2.3.24 prohibit training or model improvement from "
            "Shopify-derived data unless the required consent exists. That "
            "consent is not recorded, so this use stays prohibited.",
            ("unless required Shopify or merchant consent exists",),
        ),
        _row(
            "promoted_placement",
            "promoted placement",
            "documented_not_observed",
            "unknown",
            "not_applicable",
            "Official docs describe an invite-led Developer Preview that "
            "requires separate enrollment. Shopify does not prohibit the "
            "program. PiqSavi has not enrolled and keeps it disabled. Unknown "
            "permission fails closed.",
        ),
        _row(
            "seller_discount",
            "seller discount",
            "unknown",
            "unknown",
            "unknown",
            "No evidence that seller-discount fields were exposed or permitted.",
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
            research_capability=ResearchCapability.PROMOTION_EVIDENCE,
        ),
        _row(
            "voucher_eligibility",
            "voucher eligibility",
            "unknown",
            "unknown",
            "unknown",
            "Voucher availability would not prove shopper applicability. "
            "Neither fact is established.",
        ),
        _row(
            "destination_shipping_amount",
            "destination-dependent shipping amount",
            "unknown",
            "unknown",
            "unknown",
            "ships_to PH is a request filter, not a shipping-price grant.",
            research_capability=ResearchCapability.SHIPPING,
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
    )


def piqsavi_internal_operating_rules() -> tuple[PiqSaviInternalOperatingRule, ...]:
    """Probe and integrity rules. Separate from Shopify policy rows."""

    return (
        PiqSaviInternalOperatingRule(
            rule_id="probe_lookup_catalog_disabled",
            mode="disabled",
            summary=(
                "Sprint 32 probe budget sets lookup_catalog=0 and refuses the "
                "tool. This does not mean Shopify prohibits lookup_catalog."
            ),
        ),
        PiqSaviInternalOperatingRule(
            rule_id="promoted_placement_disabled",
            mode="disabled",
            summary=(
                "PiqSavi has not enrolled in promoted placement and does not "
                "enable it. Provider policy for that program stays unknown."
            ),
        ),
        PiqSaviInternalOperatingRule(
            rule_id="probe_raw_payload_not_stored",
            mode="no_raw_payload",
            summary=(
                "The Sprint 32 probe stores no raw Shopify product payload. "
                "That is stricter than, and separate from, Shopify's prohibition "
                "on caching catalog search results."
            ),
        ),
        PiqSaviInternalOperatingRule(
            rule_id="commission_based_organic_ranking",
            mode="integrity",
            summary=(
                "PiqSavi requires affiliate neutrality. Commission or affiliate "
                "status must not influence organic candidate selection, scores, "
                "recommendation, or ordering. This is an internal integrity rule, "
                "not a Shopify contractual prohibition."
            ),
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
    """Documentary allowed rows do not certify or route Shopify."""

    if not CERTIFICATION_PREP_ONLY or PRODUCTION_CERTIFIED:
        return True
    return any(
        row.production_eligible or row.shopper_applicability == "applicable"
        for row in shopify_global_catalog_capability_policy_rows()
    )
