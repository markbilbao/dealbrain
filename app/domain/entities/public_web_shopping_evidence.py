"""Public-web shopping evidence classification — Sprint 32.

A search/retrieval provider is not a merchant. These types preserve:

- discovery provider identity
- source URL
- merchant/retailer identity
- page/product identity
- retrieval/fetch timestamp
- price / availability / freshness evidence
- contractual policy state
- provenance

They do not certify any provider, invent prices, or execute live research.
Search snippets (Level D) must not become scored offers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from app.domain.entities.offer_economics import CanonicalComponentStatus, CanonicalMoneyLine
from app.domain.entities.research_execution import CapabilityPolicyState, ResearchCapability

ShoppingEvidenceTier = Literal["level_a", "level_b", "level_c", "level_d"]
ShoppingResultRole = Literal["discovery_only", "offer_evidence"]
ShoppingSourceKind = Literal[
    "manufacturer",
    "direct_retailer",
    "marketplace",
    "authorized_reseller",
    "review_editorial",
    "other",
]
PublicWebShippingEvidence = Literal["known_amount", "explicitly_free", "unknown"]

LEVEL_A: ShoppingEvidenceTier = "level_a"
LEVEL_B: ShoppingEvidenceTier = "level_b"
LEVEL_C: ShoppingEvidenceTier = "level_c"
LEVEL_D: ShoppingEvidenceTier = "level_d"

SNIPPET_NOT_CANONICAL_PRICE = "snippet_not_canonical_price"
LEVEL_C_NOT_POLICY_PERMITTED = "level_c_not_policy_permitted"
INSUFFICIENT_OFFER_EVIDENCE = "insufficient_offer_evidence"
UNKNOWN_SHIPPING_NOT_FREE = "unknown_shipping_not_free"
UNKNOWN_FIELD_NOT_ZERO = "unknown_field_not_zero"
SEARCH_PROVIDER_IS_NOT_MERCHANT = "search_provider_is_not_merchant"
PUBLIC_WEB_DISCOVERY_CAPABILITIES = frozenset({ResearchCapability.PRODUCT_DISCOVERY})


@dataclass(frozen=True, slots=True)
class PublicWebProvenance:
    """Identity split between retrieval provider and shopping source."""

    discovery_provider_id: str
    source_url: str
    merchant_identity: str | None = None
    page_identity: str | None = None
    product_identity: str | None = None
    retrieved_at: datetime | None = None
    provider_result_age: str | None = None
    contractual_policy: CapabilityPolicyState = "unknown"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.discovery_provider_id.strip():
            raise ValueError("discovery_provider_id is required")
        if not self.source_url.strip():
            raise ValueError("source_url is required")
        if self.contractual_policy not in {"allowed", "restricted", "prohibited", "unknown"}:
            raise ValueError("contractual_policy is unknown and fails closed")
        if self.discovery_provider_id.strip() in {
            "brave",
            "tavily",
            "exa",
            "brave-search",
            "tavily-search",
            "exa-search",
        } and (self.merchant_identity or "").strip().lower() in {
            "brave",
            "tavily",
            "exa",
        }:
            raise ValueError(SEARCH_PROVIDER_IS_NOT_MERCHANT)

    def to_dict(self) -> dict[str, Any]:
        return {
            "discovery_provider_id": self.discovery_provider_id,
            "source_url": self.source_url,
            "merchant_identity": self.merchant_identity,
            "page_identity": self.page_identity,
            "product_identity": self.product_identity,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
            "provider_result_age": self.provider_result_age,
            "contractual_policy": self.contractual_policy,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PublicWebShoppingResult:
    """One public-web hit. Default role is discovery-only."""

    query_id: str
    provenance: PublicWebProvenance
    title: str = ""
    snippet: str = ""
    evidence_tier: ShoppingEvidenceTier = LEVEL_D
    source_kind: ShoppingSourceKind = "other"
    role: ShoppingResultRole = "discovery_only"
    ph_relevant: bool | None = None
    php_price_text: str | None = None
    price_tied_to_source: bool = False
    availability_text: str | None = None
    freshness_evidence: bool = False
    outbound_url_usable: bool = False
    page_attribution_preserved: bool = False
    duplicate: bool = False
    stale_or_ambiguous: bool = False
    snippet_only_price: bool = True
    search_result_not_product_page: bool = True
    level_c_policy_permitted: bool = False
    test_fixture: bool = False
    production_certified: bool = False

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id is required")
        if self.evidence_tier not in {LEVEL_A, LEVEL_B, LEVEL_C, LEVEL_D}:
            raise ValueError("evidence_tier is unknown and fails closed")
        if self.source_kind not in {
            "manufacturer",
            "direct_retailer",
            "marketplace",
            "authorized_reseller",
            "review_editorial",
            "other",
        }:
            raise ValueError("source_kind is unknown and fails closed")
        if self.role not in {"discovery_only", "offer_evidence"}:
            raise ValueError("role is unknown and fails closed")
        if self.production_certified:
            raise ValueError("public-web results cannot self-certify production use")
        if self.evidence_tier == LEVEL_D and self.role == "offer_evidence":
            raise ValueError(SNIPPET_NOT_CANONICAL_PRICE)
        if self.role == "offer_evidence" and not self.may_enter_evaluated_set:
            raise ValueError("insufficient evidence cannot become offer_evidence")

    @property
    def may_enter_evaluated_set(self) -> bool:
        return offer_promotion_reason(self) is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "provenance": self.provenance.to_dict(),
            "title": self.title,
            "snippet": self.snippet,
            "evidence_tier": self.evidence_tier,
            "source_kind": self.source_kind,
            "role": self.role,
            "ph_relevant": self.ph_relevant,
            "php_price_text": self.php_price_text,
            "price_tied_to_source": self.price_tied_to_source,
            "availability_text": self.availability_text,
            "freshness_evidence": self.freshness_evidence,
            "outbound_url_usable": self.outbound_url_usable,
            "page_attribution_preserved": self.page_attribution_preserved,
            "duplicate": self.duplicate,
            "stale_or_ambiguous": self.stale_or_ambiguous,
            "snippet_only_price": self.snippet_only_price,
            "search_result_not_product_page": self.search_result_not_product_page,
            "level_c_policy_permitted": self.level_c_policy_permitted,
            "may_enter_evaluated_set": self.may_enter_evaluated_set,
            "test_fixture": self.test_fixture,
            "production_certified": False,
        }


def offer_promotion_reason(result: PublicWebShoppingResult) -> str | None:
    """Return why a hit must stay discovery-only, or None if offer evidence is allowed.

    Preferred hierarchy:

    - Level A: current direct product/source page with attributable offer evidence
    - Level B: provider-fetched current page content with source/fetch provenance
    - Level C: search-index structured result only if freshness + source identity +
      specific offer are established AND Sprint 32 policy explicitly permits it
    - Level D: generic search snippet — never a scored offer
    """

    if result.evidence_tier == LEVEL_D or result.snippet_only_price:
        return SNIPPET_NOT_CANONICAL_PRICE
    if result.stale_or_ambiguous:
        return INSUFFICIENT_OFFER_EVIDENCE
    if not result.price_tied_to_source:
        return INSUFFICIENT_OFFER_EVIDENCE
    if not result.freshness_evidence:
        return INSUFFICIENT_OFFER_EVIDENCE
    if not result.provenance.source_url:
        return INSUFFICIENT_OFFER_EVIDENCE
    if not result.provenance.merchant_identity:
        return INSUFFICIENT_OFFER_EVIDENCE
    if result.provenance.contractual_policy != "allowed":
        return "policy_not_allowed"
    if result.evidence_tier == LEVEL_C and not result.level_c_policy_permitted:
        return LEVEL_C_NOT_POLICY_PERMITTED
    if result.evidence_tier not in {LEVEL_A, LEVEL_B, LEVEL_C}:
        return INSUFFICIENT_OFFER_EVIDENCE
    return None


def classify_search_hit_as_discovery(
    *,
    query_id: str,
    discovery_provider_id: str,
    source_url: str,
    title: str = "",
    snippet: str = "",
    merchant_identity: str | None = None,
    page_identity: str | None = None,
    product_identity: str | None = None,
    retrieved_at: datetime | None = None,
    provider_result_age: str | None = None,
    source_kind: ShoppingSourceKind = "other",
    ph_relevant: bool | None = None,
    php_price_text: str | None = None,
    availability_text: str | None = None,
    outbound_url_usable: bool = False,
    page_attribution_preserved: bool = False,
    duplicate: bool = False,
    stale_or_ambiguous: bool = False,
    search_result_not_product_page: bool = True,
    contractual_policy: CapabilityPolicyState = "unknown",
    test_fixture: bool = True,
) -> PublicWebShoppingResult:
    """Normalize a search hit as Level D discovery evidence.

    Snippet prices remain text only. They are not listing prices.
    """

    return PublicWebShoppingResult(
        query_id=query_id,
        provenance=PublicWebProvenance(
            discovery_provider_id=discovery_provider_id,
            source_url=source_url,
            merchant_identity=merchant_identity,
            page_identity=page_identity,
            product_identity=product_identity,
            retrieved_at=retrieved_at,
            provider_result_age=provider_result_age,
            contractual_policy=contractual_policy,
        ),
        title=title,
        snippet=snippet,
        evidence_tier=LEVEL_D,
        source_kind=source_kind,
        role="discovery_only",
        ph_relevant=ph_relevant,
        php_price_text=php_price_text,
        price_tied_to_source=False,
        availability_text=availability_text,
        freshness_evidence=False,
        outbound_url_usable=outbound_url_usable,
        page_attribution_preserved=page_attribution_preserved,
        duplicate=duplicate,
        stale_or_ambiguous=stale_or_ambiguous,
        snippet_only_price=bool(php_price_text),
        search_result_not_product_page=search_result_not_product_page,
        test_fixture=test_fixture,
    )


def shipping_status_from_discovery_text(text: str | None) -> PublicWebShippingEvidence:
    """Search-result shipping language is not canonical free-shipping evidence."""

    del text
    return "unknown"


def unknown_money_line(*, kind: str, currency: str = "PHP") -> CanonicalMoneyLine:
    """Unknown economics stay unknown. Not PHP 0. Not free. Not scored as zero."""

    return CanonicalMoneyLine(
        kind=kind,  # type: ignore[arg-type]
        amount_minor=None,
        currency=currency,
        status="unknown",
        applied=False,
        label=UNKNOWN_FIELD_NOT_ZERO,
    )


def refuse_snippet_price_line(result: PublicWebShoppingResult) -> CanonicalMoneyLine:
    """Level D / snippet prices cannot enter CanonicalOfferEconomics as verified listing."""

    reason = offer_promotion_reason(result) or SNIPPET_NOT_CANONICAL_PRICE
    return CanonicalMoneyLine(
        kind="listing",
        amount_minor=None,
        currency="PHP",
        status="unknown",
        applied=False,
        label=reason,
    )


def canonical_shipping_status(
    evidence: PublicWebShippingEvidence,
) -> CanonicalComponentStatus:
    if evidence == "explicitly_free":
        return "verified"
    if evidence == "known_amount":
        return "verified"
    return "unknown"


def marketplace_url_is_not_direct_integration(source_url: str) -> bool:
    """Indexed Shopee/Lazada URLs are discovery hits, not certified connectors."""

    host = source_url.casefold()
    return any(
        token in host
        for token in (
            "shopee.",
            "lazada.",
            "tiktok.com",
            "amazon.",
        )
    )
