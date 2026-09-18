# Sprint 32 — Shopify Global Catalog PH coverage probe harness

**Document type:** Technical coverage-harness evidence (not certification)
**Date:** 2026-09-18
**Starting `origin/main`:** `af03dac771f48379e44c64a42bff9a846d4c07e7` (merge of PR #147)
**Market:** PH
**Trusted production certification records:** **zero**
**Status:** Owner live 12-query PH search coverage probe: **PASSED TECHNICAL COVERAGE TEST**. This is **not** production-certified. Deeper `get_product` cross-category validation must be rerun by the owner after the selector diversification fix. Sprint 32 remains **OPEN**. Sprint 38 remains unstarted.

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

Harness issue observed in that live run: report showed `wireless earbuds` → `GET_PRODUCT True` and the remaining 11 queries → `GET_PRODUCT False`, yet `get_product_calls == 5`. The previous selector built global incomplete/complete lists in query order and sliced `(incomplete + complete)[:5]`. When first-query results are complete, all five `get_product` validations can come from the first query. That does **not** invalidate the 12-query search coverage evidence. It does mean those five deeper `get_product` validations are not diversified enough to use as representative cross-category evidence. The owner must rerun deeper `get_product` cross-category validation after this selector fix.

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

SHOPIFY GLOBAL CATALOG PH LIVE COVERAGE PROBE:
PASSED TECHNICAL COVERAGE TEST —
NOT PRODUCTION CERTIFICATION —
DEEPER GET_PRODUCT CROSS-CATEGORY VALIDATION MUST BE RERUN BY OWNER —
SPRINT 32 REMAINS OPEN —
SPRINT 38 UNSTARTED
