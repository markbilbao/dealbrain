# Sprint 32 — Public-web discovery path

**Status:** Internal architecture note. Not a production certification. Sprint 32 remains **not complete**.  
**Date:** 2026-09-18  
**Related:** [`SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](SPRINT_31_RESEARCH_EXECUTION_ROUTER.md), [`ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](ADR_SPRINT_31_CONNECTOR_UNIFICATION.md), [`../roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)

## Decision

**B — a narrow Sprint 32 adapter/certification extension is required.**

A is insufficient because `ProviderType` had no non-merchant retrieval label, certification/evidence types did not separate discovery provider vs merchant vs source URL vs page identity, and snippet-vs-offer evidence tiers were not enforceable in types.

C is unnecessary because the Sprint 31 three-authority model already fits:

```
PublicWebResearchProvider
        ↓
ResearchProviderRegistry          (technical implementations)
        ↓
ResearchProviderCertificationEvidence
        ↓
ResearchProviderCertificationDecisionService
        ↓
ResearchProviderCertificationCatalog
        ↓
plan_authorized_research()        (the roadmap “MarketRouter”)
        ↓
PH certification gate
        ↓
Sprint 38 execute_research_plan() (not implemented here)
        ↓
MarketplaceOffer / CanonicalOfferEconomics
        ↓
existing canonical PiqScore / Recommendation
```

Do **not** create a second registry, router, scoring system, or authorization system.

## Identity split

A search provider is not a merchant.

| Field | Meaning |
|-------|---------|
| `discovery_provider_id` | Brave / Tavily / Exa implementation identity |
| `source_url` | Retailer or marketplace product/page URL |
| `merchant_identity` | Host/retailer, never the search vendor |
| `page_identity` / `product_identity` | Page and product when known |
| `retrieved_at` | Fetch timestamp when a live call actually happened |
| `contractual_policy` | Sprint 31 `allowed` / `restricted` / `prohibited` / `unknown` |

Indexed Shopee or Lazada URLs are discovery hits. They do **not** mean “PiqSavi searches Shopee” or “PiqSavi searches Lazada”.

## Evidence tiers

| Level | Meaning | May enter evaluated shopping set? |
|-------|---------|-----------------------------------|
| A | Current direct product/source page with attributable offer evidence | Yes, if policy `allowed` and freshness/source identity hold |
| B | Provider-fetched current page content with source/fetch provenance | Yes, same gates |
| C | Search-index structured result only | Only if freshness + source identity + specific offer are established **and** Sprint 32 policy explicitly permits it. Default: no. |
| D | Generic search snippet | **No.** Discovery only. |

Unknown shipping ≠ PHP 0 ≠ free. Unknown fields are not scored as zero. Do not invent price, stock, or shipping.

## Sprint 38 boundary

Sprint 32 may describe and certify a data path. It must not implement live retries, partial-result product behavior, execution-trace population, or the production live-mode gate. `PublicWebResearchProvider.execute()` remains unimplemented.

## Production state

Production registry, certification catalog, evidence catalog, and routing catalog remain empty. Documentary public-web evidence is incomplete and is not loaded by production factories.
