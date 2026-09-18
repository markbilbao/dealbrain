# Sprint 32 — PH source-rights / licensed-data path audit

**Document type:** Non-secret engineering evidence classification (rights / data-license audit)
**Audit date:** 2026-09-18
**Starting `origin/main`:** `629ab4eb92c2a1bb743632b5c1d0d195e5aa6111` (merge of PR #146)
**Market:** PH
**Trusted production certification records:** **zero**
**Outcome:** **A** — Shopify Global Catalog UCP supplies affirmative official authorization for a **restricted query-time** commercial comparison path, subject to technical validation. This is **not** production certification.

This document does **not** certify any merchant, marketplace, affiliate network, manufacturer, Shopify/UCP catalog, Icecat dataset, Tavily, or other provider. Engineering interpretation is not counsel approval. Do not store privileged legal advice in Git.

Related:

- [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)
- [`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md)
- [`../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)

---

## 0. Reassessment note

An earlier draft of this same-day audit recorded **Outcome C** because it conflated five distinct Shopify surfaces:

1. Shopify Global Catalog / UCP agent APIs
2. Shop.app personal-agent skill
3. ordinary merchant/admin APIs
4. merchant public storefront pages
5. building a persistent product index

Those are not the same path. This reassessment evaluates **Shopify Global Catalog** as its own first-party provider path. Power Mac Center written permission is **not** a prerequisite for Global Catalog. Shop.app personal-use limits do **not** disqualify the commercial Global Catalog developer surface. API Terms prohibitions on indexing, scraping, and AI training remain in force and define the restricted operating mode; they are not read as a ban on the query-time comparison shopping that Shopify’s own Developer Documentation describes.

Unauthorized public-page reuse remains not accepted.

---

## 1. Audit question and filter

Find the strongest contractually defensible route by which PiqSavi may use **current Philippine shopping/product information** in a shopper-facing commercial comparison product.

Required eventually:

- current product identity
- attributable current price
- source URL / provenance
- freshness
- commercial shopper-facing use
- comparison / recommendation use where applicable
- transformation / normalization where applicable
- no scraping workaround
- Sprint 31 fail-closed policy
- canonical offer-economics compatibility

**Survivor rule used here:** a path enters SURVIVORS only if official/current first-party terms already give affirmative evidence for enough of those capabilities, including under a Sprint 31 reduced-capability mode. Account-gated programs, private agreements, and “the page exists” are not survivors. A restricted-but-documented operating mode can still be a survivor.

Three columns are kept separate throughout:

1. technically exposed?
2. policy authorized? (`allowed` / `restricted` / `prohibited` / `unknown`)
3. usable in a canonical evaluated offer?

UNKNOWN fails closed. Technical retrieval is not product-data permission. Affiliate permission is not product-data permission. Tavily is not the merchant. A survivor rights path is not a production certification.

---

## 2. Outcome

**OUTCOME A.**

Official Shopify Global Catalog Developer Documentation plus the Shopify API License and Terms of Use already provide sufficient affirmative permission for a **restricted query-time** commercial comparison path:

- query only in response to shopper intent
- no broad crawling
- no bulk catalog copying
- no persistent Shopify product index
- no training / fine-tuning / model improvement using Shopify-derived data
- minimum data requested
- source/seller attribution retained
- offer data is not reused as a cached catalog
- fresh re-query when current data is needed
- ordinary outbound merchant / checkout link
- promoted placement / affiliate **off** initially

This is **not** production certification. Actual PH merchant coverage is **unverified** until a later live current-data probe. Production catalogs remain empty. Sprint 32 remains **OPEN**.

---

## 3. SURVIVORS

### S-1 — Shopify Global Catalog UCP (restricted query-time comparison)

**Architecture (no Tavily on this path):**

```text
PiqSavi shopper query
        ↓
Shopify Global Catalog (`https://catalog.shopify.com/api/ucp/mcp`)
        ↓
query-time product / merchant offers
        ↓
restricted no-index / no-scrape / no-bulk-cache handling
        ↓
normalized canonical offer candidate
        ↓
later Sprint 38 execution
```

Tavily may remain useful for non-Shopify discovery. Do not place Tavily between PiqSavi and Shopify Global Catalog unless a later technical constraint requires it.

| Layer | State |
|-------|-------|
| Technically exposed | **Yes, documented.** Endpoint `https://catalog.shopify.com/api/ucp/mcp`. Tools: `search_catalog`, `lookup_catalog`, `get_product`. Results clustered by Universal Product ID; offers from multiple merchants; current catalog data; prices; seller identity / URL; checkout links; availability. `catalog.view` = `"offer"` is documented for comparison shopping. |
| Policy authorized | **allowed / restricted** for the query-time Application described in Developer Documentation. **prohibited** for persistent product indexes, scraping/mining, bulk catalog copy, caching search results or images, and using derived API/Merchant Data to create/train/fine-tune/improve AI systems without the required consent. Individual retailer public-web reuse permission is **not** required for this Shopify-operated catalog path. |
| Canonical evaluated offer | **No.** Rights survivor ≠ production certification. PH inventory/coverage is unverified. No agent profile is hosted yet. No live probe was run. No Sprint 31 certification record exists. |

**Why this is a survivor.** API Terms §2.2 grant a limited, revocable license to use the Shopify API **solely in the manner described in the Terms and in the Developer Documentation**. Developer Documentation is defined as `https://shopify.dev/docs` and subordinate pages. Current Global Catalog docs expressly tell agents to use this catalog for **comparison shopping**, **cross-merchant discovery**, and **recommendations not tied to a specific store**. Promoted-placement docs describe commercial agent integrations earning commission on attributed purchases from an existing Global Catalog integration. Organic catalog results remain available when promoted placement is off.

**What this is not.**

- Not the Shop.app personal-agent skill (personal use only; commercial aggregators unauthorized).
- Not ordinary merchant Admin / Storefront GraphQL APIs.
- Not scraping merchant public pages.
- Not a licence to own catalog content or to build a persistent commerce/product index.
- Not proof that useful PH offers actually return.

**Individual merchant permission.** Not required for Global Catalog itself. API Terms §6.1.1 require merchant install/private credentials before a Developer accesses a Merchant Store or Merchant Data **except as expressly authorized by Shopify**. Global Catalog Developer Documentation is that Shopify authorization for cross-merchant catalog queries without per-merchant app install. Power Mac Center written permission is therefore **not** a prerequisite for S-1. Storefront Catalog / PMC remains a separate optional path (OA-1).

---

## 4. OWNER-ACTION CANDIDATES

None of these is certified. They remain optional or parallel to S-1.

### OA-1 — Power Mac Center Storefront Catalog (optional; separate from S-1)

Single-merchant UCP Storefront Catalog at the merchant origin. PMC [agents.md](https://powermaccenter.com/agents.md) documents storefront UCP/MCP. PMC [Terms of service](https://powermaccenter.com/policies/terms-of-service) §5(b) grant no extra public-web reuse rights. This path may later need written PMC permission because it is **not** Global Catalog. Do not treat PMC consent as required for S-1.

### OA-2 — Lazada PH Affiliate Platform product feed

Official PH CPS terms mention a product feed / CSV. Promotional Guidelines 3.5 forbid copying, storing, editing, or publishing Lazada-provided data without prior authorization. EXT-01 already `applied` (2026-09-08). Still needs written display / compare / normalize / short-TTL rights confirmation.

### OA-3 — Optimise Media publisher product catalogue

Network XML/CSV catalogue after campaign approval. Commission approval alone is insufficient. Owner-controlled publisher application only.

### OA-4 — Involve Asia Datafeed / Publisher API

Limited licence; per-offer Engagement terms control. Owner-controlled registration only.

### OA-5 — Direct written permission from additional PH retailers

Beyond the Box, Abenson, SM Appliance, Digital Walker, VillMan, Octagon. Use §9. Do not send email from this workspace.

---

## 5. Capability-policy matrix — S-1 Shopify Global Catalog

States are only `allowed` / `restricted` / `prohibited` / `unknown`. Restricted capabilities may still be usable if the certified operating mode respects the restriction. This matrix is a rights classification. It is **not** a production certification.

| Capability | Technically exposed? | Policy | Canonical evaluated offer? |
|------------|----------------------|--------|----------------------------|
| product_discovery | `search_catalog` across Shopify merchants | allowed — query-time; minimum data; rate limits | no |
| product_identity | UPID, product/variant GIDs, handles | allowed — query-time | no |
| current_pricing | variant `price`, product `price_range` | allowed — restricted: do not cache search results; re-query for freshness | no |
| seller identity | `variants[].seller` name, id, domain, url | allowed — retain attribution | no |
| seller URL / outbound destination | product `url`, variant `checkout_url` | allowed — ordinary outbound merchant/checkout link; promoted placement off | no |
| availability | `availability.available` / `status` | allowed — query-time | no |
| ships-to-PH filtering | `filters.ships_to.country` is ISO 3166-1 alpha-2 | allowed to send `PH` as documented country code | no — actual PH inventory unverified |
| currency/localization | `context.address_country`, `currency`, `language` | allowed as documented localization | no — useful PH/PHP coverage unverified |
| comparison use | docs: comparison shopping; `catalog.view` = `"offer"` | allowed — restricted: query-time only, not a persistent index | no |
| recommendation use | docs: recommendations not tied to a specific store | allowed — restricted: query-time shopper intent | no |
| runtime AI inference | shopper-facing ranking/summarization at request time | allowed — restricted: runtime inference only | no |
| transformation/normalization | offer-view clustering by UPID | restricted — Application functionality only; no content ownership | no |
| short-lived query processing | intended catalog use | allowed | no |
| caching | search results and images | prohibited for search results and images (render images in real time) | no |
| persistent product indexing | n/a as a licensed activity | prohibited — API Terms §2.3.14 | no |
| AI model training/improvement | n/a as a licensed activity | prohibited without Shopify or relevant merchant consent — API Terms §2.3.24 | no |
| commercial use | buyer-facing agents; promoted-placement program exists | allowed — restricted organic path; promoted placement off initially | no |
| attribution | seller/product/checkout URLs | allowed — retain source/seller attribution | no |
| retention | request/response lifecycle only | restricted — process then discard; do not keep a Shopify catalog | no |

Fail-closed consequence until live PH validation and a Sprint 31 certification record exist: **no Shopify Global Catalog offer may enter the canonical evaluated set yet.**

---

## 6. Candidate production policy (Sprint 31 reduced-capability mode)

Sprint 31 allows reduced modes to be represented. Candidate S-1 operating mode, if later certified:

1. Query Global Catalog only in response to a shopper intent.
2. Do not crawl, mine, scrape, or bulk-copy the catalog.
3. Do not build or persist a Shopify product index.
4. Do not cache search results. Do not download catalog images to PiqSavi servers; render in real time if shown.
5. Do not use Shopify-derived data to create, train, fine-tune, or improve AI systems.
6. Runtime shopper-facing inference/recommendation on the current response is in-scope; model improvement is not.
7. Request the minimum fields needed for identity, price, availability, seller attribution, and outbound URL.
8. Keep source/seller attribution on any displayed offer.
9. Treat response offers as short-lived. Re-query when current data is required.
10. Use the ordinary merchant/checkout URL from the response. Promoted placement / affiliate parameters stay **off** until a later explicit owner action.
11. Host a UCP agent profile and send `meta.ucp-agent.profile` on every catalog call, as documented.
12. Do not enable production until the §10 live PH probe and remaining Sprint 32 certification gates pass.

Anonymous catalog tools are documented, but production PiqSavi should identify the agent (hosted profile; Signed or Token tier when available) rather than relying on anonymous rate limits.

---

## 7. Concise BLOCKED / disqualified classes

These classes were reviewed and are **not** current Sprint 32 offer paths. Detail is in Appendix A.

| Class | Why it cannot certify |
|-------|------------------------|
| Public product pages, robots.txt, search-engine indexing, Tavily Extract | Technical retrieval only. Not a content licence. Tavily Extract does not solve PMC rights or any other source-site rights. |
| Shop.app personal AI agent skill | Official Help Center: personal use only; commercial products, aggregators, bulk catalog copy, and AI-model training from Shop data are unauthorized. This restriction does **not** disqualify S-1. |
| Shopee Open Platform (seller/ISV) | Shopee Content may not be combined with non-Shopee Content or used to benefit competing services. Incompatible with PiqSavi comparison. |
| Shopee Affiliate Program T&Cs | Licence to display Affiliate Links only. |
| Consumer storefront ToS as a reuse licence | Sony PH personal/non-commercial viewing only. PMC, Beyond the Box, Abenson, Samsung PH online shop, and Acer storefront sales terms do not affirmatively license commercial comparison reuse of **public pages**. |
| Manufacturer consumer shops without a catalog licence | Not PH offer feeds for PiqSavi. |
| Icecat Open/Full content | Specs/identity only. No attributable current PH retailer prices. |
| Generic SERP snippets, scraper APIs, unofficial wrappers | Not a legitimate provenance path. |

---

## 8. What still prevents production certification

S-1 does not close Sprint 32 until all of the following exist:

1. Hosted UCP agent profile and documented catalog calls (no live probe in this audit).
2. Real current-data probe showing **useful PH offers** (identity, current price, seller identity/URL, availability) under PH localization / `ships_to` parameters.
3. Evidence-backed Sprint 31 capability-policy rows for the reduced mode in §6.
4. Connector reliability, freshness, provenance, and canonical offer-economics compatibility.
5. Staging certification, monitoring, public coverage disclosure, kill-switch evidence.
6. No production `ResearchProviderCertification` until those gates pass.

EXT-01 `applied` (2026-09-08 Shopee/Lazada emails) is not approval, credentials, a feed, or certification. EXT-06 remains `not_started`.

---

## 9. Written permission specification (non-S-1 retailers only)

High-value PH retailers without a public reuse licence remain valid owner-action candidates for **Storefront Catalog or direct feeds**. Any permission request should ask the retailer to **explicitly authorize PiqSavi** to:

- retrieve/access current public product pages **or** a supplied official feed/API/UCP catalog
- identify products
- read/use current prices
- display and compare current prices with other authorized sources
- normalize product/spec information
- show source attribution and an outbound link to the retailer’s product URL
- cache only for an agreed short TTL and refresh periodically
- use the product information in shopper-facing AI-assisted comparison
- not imply retailer endorsement
- not modify retailer checkout

**Do not send any email from this workspace.** Owner controls external communication.

This specification is **not** required to begin S-1 Global Catalog technical validation.

---

## 10. Next technical validation (plan only; do not run in this agent)

Owner-authorized later step. This audit performed no Shopify live call.

1. Create or reuse an agent profile with official Shopify tooling ([Agent profiles](https://shopify.dev/docs/agents/profiles), [Auth and rate limiting](https://shopify.dev/docs/agents/profiles/auth-and-rate-limiting)). Catalog tools are documented even at Anonymous tier; still send `meta.ucp-agent.profile`. Prefer Signed or Token identification for production-bound work.
2. Do not scrape retailers. Do not bulk-index. Do not enable promoted placement.
3. Issue a **small** set of real PH shopping queries against `https://catalog.shopify.com/api/ucp/mcp` (`search_catalog`, then `get_product` on a shortlist).
4. Pass documented localization where applicable: `filters.ships_to.country=PH`, `context.address_country=PH`, and currency/language if the probe needs them.
5. Record whether useful PH offers actually return.
6. For any returned offer, verify product identity, current price, seller identity, seller URL / checkout URL, and availability.
7. Preserve no-index / no-cache / no-training restrictions in the harness (do not persist a catalog; do not commit extracted live payloads).
8. Do **not** enable production from the probe. A useful PH result becomes technical coverage evidence only.

Actual PH coverage remains **unverified** until that probe runs.

---

## 11. Tavily role (unchanged for non-Shopify sources)

Tavily may remain a **discovery/retrieval provider** for non-Shopify sources. It is not the merchant and is not on the S-1 path.

A Tavily Extract result does **not** solve source-site rights. Public-web snippets remain Level D / discovery-only.

---

## 12. Official Shopify sources reviewed (reassessment)

| Source | Role |
|--------|------|
| [About Catalogs](https://shopify.dev/docs/agents/catalog) | Global vs Storefront; Global best for cross-merchant discovery / comparison shopping; agent profile, no API key; no-cache guidelines |
| [Global Catalog MCP](https://shopify.dev/docs/agents/catalog/global-catalog) | Comparison shopping / recommendations; prices; seller identity/URL; checkout links; availability; `ships_to`; `context.address_country` / currency; `view=offer` |
| [Agent profiles](https://shopify.dev/docs/agents/profiles) | Hosted UCP profile URL on every request |
| [Auth and rate limiting](https://shopify.dev/docs/agents/profiles/auth-and-rate-limiting) | Catalog tools at Token, Signed, and Anonymous tiers |
| [Earn with promoted placements](https://shopify.dev/docs/agents/catalog/promoted-placement) | Commercial Global Catalog integrations contemplated; organic path works with placement off |
| [Build commerce agents with UCP](https://shopify.dev/docs/agents) | Discover products across Shopify merchants |
| [Shopify API License and Terms of Use](https://www.shopify.com/legal/api-terms) (last updated 27 February 2026) | §2.2 limited API license in the manner of Developer Documentation; §2.3.8 no scrape/mine; §2.3.14 no automated collection / product index; §2.3.24 no AI training/improvement without consent; §4.3 no ownership of accessed content; §6.1.1 merchant consent except as expressly authorized by Shopify |
| [Using Shop with personal AI agents](https://help.shop.app/en/shop/shopping/personal-agents) | Personal skill only — not S-1 |

PH localization is **documented as query parameters** (`ships_to.country` ISO 3166-1 alpha-2, including the ability to send `PH`). Documentation does **not** establish that useful PH merchants or PHP prices actually exist in Global Catalog.

---

## 13. Non-claims

This audit does **not** mean:

- any path is legal under Philippine law (no qualified legal review is recorded here)
- PiqSavi may reuse public PH product pages
- robots.txt, search indexing, or Tavily extraction is permission
- Shopify Global Catalog, PMC, Shopee, Lazada, Optimise, Involve Asia, Samsung, Sony, Acer, Icecat, Brave, Tavily, or Exa is production-certified
- actual PH inventory/coverage has been observed
- affiliate commission approval is product-data permission
- PiqSavi owns content accessed through Shopify APIs
- runtime inference equals permission to train or improve models
- Sprint 32 is complete
- production catalogs are populated
- Sprint 38 has started

---

## Appendix A — rejected-research evidence table

| Candidate | Official sources reviewed | Technically exposed? | Policy | Why not a survivor |
|-----------|---------------------------|----------------------|--------|--------------------|
| PMC public pages alone | [Terms of service](https://powermaccenter.com/policies/terms-of-service) | storefront HTML/JSON exist | unknown / restricted — §5(b) grants no rights except as expressly provided | No affirmative commercial comparison licence for public pages |
| PMC Storefront Catalog without written confirmation | [agents.md](https://powermaccenter.com/agents.md) | storefront UCP/MCP documented | unknown for commercial PiqSavi use of that origin | Separate from S-1; optional OA-1 |
| Shop.app personal skill | [Using Shop with personal AI agents](https://help.shop.app/en/shop/shopping/personal-agents); [shop.app/SKILL.md](https://shop.app/SKILL.md) | catalog search exists | **prohibited** for commercial aggregators / bulk catalog copy | Wrong program; does not disqualify S-1 |
| Beyond the Box pages | [Terms of Use](https://beyondthebox.ph/pages/terms-of-use) | public catalog | prohibited / restricted — no scrape; no exploit without written permission | Written permission required |
| Abenson pages | [Terms of Use](https://home.abenson.com/terms-of-use) | public catalog | prohibited / restricted — agent/tool navigation forbidden; non-commercial content use | Written permission required |
| Sony PH site | [Terms of Use](https://www.sony.com.ph/microsite/termsofuse/) clause 7 | public catalog | **prohibited** for copying/distribution/adaptation except personal non-commercial use, unless prior written consent | Direct commercial reuse not defensible |
| Samsung PH online shop | [Online Shop T&Cs](https://www.samsung.com/ph/info/online-shop-tnc/); [Club Affiliate](https://www.samsung.com/ph/offer/samsung-club-affiliates/) | consumer shop + Optimise affiliate | unknown — consumer terms are not a product-data licence | Optimise track is OA-3, not a survivor |
| Acer PH store | [store.acer.com/en-ph/terms-conditions](https://store.acer.com/en-ph/terms-conditions) (official URL; full text retrieval timed out in this audit) | public store prices | unknown — sales terms do not establish PiqSavi reuse | Do not infer ALLOWED |
| Shopee Affiliate T&Cs | [help.shopee.ph article 77295](https://help.shopee.ph/portal/4/article/77295) | affiliate links / possible Open API | restricted to Affiliate Link display | No catalog-comparison grant |
| Shopee Open Platform | [open.shopee.com Terms of Service](https://open.shopee.com/developer-guide/36) §§6–7 | seller/ISV APIs after approval | **prohibited** for combining with non-Shopee content and for competing-service use | Incompatible with comparison floor |
| Lazada Open Platform seller APIs | [open.lazada.com](https://open.lazada.com/) | seller-owned catalog APIs | unknown — seller APIs are not a publisher comparison licence | Wrong audience |
| Lazada consumer platform terms | [lazada.com.ph/terms-conditions](https://www.lazada.com.ph/terms-conditions) | public listings | unknown / not a reuse licence | Consumer shopping terms |
| Icecat | [Open Content License](https://iceclog.com/open-content-license/); [Full Icecat Content License](https://iceclog.com/content-license-icecat/) | specs/identity | restricted — comparison-site use contemplated for Full Icecat client services; Open Icecat bans generative-AI use; images often excluded | No current PH offer prices |
| Involve Asia / Impact / Admitad / Awin generally | network publisher terms + catalog APIs where published | feeds exist after approval | unknown until PH advertiser + offer T&Cs reviewed | Account-gated; PH shopping coverage unverified without enrollment |
| Manufacturer partner portals (Samsung Knox, Apple reseller programs, etc.) | public partner marketing pages | enterprise/reseller, not shopper offer feeds | unknown | Not a first PH offer floor |

---

## 14. PH coverage harness follow-up (does not close this sprint)

A later same-day slice prepared the private-local Anonymous PH coverage harness described in [`SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md`](SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md). That harness is evidence tooling only. This audit still performed no Shopify live catalog call. **PH LIVE COVERAGE VALIDATION STILL REQUIRED.**

---

## 15. Owner live 12-query PH coverage probe addendum (2026-09-18; does not close this sprint)

This addendum does **not** rewrite earlier snapshots. After PR #149 the owner ran the controlled Anonymous 12-query PH coverage probe. Result: **PASSED TECHNICAL COVERAGE TEST**. This agent did **not** make that live call.

Recorded facts: 12/12 `USEFUL_PH_OFFER`; 120 first-page products; 122 offer records; Anonymous; no credentials; no scraping; no pagination; no bulk lookup; no raw persistence. Mixed returned currencies despite PHP context. The five `get_product` validations in that run were concentrated in one query and must be rerun by the owner after the selector diversification fix.

This is **not** production certification. This does **not** close Sprint 32. Shopify remains a restricted query-time rights survivor / technical candidate. Production catalogs remain empty. Sprint 38 remains unstarted.

---

## 16. Owner live diversified get_product validation addendum (2026-09-18; does not close this sprint)

This addendum does **not** rewrite earlier snapshots. After PR #150 merged, the owner reran the controlled Anonymous 12-query PH coverage probe. The required cross-category `get_product` rerun is **COMPLETE**. Result: **PH LIVE TECHNICAL COVERAGE VALIDATED**. This agent did **not** make that live call.

Recorded facts: 12/12 `USEFUL_PH_OFFER`; five `get_product` validations across five distinct categories (wireless earbuds, gaming laptop, mechanical keyboard, USB-C charger, phone case); 120 products; 130 offer records (additional offers are compatible with multi-variant products, not 130 distinct products). Anonymous; no credentials; no scraping; no pagination; no bulk lookup; no raw persistence.

This is **not** production certification. This does **not** close Sprint 32. Shopify remains a restricted query-time rights survivor / technical candidate. Production catalogs remain empty. Sprint 38 remains unstarted.

---

## 17. PiqSavi UCP agent-profile foundation addendum (2026-09-18; does not close this sprint)

This addendum does **not** rewrite earlier snapshots. PiqSavi now hosts its own least-privilege UCP agent-profile JSON in the existing FastAPI application. Status: **IMPLEMENTED LOCALLY — NOT YET DEPLOYED/VALIDATED**. Proposed canonical URL: `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`. Route: `GET /ucp/agent-profiles/2026-08-25/piqsavi.json`. UCP version `2026-08-25`. Declared capabilities: catalog.search, catalog.lookup, and `dev.shopify.catalog.global`. The Shopify-hosted fixture remains **TECHNICAL TEST ONLY** and remains the PH probe default.

This agent did **not** deploy. This agent did **not** call Shopify. Shopify has **not** fetched the PiqSavi profile. Production catalogs remain empty. Sprint 32 remains open. Sprint 38 remains unstarted.

---

SHOPIFY GLOBAL CATALOG REASSESSMENT COMPLETE —
OFFICIAL QUERY-TIME COMPARISON PATH IDENTIFIED —
PH LIVE TECHNICAL COVERAGE VALIDATED —
5/5 GET_PRODUCT VALIDATIONS DIVERSIFIED ACROSS FIVE CATEGORIES —
PIQSAVI UCP AGENT PROFILE IMPLEMENTED LOCALLY — NOT YET DEPLOYED/VALIDATED —
PRODUCTION CERTIFICATION STILL REQUIRED —
SPRINT 32 REMAINS OPEN
