# Sprint 32 — Philippines Merchant Certification

**Status:** In progress — blocked on external certification. Internal foundation slices 32.1–32.6 are complete. Sprint 32 is **not complete**.
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
| Real PH product-data path | blocked |
| Production provider | none |
| Production certification | none |
| Live current-data validation | technical coverage exists for Shopify Global Catalog; production operational validation/certification incomplete |
| Sprint 32 closure | blocked |

The trusted Philippines certification architecture is built and validated. PiqSavi still has **no** real production-certified Philippines merchant-data path. Do not claim PH support, PH certification, live Shopee research, live Lazada research, or production-ready merchant integration.

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

### Closure blockers (current)

- No merchant has a real approved product-data / API path
- No real production provider
- Current-data technical coverage validation exists for Shopify Global Catalog, but production operational validation/certification is incomplete.
- No trusted production certification
- Staging certification incomplete
- Monitoring / public coverage disclosure incomplete
- Kill-switch closure evidence incomplete as required
- EXT-01 is now `applied` (2026-09-08 PH product-data requests). That is **not** provider approval, credentials, a feed, or certification. EXT-06 remains `not_started`.
- EXT-07 is `n_a_beta` for September and does not block this sprint's product-data certification purpose
- A submitted email request alone does **not** satisfy Sprint 32. Shopee and Lazada remain **not certified**.
- Owner-observed Shopee dashboard / Affiliate Open API facts are **not** official Sprint 32 certification evidence. The 2026-09-07 Sprint 26 reconciliation recorded those affiliate facts as **not** satisfying EXT-01; the later 2026-09-08 emails satisfy EXT-01 `applied` only.
- Public-web discovery architecture/harness exists and is **not** a certified PH shopping-data path. No owner credentials. No live current-data response. Fixtures cannot close this sprint.
- 2026-09-18 source-rights reassessment: Shopify Global Catalog is a **rights survivor** (Outcome A, restricted query-time comparison). It is **not** production-certified. Owner live 12-query PH search coverage **PH LIVE TECHNICAL COVERAGE VALIDATED** (12/12 `USEFUL_PH_OFFER`; Anonymous; no credentials; no scraping/pagination/bulk lookup). Diversified 5/5 `get_product` validations completed across five distinct categories after PR #150. That is **not** production certification and does **not** close Sprint 32. The staging PiqSavi UCP profile is **STAGING DEPLOYED / OWNER HTTPS-VALIDATED** (`PIQSAVI_UCP_AGENT_PROFILE_STAGING_DEPLOYED = True`; Deploy Staging run `35430542107`; SHA `e5654a63fe650fd21c219a24270455f8902519a0`). The production profile is **NOT validated/deployed** (`PIQSAVI_UCP_AGENT_PROFILE_PRODUCTION_DEPLOYED = False`). `SHOPIFY_HAS_FETCHED_PIQSAVI_PROFILE = False`. Live PiqSavi-profile Shopify negotiation may unlock only the exact deployed staging URL and remains fail-closed for production and arbitrary URLs. Shopify-fetch validation is a later, separate milestone. Sprint 31 policy rows and remaining certification gates are still required. Sprint 38 remains unstarted.

### Production defaults

Certification records = 0. Production evidence = 0. Providers = 0. Routing policies = 0. Documentary PH merchant evidence records = 15 (incomplete; not loaded by production factories). Documentary PH public-web evidence records = 3 (incomplete; not loaded by production factories).

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
- Each named market requires: at least one legally usable real source path; current-data evidence; capability-policy evidence; credential/provider approval; truthful coverage definition; staging/limited production proof where required
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
