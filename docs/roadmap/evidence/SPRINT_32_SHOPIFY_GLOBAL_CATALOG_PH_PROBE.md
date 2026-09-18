# Sprint 32 — Shopify Global Catalog PH coverage probe harness

**Document type:** Technical coverage-harness evidence (not certification)
**Date:** 2026-09-18
**Starting `origin/main`:** `af03dac771f48379e44c64a42bff9a846d4c07e7` (merge of PR #147)
**Market:** PH
**Trusted production certification records:** **zero**
**Status:** Harness ready. **Owner live PH coverage test required.** This is **not** production-certified. Sprint 32 remains **OPEN**.

This document does **not** certify Shopify Global Catalog, any merchant, Shopee, Lazada, Tavily, or PiqSavi shopping beta. A successful later live probe would mean only that Global Catalog returned technically useful PH offers for the tested queries.

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

---

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

SHOPIFY GLOBAL CATALOG PH PROBE HARNESS READY —
OWNER LIVE PH COVERAGE TEST REQUIRED —
NO PRODUCTION CERTIFICATION YET —
SPRINT 32 REMAINS OPEN
