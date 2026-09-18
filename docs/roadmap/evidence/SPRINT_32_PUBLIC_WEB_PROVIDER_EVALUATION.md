# Sprint 32 — Public-web provider evaluation

**Document type:** Non-secret architecture / terms / benchmark evaluation
**Date recorded:** 2026-09-18
**Baseline:** `9222e5b506097d274a2ec940ed80d68f3353d81f` (origin/main at start of this work)
**Market:** PH
**Trusted production certification records:** **zero**

This document does **not** certify Brave, Tavily, Exa, Shopee, Lazada, or any retailer. Fixtures, documentation, and a provider account cannot close Sprint 32.

Related:

- [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)
- [`SPRINT_32_PH_PUBLIC_WEB_SHOPPING_BENCHMARK.json`](SPRINT_32_PH_PUBLIC_WEB_SHOPPING_BENCHMARK.json)
- [`../../architecture/SPRINT_32_PUBLIC_WEB_DISCOVERY_PATH.md`](../../architecture/SPRINT_32_PUBLIC_WEB_DISCOVERY_PATH.md)

---

## 1. Starting SHA

Verified `origin/main` = `9222e5b506097d274a2ec940ed80d68f3353d81f`
Merge of PR #144: “Sprint 29: final checkpoint — internal implementation complete, live-research acceptance dependent”

## 2. Architecture decision

**B.** Existing Sprint 31 architecture can host a public-web discovery provider, but a narrow Sprint 32 extension is required:

- `ProviderType` value `public_web`
- `PublicWebResearchProvider` (discovery-only technical descriptor)
- shopping-evidence tiers and provenance identity split
- snippet-not-price / unknown-shipping-not-free guards against `CanonicalOfferEconomics`
- documentary incomplete evidence + provider-neutral benchmark harness

Not A, because those types did not exist. Not C, because no parallel registry/router is required and Sprint 38 execution is not pulled forward.

## 3. Candidate providers

Evaluated from public official documentation only. No paid signup. No credentials requested or stored.

| Provider | First live candidate? | Why |
|----------|-----------------------|-----|
| Brave Search API | Yes | Clear Customer Applications license to use search results; snippets only; using Search Results to train/evaluate/improve AI models is prohibited; runtime LLM grounding is unknown (not a blanket AI ban); PH `country` enum membership is unverified so the harness omits `country` |
| Tavily Search API | Yes | Free Researcher 1,000 credits/month; explicit `philippines` country boost; Extract could later be Level B *if* policy allows; shopper-facing reuse is unknown |
| Exa Search API | Comparison only | Contents/livecrawl is technically interesting for Level B; consumer reuse terms are more ambiguous; no verified PH country parameter |

## 4. Policy / terms status

Sprint 31 states only: `allowed` / `restricted` / `prohibited` / `unknown`. Ambiguity stays **unknown**. Engineering interpretation is not counsel approval.

Authoritative machine-readable copy: `app/research/public_web_policy.py`.

### Brave Search API

