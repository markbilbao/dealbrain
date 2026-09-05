# ADR — Sprint 31 connector unification (Sprint 4 / Sprint 18 dual-run)

**Status:** Accepted. Sprint 31 was formally owner-closed before Sprint 32 implementation began.
**Date:** 2026-08-25 (architecture review recorded); owner-close status reconciled 2026-09-02
**Baseline recorded:** `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` (PR #96 merge)
**Sprint 31 status:** Formally owner-closed. This ADR remains the recorded 2026-08-25 architecture review.
**Sprint 32 status:** In progress (foundation slices). Sprint 32 is **not complete**. Production certified providers remain zero.
**September 15 dual-path disposition:** Recorded 2026-09-05 against official `main` `4a3f64543cfb3affb2ea139409830cb00d501ba0`. Decision: retain intentional dual implementations. Sprint 31 remains formally closed.

This document is the recorded Sprint 31 architecture review for the Sprint 4 / Sprint 18 connector boundary.

**Related:**

- [`ARCHITECTURE_LOCK.md`](ARCHITECTURE_LOCK.md)
- [`SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](SPRINT_31_RESEARCH_EXECUTION_ROUTER.md)
- [`../CONNECTOR_ARCHITECTURE.md`](../CONNECTOR_ARCHITECTURE.md)
- [`../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md`](../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md)
- [`../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
- [`../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)

## Terminology — “4/18”

**“4/18” means Sprint 4 versus Sprint 18.** It does **not** mean “4 completed out of 18 items.”

| Label | Meaning |
|-------|---------|
| Sprint 4 | Query-time search connector path |
| Sprint 18 | Background / current-offer sync connector path |

The architecture also includes Sprint 8 historical collection and Sprint 31 authorized-research planning. Those are intentionally different responsibilities.

## Context

Sprint 31’s title is Merchant Platform Unification (P1-1A). The merged research execution router (PR #96) established the certified planning contract. It did **not** retire the Sprint 4 search path or the Sprint 18 sync path.

The master roadmap allows either retiring the 4/18 dual-path **or** documenting dual-run. The critical-path fallback requires documented dual-run with a **hard end date**.

Architecture Lock forbids silently taking Sprint 4 search, Sprint 18 current-offer sync, or Sprint 8 historical collection ownership.

## Connector families (current roles)

### Sprint 4 — query-time search

**Abstraction:** `MarketplaceConnector`

**Role:** shopper-request-time listing discovery, product lookup, and listing normalization.

This family must not be assigned background sync, checkpoints, or current-offer freshness ownership.

### Sprint 18 — current-offer / background sync

**Abstraction:** `MarketplaceDataConnector`

**Role:** background / current-offer synchronization, technical `ConnectorCapability` declarations, fetch operations, health, and checkpoint semantics.

This family must not be turned into query-time search.

### Sprint 8 — historical collection

**Abstraction:** `MarketplaceCollector`

**Role:** historical marketplace collection into Price History.

Architecture Lock ownership remains Sprint 8. Do not merge collectors into search, sync, or research planning.

### Sprint 31 — authorized research planning

**Abstraction:** `ResearchProvider`

**Role:** technical provider capability description, certified planning eligibility, and authorized research planning.

This family is **not** live execution. `execute_research_plan(...)` remains unimplemented. Planned ≠ attempted ≠ source checked.

## Decision

**Do not collapse the connector families into one giant implementation or one mega-interface.**

Unification means shared architectural contracts where useful, while implementation responsibilities remain separate.

Shared-contract layer (already started by Sprint 31, extended later only when needed):

- merchant / source identity **conventions** (not a forced common runtime ID in this sprint)
- capability vocabulary (technical adapter capability ≠ contractual/policy authorization)
- market semantics (ISO 3166-1 alpha-2; exact-market certification)
- reliability **result types** (timeout, bounded retry, backoff, quota, credential failure, partial failure, kill-switch, circuit-breaker snapshot)
- certification / policy authority (trusted server catalog)
- routing-policy authority (trusted server catalog)
- provenance / execution-trace **compatibility** (empty trace contract now; Sprint 38 populates)
- adapters only when there is demonstrated duplication or incompatibility

PR #96 did **not** retire Sprint 4 or Sprint 18. Those paths remain a documented **dual-path / dual-run** architecture.

## Three-authority research model (locked)

Do not reopen these decisions.

### Provider capability authority

`ResearchProviderDescriptor` / the technical registry answers what an implementation can do.

Providers do **not** own certification, contractual policy approval, or routing priority.

### Certification authority

The trusted server certification catalog controls exact:

`provider + capability + market + source`

production approval.

A provider cannot self-certify. No matching record means not certified. Production contains **zero** certified real providers.

### Routing authority

The trusted server routing-policy catalog determines ordering among **already eligible** certified providers.

A provider cannot self-prioritize. Commercial / affiliate payout must not determine priority.

## Merchant / source identity guidance

Current identifiers are **family-local** and remain valid internally:

| Family | Identifier |
|--------|------------|
| Sprint 4 search | `marketplace_name` |
| Sprint 18 sync | `connector_id` |
| Sprint 31 research | `provider_id` plus source identities on plans/certifications |

This ADR does **not** implement a shared identifier table.

A future **thin** shared merchant/source identity mapping is appropriate if later work must correlate the same merchant across families. Until then, family-local identifiers stay valid. Do not invent a common ID merely for symmetry.

## Sprint 18 duplicate `connector_id` registration

The Sprint 18 `MarketplaceConnectorRegistry` currently overwrites a duplicate `connector_id`.

This is a **P1 follow-up, not a Sprint 31 closure blocker.** Do not change that registry in the Sprint 31 closure-evidence branch.

The research registry already rejects duplicate `provider_id`. That uniqueness rule stays.

## Dual-run hard end date

Sprint 4 and Sprint 18 remain in documented dual-run.

# Hard architecture-review deadline: September 15, 2026

By **September 15, 2026**, the team must have one of:

1. formally approved thin shared adapters / identity contracts, with dual implementations retained **intentionally**; or
2. an evidence-backed retirement / migration plan for one duplicated path **only where** duplication is genuinely unnecessary.

This deadline is a **decision / architecture disposition** deadline. It does **not** require:

- rewriting all connectors by that date
- finishing live research
- completing Sprints 32–38
- forcing search and sync into one implementation

The launch gate remains Sprint 45, no later than September 30, 2026.

## Architecture review record

The Sprint 31 closure review accepts:

- separate search / sync / collection / research implementations
- shared contracts instead of one mega-interface
- certification and routing authority remain server-controlled
- affiliate economics remain downstream of organic selection, scoring, eligibility, and routing
- future adapters may be introduced only when there is demonstrated duplication or incompatibility

### Decision

Retain four connector families. Unify through contracts and catalogs, not one port.

### Rationale

Search, sync, historical collection, and authorized-research planning have different callers, freshness models, and failure modes. Collapsing them would silently redistribute Architecture Lock ownership and create a false “one connector” claim. Shared certification, routing, reliability types, and market/source exactness already give Sprints 32–36 a stable contract.

### Alternatives considered

| Alternative | Outcome |
|-------------|---------|
| One giant `MerchantConnector` for search + sync + collection + research | Rejected. Violates Architecture Lock and over-unifies distinct jobs. |
| Retire Sprint 4 or Sprint 18 immediately | Rejected. No evidence that either path is unused or safely replaceable. |
| Leave dual-run undocumented / undated | Rejected. Master roadmap requires documented dual-run with a hard date. |
| Shared contracts + documented dual-run + September 15 disposition | **Accepted.** |

### Consequences

- Sprint 31 may close once owner review accepts this evidence plus the onboarding runbook. It must not close by pretending 4/18 are already one runtime.
- Sprints 32–36 certify against the research planning contract. They do not need a mega-interface.
- September 15, 2026 remains the dual-path disposition review. Missing that review is an architecture-control miss, not automatic permission to collapse implementations.

### Follow-up deadline

**September 15, 2026** — dual-path disposition review. **Satisfied** by the recorded review below. Sprint 31 remains formally closed.

### Later-sprint ownership

| Work | Owner |
|------|-------|
| Country / merchant certification evidence; first planned market Philippines | Sprints 32–36 |
| MarketContext, currency, destination-sensitive behavior | Sprint 37 |
| Live execution, runtime reliability, retries / circuit breakers, truthful degradation, populated traces | Sprint 38 |
| Sprint 18 duplicate `connector_id` reject-on-register | P1; not a 31 closer; not implemented in the 2026-09-05 disposition branch |
| Optional thin identity mapping / adapters | Reviewed 2026-09-05; no demonstrated need; not implemented |

## What this ADR does not claim

Recorded 2026-08-25 as closure evidence, not as the owner close itself. Formal owner close has since been recorded. This ADR still does not claim:

- Sprint 32 is complete
- Any production provider is certified (count remains **zero**)
- Live research execution exists
- Search and sync share one runtime path today
- Affiliate payout may influence certification, eligibility, routing, PiqScore, or Recommendation

## Sprint 31 evidence posture

Merged engineering on the recorded baseline:

- planning-only research execution router
- technical provider registry
- trusted certification catalog (production empty)
- trusted routing-policy catalog (production empty)
- exported reliability contract types
- fail-closed authorization-before-planning

This ADR plus [`../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../runbooks/MERCHANT_PROVIDER_ONBOARDING.md) completed the two remaining Sprint 31 P0 documentation / evidence items. Formal owner close has since been recorded. Sprint 32 is now in progress and is **not complete**.

# September 15 Dual-Path Disposition Review

**Status:** Recorded. September 15 obligation **satisfied**.
**Review date:** 2026-09-05 (no later than 2026-09-15)
**Official `main` baseline inspected:** `4a3f64543cfb3affb2ea139409830cb00d501ba0` (PR #107 merged)
**Sprint 31 status after this review:** **SPRINT 31 — FORMALLY CLOSED**. This review does not reopen Sprint 31, start Sprint 38, or collapse connector families.

This is a decision / architecture-disposition record. It is **not** a connector rewrite.

## Baseline

Verified before any documentation change:

| Check | Result |
|-------|--------|
| Branch at start | `main` |
| `HEAD` | `4a3f64543cfb3affb2ea139409830cb00d501ba0` |
| `origin/main` | `4a3f64543cfb3affb2ea139409830cb00d501ba0` |
| Working tree | clean |

Review work proceeded on dedicated branch `arch/sprint31-sept15-disposition`.

## Repository evidence inspected

Authoritative documents:

- this ADR
- [`../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md`](../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md)
- [`../CONNECTOR_ARCHITECTURE.md`](../CONNECTOR_ARCHITECTURE.md)
- [`ARCHITECTURE_LOCK.md`](ARCHITECTURE_LOCK.md)
- [`SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](SPRINT_31_RESEARCH_EXECUTION_ROUTER.md)
- [`ADR_SPRINT_37_MARKETCONTEXT.md`](ADR_SPRINT_37_MARKETCONTEXT.md)
- [`../roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](../roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)

Current runtime evidence (not assumed from older sprint notes):

| Family | Port | Primary implementations | Registry / wiring | Primary callers |
|--------|------|-------------------------|-------------------|-----------------|
| Sprint 4 query-time search | `MarketplaceConnector` (`app/domain/interfaces/marketplace_connector.py`) | `ShopeeConnector`, `LazadaConnector` (`app/intelligence/marketplace/shopee/connector.py`, `lazada/connector.py`) | No registry class. `get_marketplace_connectors()` returns a fixed list (`app/core/dependencies.py`) | `MarketplaceIntelligenceService.search()`; `GET /api/v1/marketplace/search`; `DealRecommendationService.recommend()`; `PriceHistoryService.search_and_record()` |
| Sprint 18 current-offer sync | `MarketplaceDataConnector` (`app/domain/interfaces/marketplace_data_repository.py`) | `FixtureMarketplaceConnector`, `ImportedMarketplaceConnector`, `MockLiveMarketplaceConnector`, `FutureOfficialConnectorStub` | `MarketplaceConnectorRegistry` (`app/marketplace/registry.py`) | `MarketplaceDataService` / `MarketplaceSyncEngine`; `GET/POST /api/v1/marketplaces/*`; optional provenance into DealScore / Shopping Assistant / Alerts when `marketplace_data_enabled` |
| Sprint 8 historical collection | `MarketplaceCollector` (`app/domain/interfaces/marketplace_collector.py`) | `MockShopeeCollector`, `MockLazadaCollector` | No registry class. `get_marketplace_collectors()` returns a fixed list; `MarketplaceCollectionService` keys by `marketplace_name` | `MarketplaceCollectionService`; `CollectionOperationsService`; collection APIs |
| Sprint 31 research planning | `ResearchProvider` Protocol (`app/domain/interfaces/research_provider.py`) | `StaticResearchProvider` (`app/research/providers.py`) | `ResearchProviderRegistry` rejects duplicate `provider_id`; production factory is empty | `plan_authorized_research()`; `plan_authorized_research_if_coverage_allows()`; **no** HTTP research-execution API |

Confirmed production truth on this baseline:

- `production_research_provider_registry()` = 0 providers
- `production_research_provider_certification_catalog()` = 0 certifications
- `production_research_provider_certification_evidence_catalog()` = 0 evidence records
- `production_research_provider_routing_policy_catalog()` = 0 routing policies
- `production_certified_shopping_markets()` = 0 certified shopping markets
- `execute_research_plan(...)` raises `NotImplementedError`
- `StaticResearchProvider.execute(...)` raises `NotImplementedError`
- Philippines documentary IDs (`ph-shopee`, `ph-lazada`, `ph-tiktok-shop`, `ph-amazon`, `ph-temu`) are **not** loaded into production catalogs
- No live PH shopping-data path

## Duplication matrix

Classification key:

- **legitimate separate responsibility** — different caller, lifecycle, or ownership; keep separate
- **useful shared contract** — shared type/convention already exists or would be useful later; not a rewrite
- **duplicated implementation requiring disposition** — same job implemented twice without a valid reason
- **future-only concern** — no current runtime need

| Concern | Sprint 4 | Sprint 18 | Sprint 8 | Sprint 31 | Classification |
| -------- | -------- | --------- | -------- | --------- | -------------- |
| merchant identity | `marketplace_name` (`shopee`, `lazada`) | `connector_id` (`fixture-marketplace`, `future-shopee-official`, …) plus separate `marketplace` | `marketplace_name` (`shopee`, `lazada`) | `provider_id` plus plan/certification `source` | family-local IDs remain valid; **no shared mapping required** (future-only if a live certified path later must join them) |
| market identity | implicit PHP / `.ph` URLs; no ISO field | connector `marketplace` string; config region; no ISO market catalog | `CollectionTarget.marketplace`; no ISO field | exact ISO 3166-1 alpha-2 on descriptors/certifications; optional `TrustedMarketContext` | legitimate separate responsibility; Sprint 31/37 already own exact-market semantics |
| product identity | listing `product_id` | offer / raw-record IDs + `MarketplaceProductMatcher` | marketplace + `product_id` tuple into Price History | frozen scope / outside-set names; no live SKU fetch | legitimate separate responsibility |
| search | query-time `search()` / listing aggregation | does not search shopper queries | does not search | planning capability `product_discovery` / `offer_discovery` only | legitimate separate responsibility |
| current-offer sync | none | `MarketplaceSyncEngine.run()` via `fetch_offers`; checkpoints; freshness | none | planning capability `current_pricing` only; no sync | legitimate separate responsibility |
| history | optional `PriceHistoryService.search_and_record()` consumes search listings | offer/price/inventory snapshots on sync | owns historical collection into Price History | none | legitimate separate responsibility |
| certification | none | technical `ConnectorCapability` only | none | trusted `ResearchProviderCertificationCatalog`; exact provider + capability + market + source | legitimate separate responsibility |
| routing | fixed DI list order; no routing catalog | registry order + on-demand sync; no research router | collector dict by marketplace name | trusted routing-policy catalog among already eligible certified providers | legitimate separate responsibility |
| normalization | `ShopeeConnector.normalize_listing` / `LazadaConnector.normalize_listing` → `MarketplaceListing` | `MarketplaceRecordNormalizer` → Sprint 18 offer entities | reuses Sprint 4 `normalize_listing` for mock fixtures only | none | Sprint 8 reuse is fixture-helper interoperability, not a shared runtime connector; Sprint 4 vs 18 normalizers target different entities |
| provenance | DealScore mock-source note; optional title-match notes from Sprint 18 offers | `source_mode`, freshness, simulated/live labels | `source_marketplace` on collected listings | empty `ResearchExecutionTrace`; plan digest binds catalog fingerprints | useful shared contract already started (honesty labels / empty research trace); not duplicated execution |
| freshness | none | `evaluate_freshness()`; checkpoint + config thresholds | none as current-offer freshness owner | planning may require freshness in frozen scope; does not compute offer freshness | legitimate separate responsibility |
| health | none on search path | `report_health()` / `ConnectorHealth` | collector `health_check()` | kill-switch + circuit-breaker snapshot on descriptors | legitimate separate responsibility |

**No duplicated implementation requiring disposition was found.** Shared vocabulary (`shopee`, `lazada`, “connector”, “marketplace”) is not shared runtime ownership.

## Final disposition

# RETAIN INTENTIONAL DUAL IMPLEMENTATIONS

Do **not** retire Sprint 4 search. Do **not** retire Sprint 18 sync. Do **not** merge Sprint 8 collectors into search, sync, or research planning. Do **not** turn Sprint 31 into live execution.

## Rationale

1. **Different jobs.** Sprint 4 answers a shopper query now. Sprint 18 synchronizes current offers, checkpoints, and freshness. Sprint 8 collects historical listings into Price History. Sprint 31 plans certified research and stops. Architecture Lock already assigns those jobs to different sprints.
2. **Different ports and callers.** Four distinct interfaces are wired through four distinct DI factories. Sprint 31 tests already forbid research modules from importing Sprint 18 fixture/mock-live connectors.
3. **Neither search nor sync is unused or safely replaceable.** Marketplace search still feeds DealScore, Recommendation, and price-history search. Sprint 18 still owns `/api/v1/marketplaces/*`, sync, import, and freshness. Collapsing them would silently redistribute Architecture Lock ownership.
4. **Sprint 8 interoperability is narrow and legitimate.** Collectors borrow Sprint 4 `normalize_listing` and mock fixtures. They do not call `search()`, do not enter `MarketplaceConnectorRegistry`, and do not participate in research planning.
5. **Sprint 31 remains planning/certification/routing.** `plan_authorized_research(...)` never calls `execute`. Production catalogs are empty and fail closed. That is not a live search or sync path.
6. **Sprint 32 / 37 do not create a join requirement today.** Documentary PH provider IDs are not production `provider_id` values. `MarketContext` composes trusted country + `DeliveryContext` and contains no `connector_id` / `marketplace_name` / `provider_id`. Certified shopping markets remain zero. Uncertified markets cannot become connector-eligible.
7. **A mega-interface would make the architecture look simpler and be wrong.** Search, sync, history, and authorized-research planning have different freshness models and failure modes. Shared contracts (certification, routing, reliability types, exact market/source) already exist where unification is actually needed.

## Merchant / source identity mapping

**Not required on this baseline.**

Current identifiers stay family-local:

| Family | Identifier | Current examples |
|--------|------------|------------------|
| Sprint 4 | `marketplace_name` | `shopee`, `lazada` |
| Sprint 18 | `connector_id` | `fixture-marketplace`, `imported-marketplace`, `mock-live-marketplace`, `future-shopee-official` |
| Sprint 8 | `marketplace_name` | `shopee`, `lazada` |
| Sprint 31 | `provider_id` + source on plans/certifications | production: none |
| Sprint 32 documentary only | candidate `provider_id` + `source` | `ph-shopee` / `shopee` — not production registry IDs |
| Sprint 20 affiliate | `merchant_id` | downstream monetization only |

Lexical overlap (`shopee` as a Sprint 4 name, a Sprint 18 stub `marketplace`, and a Sprint 32 documentary source) is not a runtime correlation. No caller joins these families by a shared merchant key. Sprint 37 coverage uses ISO country codes independently of connector/provider IDs.

Do **not** create a shared merchant registry now. If a later certified live path must present the same merchant across search, sync, and research, the smallest contract is a documentation/table mapping of family-local IDs — not a mega-registry.

## Sprint 18 duplicate `connector_id` registration

**Current behavior (still true):** `MarketplaceConnectorRegistry.register()` overwrites an existing `connector_id`. `_order` keeps the first-seen ID. No error and no warning.

Exact code: `app/marketplace/registry.py` `register()`.

**Actual current use:** `MarketplaceDataService.__init__` intentionally re-registers `ImportedMarketplaceConnector` with a repository-backed offer provider. That overwrite is the live wiring path for imported offers, not an accidental collision among official connectors.

**Risk:** low on this baseline. Active IDs are distinct constants. Future stubs use `future-*` IDs and are excluded from sync. The realistic failure mode is a later official connector silently replacing another if someone reuses an ID.

**Smallest safe follow-up (not implemented here; owner approval required):**

1. Keep the intentional imported-connector rewire as an explicit `replace(...)` (or equivalent) used only by `MarketplaceDataService`.
2. Make unexpected duplicate `register()` fail, matching `ResearchProviderRegistry`.
3. Add a unit test for reject-on-unexpected-duplicate without breaking the imported-connector rewire.

This review does **not** implement that change.

## Sprint 32 / Sprint 37 impact

Unchanged by this disposition:

- exact provider + capability + market + source certification
- certification authority remains the trusted server catalog
- production certified-provider count remains **0**
- fail-closed connector eligibility remains catalog-owned
- selected shopping market, `MarketContext`, delivery context, source currency, PH certification state, and unsupported-market fail-closed behavior remain Sprint 37 / coverage-owned
- `MarketContext` is not connector-owned (`app/market/context.py` has no connector/provider fields)

## Affiliate neutrality

Unchanged. Shopee affiliate, Admitad / Mitgo, Optimise, and Involve Asia remain downstream monetization. They are not certification authority, routing authority, merchant-data permission authority, or PiqScore / Recommendation inputs. This branch contains no affiliate implementation.

## Remaining follow-up items

| Item | Status |
|------|--------|
| Dual-path disposition decision | **Done.** Retain intentional dual implementations. |
| Shared identity mapping | **Not required.** Revisit only when a live certified path must join family-local IDs. |
| Sprint 18 unexpected duplicate `connector_id` reject | **P1 follow-up.** Documented; owner approval required before code change. |
| Sprint 32 PH production certification | Still Sprint 32; catalogs remain empty. |
| Sprint 37 MarketContext / unsupported-market product policy | Still Sprint 37; not connector-owned. |
| Live research execution | Still Sprint 38. |
| Affiliate integration | Still Sprint 20 / later monetization. Not this review. |

## September 15 obligation

**Satisfied.**

The 2026-08-25 ADR required one of two outcomes by 15 September 2026:

1. formally approved thin shared adapters / identity contracts, with dual implementations retained intentionally; or
2. an evidence-backed retirement / migration plan for genuinely unnecessary duplication.

This review chooses (1) in the narrow sense required by the deadline: dual implementations are **formally retained as intentional**, and no new shared identity/adapter layer is approved because current repository evidence does not demonstrate the need. The deadline was a decision obligation, not a rewrite obligation.

# SPRINT 31 — FORMALLY CLOSED
