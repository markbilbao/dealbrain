# Sprint 32 — Shopify Global Catalog PH coverage probe harness

**Document type:** Technical coverage-harness evidence (not certification)
**Date:** 2026-09-18
**Starting `origin/main`:** `af03dac771f48379e44c64a42bff9a846d4c07e7` (merge of PR #147)
**Market:** PH
**Trusted production certification records:** **zero**
**Status:** Owner live 12-query PH search coverage: **PH LIVE TECHNICAL COVERAGE VALIDATED**. 12/12 categories `USEFUL_PH_OFFER`. Diversified 5/5 `get_product` validations completed across five distinct categories after PR #150. This is **not** production-certified. Sprint 32 remains **OPEN**. Sprint 38 remains unstarted.

This document does **not** certify Shopify Global Catalog, any merchant, Shopee, Lazada, Tavily, or PiqSavi shopping beta. The owner live 12-query result means only that Global Catalog returned technically useful PH offers for the tested queries. It is not production certification.

Related:

- [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md`](SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md)
- [`../../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](../../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md)

---

## Official Shopify contract revalidated 2026-09-18

| Source | Current fact used by this harness |
|--------|-----------------------------------|
| [About Catalogs](https://shopify.dev/docs/agents/catalog) | Endpoint `https://catalog.shopify.com/api/ucp/mcp`. Agent profile, **no API key**. Best for cross-merchant discovery / comparison shopping. |
| [Global Catalog MCP](https://shopify.dev/docs/agents/catalog/global-catalog) | Tools `search_catalog`, `lookup_catalog`, `get_product`. `filters.ships_to.country` ISO 3166-1 alpha-2. `filters.available`. `context.address_country` / `currency` / `language`. `view` = `"offer"` on search for comparison shopping. Inferred fields marked in docs. |
| [Agent profiles](https://shopify.dev/docs/agents/profiles) | Every request must send `meta.ucp-agent.profile`. Official hosted fixtures exist **to use and test UCP**. |
| [Auth and rate limiting](https://shopify.dev/docs/agents/profiles/auth-and-rate-limiting) | Catalog tools are available at Token, Signed, **and Anonymous** tiers. Anonymous: no `Authorization` header or signature headers. |

Anonymous technical probe is **currently supported**. This harness uses that documented Anonymous tier plus Shopify’s hosted 2026-08-25 valid-with-capabilities fixture:

`https://shopify.dev/ucp/agent-profiles/2026-08-25/valid-with-capabilities.json`

That fixture is **TECHNICAL TEST ONLY**. It is **not** a PiqSavi identity. It does **not** mean Shopify authenticated or approved PiqSavi. Production-bound work still needs PiqSavi’s own hosted UCP profile.

`get_product` documents `view` = `"summary"`, not `"offer"`. This harness sends `view` = `"offer"` only on `search_catalog`.

`lookup_catalog` (bulk IDs, up to 50) is **not** used.

---

## Harness architecture

```text
Owner CLI (scripts/shopify_global_catalog_ph_probe.py)
        ↓
library helpers (app/research/shopify_global_catalog_ph_probe.py)
        ↓
Anonymous JSON-RPC tools/call → catalog.shopify.com
        ↓
minimized PH coverage evidence outside Git
```

This is **certification evidence tooling only**. It is not a production connector, not a Sprint 31 provider registration, and not Sprint 38 execution.

Default live evidence directory: `/tmp/piqsavi-shopify-global-ph`.

Live `--output-dir` values that resolve inside the repository, including relative paths and symlinks, are refused.

---

## PH request shape

Every `search_catalog` call sends:

- `catalog.query`
- `catalog.filters.ships_to.country` = `"PH"`
- `catalog.filters.available` = `true`
- `catalog.context.address_country` = `"PH"`
- `catalog.context.currency` = `"PHP"`
- `catalog.context.language` = `"en"`
- `catalog.view` = `"offer"`
- first page only (`pagination.limit` = 10, no cursor)

Every `get_product` call sends one `catalog.id` plus the same PH `filters` / `context`. No bulk `ids`. No `catalog_id`. No promoted placement. No affiliate parameters.

Maximum: **12** `search_catalog` queries and **5** `get_product` validations.

`select_promising_product_ids()` diversifies those five `get_product` validations. When candidates exist across multiple query IDs, the first pass selects at most one candidate per query: incomplete evidence is preferred within a query, then incomplete-query representatives are taken in deterministic query order before complete-query representatives. Remaining eligible candidates fill leftover slots only after that distinct-query pass. Selection is not randomized and does not increase the network budget.

---

## Query set

1. wireless earbuds
2. gaming laptop
3. mechanical keyboard
4. USB-C charger
5. phone case
6. portable power bank
7. skincare serum
8. running shoes
9. backpack
10. air fryer
11. coffee grinder
12. home office chair

---

## Classification rules

| Class | Meaning |
|-------|---------|
| `USEFUL_PH_OFFER` | At least one non-placeholder offer has identifiable product, integer `price_amount_minor` plus currency, seller identity, an actual seller/product/checkout URL, sale-ready availability when provided, and PH query context applied. A seller domain alone is not a destination URL. |
| `PARTIAL_PH_RESULT` | Products return but comparison-critical offer evidence is incomplete. |
| `NO_USEFUL_PH_RESULT` | No useful offer exists, including empty or obvious placeholder/test results. JSON-RPC/MCP tool failures are **not** this class; they fail the probe closed. |

Inferred Shopify fields (`description`, `options`, `metadata.*`, `variants[].condition`) are recorded as inferred and are not treated as merchant-authored source facts.

Persisted live evidence is minimized only: query, timestamp, classification, product identifier, seller identity/domain, `price_amount_minor`, currency, availability, actual URL presence, and flags. No product images. No broad inferred marketing copy. No raw Shopify catalog payloads. Amounts never enter PiqScore.

HTTP 200 JSON-RPC `error` envelopes and MCP `result.isError=true` fail the probe. They are not empty-catalog coverage results. Non-fatal `structuredContent.messages` on an otherwise successful product response are not treated as errors.

Live catalog HTTP requests send an explicit probe User-Agent:

`PiqSavi-Sprint32-PH-Coverage-Probe/1.0`

plus `Content-Type: application/json` and `Accept: application/json`. No `Authorization` or signature headers. This is not a Shopify CLI User-Agent.

---

## Owner live diagnostic addendum (2026-09-18; not certification)

Owner live diagnostic from the same Cursor environment, after PR #148 merged. This is **not** the controlled 12-query certification probe. It does **not** certify Shopify. Sprint 32 remains **OPEN**.

- The merged custom Python harness initially returned **HTTP 403** from `https://catalog.shopify.com/api/ucp/mcp`.
- Official Shopify CLI from the same environment succeeded for PH-localized `wireless earbuds` (`npx -y @shopify/ucp-cli@latest catalog search` with PH `ships_to`, PH `address_country`, PHP currency, `available=true`, first page `limit=3`).
- CLI reported UCP `2026-08-25`, status success, **478** available results, and a first page of real cross-merchant offers. That count is **not** a claim that all 478 are useful comparison offers, that checkout would succeed, or that sellers are Philippine merchants.
- Returned offers included **PHP** prices and at least one **USD** price despite PHP context. Requested `context.currency=PHP` does **not** guarantee every returned offer currency is PHP, and this harness must not overwrite or fabricate returned currency.
- `filters.ships_to.country=PH` does **not** prove seller location is the Philippines. Seller location must not be inferred from that filter.
- One controlled Python request using the existing harness payload (`build_search_catalog_arguments()` / `build_jsonrpc_request()` / same endpoint) plus `User-Agent: PiqSavi-Sprint32-PH-Coverage-Probe/1.0` returned **HTTP 200** and `Content-Type: application/json`.
- Isolated cause in the tested environment: missing explicit User-Agent on the custom harness path. Explicit client identification is required for this probe path here.
- Shopify Global Catalog remains a **rights survivor / technical candidate**, **not** production-certified. Production provider and certification catalogs remain empty. Sprint 38 has not started.

---

## Owner live 12-query PH coverage probe (2026-09-18; technical coverage only)

SHOPIFY GLOBAL CATALOG PH LIVE COVERAGE PROBE: **PASSED TECHNICAL COVERAGE TEST**

Owner-supplied live evidence after PR #149. This agent did **not** call Shopify. This is **not** production certification. This does **not** close Sprint 32. Shopify remains a restricted query-time rights survivor / technical candidate. Sprint 38 remains unstarted. Production provider and certification registries remain empty.

Observed probe facts:

| Fact | Value |
|------|-------|
| `live` | `true` |
| `auth_tier` | Anonymous |
| `credentials_required` | `false` |
| `search_calls` | 12 |
| `get_product_calls` | 5 |
| `lookup_catalog_calls` | 0 |
| `pagination_followed` | `false` |
| `bulk_ids_used` | `false` |
| `raw_response_persisted` | `false` |
| `production_certified` | `false` |
| `certifies_shopify` | `false` |
| `closes_sprint_32` | `false` |
| `starts_sprint_38` | `false` |
| `affiliate_or_promoted_placement` | `false` |
| `scraping` | `false` |
| `environment_mutation` | `false` |

All 12 queries classified `USEFUL_PH_OFFER`:

1. wireless earbuds
2. gaming laptop
3. mechanical keyboard
4. USB-C charger
5. phone case
6. portable power bank
7. skincare serum
8. running shoes
9. backpack
10. air fryer
11. coffee grinder
12. home office chair

First-page totals from owner output:

- 120 products total
- 122 offer records
- every query had `usable_for_comparison`, `price_present`, `currency_present`, `identifiable_seller`, `destination_present`, and `availability_present` = `true`

Returned currencies were mixed despite `context.currency=PHP`. Observed currencies across categories included PHP, USD, INR, GBP, SGD, AUD, EUR, and ZAR.

Therefore:

- `context.currency=PHP` MUST NOT be interpreted as guaranteed PHP output
- preserve the returned offer currency; never fabricate PHP conversion
- `ships_to.country=PH` MUST NOT be interpreted as seller location in the Philippines
- a successful search result MUST NOT be interpreted as guaranteed checkout success
- 12 tested intents do NOT equal complete PH retail coverage
- this does NOT mean every Shopify merchant ships successfully to PH at checkout

Harness issue observed in that live run: report showed `wireless earbuds` → `GET_PRODUCT True` and the remaining 11 queries → `GET_PRODUCT False`, yet `get_product_calls == 5`. The previous selector built global incomplete/complete lists in query order and sliced `(incomplete + complete)[:5]`. When first-query results are complete, all five `get_product` validations can come from the first query. The current 5 `get_product` validations were concentrated in one query because of that selector issue. That does **not** invalidate the 12-query search coverage evidence. It does mean those five deeper `get_product` validations are not diversified enough to use as representative cross-category evidence. The owner must rerun deeper `get_product` cross-category validation after this selector fix.

## Owner live diversified get_product validation (2026-09-18; after PR #150)

SHOPIFY GLOBAL CATALOG PH LIVE TECHNICAL COVERAGE VALIDATED

Owner-supplied live evidence after PR #150 merged. This agent did **not** call Shopify. The required owner cross-category `get_product` rerun is **COMPLETE**. This is still **PH LIVE TECHNICAL COVERAGE VALIDATED**. It is **not** production certification, Shopify/PiqSavi production approval, complete PH retail coverage, proof every returned offer completes checkout to PH, proof seller location is the Philippines, Sprint 32 closure, or Sprint 38 execution.

Observed summary:

| Fact | Value |
|------|-------|
| `live` | `true` |
| `fixture` | `false` |
| `auth_tier` | Anonymous |
| `credentials_required` | `false` |
| `search_calls` | 12 |
| `get_product_calls` | 5 |
| `lookup_catalog_calls` | 0 |
| `pagination_followed` | `false` |
| `bulk_ids_used` | `false` |
| `raw_response_persisted` | `false` |
| `production_certified` | `false` |
| `certifies_shopify` | `false` |
| `closes_sprint_32` | `false` |
| `starts_sprint_38` | `false` |
| `affiliate_or_promoted_placement` | `false` |
| `scraping` | `false` |
| `environment_mutation` | `false` |

All 12 query classifications remained `USEFUL_PH_OFFER`.

The five live `get_product` validations were distributed across five distinct categories:

| Query | Classification | Products | Offers | `usable_for_comparison` |
|-------|----------------|----------|--------|-------------------------|
| wireless earbuds | `USEFUL_PH_OFFER` | 10 | 10 | `true` |
| gaming laptop | `USEFUL_PH_OFFER` | 10 | 10 | `true` |
| mechanical keyboard | `USEFUL_PH_OFFER` | 10 | 10 | `true` |
| USB-C charger | `USEFUL_PH_OFFER` | 10 | 19 | `true` |
| phone case | `USEFUL_PH_OFFER` | 10 | 11 | `true` |

Remaining seven categories did not use `get_product` and all remained `USEFUL_PH_OFFER`.

Second-run totals: **120 products** and **130 offer records**. The additional offer records after `get_product` are compatible with products exposing multiple variants. This is **not** 130 distinct products.

Completed technical evidence:

- rights survivor identified for restricted query-time Shopify Global Catalog use
- Anonymous technical connectivity works
- PH-localized current-data search works
- 12/12 controlled query categories returned `USEFUL_PH_OFFER`
- five deeper `get_product` validations succeeded across five distinct categories
- returned price/currency/seller/destination/availability evidence remained usable
- actual returned currencies must remain preserved
- no scraping required
- no credentials required for Anonymous technical path

Completed staging Shopify negotiation evidence:

- PiqSavi-owned **staging** UCP agent profile **live-fetch validated by Shopify** (`SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = True`) after Deploy Staging #40 (`run_id` `35439563878`; SHA `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620`). One owner-controlled `search_catalog` retry (`wireless earbuds`) returned HTTP 200, JSON-RPC `error = null`, MCP `isError = false`, and `product_count = 3`. This is **not** production-profile negotiation or production certification.

Still **not** completed:

- PiqSavi-owned **production** UCP agent profile deployed and owner HTTPS-validated (`PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False`; production URL is **NOT** owner-validated)
- real production provider registration
- trusted production certification
- Sprint 31 capability-policy rows/evidence for Shopify PH path
- production normalization/matching evidence as required
- reliability/failure-mode certification
- staging certification
- monitoring
- public coverage disclosure
- kill-switch closure evidence
- limited production validation where required

Production provider registry = zero. Production certification catalog = zero. Production evidence catalog = zero. Production routing policies = zero. Sprint 32 remains **OPEN**. Sprint 38 remains **UNSTARTED**.

## PiqSavi UCP agent profile

**PIQSAVI UCP AGENT PROFILE: IMPLEMENTED LOCALLY — NOT YET DEPLOYED/VALIDATED**

This heading is the 2026-09-18 local-implementation snapshot. It does **not** rewrite the owner live PH coverage evidence above. Current environment-specific deployment and Shopify-negotiation state is recorded in the later addenda below. No live Shopify call was made for this 2026-09-18 documentation slice. At that snapshot Shopify has not fetched PiqSavi's profile.

| Field | Value |
|-------|-------|
| Proposed canonical production URL | `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Staging URL (owner-validated 2026-09-19) | `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Hosting application | Existing FastAPI app (`create_app()` in `app/main.py`) |
| Hosting route | `GET /ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Why this host | Production public HTTPS origin is `https://piqsavi.com` (apex). `www.piqsavi.com` is a trusted host that cutover sends to apex. The FastAPI app already serves unauthenticated public documents (`/robots.txt`, `/sitemap.xml`, `/health`). No new service. |
| HTTP contract | GET, public, unauthenticated, HTTP 200, `Content-Type: application/json`, deterministic body, `Cache-Control: public, max-age=300`, no application-layer redirect on the canonical path, no DB/Redis/network, no cookies, no personalization |
| UCP version | `2026-08-25` |
| Declared capabilities | `dev.ucp.shopping.catalog.search`, `dev.ucp.shopping.catalog.lookup`, `dev.shopify.catalog.global` |
| Why those capabilities | Least privilege for Global Catalog search + `get_product`. Official `dev.shopify.catalog.global` extends both catalog.search and catalog.lookup. UCP maps `get_product` to Lookup. Declaring lookup is **not** permission to run bulk `lookup_catalog`; the PH probe still forbids that tool. Checkout, cart, order, payment, fulfillment, buyer consent, discount, and storefront catalog are omitted. |
| Server-owned URL setting | `PIQSAVI_UCP_AGENT_PROFILE_URL` (public, non-secret; not shopper/request/frontend controlled) |
| `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED` | `True` (code constant; not request/env/browser controlled). Exact staging HTTPS profile deployed and owner-validated. Does **not** mean Shopify fetched it. |
| `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` | `False` (code constant; not request/env/browser controlled). Production HTTPS profile is not owner-validated. |
| `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` | `True` (recorded after the 2026-09-22 successful live Shopify retry against the deployed staging profile). This is **not** production-profile negotiation or production certification. |
| Live `--agent-profile-source piqsavi` | Allowed only when `piqsavi_profile_deployed_for_url(exact selected trusted URL)` is true. Staging may unlock. Production remains **FAIL CLOSED**. Arbitrary URLs fail closed. |
| Shopify test fixture | `https://shopify.dev/ucp/agent-profiles/2026-08-25/valid-with-capabilities.json` remains **TECHNICAL TEST ONLY** and is still the PH probe default |
| PiqSavi-owned profile | Explicit `--agent-profile-source piqsavi` only. Evidence source is `piqsavi`; usage is `PIQSAVI_OWNED_PROFILE`. Deployment/fetch truth is in the lifecycle booleans. Live default is **not** switched to PiqSavi. Offline fixture mode may still select `piqsavi`. Staging URL may unlock when deployed; production remains fail-closed. |
| Next sequence | Production profile HTTP/2 404 recorded 2026-09-23. `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` remains False. Production profile deployment and HTTPS validation belong to Sprint 41 and are not pulled into Sprint 32. Capability-policy preparation continues from staging and live technical evidence. Production certification remains incomplete. |
| Local tests | Focused profile route + PH probe contract tests, including fail-closed zero-network proof |
| Live Shopify call in this slice | None |
| Shopify fetched PiqSavi profile | Yes for staging only. Not production. |
| Production registries | Empty |
| Sprint 32 | Remains **OPEN** |
| Sprint 38 | Remains **UNSTARTED** |

Exact local profile document:

```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/catalog/search",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_search.json"
        }
      ],
      "dev.ucp.shopping.catalog.lookup": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/catalog/lookup",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_lookup.json"
        }
      ],
      "dev.shopify.catalog.global": [
        {
          "version": "2026-08-25",
          "spec": "https://shopify.dev/docs/agents/catalog/global-catalog",
          "schema": "https://shopify.dev/ucp/schemas/2026-08-25/shopify_catalog_global.json",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup"
          ]
        }
      ]
    }
  }
}
```

## 2026-09-19 staging PiqSavi UCP profile owner-validated

This addendum does **not** rewrite the owner live PH coverage evidence or claim production readiness.

| Field | Value |
|-------|-------|
| Staging profile deployed | **True** |
| Exact staging URL | `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Owner validation | Public HTTP/2 200; expected JSON (`ucp.version = 2026-08-25`, catalog.search, catalog.lookup, `dev.shopify.catalog.global`) |
| Deploy Staging | run_id `35430542107`, run_number 38, result success |
| Deployed SHA | `e5654a63fe650fd21c219a24270455f8902519a0` |
| Production profile deployed | **False**. `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` is **not** owner-validated |
| `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` | **False**. Public HTTPS deployment is not Shopify fetch/negotiation |
| Production certification | **False** |
| Live Shopify call in this slice | **None**. This workspace did not call Shopify |
| AWS mutation / deploy in this slice | **None** |
| Live gate | `piqsavi_profile_deployed_for_url(exact selected trusted URL)`. Staging may unlock. Production remains fail-closed. Arbitrary URLs fail closed |
| Evidence labels | Source `piqsavi`. Usage `PIQSAVI_OWNED_PROFILE`. Notes say "PiqSavi-owned profile selected." Staging output must not claim the selected profile is undeployed or production-intended. Lifecycle booleans remain the source of truth. |
| Shopify technical fixture | Unchanged. Still the PH probe default. **TECHNICAL TEST ONLY** |
| Sprint 32 | Remains **OPEN** |
| Sprint 38 | Remains **UNSTARTED** |

## 2026-09-19 first PiqSavi profile Shopify discovery attempt failed

This addendum does **not** rewrite the owner live PH coverage evidence, the 2026-09-18 local profile snapshot, or the staging HTTPS-validation addendum. It records the owner-observed **failed** first Shopify discovery attempt against the already-reachable staging profile. This workspace did **not** call Shopify, deploy, or mutate AWS.

PUBLIC PROFILE REACHABLE = yes

SHOPIFY DISCOVERY ATTEMPTED = yes

SUCCESSFUL UCP NEGOTIATION = no

PRODUCTION CERTIFIED = no

| Field | Value |
|-------|-------|
| PUBLIC PROFILE REACHABLE | **yes**. Exact staging URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` returned public HTTP/2 200 after Deploy Staging #39 |
| Advertised capabilities on that reachable profile | `dev.shopify.catalog.global`, `dev.ucp.shopping.catalog.lookup`, `dev.ucp.shopping.catalog.search` |
| SHOPIFY DISCOVERY ATTEMPTED | **yes**. Exactly one owner `search_catalog` request |
| Query | `wireless earbuds` |
| Profile used | `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Request budget | `search_catalog = 1`; `get_product = 0`; `lookup_catalog = 0`; pagination = 0 |
| Shopify HTTP | **422** |
| JSON-RPC | `error.code = -32001`; `error.message = "UCP discovery failed"` |
| Discovery error | `error.data.code = "profile_malformed"`; `error.data.content = "Unable to fetch agent profile: Missing services"` |
| Product result | none |
| `get_product` call | none |
| `lookup_catalog` call | none |
| Pagination | none |
| SUCCESSFUL UCP NEGOTIATION | **no** |
| PRODUCTION CERTIFIED | **no** |
| `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` | **False**. Do not set true after HTTP 422 / `profile_malformed` |
| `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED` | **True**. Public reachability is not successful negotiation |
| `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` | **False** |
| Root cause | Official Shopify/UCP 2026-08-25 agent profiles require `ucp.services` and `ucp.payment_handlers`. The reachable profile omitted both |
| Profile-shape fix in this slice | Add `services.dev.ucp.shopping` (`version` `2026-08-25`, `spec` `https://ucp.dev/2026-08-25/specification/overview`, `transport` `mcp`, `schema` `https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json`) and `payment_handlers: {}`. Capability set unchanged. No cart/checkout/order/payment/storefront-catalog capabilities. No service `endpoint` field |
| Live Shopify call in this workspace | **None** |
| AWS mutation / deploy in this workspace | **None** |
| Sprint 32 | Remains **OPEN** |
| Sprint 38 | Remains **UNSTARTED** |

Corrected local profile document after this slice (not yet staging-redeployed by this workspace):

```json
{
  "ucp": {
    "version": "2026-08-25",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/catalog/search",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_search.json"
        }
      ],
      "dev.ucp.shopping.catalog.lookup": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/catalog/lookup",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/catalog_lookup.json"
        }
      ],
      "dev.shopify.catalog.global": [
        {
          "version": "2026-08-25",
          "spec": "https://shopify.dev/docs/agents/catalog/global-catalog",
          "schema": "https://shopify.dev/ucp/schemas/2026-08-25/shopify_catalog_global.json",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup"
          ]
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

## 2026-09-22 staging PiqSavi profile Shopify negotiation succeeded

This addendum does **not** rewrite the owner live PH coverage evidence, the 2026-09-18 local profile snapshot, the staging HTTPS-validation addendum, or the 2026-09-19 failed first Shopify discovery attempt. The earlier HTTP 422 / `profile_malformed` / `Missing services` attempt remains historically true. This workspace did **not** call Shopify, deploy, or mutate AWS.

After Deploy Staging #40 (`run_id` `35439563878`; SHA `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620`), the owner verified the exact public staging URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` contained official `ucp.services.dev.ucp.shopping` (`version` `2026-08-25`, `spec` `https://ucp.dev/2026-08-25/specification/overview`, `transport` `mcp`, `schema` `https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json`) and `payment_handlers: {}`. Catalog capabilities remained catalog.search, catalog.lookup, and `dev.shopify.catalog.global`.

The owner then made exactly one controlled Shopify `search_catalog` retry (`wireless earbuds`) using that profile. Shopify returned HTTP 200, JSON-RPC `jsonrpc = "2.0"`, `id = 2`, `error = null`, MCP `isError = false`, `product_count = 3`, and `messages = []`. Request budget: `search_catalog = 1`; `get_product = 0`; `lookup_catalog = 0`; pagination followed = 0. Localization: `ships_to.country = PH`; `available = true`; `address_country = PH`; `currency = PHP`; `language = en`; `view = offer`; `pagination.limit = 3`. User-Agent: `PiqSavi-Sprint32-PH-Coverage-Probe/1.0`. No authentication. No second request. The raw Shopify product payload is **not** stored.

PUBLIC PROFILE REACHABLE = yes

SHOPIFY DISCOVERY ATTEMPTED = yes

SUCCESSFUL UCP NEGOTIATION = yes

LIVE SEARCH_CATALOG RESPONSE = yes

PRODUCTS RETURNED = 3

PRODUCTION PROFILE DEPLOYED = no

PRODUCTION CERTIFIED = no

SPRINT 32 COMPLETE = no

SPRINT 38 STARTED = no

| Field | Value |
|-------|-------|
| PUBLIC PROFILE REACHABLE | **yes**. Exact staging URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` after Deploy Staging #40 |
| Deploy Staging | run_id `35439563878`, run_number 40, result SUCCESS, SHA `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620` |
| SHOPIFY DISCOVERY ATTEMPTED | **yes**. Exactly one owner `search_catalog` retry |
| Query | `wireless earbuds` |
| Profile used | `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| Endpoint | `https://catalog.shopify.com/api/ucp/mcp` |
| Request budget | `search_catalog = 1`; `get_product = 0`; `lookup_catalog = 0`; pagination followed = 0 |
| Shopify HTTP | **200** |
| JSON-RPC | `jsonrpc = "2.0"`; `id = 2`; `error = null` |
| MCP | `isError = false`; `messages = []` |
| Product count | **3**. Raw product payload not stored |
| SUCCESSFUL UCP NEGOTIATION | **yes** |
| LIVE SEARCH_CATALOG RESPONSE | **yes** |
| PRODUCTS RETURNED | **3** |
| PRODUCTION PROFILE DEPLOYED | **no** |
| PRODUCTION CERTIFIED | **no** |
| SPRINT 32 COMPLETE | **no** |
| SPRINT 38 STARTED | **no** |
| `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` | **True**. Recorded after this successful staging retry |
| `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED` | **True** |
| `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` | **False** |
| Earlier failed attempt | HTTP 422 / `-32001` / `profile_malformed` / `Missing services` remains historical evidence |
| Live Shopify call in this workspace | **None** |
| AWS mutation / deploy in this workspace | **None** |
| Sprint 32 | Remains **OPEN** |
| Sprint 38 | Remains **UNSTARTED** |

## 2026-09-23 production profile HTTP 404 (does not close this sprint)

This addendum does **not** rewrite earlier snapshots. The owner performed a read-only HTTPS check. This workspace did **not** call Shopify, deploy, or mutate AWS.

PRODUCTION PROFILE URL CHECKED = yes

PRODUCTION PROFILE HTTP STATUS = 404

PRODUCTION PROFILE DEPLOYED = no

PRODUCTION PROFILE VALIDATED = no

PRODUCTION PROFILE NEGOTIATED = no

PRODUCTION CERTIFIED = no

AWS MUTATION = no

DEPLOYMENT = no

SHOPIFY CALL = no

| Field | Value |
|-------|-------|
| URL checked | `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` |
| HTTP | HTTP/2 **404** |
| content-type | `application/json` |
| PRODUCTION PROFILE DEPLOYED | **no** |
| PRODUCTION PROFILE VALIDATED | **no** |
| PRODUCTION PROFILE NEGOTIATED | **no** |
| PRODUCTION CERTIFIED | **no** |
| `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` | **False** |
| `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED` | **True** |
| `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` | **True** for staging only |
| Deployment owner | Sprint 41 production environment/deployment path. Not pulled forward into Sprint 32. |
| Capability-policy prep | Continues on the existing Sprint 31 model using staging and live technical evidence. No production registry rows. |
| AWS MUTATION | **no** |
| DEPLOYMENT | **no** |
| SHOPIFY CALL | **no** |
| Sprint 32 | Remains **OPEN** |
| Sprint 38 | Remains **UNSTARTED** |
| Sprint 41 | Remains **Planned** / unstarted |

Production profile deployment belongs to the later Sprint 41 production environment/deployment path and is not being pulled forward into Sprint 32.

## Owner live command

Credentials: **none**. Do not create a Partner account, Dev Dashboard token, or PiqSavi profile for this Anonymous probe.

```bash
uv run python scripts/shopify_global_catalog_ph_probe.py \
  --live \
  --output-dir /tmp/piqsavi-shopify-global-ph
```

Offline synthetic check:

```bash
uv run python scripts/shopify_global_catalog_ph_probe.py \
  --output-dir /tmp/piqsavi-shopify-global-ph-fixture
```

---

## Non-claims

This harness does **not** mean:

- Sprint 32 is closed
- Shopify is production-certified
- every Shopify merchant ships to PH
- Shopee / Lazada are covered
- complete PH retail coverage
- PiqSavi shopping beta is live
- production provider/certification catalogs are populated
- Sprint 38 has started
- this harness may feed PiqScore / Recommendation / Best Piq

---

SHOPIFY GLOBAL CATALOG PH LIVE TECHNICAL COVERAGE VALIDATED —
12/12 SEARCH CATEGORIES USEFUL —
5/5 GET_PRODUCT VALIDATIONS DIVERSIFIED ACROSS FIVE CATEGORIES —
STAGING PIQSAVI UCP PROFILE DEPLOYED / OWNER HTTPS-VALIDATED —
PRODUCTION PROFILE NOT VALIDATED —
SHOPIFY HAS FETCHED STAGING PIQSAVI PROFILE —
PUBLIC PROFILE REACHABLE = YES —
SHOPIFY DISCOVERY ATTEMPTED = YES —
SUCCESSFUL UCP NEGOTIATION = YES —
LIVE SEARCH_CATALOG RESPONSE = YES —
PRODUCTS RETURNED = 3 —
PRODUCTION CERTIFIED = NO —
FIRST DISCOVERY ATTEMPT PROFILE MALFORMED / MISSING SERVICES —
LATER CONTROLLED RETRY HTTP 200 —
SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = TRUE —
PRODUCTION PROFILE URL CHECKED = YES —
PRODUCTION PROFILE HTTP STATUS = 404 —
PRODUCTION PROFILE DEPLOYED = NO —
PRODUCTION PROFILE VALIDATED = NO —
PRODUCTION PROFILE NEGOTIATED = NO —
NOT PRODUCTION CERTIFICATION —
PRODUCTION PROFILE DEPLOYMENT BELONGS TO SPRINT 41 —
SPRINT 32 REMAINS OPEN —
SPRINT 38 UNSTARTED —
SPRINT 41 UNSTARTED
