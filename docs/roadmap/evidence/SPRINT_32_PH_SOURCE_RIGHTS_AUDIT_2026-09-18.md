# Sprint 32 — PH source-rights / licensed-data path audit

**Document type:** Non-secret engineering evidence classification (rights / data-license audit)
**Audit date:** 2026-09-18
**Starting `origin/main`:** `629ab4eb92c2a1bb743632b5c1d0d195e5aa6111` (merge of PR #146)
**Market:** PH
**Trusted production certification records:** **zero**
**Outcome:** **C** — no current public or partner path reaches the Sprint 32 survivor bar

This document does **not** certify any merchant, marketplace, affiliate network, manufacturer, Shopify/UCP catalog, Icecat dataset, Tavily, or other provider. Engineering interpretation is not counsel approval. Do not store privileged legal advice in Git.

Related:

- [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)
- [`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md)
- [`../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)

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

**Survivor rule used here:** a path enters SURVIVORS only if official/current first-party terms already give affirmative evidence for enough of those capabilities. Account-gated programs, private agreements, and “the page exists” are not survivors.

Three columns are kept separate throughout:

1. technically exposed?
2. policy authorized? (`allowed` / `restricted` / `prohibited` / `unknown`)
3. usable in a canonical evaluated offer?

UNKNOWN fails closed. Technical retrieval is not product-data permission. Affiliate permission is not product-data permission. Tavily is not the merchant.

---

## 2. Outcome

**OUTCOME C.**

No reviewed official public/partner instrument currently grants PiqSavi enough affirmative product-data rights to certify a PH shopping-offer path. Unauthorized public-page reuse is not accepted.

There **are** owner-action programs that expose structured current product data and that could become legitimate after approval or written permission. The strongest of those is identified below. Production catalogs remain empty. Sprint 32 remains **OPEN**.

---

## 3. SURVIVORS

**None.**

No official API, feed, or public program terms reviewed on 2026-09-18 explicitly authorize commercial publisher use of current PH product/catalog data for shopper-facing display **and** comparison at the Sprint 32 bar.

---

## 4. OWNER-ACTION CANDIDATES

Ranked by combination of (a) current PH shopping usefulness, (b) official structured data path, and (c) a realistic permission/approval route. None of these is certified.

### OA-1 — Shopify commercial UCP catalog + Power Mac Center storefront (strongest)

**Why this is the strongest path.** Power Mac Center is a genuine PH Apple/electronics retailer with current storefront prices. The merchant publishes an official agent-facing document describing UCP/MCP catalog search and product identity endpoints. Shopify’s commercial developer documentation describes Global Catalog / Storefront Catalog as query-time product discovery for AI agents, including comparison shopping as an intended Global Catalog use. Marketplace coverage is not required for the first technical floor.

This is **not** the Shop.app personal-agent skill. Shop Help Center states that the Shop skill is for personal, individual use only and prohibits building commercial products/services/platforms, bulk catalog download, and aggregators. Businesses are directed to Shop/Shopify developer documentation instead.

| Layer | State |
|-------|-------|
| Technically exposed | **Yes, documented.** PMC: [agents.md](https://powermaccenter.com/agents.md), `GET /.well-known/ucp`, `POST /api/ucp/mcp`, product JSON/search paths. Shopify: [Build commerce agents with UCP](https://shopify.dev/docs/agents), [About Catalogs](https://shopify.dev/docs/agents/catalog), [Storefront Catalog MCP](https://shopify.dev/docs/agents/catalog/storefront-catalog), [Global Catalog MCP](https://shopify.dev/docs/agents/catalog/global-catalog). |
| Policy authorized | **unknown / restricted.** PMC [Terms of service](https://powermaccenter.com/policies/terms-of-service) §5(b): the terms grant no rights in the Web Store or contents except as expressly provided. `agents.md` describes how personal shopping assistants may interact; it does not expressly license a commercial comparison product. Shopify [API License and Terms of Use](https://www.shopify.com/legal/api-terms) grant a limited API license for Applications that interoperate with Shopify Services; they prohibit building a commerce/product index, systematic automated collection, and using derived API/Merchant Data to train or improve AI systems without written Shopify (or, for Merchant Data, merchant) consent. Catalog usage guidelines prohibit caching search results and images. Content accessed through the APIs is not licensed to the developer as owned data. |
| Canonical evaluated offer | **No.** Query-time catalog fields are not permission. Persistence/index/cache/AI summarization remain fail-closed. PH coverage of Global Catalog is unverified (no live catalog calls were made). Agent profile / Dev Dashboard / trust-tier access is not established. |

**Smallest owner action.** Do not sign up from this agent. Owner should, out of band:

1. Ask Power Mac Center in writing for the permission set in §8 (storefront UCP/catalog use for PiqSavi comparison, not checkout modification, no endorsement).
2. In parallel, use Shopify Partner / Dev Dashboard commercial UCP docs to host an agent profile and obtain written confirmation that a query-time shopper-facing comparison agent for PH Shopify merchants is an intended Application, not a prohibited product index.
3. Counsel-review the no-cache / no-index / no-AI-training clauses against PiqSavi canonical-offer persistence and runtime summarization.

Tavily may remain a discovery provider pointing at authorized PMC URLs only after source-side permission is actually defensible. Tavily Extract does not solve PMC rights.

### OA-2 — Lazada PH Affiliate Platform product feed (already requested)

Official PH CPS terms operate the Affiliate Platform at [adsense.lazada.com.ph](https://adsense.lazada.com.ph) and expressly mention provision of a **product feed** / CSV files as a Lazada service. Marketing Materials include “any product information shown in equivalent forms.” Affiliates may place those materials on registered, approved Affiliate Media.

That is **not** yet a display/comparison/cache/AI license.

| Official source | What it actually says |
|-----------------|------------------------|
| [PH-Affiliate Program (CPS) T&Cs](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_other/suit_bu1_other201808302007_72534.html) | 3.2: place Marketing Materials on registered/approved media. 4.1: no use or modification of Marketing Materials other than as expressly allowed, without prior written agreement. 4.5: no crawling; no copying graphics/texts/other content from Lazada web presence; brand/logo use needs prior written approval. 5.2: Lazada operates services “such as the provision of product feed” / CSV files, quality at Lazada’s discretion. |
| [Lazada Online Promotional Guidelines](https://terms.alicdn.com/legal-agreement/terms/product/20230331141234394/20230331141234394.html) (effective 1 June 2023) | 3.5: data provided by Lazada “shall be used in the manner previously confirmed by Lazada” and shall **not** be copied, stored, edited, published, rented, sold, or otherwise disclosed or used without prior authorization. |

EXT-01 already records a 2026-09-08 product-data / feed request to `affiliate@lazada.com.ph`. That request is **applied**, not approved.

**Smallest owner action.** Owner-controlled follow-up asking Lazada to confirm, in writing, that an approved publisher may (i) ingest the official product feed, (ii) display current title/price/availability/URL, (iii) compare those offers with non-Lazada sources, (iv) normalize fields, (v) cache only under an agreed short TTL, and (vi) use the data as shopper-facing recommendation evidence. Until that confirmation exists, policy for comparison/caching/transformation/AI remains **unknown** (fail-closed). Historical Optimise campaign observation of “Product Feed: 0 items” is not a rights grant and is not recertified here.

### OA-3 — Optimise Media publisher product catalogue (Lazada PH / Samsung Club PH)

Optimise documents a network product catalogue distributed to publishers as XML/CSV, with current price, discounted/was price, product URL, availability, and brand fields. Feed access is gated by campaign approval. Advertiser terms authorize Optimise to provide affiliates a licence to use advertiser brand/content **for promoting the company**. Samsung Philippines’ Club Affiliate Program publicly routes partnership contact to Optimise (`partnerships.sea@optimisemedia.com`). Lazada PH appears in the Optimise advertiser directory.

| Official source | Role |
|-----------------|------|
| [Optimise Product Feeds](https://docs.optimisemedia.com/docs/advertisers/getting-started/publisher-content/advertiserproductfeeds/) | Technical feed/catalogue for publishers; access controlled by advertiser/account manager |
| [Optimise Network API — List Product Feeds](https://docs.optimisemedia.com/api/) | Publisher API can list feeds for campaigns the publisher is promoting |
| [Optimise Advertiser Terms](https://optimisemedia.com/terms/Optimise-Terms-of-Service-0418.pdf) | Product Feed defined so affiliates can present Products on Affiliate Media; advertiser licences brand/content to Optimise and its affiliates for promotion |
| [Samsung Club Affiliate Program](https://www.samsung.com/ph/offer/samsung-club-affiliates/) | PH official-store affiliate program operated via Optimise |
| [lazada ph Affiliate Program \| Optimise Media](https://optimisemedia.com/advertiser-directory/lazada-ph-affiliate-program-2107053/) | Directory listing; not a data-rights grant |

**Smallest owner action.** Owner-controlled publisher application (not from this agent). After approval, request product-feed access for a PH shopping advertiser and obtain the campaign’s publisher terms on display, comparison, caching, transformation, and AI use. Commission approval alone is insufficient.

### OA-4 — Involve Asia Datafeed / Publisher API

Involve Asia publishes a Datafeed product whose stated purpose is to populate advertiser products on a publisher website with tracking links already inserted. The Publisher API can filter offers by `filters[offer_country]=Philippines`. The Publisher Agreement licences Qualifying Links and provided Content only as supplied; publishers may not modify advertiser Content unless expressly authorized; each Engagement has its own terms.

| Official source | Role |
|-----------------|------|
| [Involve Asia Datafeed](https://involve.asia/products/datafeed/) | Publisher catalog-listing tool |
| [Publisher API](https://api.involve.asia/) | Offers, deeplinks; PH country filter exists |
| [Publisher Agreement](https://involve.asia/terms-conditions/) | Limited licence; no modification of Content; per-offer Engagement terms control |
| [How to apply for offers](https://helpcentre.involve.asia/portal/en/kb/articles/how-to-apply-for-offers) | Per-offer promotional guidelines and T&Cs must be accepted |

Public glossary copy mentioning “comparison content” is marketing language, not a licence grant. **Smallest owner action:** owner-controlled publisher registration, then apply only to PH shopping advertisers that actually supply a current product feed and whose offer T&Cs allow consumer-facing listing/comparison.

### OA-5 — Direct written permission from additional PH retailers

No reviewed PH specialty retailer publicly grants commercial comparison reuse. Several remain high-value written-permission targets because they sell current PH electronics with attributable prices:

1. **Power Mac Center** — already OA-1; still the first retailer letter.
2. **Beyond the Box** — Apple Premium Reseller. [Terms of Use](https://beyondthebox.ph/pages/terms-of-use) prohibit reproducing/exploiting any portion of the site without express written permission, and prohibit spider/crawl/scrape.
3. **Abenson** — [Terms of Use](https://home.abenson.com/terms-of-use) forbid using any agent/tool (other than Abenson-provided tools and third-party search engines) to navigate the site; content reuse is limited to personal/educational/non-commercial printouts.
4. **SM Appliance / Digital Walker / VillMan / Octagon** — useful PH electronics coverage; no official public product-data licence found. Treat as written-permission targets, not scrape targets.

Do not send retailer email from this agent. Owner controls external communication. Use the specification in §8.

---

## 5. Capability-policy matrix — strongest path (OA-1)

States are only `allowed` / `restricted` / `prohibited` / `unknown`. This matrix is for the **combined** Shopify commercial UCP + PMC storefront path **before** written permission. It is not a certification.

| Capability | Technically exposed? | Policy | Canonical evaluated offer? |
|------------|----------------------|--------|----------------------------|
| product_discovery | documented UCP `search_catalog` / storefront search | unknown | no |
| product_identity | documented product/variant IDs and handles | unknown | no |
| current_pricing | documented catalog price fields | unknown | no |
| availability | documented in UCP get_product / stock fields | unknown | no |
| shipping | destination-dependent; UCP checkout/context may expose later | unknown | no — Sprint 37 honesty still applies |
| promotion/discount | possible in catalog; not confirmed for PMC | unknown | no |
| caching | catalog guidelines: do not cache search results or images | restricted / unknown | no |
| redistribution/display | PMC ToS grant no extra rights; Shopify API does not transfer content ownership | unknown | no |
| comparison use | Shopify Global Catalog docs name comparison shopping; API Terms prohibit building a product index | unknown | no |
| transformation/normalization | not expressly granted | unknown | no |
| runtime AI summarization | Shopify API Terms restrict using derived API/Merchant Data to train/improve AI systems without written consent; runtime inference is not clearly allowed | unknown | no |
| recommendation/scoring input | not expressly granted | unknown | no |
| source URL attribution | product URLs are technically present | unknown | no |
| retention | no-cache guideline; PMC ToS silent on PiqSavi retention | restricted / unknown | no |
| commercial use | Shop personal skill: prohibited for commercial aggregators. Commercial UCP developer path: unknown pending agent profile and written confirmation | unknown | no |

Fail-closed consequence: **no PMC/Shopify offer may enter the canonical evaluated set on this evidence.**

---

## 6. Concise BLOCKED / disqualified classes

These classes were reviewed and are **not** current Sprint 32 offer paths. Detail is in Appendix A.

| Class | Why it cannot certify |
|-------|------------------------|
| Public product pages, robots.txt, search-engine indexing, Tavily Extract | Technical retrieval only. Not a content licence. Source-site policy remains unknown. |
| Shop.app personal AI agent skill | Official Help Center: personal use only; commercial products, aggregators, bulk catalog copy, and AI-model training from Shop data are unauthorized. |
| Shopee Open Platform (seller/ISV) | Public ToS allow display of Shopee Content in an approved Application, but Shopee Content **may not be combined with non-Shopee Content**, may not be used to benefit competing services, and may not be displayed relative to third-party services. That is incompatible with PiqSavi comparison. Access also requires a separate approved developer account (currently held). |
| Shopee Affiliate Program T&Cs | Grant a licence to display **Affiliate Links** only. They do not grant product-catalog comparison rights. Affiliate Open API documentation ≠ PiqSavi authorization. |
| Consumer storefront ToS as a reuse licence | Sony PH expressly authorizes personal, non-commercial viewing only. PMC, Beyond the Box, Abenson, Samsung PH online shop, and Acer storefront sales terms do not affirmatively license commercial comparison reuse. |
| Manufacturer consumer shops / partner pages without a catalog licence | Samsung PH, Sony PH, Acer PH, Apple reseller pages, Knox/EPP/business-partner pages are not PH offer feeds for PiqSavi. |
| Icecat Open/Full content | Licensed product **specs/identity** (Full Icecat even lists comparison sites as a typical client). It does **not** supply attributable current PH retailer prices or merchant source URLs. Open Icecat voids the licence if data is used in a generative-AI framework. Complementary identity source only — not a Sprint 32 offer path. |
| Generic SERP snippets, scraper APIs, unofficial wrappers | Not a legitimate provenance path. Forbidden as a workaround. |

---

## 7. What still prevents production certification

Even OA-1 cannot close Sprint 32 until all of the following exist:

1. Written source-side permission or an executed program agreement covering the §8 uses.
2. Provider/merchant approval and credentials where the program requires them (EXT-06 still `not_started`).
3. Technical connectivity against the authorized path (not Tavily-as-merchant; not fixtures).
4. Evidence-backed Sprint 31 capability-policy rows, with unknown remaining fail-closed.
5. Current-data validation, freshness, provenance, and canonical offer-economics compatibility.
6. Staging certification, monitoring, public coverage disclosure, kill-switch evidence.

EXT-01 `applied` (2026-09-08 Shopee/Lazada emails) is not approval, credentials, a feed, or certification.

---

## 8. Written permission specification (owner-controlled; do not send)

High-value PH retailers without a public reuse licence remain valid owner-action candidates. Any permission request should ask the retailer/platform to **explicitly authorize PiqSavi** to:

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

Also state: PiqSavi is a shopper-facing comparison assistant; initial public beta is planned without affiliate commissions; ordinary outbound merchant links are sufficient.

**Do not send any email from this workspace.** Owner controls external communication.

Suggested first five addressees, in order:

1. Power Mac Center (`webstore@powermaccenter.com` is the public web-store support address on the official terms page)
2. Lazada PH affiliate / product-data follow-up (`affiliate@lazada.com.ph` — EXT-01 already applied)
3. Shopify commercial UCP / Partner support via official developer support path (confirm query-time comparison agent vs product-index prohibition)
4. Beyond the Box (`inquiry@beyondthebox.ph`)
5. Abenson (`shop@abenson.com` appears on the public terms page)

---

## 9. Tavily role (unchanged)

Tavily may remain a **discovery/retrieval provider**. It is not the merchant.

Possible later architecture, only if the source-side permission is actually defensible:

```text
Tavily discovery/retrieval
        ↓
authorized retailer/source (first target: Power Mac Center / Shopify UCP)
        ↓
source-site rights = allowed or restricted-as-certified
        ↓
Level B evidence
        ↓
later Sprint 38 execution
        ↓
canonical normalized offer
```

A Tavily Extract result does **not** solve source-site rights. Public-web snippets remain Level D / discovery-only.

---

## 10. Next external action

Owner-only. This audit performed no signup, application, email, payment, credential creation, merchant API call, or scrape.

1. Send the PMC written-permission request (§8).
2. Request Shopify written confirmation of commercial UCP query-time comparison use.
3. Follow up Lazada EXT-01 specifically on feed **display / compare / normalize / short-TTL cache / AI-assisted recommendation** rights.
4. Keep Shopee Open Platform out of the first comparison floor unless Shopee grants a written waiver of the no-combining / no-competing-service clauses.
5. Counsel-review any draft agreement before treating a capability as `allowed`.

---

## 11. Non-claims

This audit does **not** mean:

- any path is legal under Philippine law (no qualified legal review is recorded here)
- PiqSavi may reuse public PH product pages
- robots.txt, search indexing, or Tavily extraction is permission
- Shopee, Lazada, PMC, Shopify, Optimise, Involve Asia, Samsung, Sony, Acer, Icecat, Brave, Tavily, or Exa is certified
- affiliate commission approval is product-data permission
- Sprint 32 is complete
- production catalogs are populated
- Sprint 38 has started

---

## Appendix A — rejected-research evidence table

| Candidate | Official sources reviewed | Technically exposed? | Policy | Why not a survivor |
|-----------|---------------------------|----------------------|--------|--------------------|
| PMC public pages alone | [Terms of service](https://powermaccenter.com/policies/terms-of-service) | storefront HTML/JSON exist | unknown / restricted — §5(b) grants no rights except as expressly provided | No affirmative commercial comparison licence |
| PMC `agents.md` / storefront UCP without written confirmation | [agents.md](https://powermaccenter.com/agents.md) | UCP/MCP and product JSON documented | unknown — framed for personal shopping assistants; Shop skill recommended | Technical protocol ≠ PiqSavi licence |
| Shop.app personal skill | [Using Shop with personal AI agents](https://help.shop.app/en/shop/shopping/personal-agents); [shop.app/SKILL.md](https://shop.app/SKILL.md) | catalog search exists | **prohibited** for commercial aggregators / bulk catalog copy | Wrong program for PiqSavi |
| Shopify Global Catalog as a public licence | [About Catalogs](https://shopify.dev/docs/agents/catalog); [API Terms](https://www.shopify.com/legal/api-terms) | comparison shopping named in developer docs | unknown / restricted — no-index, no-cache, no-AI-training, no content ownership | Needs agent profile + written confirmation |
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

SPRINT 32 SOURCE-RIGHTS AUDIT COMPLETE —
NO UNAUTHORIZED PUBLIC-PAGE REUSE ACCEPTED —
STRONGEST LEGITIMATE PATH IDENTIFIED —
EXTERNAL PERMISSION / PROVIDER EVIDENCE STILL REQUIRED —
SPRINT 32 REMAINS OPEN