Reviewed: [Terms of Use](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) (updated 1 Sep 2026), [product](https://brave.com/search/api/), [query docs](https://api-dashboard.search.brave.com/app/documentation/web-search/query), [pricing](https://api-dashboard.search.brave.com/documentation/pricing), [LLM Context API](https://api-dashboard.search.brave.com/api-reference/ai/llm_context/get).

| Topic | State |
|-------|-------|
| API use | allowed |
| Search result reuse | restricted |
| URL/result display | allowed |
| Caching | restricted |
| Content retrieval | unknown |
| Attribution | restricted |
| Rate limits | unknown |
| Retention | restricted |
| Model training / evaluation / improvement | prohibited |
| Runtime AI/LLM grounding or inference | unknown |
| Country/localization | unknown |
| Freshness metadata | restricted |
| Structured offer fields | unknown |
| Product discovery | restricted |
| Current pricing | unknown |

Brave grants a limited license to use the API and Search Results with Customer Applications. Storing/caching a database of results is prohibited except transient operational storage. Using Search Results to create, evaluate, train, re-train, fine-tune, benchmark, or otherwise improve AI models or services is prohibited. That is **not** a blanket ban on all runtime LLM use. Brave also documents an LLM Context API for AI agents, grounding, and RAG. The reviewed Search API terms do not clearly establish that PiqSavi may transform, summarize, score, or send third-party Search Results through its runtime AI pipeline, so runtime grounding stays **unknown** (fail-closed; not converted to allowed). Derivative-work restrictions remain relevant. Third-party webpage rights and direct source/page rights remain separate. Using Brave only for URL discovery is different from using Brave snippets as PiqSavi recommendation evidence. Attribution is optional and, if used, must be “POWERED BY BRAVE” plus logo. PH membership of the `country` request-parameter enum is **unverified** from the truncated public list (visible codes include AR/AU/AT plus examples US/DE). The live harness therefore **omits** `country` and keeps PH intent in the query text. Do not send `country=PH`. Do not silently substitute `x-loc-country`.

Public pricing observed: Search prepaid **$5 / 1,000 requests**. Product page still describes a free plan that requires a credit card as anti-fraud. Historical marketing mentions 2,000 free queries/month. Exact current free-tier quota is account-dependent.

### Tavily Search API

Reviewed: [Terms](https://www.tavily.com/terms), [Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Extract](https://docs.tavily.com/documentation/api-reference/endpoint/extract), [credits](https://docs.tavily.com/documentation/api-credits).

| Topic | State |
|-------|-------|
| API use | restricted |
| Search result reuse | unknown |
| URL/result display | unknown |
| Caching | unknown |
| Content retrieval | unknown |
| Attribution | unknown |
| Rate limits | restricted |
| Retention | unknown |
| Model training / evaluation / improvement | unknown |
| Runtime AI/LLM grounding or inference | unknown |
| Country/localization | unknown |
| Freshness metadata | unknown |
| Structured offer fields | unknown |
| Product discovery | unknown |
| Current pricing | unknown |

Terms limit use to Customer’s **internal business purposes**. Shopper-facing PiqSavi use is not clearly the same thing. Extract retrieves page content via Tavily; that is not PiqSavi scraping, and it is not certified offer evidence. Search `country` enum includes `philippines` (technical targeting, not contractual authorization).

Public pricing observed: Researcher **1,000 free credits/month**, no credit card. Basic search = 1 credit. Extract basic = 1 credit / 5 URLs.

### Exa Search API

Reviewed: [Terms of Service](https://exa.ai/assets/Exa_Labs_Terms_of_Service.pdf), [Contents](https://exa.ai/docs/reference/get-contents), [pricing](https://exa.ai/docs/reference/pricing).

| Topic | State |
|-------|-------|
| API use | restricted |
| Search result reuse | unknown |
| URL/result display | unknown |
| Caching | unknown |
| Content retrieval | unknown |
| Attribution | unknown |
| Rate limits | restricted |
| Retention | unknown |
| Model training / evaluation / improvement | unknown |
| Runtime AI/LLM grounding or inference | unknown |
| Country/localization | unknown |
| Freshness metadata | restricted |
| Structured offer fields | unknown |
| Product discovery | unknown |
| Current pricing | unknown |

API use is documentation-limited. Copying/distributing obtained information is restricted except as expressly permitted. `maxAgeHours` is a useful technical freshness control (0 = livecrawl). No verified PH country parameter.

Public pricing observed: pay-as-you-go Search **$7 / 1,000 requests**; Contents **$1 / 1,000 pages** per content type. New accounts: $20 free credits + $10/month free-tier credits.

## 5. PH benchmark design

32 intents in [`SPRINT_32_PH_PUBLIC_WEB_SHOPPING_BENCHMARK.json`](SPRINT_32_PH_PUBLIC_WEB_SHOPPING_BENCHMARK.json). Categories: smartphones, laptops, cameras, TVs, headphones, appliances, gaming, home electronics, household goods, beauty/personal care. Mix of recognizable products and generic purchase intents.

Harness: `scripts/public_web_ph_benchmark.py`. Offline fixtures are unmistakably non-production. Live mode calls official search APIs only and does not scrape merchant pages. Brave live requests omit the unverified `country` enum and keep Philippines in the query text. Tavily still sends documented `country=philippines` when `topic=general`.

A successful Brave/Tavily discovery benchmark only proves discovery usefulness. It does **not** create the real shopping-offer path required to close Sprint 32. Offers still need a legitimate Level A/B route with attributable current price/freshness before they may enter the canonical evaluated set.

## 6. Minimum evidence to treat a result as an offer

All of:

1. Evidence tier A or B (or C only if Sprint 32 policy explicitly permits it)
2. Direct source URL
3. Identifiable merchant/retailer (not the search vendor)
4. Price tied to that source
5. Freshness/fetch evidence
6. Contractual policy `allowed` for the relevant capability
7. Shipping/voucher/availability only from attributable evidence; otherwise unknown

## 7. Snippet-only treatment

Level D stays `discovery_only`. Snippet PHP text is not a listing price. “Free shipping” in a snippet is not canonical free shipping. Unknown fields are not zero and are not scored as zero.

## 8. Owner credentials (next blocker)

Do not paste secrets into chat, Git, Cursor prompts, or source code.

| Provider | Signup | Credential | Store where |
|----------|--------|------------|-------------|
| Brave Search | https://api-dashboard.search.brave.com/ — prefer free/testing plan; do not buy unless the owner chooses | `BRAVE_SEARCH_API_KEY` (subscription token) | Owner secret store; later `dealbrain/<env>/` Secrets Manager leaf if production wiring is approved. Local live run: export in the shell only. |
| Tavily | https://www.tavily.com/ — Researcher free plan, no card | `TAVILY_API_KEY` | Same |
| Exa | https://dashboard.exa.ai/ — documented free credits | `EXA_API_KEY` | Same; not required for the first live test |

Recommended first live run: Brave, then Tavily. Exa is optional comparison.

## 9. Explicit non-claims

- No scraping of Shopee, Lazada, TikTok Shop, Amazon, or retailer sites
- No production/staging/AWS/Terraform/DNS/SSM/RDS/IAM/Secrets Manager/Resend mutation
- No paid signup
- No Sprint 38 live execution
- Sprint 32 remains open
