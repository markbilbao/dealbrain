"""Sprint 32 Shopify Global Catalog PH certification evidence.

Real, non-test evidence for capabilities already supported by repository
evidence. ``completeness="recorded"`` means capture is complete. It does not
mean the use is legally sufficient, production certified, eligible, or routed.

These rows load into the production evidence catalog only. They do not enter
the production provider registry, certification catalog, or routing catalog.
"""

from __future__ import annotations

from datetime import date

from app.domain.entities.research_execution import (
    ResearchCapability,
    ResearchProviderCertificationEvidence,
)
from app.research.certification_evidence import make_research_provider_certification_evidence
from app.research.shopify_global_catalog_capability_policy import (
    SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
    SHOPIFY_GLOBAL_CATALOG_MARKET,
)

SHOPIFY_GLOBAL_CATALOG_SOURCE = "shopify_global_catalog"
SHOPIFY_EVIDENCE_DATE = date(2026, 9, 18)
SHOPIFY_EVIDENCE_REVIEW_DATE = date(2026, 9, 23)
SHOPIFY_EVIDENCE_REVIEWER = "Non-secret engineering evidence classification (not counsel approval)"
SHOPIFY_EVIDENCE_CAPABILITIES = (
    ResearchCapability.PRODUCT_DISCOVERY,
    ResearchCapability.OFFER_DISCOVERY,
    ResearchCapability.CURRENT_PRICING,
    ResearchCapability.AVAILABILITY,
)

_EVIDENCE_SOURCE = (
    "docs/roadmap/evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md"
    "; docs/roadmap/evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md"
    "; app/research/shopify_global_catalog_capability_policy.py"
)
_PROGRAM_REFERENCE = (
    "Shopify Global Catalog documented Anonymous catalog mode. "
    "About Catalogs https://shopify.dev/docs/agents/catalog ; "
    "Global Catalog MCP https://shopify.dev/docs/agents/catalog/global-catalog ; "
    "Auth and rate limiting https://shopify.dev/docs/agents/profiles/auth-and-rate-limiting ; "
    "Shopify API License and Terms of Use https://www.shopify.com/legal/api-terms "
    "(last updated 27 February 2026). "
    "This reference does not record a partnership, endorsement, special approval, "
    "preferred-developer status, or production-app approval."
)
_RESTRICTIONS = (
    "evidence only; not production certification",
    "query-time use",
    "re-query for freshness; do not cache Shopify Catalog search results or images",
    "no persistent product index",
    "no AI training or model improvement without required consent",
    "lookup_catalog remains restricted and is not a product index",
    "normalization within PiqSavi remains restricted",
    "short-lived retention",
    "shipping amount unknown and excluded",
    "promotion and voucher evidence unknown and excluded",
    "shopper applicability not established",
    "production profile undeployed",
    "production provider not registered",
)
_ATTRIBUTION = (
    "retain source and seller attribution",
    "do not imply Shopify partnership, endorsement, special approval, "
    "or preferred-developer status",
)
_CAPABILITY_NOTES = {
    ResearchCapability.PRODUCT_DISCOVERY: (
        "12/12 owner PH search probes returned USEFUL_PH_OFFER. "
        "Staging search_catalog negotiation returned HTTP 200, error null, "
        "isError false, and product_count 3. "
        "This row is evidence, not certification."
    ),
    ResearchCapability.OFFER_DISCOVERY: (
        "Documented comparison shopping uses catalog view offer. "
        "Owner probe offer records were technically useful under PH localization. "
        "This row is evidence, not certification."
    ),
    ResearchCapability.CURRENT_PRICING: (
        "Owner live probe summaries record usable current price evidence. "
        "Returned currencies stay as returned. "
        "This row is evidence, not certification, and is not a canonical shopper price."
    ),
    ResearchCapability.AVAILABILITY: (
        "Owner live summaries record usable availability evidence on the PH searches. "
        "This row is evidence, not certification."
    ),
}


def shopify_global_catalog_certification_evidence_records() -> tuple[
    ResearchProviderCertificationEvidence, ...
]:
    """PH Anonymous Global Catalog evidence. Not certification records."""

    records: list[ResearchProviderCertificationEvidence] = []
    for capability in SHOPIFY_EVIDENCE_CAPABILITIES:
        records.append(
            make_research_provider_certification_evidence(
                provider_id=SHOPIFY_GLOBAL_CATALOG_DOCUMENTARY_PROVIDER_ID,
                capability=capability,
                market=SHOPIFY_GLOBAL_CATALOG_MARKET,
                source=SHOPIFY_GLOBAL_CATALOG_SOURCE,
                evidence_source=_EVIDENCE_SOURCE,
                program_reference=_PROGRAM_REFERENCE,
                evidence_date=SHOPIFY_EVIDENCE_DATE,
                review_date=SHOPIFY_EVIDENCE_REVIEW_DATE,
                reviewer=SHOPIFY_EVIDENCE_REVIEWER,
                restrictions=_RESTRICTIONS,
                attribution_requirements=_ATTRIBUTION,
                completeness="recorded",
                notes=_CAPABILITY_NOTES[capability],
                test_fixture=False,
            )
        )
    return tuple(records)
