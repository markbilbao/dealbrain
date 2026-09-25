# Sprint 32 — Philippines Merchant Certification

**Status:** In progress — not production-certified. Internal foundation slices 32.1–32.6 are complete. Sprint 32 is **not complete**.
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name PH
**Inventory:** [`../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)
**Public-web evaluation:** [`../evidence/SPRINT_32_PUBLIC_WEB_PROVIDER_EVALUATION.md`](../evidence/SPRINT_32_PUBLIC_WEB_PROVIDER_EVALUATION.md)
**Source-rights audit:** [`../evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md`](../evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md)

## Authoritative status

Sprint 31 was formally owner-closed before Sprint 32 implementation began. 32.1–32.6 build the trusted certification architecture and a provider-neutral public-web discovery evaluation path. They do **not** close Sprint 32.

| Area | Status |
|------|--------|
| Sprint 31 architecture | closed |
| 32.1 evidence contracts | complete |
| 32.2 trusted decision path | complete |
| 32.3 PH documentary evidence | complete |
| 32.4 hardening | complete |
| 32.5 reconciliation / validation | complete |
| 32.6 public-web discovery evaluation path | internal foundation only — not certified |
| Real PH product-data path | reduced Shopify Global Catalog capability set trusted-certified; not production-deployment ready |
| Production provider | `ph-shopify-global-catalog` registered, operationally DISABLED |
| Production certification | 4 trusted reduced-capability records; not production-deployment certification |
| Live current-data validation | LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED for the reduced path; production operational validation remains |
| Sprint 32 closure | blocked |
| Canonical Shopify normalization | LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED on owner attempt #3 (2026-09-25); attempts #1 and #2 remain failed closed on HTTP 429 |
| Kill-switch engineering check | synthetic Sprint 31 behavior validated; operational closure still incomplete |

The trusted Philippines certification architecture is built and validated. A reduced Shopify Global Catalog capability set is trusted-certified and the provider identity is registered operationally DISABLED. Certified reduced capability set is not production deployment ready. Do not claim PH support, live Shopee research, live Lazada research, or production-ready merchant integration.

### 2026-09-06 owner lock (documentation only; does not close this sprint)

Philippines is the **initial commercial/product validation focus** for the September 2026 beta. That is a market-priority decision, not a restriction that PiqSavi may only ever search two marketplaces, and not a change to the existing rule that PH certification failure removes/delays PH only.

**Initial affiliate-monetization targets** for the September PH beta were recorded on 2026-09-06 as Shopee Philippines and Lazada Philippines. That monetization targeting is **historical**. The 2026-09-07 lock launches **without affiliate monetization**. Ordinary outbound merchant links are valid launch behavior. EXT-07 is not a Sprint 32 September blocker.

Existing Sprint 32 truth remains authoritative:

- no PH merchant may be called certified unless real evidence supports it;
- **product-data rights and affiliate rights remain separate**;
- affiliate approval does **not** satisfy EXT-01 unless it independently provides product-data rights sufficient for live PiqSavi research;
- production certification remains evidence-based;
- do not falsely mark Shopee or Lazada as live, approved, production-ready, or contractually usable until actual certification is complete;
- zero affiliate-enabled merchants is acceptable for September.

### 2026-09-07 owner lock (primarily roadmap/policy plus narrow launch-UI honesty; does not close this sprint)

**Affiliate monetization is deferred for the September public beta.** Shopee and Lazada are no longer September affiliate launch dependencies. Optimise/Lazada affiliate approval, Shopee affiliate approval, tracking access, payout setup, or network credentials must not block Sprint 32 closure or Sprint 45. The 2026-09-06 “initial affiliate-monetization targets” clause is superseded for launch sequencing; it remains a historical record.

This does **not** permit a fake or data-less PH shopping launch. At least one genuinely useful PH shopping path must still have legitimate, certified data access (official API, authorized product feed, direct retailer integration, authorized partner feed, permitted public source, or another documented legitimate data route). Do not scrape merchants merely because affiliate monetization is removed. Affiliate approval is not product-data permission.

At launch, merchant links are ordinary outbound merchant links: no affiliate parameters, Sub IDs, redirect/tracking layer, commission claim, or PiqSavi-initiated affiliate attribution cookie, and no sponsored ranking. A legitimate merchant remains fully eligible to enter research, enter the evaluated set, receive PiqScore, become Best Piq, become Recommendation, and receive an outbound merchant link. PiqSavi may earn ₱0. That is intentional.

Affiliate architecture must not be deleted. Future activation remains downstream of organic decision → winning merchant → optional affiliate attachment. It may never modify source eligibility, evaluated set, PiqScore, Recommendation, Best Piq, or organic ordering.

**Merchant-neutral search/recommendation.** Affiliate status must never exclude an otherwise legitimate source from consideration. All relevant, enabled, certified merchant/data sources for the shopper's market are eligible for server-side research routing regardless of monetization status — including official brand stores, direct retailers, electronics retailers, authorized reseller sites, and other marketplaces with a legitimate data path. Eligibility is not a requirement to query every integrated merchant on every shopper request. The research/router may decide which sources are actually attempted for a specific request using legitimate non-affiliate factors such as shopper market, requested category/product, connector capability, provider restrictions, coverage, source health, availability, timeout/degradation, and other operational relevance. Affiliate commission, affiliate availability, or partner economics must never include/exclude a source from organic consideration, prioritize a source, or alter PiqScore, Recommendation, Best Piq, or organic ordering. A source that is actually evaluated remains fully eligible to receive canonical PiqScore, become Best Piq, become the Recommendation, rank above affiliate merchants, and receive a normal outbound merchant link. If a non-affiliate merchant wins, PiqSavi may earn ₱0 and must still recommend it. Public language remains **Best Piq among the offers PiqSavi evaluated**. Do not imply all supported merchants were queried unless later execution evidence proves they were. Sprint 38 execution traces remain responsible later for truthful attempted / succeeded / failed / timed-out sources and evaluated-offer count; this lock does not start Sprint 38.

**Search inclusion** depends on a legitimate, sufficiently trustworthy data path (official API, authorized product feed, approved affiliate/product feed, direct retailer/partner integration, permitted public data source, or another contractually/technically legitimate source). Affiliate status is not the inclusion or exclusion test. Do not use scraping as a workaround. If a merchant has no legitimate usable product-data path, or was not actually queried, do not claim it was searched.

**TikTok Shop PH** is not required for the September 2026 beta. It must not delay Sprint 45, must not appear in public marketplace-coverage claims unless actually supported, must not receive pre-launch engineering priority over higher-value launch work, and must not be represented as searched when it was not queried. Do not destructively remove existing general architecture merely because TikTok is deferred.

**Effective-cost field evidence.** Each PH source certification must record the following components **without conflating technical availability with policy authorization**:

- current listing price
- seller discount
- platform discount
- voucher/promotion information
- voucher eligibility/applicability information
- destination-dependent shipping
- free-shipping status
- unavoidable checkout/other costs where exposed
- timestamp/freshness

For each component, evidence must distinguish:

1. **Technical / source availability** — whether the authorized data path actually exposes enough data for that component. This is factual evidence about the provider response/path. It is **not** `CapabilityPolicyState`. Reuse existing technical connector/certification evidence where possible. If `ConnectorCapability` is operation-level rather than field-level, record field exposure in the certification evidence/report rather than treating policy state as technical availability.
2. **Contractual / policy authorization** — whether PiqSavi is permitted to ingest, use, display, transform, or compare that field for the provider/market. Continue using only the existing Sprint 31 policy states: `allowed` / `restricted` / `prohibited` / `unknown`. Do not invent a second authorization system.
3. **Offer / shopper applicability** — even when a discount/voucher field is technically exposed and policy-allowed, it may reduce effective purchase cost only when evidence establishes applicability to the evaluated offer under the known shopper context.

Preserved distinctions: field present ≠ permitted to use; permitted to use ≠ field actually available; voucher available ≠ voucher applicable to this shopper/offer. All required conditions must be satisfied before a component can influence scored effective purchase cost. Provider approval and affiliate approval do not imply technical exposure or policy permission. Do not require a merchant to expose fields it does not provide; record the limitation honestly.

### 2026-09-18 public-web discovery evaluation (does not close this sprint)

PiqSavi may evaluate a legitimate public-web search/retrieval provider as a **discovery** path. That is not a Shopee, Lazada, or merchant API. The search provider is not the merchant. Search snippets are not canonical prices.

Architecture decision: **B** — a narrow Sprint 32 adapter/certification extension. Existing `ResearchProviderRegistry`, certification evidence, `CapabilityPolicyState`, `plan_authorized_research()`, provenance, and canonical offer economics are reused. No parallel registry/router. Sprint 38 still owns live execution.

Public-web `PRODUCT_DISCOVERY` may later be planned when certified. `CURRENT_PRICING` / scored offers still require Level A or Level B evidence (or Level C only if Sprint 32 policy later explicitly permits it). Level D snippets stay discovery-only.

This slice is a **public-web discovery foundation**. It is **not** the real shopping-offer path required to close Sprint 32. A successful Brave/Tavily search benchmark only proves discovery usefulness. Sprint 32 still needs a legitimate route capable of establishing stronger Level A/B offer evidence, including attributable current price/freshness, before offers may enter the canonical evaluated set.

This slice does **not** scrape merchants, does **not** buy API plans, does **not** store credentials, and does **not** certify Brave, Tavily, or Exa. Live benchmark requires owner-supplied credentials. Brave `country=PH` is not sent because PH membership in the published `country` enum is unverified; PH intent stays in the query text. See [`../evidence/SPRINT_32_PUBLIC_WEB_PROVIDER_EVALUATION.md`](../evidence/SPRINT_32_PUBLIC_WEB_PROVIDER_EVALUATION.md) and [`../../architecture/SPRINT_32_PUBLIC_WEB_DISCOVERY_PATH.md`](../../architecture/SPRINT_32_PUBLIC_WEB_DISCOVERY_PATH.md).

### 2026-09-18 Tavily Extract technical harness (does not close this sprint)

A private-local Tavily Extract harness now exists so the owner can test whether official Extract can retrieve enough current, attributable page content from direct PH retailer/product URLs to create **technical** Level-B candidates.

This does **not** certify Tavily. It does **not** certify any retailer. Technical Level-B candidate ≠ offer evidence. Source-site policy stays unknown and blocks evaluated-set promotion. PiqSavi still must not fetch merchant pages. Live mode may call only the official Tavily Extract API, `extract_depth=basic`, max 15 URLs. Advanced extraction is a later explicit owner action. Live artifacts stay in `/tmp` and must not be committed. Sprint 32 remains open.

### 2026-09-18 PH source-rights / licensed-data path audit (does not close this sprint)

A first-party rights audit of PH retailers, marketplaces, affiliate/product-feed programs, manufacturer shops, and licensed catalog APIs initially conflated Shopify Global Catalog with Shop.app personal skill, merchant Admin APIs, public storefront pages, and persistent product indexes. Reassessment of official Shopify Global Catalog docs plus API Terms records **Outcome A**: Global Catalog is a **rights survivor** for a restricted query-time commercial comparison path. This is **not** production certification. Actual PH coverage is unverified. Unauthorized public-page reuse is not accepted.

S-1 architecture is PiqSavi → Shopify Global Catalog (no Tavily on this path). Individual retailer permission, including Power Mac Center, is **not** required for Global Catalog. PMC Storefront Catalog remains an optional separate owner-action path. Shop.app personal-agent skill stays prohibited for commercial aggregators and does not disqualify Global Catalog. Promoted placement stays off initially.

This audit performed no signup, application, email, payment, credential creation, merchant API call, Shopify live catalog call, scrape, or environment mutation. See [`../evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md`](../evidence/SPRINT_32_PH_SOURCE_RIGHTS_AUDIT_2026-09-18.md). Sprint 32 remains open.

### 2026-09-18 Shopify Global Catalog PH coverage probe harness (does not close this sprint)

A private-local Anonymous technical harness now exists so the owner can test whether Shopify Global Catalog returns genuinely useful Philippine shopping offers under documented PH localization (`ships_to.country=PH`, `context.address_country=PH`, `context.currency=PHP`, `view=offer` on search).

This does **not** certify Shopify. It does **not** host a PiqSavi UCP profile. The Shopify-hosted agent-profile fixture is **TECHNICAL TEST ONLY**. Live mode may call only `https://catalog.shopify.com/api/ucp/mcp`, at most 12 `search_catalog` queries and 5 `get_product` validations, first page only, no bulk lookup, no crawl, no product index, no promoted placement. Live artifacts stay in `/tmp/piqsavi-shopify-global-ph` and must not be committed. This Cursor agent does **not** run the live catalog call. See [`../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md`](../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md). Sprint 32 remains open.

### 2026-09-18 owner live Shopify Global Catalog PH coverage probe (does not close this sprint)

Owner-supplied live evidence after PR #149 recorded **PASSED TECHNICAL COVERAGE TEST** for the controlled 12-query first-page PH search probe: 12/12 `USEFUL_PH_OFFER`, 120 products / 122 offers, Anonymous, no credentials, no scraping, no pagination, no bulk lookup, no raw persistence. Mixed returned currencies despite PHP context. `get_product` validations in that run were concentrated in one query because of the previous selector; they are not representative cross-category evidence. Production provider/certification registries remain empty. Sprint 38 remains unstarted. See [`../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md`](../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md). Sprint 32 remains open.

### 2026-09-18 owner live diversified get_product validation (does not close this sprint)

After PR #150 merged, the owner reran the controlled Anonymous PH probe. Result: **PH LIVE TECHNICAL COVERAGE VALIDATED**. 12/12 categories remained `USEFUL_PH_OFFER`. Five `get_product` validations succeeded across five distinct categories (wireless earbuds, gaming laptop, mechanical keyboard, USB-C charger, phone case). Second-run totals: 120 products / 130 offer records (additional offers are compatible with multi-variant products, not 130 distinct products). This is **not** production certification. A production PiqSavi agent profile, Sprint 31 policy rows, and remaining certification gates are still required. Production provider/certification registries remain empty. Sprint 38 remains unstarted. See [`../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md`](../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md). Sprint 32 remains open.

### 2026-09-18 PiqSavi UCP agent-profile foundation (does not close this sprint)

PiqSavi now has its own least-privilege UCP agent-profile JSON, served from the existing FastAPI public application at `GET /ucp/agent-profiles/2026-08-25/piqsavi.json`.

**PIQSAVI UCP AGENT PROFILE: IMPLEMENTED LOCALLY — NOT YET DEPLOYED/VALIDATED.**

This slice does **not** deploy. Shopify has **not** fetched the PiqSavi profile. The Shopify-hosted fixture remains the PH probe default (`technical-test-fixture` mode) and is **TECHNICAL TEST ONLY**. Production-intended PiqSavi identity is explicit (`--agent-profile-source piqsavi`) and is not used as the live default. Live `--agent-profile-source piqsavi` is **FAIL CLOSED** while undeployed: zero Shopify/network calls, non-zero exit. Offline fixture mode may still select `piqsavi`. Production provider/certification registries remain empty. Sprint 32 remains open. Sprint 38 remains unstarted. See [`../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md`](../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_PROBE.md).

**Lifecycle states (separate; both currently false; not request/env/browser controlled):**

- `PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED = False` — public HTTPS profile is not deployed and has not been owner-validated. Deployment is **not** Shopify validation.
- `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = False` — Shopify has not fetched or negotiated the PiqSavi profile. Recorded only after a successful live Shopify response against the deployed profile.

Do not conflate those two milestones. `PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED_AND_VALIDATED` is not used.

**Next sequence (not performed in this PR):**

A. Merge this foundation PR.
B. Deploy the FastAPI profile route.
C. Owner verifies the exact public HTTPS profile URL returns the expected JSON.
D. Record PROFILE DEPLOYED / HTTP VALIDATED (`PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED`).
E. Only then unlock a controlled live Shopify call using the PiqSavi profile.
F. Successful Shopify response proves Shopify fetched/accepted the profile (`SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE`).
G. Only after that continue capability-policy / production certification work.

This workspace did not perform B–G. Both lifecycle constants remain false.

### 2026-09-19 staging PiqSavi UCP profile owner-validated (does not close this sprint)

Owner evidence after Deploy Staging run `35430542107` on main SHA `e5654a63fe650fd21c219a24270455f8902519a0` recorded a public HTTP/2 200 for the exact staging profile URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`. Expected JSON was returned (`ucp.version = 2026-08-25`, catalog.search, catalog.lookup, `dev.shopify.catalog.global`). The internal staging route also returned HTTP 200.

This does **not** validate the production URL `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`. Shopify has **not** fetched or negotiated the PiqSavi profile. Production certification remains false.

**Current lifecycle states (environment-specific; not request/env/browser controlled):**

- `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED = True` — exact staging HTTPS profile is deployed and owner-validated. This is **not** Shopify validation.
- `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False` — production HTTPS profile is not owner-validated and must not be unlocked.
- `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = False` — Shopify has not fetched or negotiated the PiqSavi profile. A successful public HTTPS deployment is not Shopify fetch/negotiation.

There is no global `PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED` flag. Live `--agent-profile-source piqsavi` checks `piqsavi_profile_deployed_for_url(exact selected trusted URL)`. Staging may unlock. Production remains **FAIL CLOSED**. Arbitrary URLs fail closed. Shopify technical fixture behavior is unchanged. Evidence source is `piqsavi` and usage is `PIQSAVI_OWNED_PROFILE`; lifecycle booleans remain the source of truth. Staging output must not claim the selected profile is undeployed or production-intended. This workspace did **not** call Shopify, deploy, or mutate AWS. Sprint 32 remains open. Sprint 38 remains unstarted.

**Next sequence (not performed in this PR):**

E. Controlled live Shopify call using only the exact deployed staging PiqSavi profile URL.
F. Successful Shopify response proves Shopify fetched/accepted the profile (`SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE`).
G. Owner-validate the exact production profile URL, then record `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED`.
H. Only after that continue capability-policy / production certification work.

### 2026-09-19 first PiqSavi profile Shopify discovery attempt failed (does not close this sprint)

After Deploy Staging #39 succeeded, the owner revalidated the exact staging profile URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` and received public HTTP/2 200. The reachable profile advertised `dev.shopify.catalog.global`, `dev.ucp.shopping.catalog.lookup`, and `dev.ucp.shopping.catalog.search`.

The owner then performed exactly **one** Shopify Global Catalog request:

- tool: `search_catalog`
- query: `wireless earbuds`
- profile: `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`
- request budget: `search_catalog = 1`, `get_product = 0`, `lookup_catalog = 0`, pagination = 0

Shopify response:

- HTTP 422
- JSON-RPC `error.code = -32001`
- `error.message = "UCP discovery failed"`
- `error.data.code = "profile_malformed"`
- `error.data.content = "Unable to fetch agent profile: Missing services"`

This is **not** successful UCP negotiation. No product result. No `get_product` call. No `lookup_catalog` call. No pagination. No production certification. `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` remains **false**.

PUBLIC PROFILE REACHABLE = yes

SHOPIFY DISCOVERY ATTEMPTED = yes

SUCCESSFUL UCP NEGOTIATION = no

PRODUCTION CERTIFIED = no

| Gate | Result |
|------|--------|
| PUBLIC PROFILE REACHABLE | yes |
| SHOPIFY DISCOVERY ATTEMPTED | yes |
| SUCCESSFUL UCP NEGOTIATION | no |
| PRODUCTION CERTIFIED | no |

Root cause: the then-deployed PiqSavi profile contained `ucp.version` and `ucp.capabilities` but omitted official Shopify/UCP 2026-08-25 agent-profile fields `ucp.services` and `ucp.payment_handlers`. This slice adds exactly `dev.ucp.shopping` (version `2026-08-25`, spec `https://ucp.dev/2026-08-25/specification/overview`, transport `mcp`, schema `https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json`) and `payment_handlers: {}`. Catalog capabilities remain unchanged. Checkout, cart, order, fulfillment, buyer consent, discount, payment, and Shopify storefront catalog remain absent.

**Current lifecycle states (unchanged by this failed attempt):**

- `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED = True` — exact staging HTTPS profile remains deployed and owner-reachable. This is **not** successful Shopify negotiation.
- `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False` — production HTTPS profile is not owner-validated.
- `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = False` — Shopify discovery was attempted and failed. Do not treat HTTP 422 / `profile_malformed` as fetch success.

This workspace did **not** call Shopify, deploy, or mutate AWS. Sprint 32 remains open. Sprint 38 remains unstarted.

**Next sequence (not performed in this PR):**

E2. After this profile-shape fix is merged and staging is redeployed, owner may retry one controlled live Shopify call using only the exact deployed staging PiqSavi profile URL.
F. Successful Shopify response proves Shopify fetched/accepted the profile (`SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE`).
G. Owner-validate the exact production profile URL, then record `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED`.
H. Only after that continue capability-policy / production certification work.

### 2026-09-22 staging PiqSavi profile Shopify negotiation succeeded (does not close this sprint)

This addendum does **not** rewrite earlier snapshots. The 2026-09-19 first Shopify discovery attempt remains historically true: HTTP 422, JSON-RPC `-32001`, `UCP discovery failed`, `profile_malformed`, `Missing services`.

After the official `ucp.services` + `payment_handlers` profile-shape fix, Deploy Staging #40 (`run_id` `35439563878`) on main SHA `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620` succeeded. The owner revalidated the exact public staging URL `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` and confirmed:

- `ucp.version = 2026-08-25`
- `ucp.services.dev.ucp.shopping`: version `2026-08-25`, spec `https://ucp.dev/2026-08-25/specification/overview`, transport `mcp`, schema `https://ucp.dev/2026-08-25/services/shopping/mcp.openrpc.json`
- `ucp.payment_handlers = {}`
- capabilities: `dev.ucp.shopping.catalog.search`, `dev.ucp.shopping.catalog.lookup`, `dev.shopify.catalog.global`

The owner then performed exactly **one** controlled Shopify Global Catalog retry. This workspace did **not** repeat that request.

- endpoint: `https://catalog.shopify.com/api/ucp/mcp`
- tool: `search_catalog`
- query: `wireless earbuds`
- profile: `https://staging.piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`
- `ships_to.country = PH`
- `available = true`
- `address_country = PH`
- `currency = PHP`
- `language = en`
- `view = offer`
- `pagination.limit = 3`
- User-Agent: `PiqSavi-Sprint32-PH-Coverage-Probe/1.0`
- No authentication
- request budget: `search_catalog = 1`, `get_product = 0`, `lookup_catalog = 0`, pagination followed = 0

Shopify response:

- HTTP 200
- JSON-RPC `jsonrpc = "2.0"`, `id = 2`, `error = null`
- MCP `isError = false`
- `product_count = 3`
- `messages = []`

No second request was made. The raw Shopify product payload is **not** stored.

This is **not** production-profile negotiation, production certification, Shopify partnership, Shopify endorsement, or full Philippine retail coverage.

PUBLIC PROFILE REACHABLE = yes

SHOPIFY DISCOVERY ATTEMPTED = yes

SUCCESSFUL UCP NEGOTIATION = yes

LIVE SEARCH_CATALOG RESPONSE = yes

PRODUCTS RETURNED = 3

PRODUCTION PROFILE DEPLOYED = no

PRODUCTION CERTIFIED = no

SPRINT 32 COMPLETE = no

SPRINT 38 STARTED = no

**Current lifecycle states (environment-specific; not request/env/browser controlled):**

- `PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED = True` — exact staging HTTPS profile remains deployed and owner-reachable.
- `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False` — production HTTPS profile is not owner-validated.
- `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = True` — recorded after the successful live Shopify retry against the deployed staging profile.

`piqsavi_profile_is_shopify_negotiated()` is now **True** because the fetch milestone is true and at least one trusted PiqSavi environment is deployed. There is no global `PIQSAVI_UCP_AGENT_PROFILE_DEPLOYED` flag. Production live `--agent-profile-source piqsavi` remains **FAIL CLOSED**. Arbitrary URLs fail closed. Shopify technical fixture behavior is unchanged. This workspace did **not** call Shopify, deploy, or mutate AWS. Sprint 32 remains open. Sprint 38 remains unstarted.

**Next sequence recorded on 2026-09-22 (historical for that slice; superseded below):**

G. Owner-validate the exact production profile URL, then record `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED`.
H. Only after that continue capability-policy / production certification work.

### 2026-09-23 production profile HTTP 404 and Sprint 41 sequencing (does not close this sprint)

This addendum does **not** rewrite earlier snapshots. The owner performed a read-only HTTPS check of the exact production profile URL `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json`.

Result: HTTP/2 404. `content-type = application/json`. No deployment or mutation was performed.

PRODUCTION PROFILE URL CHECKED = yes

PRODUCTION PROFILE HTTP STATUS = 404

PRODUCTION PROFILE DEPLOYED = no

PRODUCTION PROFILE VALIDATED = no

PRODUCTION PROFILE NEGOTIATED = no

PRODUCTION CERTIFIED = no

AWS MUTATION = no

DEPLOYMENT = no

SHOPIFY CALL = no

`PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` remains **False**. Do not mark the production profile deployed, validated, negotiated, or production certified. The exact production URL remains **FAIL CLOSED**.

The master roadmap assigns production AWS/environment provisioning, the production deploy path, and production deploy/rollback validation to **Sprint 41**. Sprint 32 must **not** force an early production deployment merely to make the production UCP profile reachable.

Production profile deployment belongs to the later Sprint 41 production environment/deployment path and is not being pulled forward into Sprint 32.

Staging evidence remains available for certification preparation:

- PH technical search coverage: 12/12 useful queries
- Diversified `get_product`: 5/5 across five categories
- PiqSavi staging profile: deployed and owner HTTPS-validated
- Shopify staging negotiation: successful
- Controlled retry: HTTP 200, `error = null`, `isError = false`, `product_count = 3`
- `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = True`

That staging/live technical evidence does **not** certify production.

**Operative sequence (supersedes the 2026-09-22 items G and H for current work):**

G. Record this production-profile HTTP 404 truthfully. Keep `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False`.
H. Defer production-profile deployment and production HTTPS validation to Sprint 41. Do not pull that deploy into Sprint 32.
I. Continue Sprint 32 provider capability-policy and certification preparation on the existing Sprint 31 model, using legitimate staging and live technical evidence.
J. Keep final production validation and production certification incomplete until later production gates, including Sprint 41, are satisfied.

Sprint 32 acceptance criteria are unchanged. Sprint 32 is **not complete**. Sprint 38 remains unstarted. Sprint 41 implementation is not started.

### 2026-09-23 Shopify canonical normalization, variant identity, and reliability validation (does not close this sprint)

This slice adds an in-process Shopify Global Catalog normalization adapter. It accepts already validated in-memory product and variant structures. It does not perform HTTP. It does not persist the raw Shopify response. It does not create a Shopify product index.

Existing architecture reused, and not replaced:

- Sprint 18 `RuleBasedProductParser` and `ExactVariantProductMatcher`
- `CanonicalMoneyLine` and `CanonicalOfferEconomics` integer `amount_minor`
- Sprint 18 `DataProvenance`, `DataFreshness`, and `evaluate_freshness`
- Sprint 31 `ResearchProviderDescriptor.is_operationally_available`, `KillSwitch`, `CircuitBreakerSnapshot`, `ConnectorOperationalStatus`, timeout/retry/backoff policies, and typed failure results

Recorded behavior:

- Shopify `product.id` and `variant.id` stay distinct. Parser output does not overwrite them. A different non-empty variant id is not merged because titles are similar.
- Listing `price.amount` stays an integer minor-unit amount. It is not round-tripped through binary float and it is not rescaled for an assumed two-digit currency exponent.
- The currency Shopify returned is preserved. PH/PHP query context does not rewrite another returned currency. Mixed currencies stay mixed.
- Unknown shipping, tax, duty, import charge, voucher, seller discount, platform discount, and checkout cost stay unknown. Unknown shipping and tax are not zero. An unknown voucher does not reduce price. The canonical price state is `price_before_shipping`, not `final_effective_cost`.
- `checked_at` is the time PiqSavi queried Shopify. A provider freshness timestamp is recorded only when the validated structure actually contains `source_timestamp`. This slice does not fabricate that timestamp from the local clock. Retained shopper-facing freshness remains not established, matching the capability-policy map. Fixture and synthetic observations are not labeled live.
- Kill-switch, open-circuit, DISABLED, and UNAVAILABLE behavior is validated synthetically against the existing Sprint 31 operational predicate. Browser, request, and shopper input cannot disengage a server-owned kill switch. Those tests are engineering behavior. They are not live operational evidence and they do not certify Shopify.
- Operational kill-switch closure remains incomplete. No production provider is registered, and no deployed Shopify path was exercised by this workspace.
- An owner-run harness exists at `scripts/shopify_global_catalog_normalization_validation.py`. This workspace did not execute it. The harness allows at most 5 `search_catalog` calls and 5 `get_product` calls, prohibits `lookup_catalog` and pagination, and may later call only `https://catalog.shopify.com/api/ucp/mcp` with the exact deployed staging PiqSavi profile. It keeps Shopify payloads in memory and writes a minimized summary only.

This workspace did not call Shopify, deploy, or mutate AWS. No production certification was created. No production routing policy was created.

Production provider registry remains 0. Production certification catalog remains 0. Production evidence catalog remains 4. Production routing catalog remains 0.

The next trusted production certification slice still requires a real non-fixture `ResearchProviderDescriptor` in the production provider registry. `ResearchProviderCertificationDecisionService` refuses that production write with `provider_missing` until the descriptor exists. This slice does not register one. The in-memory normalization candidate is explicitly non-authoritative.

Sprint 32 remains open. Sprint 38 remains unstarted. Sprint 41 remains unstarted. Owner live normalization validation is still required.

The capability-policy preparation map is documentary only. It uses existing Sprint 31 states (`allowed` / `restricted` / `prohibited` / `unknown`). It does not create a second policy system and does not populate production provider, certification, or routing registries. Technical exposure is not permission and does not forbid an `allowed` policy. The 2026-09-18 rights audit's query-time uses that are `allowed` with operating limits stay `allowed`; those limits are restrictions, not a conversion to `restricted`. `restricted` remains the state where the audit itself uses that state, including normalization and short-lived retention. `lookup_catalog` is `restricted` because the tool is documented and bulk indexing stays out of bounds; the Sprint 32 probe separately disables it and does not call it. Promoted placement is provider-`unknown` because enrollment is absent, and PiqSavi keeps it disabled. Commission-based organic ranking is a PiqSavi integrity rule, not a Shopify prohibition. Search-result caching, a persistent product index, and AI training without the required consent stay `prohibited`. Discount, voucher, shipping-amount, free-shipping, and checkout-cost permissions remain `unknown`. No documentary row is a production certification. Canonical shopper/offer applicability is not established.

### 2026-09-25 owner live normalization validation attempt #1 (does not close this sprint)

Owner live normalization validation attempt #1 on 2026-09-25:

- Preflight passed.
- The exact staging PiqSavi profile loaded.
- The owner invoked the bounded live normalization harness in AWS CloudShell. AWS CloudShell was only the owner execution environment. Repository cloning and temporary tool installation inside that CloudShell environment are not staging or production infrastructure deployment or mutation.
- Shopify Global Catalog returned HTTP 429.
- The harness failed closed.
- Successful 5/5 normalization validation was not obtained.
- This is not a provider rejection of PiqSavi. The response was a rate limit.
- Production certification remains false.
- Sprint 32 remains open.
- No PiqSavi AWS infrastructure/resource mutation and no deployment.
- No Sprint 38 execution.
- No Sprint 41 execution.

How many Shopify calls completed before the HTTP 429 is not recorded here. Existing evidence does not prove that count. This attempt is not production certification and does not close Sprint 32.

### 2026-09-25 owner live normalization validation attempt #2 (does not close this sprint)

Owner live normalization validation attempt #2 on 2026-09-25, recorded separately from attempt #1:

- AWS CloudShell was only the owner execution environment. The owner ran the exact merged harness from main. Repository cloning and temporary tool installation inside that CloudShell environment are not staging or production infrastructure deployment or mutation.
- Fresh output directory.
- Preflight passed.
- 5 `search_catalog` logical operations were attempted.
- 5 `search_catalog` logical operations completed.
- 1 `get_product` logical operation was attempted.
- 0 `get_product` logical operations completed.
- Shopify Global Catalog returned HTTP 429 on `get_product`.
- JSON-RPC request id 6.
- That 429 was network HTTP request #6.
- Retry-After = 1 second.
- The harness failed closed.
- No automatic retry.
- No raw payload persisted.
- Successful 5/5 normalization validation was not obtained. The five completed search operations are not full certification success. Detail/`get_product` validation did not complete.
- This is rate limiting, not a provider rejection of PiqSavi.
- Production certification remains false.
- Sprint 32 remains open.
- Sprint 38 remains unstarted.
- Sprint 41 remains unstarted.
- No PiqSavi AWS infrastructure/resource mutation and no deployment.
- No Sprint 38 execution.
- No Sprint 41 execution.

### 2026-09-25 owner live normalization validation attempt #3 (does not close this sprint)

Owner live normalization validation attempt #3 on 2026-09-25 succeeded. It is recorded separately from attempts #1 and #2. Non-secret evidence: [`../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_NORMALIZATION_ATTEMPT_3.md`](../evidence/SPRINT_32_SHOPIFY_GLOBAL_CATALOG_PH_NORMALIZATION_ATTEMPT_3.md).

- Owner execution. This workspace did not run the live harness.
- AWS CloudShell was the execution environment only. Repository cloning and temporary tool installation inside that CloudShell environment are not staging or production infrastructure deployment or mutation.
- Exact merged main: `5022c2ddac80d202db371d1e0e4fa26252e0c397`.
- Exact deployed staging PiqSavi profile. `agent_profile_source = piqsavi`. `staging_profile_exact_url_classification = exact_deployed_staging`. Market = PH.
- Preflight passed.
- Pacing = PiqSavi conservative 1.25-second cadence. `minimum_request_interval_seconds = 1.25`. `pacing_sleep_count = 9`. Total pacing sleep was approximately 9.1589 seconds.
- 5 `search_catalog` completed.
- 5 `get_product` completed.
- 0 `lookup_catalog`.
- Pagination was not followed. Pagination metadata was observed.
- All five categories normalized successfully: wireless earbuds, gaming laptop, mechanical keyboard, USB-C charger, phone case.
- 5 distinct selected product identities stayed stable from search to detail.
- 5 search variant identities were confirmed in detail.
- Detail exposed 9 variant identities total.
- 14 normalized offers preserved integer minor-unit pricing.
- Returned currencies PHP and USD were preserved. `currencies_observed_count = 2`.
- 14 seller identities were present.
- 14 availability results were non-unknown. `availability_unknown_count = 0`. `availability_normalized_count = 14`.
- 8 different-variant conflicts were correctly held apart.
- 5 comparisons remained ambiguous or insufficient and were not declared exact. That count is fail-closed integrity, not failed normalization.
- Shipping, tax, and voucher fabricated counts are 0.
- Raw payload persistence is false. No persistent Shopify product index.
- Source identity digests stay in the owner summary. They are not reconstructed here. Raw Shopify product and variant IDs are not stored.
- `canonical_parsing_attempted_count = 14`. `exact_variant_comparisons_count = 13`.
- Generated `2026-09-25T04:34:35.325772+00:00`.
- `owner_live_validation = true`. `cursor_executed_live_harness = false`.
- Production certification was false at the time of the owner run.
- Sprint 38 was not started. Sprint 41 was not started.
- LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED for the exact reduced Shopify Global Catalog path.
- This attempt does not close Sprint 32 and does not make the path production-deployment ready.

### Closure blockers (current)

- Provider identity `ph-shopify-global-catalog` is registered and operationally DISABLED. Execution remains unavailable. Registration is not permission to execute.
- Trusted reduced-capability certification exists for PRODUCT_DISCOVERY, OFFER_DISCOVERY, CURRENT_PRICING, and AVAILABILITY only. Certified reduced capability set is not production deployment ready.
- Production profile undeployed
- LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED for the exact reduced Shopify Global Catalog path on owner attempt #3. Attempts #1 and #2 remain historical HTTP 429 fail-closed runs and are not this pass. Ambiguous or insufficient comparisons stayed fail-closed. Unknown shipping, tax, voucher, and checkout costs stay fail-closed.
- Staging certification not yet complete
- Monitoring / public coverage disclosure incomplete
- Kill-switch engineering behavior is validated synthetically against Sprint 31 `ResearchProviderDescriptor.is_operationally_available`: an engaged kill switch, an open circuit breaker, DISABLED, and UNAVAILABLE are unavailable and ineligible, and browser/request/shopper input cannot disengage a server-owned kill switch. Operational kill-switch closure evidence remains incomplete because the registered provider stays DISABLED and no deployed Shopify path was exercised. This is not production-deployment certification.
- Later production validation remains
- Unknown effective-cost components remain excluded and fail-closed
- Shopify Global Catalog Anonymous catalog mode does not require a separate application, separate provider preapproval, or merchant/API credentials. That fact does not make the path production-ready or production-certified.
- Current-data technical coverage validation exists for Shopify Global Catalog, but production operational validation/certification is incomplete.
- EXT-01 remains `applied` for the 2026-09-08 Shopee and Lazada product-data requests. That is **not** provider approval, credentials, a feed, or certification, and it is **not** Shopify approval. Shopee and Lazada remain unapproved and unprovisioned. EXT-06 remains `not_started` for paths that require credentials. EXT-06 is **not applicable** to the S-1 Anonymous Shopify Global Catalog path. Lack of credentials must not block that path. Do not mark EXT-06 `provisioned`.
- EXT-07 is `n_a_beta` for September and does not block this sprint's product-data certification purpose
- A submitted email request alone does **not** satisfy Sprint 32. Shopee and Lazada remain **not certified**.
- Owner-observed Shopee dashboard / Affiliate Open API facts are **not** official Sprint 32 certification evidence. The 2026-09-07 Sprint 26 reconciliation recorded those affiliate facts as **not** satisfying EXT-01; the later 2026-09-08 emails satisfy EXT-01 `applied` only.
- Public-web discovery architecture/harness exists and is **not** a certified PH shopping-data path. No owner credentials. No live current-data response. Fixtures cannot close this sprint.
- 2026-09-18 source-rights reassessment: Shopify Global Catalog is a **rights survivor** (Outcome A, restricted query-time comparison). It is **not** production-certified. Owner live 12-query PH search coverage **PH LIVE TECHNICAL COVERAGE VALIDATED** (12/12 `USEFUL_PH_OFFER`; Anonymous; no credentials; no scraping/pagination/bulk lookup). Diversified 5/5 `get_product` validations completed across five distinct categories after PR #150. That is **not** production certification and does **not** close Sprint 32. The staging PiqSavi UCP profile is **STAGING DEPLOYED / OWNER HTTPS-VALIDATED** (`PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED = True`; Deploy Staging run `35430542107`; SHA `e5654a63fe650fd21c219a24270455f8902519a0`; later corrected-profile redeploy Deploy Staging #40, run `35439563878`, SHA `06be0411479c6c5dfba9d8cf94ca8bfc3b3e9620`). The production profile is **NOT validated/deployed** (`PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False`). `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = True` after the later successful staging retry. Live PiqSavi-profile Shopify negotiation may unlock only the exact deployed staging URL and remains fail-closed for production and arbitrary URLs. This is **not** production-profile negotiation or production certification. Sprint 31 policy rows and remaining certification gates are still required. Sprint 38 remains unstarted.
- 2026-09-19 owner first PiqSavi-profile Shopify discovery attempt failed after Deploy Staging #39: staging profile publicly reachable HTTP/2 200; one `search_catalog` (`wireless earbuds`); Shopify returned HTTP 422, JSON-RPC `-32001`, `UCP discovery failed`, `profile_malformed`, `Missing services`. No product result. No `get_product`. No `lookup_catalog`. No pagination. PUBLIC PROFILE REACHABLE = yes. SHOPIFY DISCOVERY ATTEMPTED = yes. SUCCESSFUL UCP NEGOTIATION = no. PRODUCTION CERTIFIED = no. `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE` remains false. Sprint 32 remains open. Sprint 38 remains unstarted.
- 2026-09-22 owner controlled Shopify retry after Deploy Staging #40 succeeded: staging profile publicly reachable with official `ucp.services` + `payment_handlers`; one `search_catalog` (`wireless earbuds`); Shopify returned HTTP 200, JSON-RPC `error = null`, MCP `isError = false`, `product_count = 3`. No `get_product`. No `lookup_catalog`. No pagination. No raw product payload stored. PUBLIC PROFILE REACHABLE = yes. SHOPIFY DISCOVERY ATTEMPTED = yes. SUCCESSFUL UCP NEGOTIATION = yes. LIVE SEARCH_CATALOG RESPONSE = yes. PRODUCTS RETURNED = 3. PRODUCTION PROFILE DEPLOYED = no. PRODUCTION CERTIFIED = no. SPRINT 32 COMPLETE = no. SPRINT 38 STARTED = no. `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = True`. Sprint 32 remains open. Sprint 38 remains unstarted.
- 2026-09-23 owner read-only production profile check: `https://piqsavi.com/ucp/agent-profiles/2026-08-25/piqsavi.json` returned HTTP/2 404, `content-type = application/json`. PRODUCTION PROFILE URL CHECKED = yes. PRODUCTION PROFILE HTTP STATUS = 404. PRODUCTION PROFILE DEPLOYED = no. PRODUCTION PROFILE VALIDATED = no. PRODUCTION PROFILE NEGOTIATED = no. PRODUCTION CERTIFIED = no. AWS MUTATION = no. DEPLOYMENT = no. SHOPIFY CALL = no. `PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED` remains False. Production profile deployment belongs to the later Sprint 41 production environment/deployment path and is not being pulled forward into Sprint 32. Capability-policy preparation may continue from staging and live technical evidence. Production registries remain empty. Sprint 32 remains open. Sprint 38 remains unstarted. Sprint 41 remains unstarted.

### Production defaults

Certification records = 4 trusted reduced-capability records for `ph-shopify-global-catalog` / PH / `shopify_global_catalog` (`PRODUCT_DISCOVERY`, `OFFER_DISCOVERY`, `CURRENT_PRICING`, `AVAILABILITY`), version `shopify-global-catalog-ph-2026-09-25-v1`, written only by `ResearchProviderCertificationDecisionService`. Production evidence = 4 Shopify Global Catalog PH rows for the same targets. Evidence date and review date are 2026-09-25. Reviewer is PiqSavi owner / engineering evidence review (not counsel approval). `completeness="recorded"` means capture is complete, not legal sufficiency and not production-deployment readiness. `ResearchProviderCertificationEvidence.restrictions` records only unresolved certification blockers and is empty on these four rows. Permanent allowed-mode operating conditions stay on the capability-policy map, the evidence notes, and attribution requirements. Providers = 1, operationally DISABLED, non-fixture. Routing policies = 0. `SHIPPING`, `TAXES_IMPORT`, and `PROMOTION_EVIDENCE` remain uncertified and unknown. Documentary PH merchant evidence records = 15 (incomplete; not loaded by production factories). Documentary PH public-web evidence records = 3 (incomplete; not loaded by production factories). Certified reduced capability set is not production deployment ready.

### Shopify Anonymous Global Catalog access stage (current)

Application required: N/A for documented Anonymous catalog mode.

Provider preapproval required: N/A for ordinary documented Anonymous catalog tools.

Credentials: N/A / not required for Anonymous catalog mode.

Agent profile: required.

Staging profile: validated.

Live technical connection: validated.

PH technical coverage: validated.

Capability-policy evidence: recorded/prepared.

Production profile: not deployed.

Production provider: registered, operationally disabled.

Executable production certification: none.

Routing: none.

Production certified: NO. Four trusted reduced-capability records are not production-deployment certification.

Sprint 32: OPEN.

Sprint 38: UNSTARTED.

Sprint 41: UNSTARTED.

Canonical normalization adapter: implemented in-process. LIVE MARKET-SPECIFIC NORMALIZATION VALIDATION = PASSED on owner attempt #3. Attempts #1 and #2 failed closed on HTTP 429 and remain historical. Kill-switch operational closure: incomplete. Certified reduced capability set is not production deployment ready.

Do not call this path production ready.

## Objective

Certify at least one real, legally usable, operationally validated merchant-data path for the Philippines.

## Included requirements

- Full market path: provider selection, access application, legal/terms, credentials, sandbox (where available), real endpoint, mapping, matching, rate/quota/timeout/retry, failure modes, circuit-breaker hooks, provenance/freshness, shipping/availability, affiliate validation, monitoring, staging, limited rollout, production validation prep, public disclosure row
- Implement and validate Sprint 31 minimum reliability contracts on the PH real path (timeout, bounded retry, backoff, quota/credential/partial-failure types, health, kill switch, breaker baseline)
- Populate and certify Sprint 31 merchant contractual capability/policy metadata for the PH real path (provider/market-scoped; fail-closed when unknown), and separately record effective-cost technical field exposure plus offer/shopper applicability evidence as listed in the 2026-09-06 owner lock

### Merchant capability / authorization evidence (shared bar for 32–36)

Each real merchant/provider path used for certification must record non-secret operational facts for:

- provider identity
- market
- relevant program / agreement / API policy identifier
- review / evidence date
- capability policy (conceptual states: allowed / restricted / prohibited / unknown — final names per Sprint 31 design)
- restrictions and applicable TTL / freshness requirements
- attribution / disclosure requirements where relevant
- evidence source / reference
- enforcement validation against the Sprint 31 harness

Certification stages must remain distinct (do not collapse):

1. application submitted
2. provider approved
3. credentials issued
4. technical connection works
5. capabilities legally/contractually usable (evidence-backed; not inferred from approval alone)
6. production certified

That sequence is valid for a provider path that actually requires application, approval, or credentials. It must not invent those stages for an official access path whose documented catalog mode does not require them. For the documented Shopify Global Catalog Anonymous catalog mode, separate application is not required, separate provider preapproval is not documented for ordinary catalog tools, and merchant/API credentials are not required. An agent profile is required. Signed and Token tiers are optional stronger identification modes and are not required to prove Anonymous catalog-tool access. Promoted placement is a different path: not enrolled, disabled, and policy unknown. This wording does not record a Shopify partnership, endorsement, special approval, preferred-developer status, or production-app approval. Staging technical validation is not production certification.

**Rules:**

- Provider approval does **not** automatically authorize every capability.
- Affiliate permission and product-data permission are independent.
- Unknown / unverified permissions fail closed and do not enable production features.
- Sensitive/high-risk uses (reviews; AI reuse; ambiguous comparison rights; caching beyond explicit documentation; material transformation) remain unknown/restricted unless suitable evidence exists.
- Engineering interpretation ≠ professional legal approval; contested items need stronger evidence/counsel confirmation.
- Do not store privileged legal advice in Git.
- Reduced capability modes are allowed when explicitly certified (e.g. data/compare without affiliate; affiliate destination without current-data comparison). Affiliate-only paths cannot independently satisfy EC-09 market naming.
- **Fixtures, mocks, imported samples, or simulations cannot satisfy production merchant capability certification.**

## Explicit non-goals

- US/SG/UK/CA certification
- Claiming complete PH retail coverage
- Treating Shopee and Lazada as the exclusive search/recommendation universe
- Treating Shopee/Lazada affiliate approval as a Sprint 32 or Sprint 45 launch blocker
- Falsely marking Shopee, Lazada, TikTok Shop, or any other PH source as live, approved, production-ready, or certified
- Making TikTok Shop PH launch-critical for September 2026
- Destructively removing affiliate services, attribution models, neutrality tests, or provider/network support
- Cross-connector production hardening suite (38)
- Owning the shared capability/policy contract design (Sprint 31)
- Creating a second price model or a parallel authorization model for effective-cost fields
- Treating `CapabilityPolicyState` as technical field availability, or treating field presence as permission or shopper/offer applicability
- Implying that merchant neutrality requires querying every integrated merchant on every request

## External dependencies

- EXT-01 (PH product-data access — launch-critical)
- EXT-06 (PH credentials when a path is approved)
- EXT-07 is **not** required for September (`n_a_beta` / post-beta)

## Implementation deliverables

- PH connector/feed integration on unified platform

## Documentation deliverables

- PH coverage row
- Provider status notes
- Certification report including capability-policy evidence map (non-secret)
- 32.1 PH source certification inventory (foundational; does not close this sprint)

## Required tests

- Certification suite against real/sandbox
- Failure injection using Sprint 31 contracts
- Freshness label tests
- Capability-policy enforcement validation (unknown/prohibited fail closed; reduced modes behave as declared)

## Required staging evidence

- Real current-data response evidenced

## Required production evidence

- Prod validation may complete in 45 if dry-run in 41/44

## Acceptance criteria

- At least one real, legally usable merchant path with current-data validation
- Market-specific normalization and product/variant matching evidenced
- Sprint 31 contractual capability/policy metadata populated, evidence-backed, and enforcement-validated for that path (fail-closed for unknown)
- Effective-cost components recorded with technical field exposure, policy authorization, and applicability distinguished; policy states remain `allowed` / `restricted` / `prohibited` / `unknown`
- Certification report distinguishes application / approval / credentials / technical connectivity / contractual usability / production certification
- Shopee / Lazada / any other PH source remain uncertified until the production-certification stage is actually met
- Staging certification complete; limited production validation prepared/executed as required by gate
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**
- PH may be named only after this gate + claims approval
- Each named market requires a legitimate authorized access path whose actual access requirements are satisfied, plus current-data evidence, capability-policy evidence, a truthful coverage definition, and staging/limited production proof where required. Where the selected path requires provider approval, provisioning, or credentials, those stages must be satisfied. Where official provider documentation establishes a public/keyless/anonymous mode with no separate credential or preapproval requirement, that documented mode satisfies the access stage and the remaining certification evidence is still required. This exception applies only to the actual documented path and does not weaken Shopee, Lazada, or other credential-required providers.
- Failure of PH certification delays/removes PH shopping claims; it does not authorize substituting US/SG/UK/CA as the September beta unless the owner later expands supported markets
- Sprint 45 does not require US/SG/UK/CA for September

## Predecessor sprints

31 (unification + minimum reliability contracts + capability/policy model) — **strict**; formally owner-closed before this sprint began. 32.1–32.5 do not reopen Sprint 31 contracts.

## Parallelizable work

33–36 (after 31)

## Go / no-go gate

Go for PH naming iff AC met; else remove PH from supported list

## Rollback or contingency

Disable PH merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
