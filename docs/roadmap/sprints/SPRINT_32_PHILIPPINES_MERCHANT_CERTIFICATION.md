# Sprint 32 — Philippines Merchant Certification

**Status:** In progress — blocked on external certification. Internal foundation slices 32.1–32.5 are complete. Sprint 32 is **not complete**.
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name PH
**Inventory:** [`../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)

## Authoritative status

Sprint 31 was formally owner-closed before Sprint 32 implementation began. 32.1–32.5 build the trusted certification architecture. They do **not** close Sprint 32.

| Area | Status |
|------|--------|
| Sprint 31 architecture | closed |
| 32.1 evidence contracts | complete |
| 32.2 trusted decision path | complete |
| 32.3 PH documentary evidence | complete |
| 32.4 hardening | complete |
| 32.5 reconciliation / validation | complete |
| Real PH product-data path | blocked |
| Production provider | none |
| Production certification | none |
| Live current-data validation | none |
| Sprint 32 closure | blocked |

The trusted Philippines certification architecture is built and validated. PiqSavi still has **no** real production-certified Philippines merchant-data path. Do not claim PH support, PH certification, live Shopee research, live Lazada research, or production-ready merchant integration.

### 2026-09-06 owner lock (documentation only; does not close this sprint)

Philippines is the **initial commercial/product validation focus** for the September 2026 beta. That is a market-priority decision, not a restriction that PiqSavi may only ever search two marketplaces, and not a change to the existing rule that PH certification failure removes/delays PH only.

**Initial affiliate-monetization targets** for the September PH beta:

- Shopee Philippines
- Lazada Philippines

Use affiliate links for those merchants where affiliate approval/tracking is available and legally permitted. This does **not** make Shopee or Lazada the exclusive search/recommendation universe, and it does **not** grant ranking privileges. Existing Sprint 32 truth remains authoritative:

- no PH merchant may be called certified unless real evidence supports it;
- product-data rights and affiliate rights remain separate;
- production certification remains evidence-based;
- do not falsely mark Shopee or Lazada as live, approved, production-ready, or contractually usable until actual certification is complete.

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

### Closure blockers (current)

- No merchant has a real approved product-data / API path
- No real production provider
- No current-data operational validation
- No trusted production certification
- Staging certification incomplete
- Monitoring / public coverage disclosure incomplete
- Kill-switch closure evidence incomplete as required
- EXT-01 / EXT-06 / EXT-07 remain unresolved on the authoritative register
- Owner-observed Shopee dashboard / Affiliate Open API facts are **not** official Sprint 32 evidence until separately reconciled into Sprint 26 on `main`

### Production defaults

Certification records = 0. Production evidence = 0. Providers = 0. Routing policies = 0. Documentary PH evidence records = 15 (incomplete; not loaded by production factories).

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
- Falsely marking Shopee, Lazada, TikTok Shop, or any other PH source as live, approved, production-ready, or certified
- Making TikTok Shop PH launch-critical for September 2026
- Cross-connector production hardening suite (38)
- Owning the shared capability/policy contract design (Sprint 31)
- Creating a second price model or a parallel authorization model for effective-cost fields
- Treating `CapabilityPolicyState` as technical field availability, or treating field presence as permission or shopper/offer applicability
- Implying that merchant neutrality requires querying every integrated merchant on every request

## External dependencies

- EXT-01
- EXT-06
- EXT-07

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
- Failure of PH certification removes/delays PH only; it does not necessarily delay Sprint 45 if another certified useful market exists
- Sprint 45 does not require all five planned markets

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
