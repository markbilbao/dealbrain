# DealBrain Architecture Lock

**Status:** Locked as of Sprint 23; Sprint 24 API-contract ownership added (additive)  
**Hard endpoint:** Sprint 40  
**Runtime enforcement:** This document is a change-control policy. It is **not** enforced by a separate runtime policy engine unless a specific check is implemented and documented elsewhere.

---

## 1. Purpose

This lock freezes domain ownership and architectural invariants established by the Sprint 1–22 architecture audit. Future sprints may harden adapters, operations, and integrations, but must not silently redistribute ownership or change ranking/recommendation semantics.

Sprint 23 may **replace adapters**, not **domain owners**. Persistence changes must be **behavior-preserving**. Any future ownership change requires **explicit architecture review**. The launch roadmap has a **hard endpoint at Sprint 40**.

Sprint 24 owns **API contracts only** (OpenAPI, response shapes, pagination/filter/sort conventions, error documentation, compatibility gates). It does **not** take domain or persistence ownership from Sprints 1–23.

---

## 2. Locked ownership matrix

| Sprint | Canonical ownership |
|--------|---------------------|
| 1–3 | Product Identity, Product Registry, Product Matching |
| 4 | Marketplace Search, Marketplace Intelligence |
| 5 | DealScore |
| 6 | Recommendation decisions (Buy / Wait / Consider / Avoid) |
| 7 | Historical Price Data, Price Statistics, Price Trends |
| 8 | Marketplace Collection (historical collection) |
| 9 | Collection Operations, Pause / Resume, Manual Runs, Operational Health |
| 10 | Watchlists; Legacy Alerts during migration |
| 11 | Reviews |
| 12 | Review Summaries |
| 13 | Shopping Assistant ranking and presentation |
| 14 | Community |
| 15 | Knowledge Graph |
| 16 | Personal AI and personal presentation |
| 17 | Consumer Users, Authentication, Sessions, Account Profiles, Account Preferences |
| 18 | Current Marketplace Offers, Marketplace Synchronization, Sync Checkpoints, Marketplace Freshness |
| 19 | Alert Rules, Alert Evaluation, Alert Events, Notification Preferences, Notification Delivery Orchestration |
| 20 | Affiliate Partners, Affiliate Link Generation, Click and Conversion Attribution |
| 21 | Merchant Organizations, Merchant Accounts, Merchant Catalog, Merchant Offers, Merchant Campaigns, Merchant Moderation |
| 22 | Launch Infrastructure, Startup Validation, Health and Readiness, Logging, Rate Limiting, Launch Cache, Diagnostics |
| 23 | Production persistence adapters, migrations, transaction infrastructure, durable operational state, persistence validation, restart recovery, production configuration hardening, deeper readiness checks related to persistence |
| 24 | API contracts, endpoint consistency, DTO/OpenAPI standardization, pagination/filtering/sorting conventions, error-response documentation, API integration/contract tests, API documentation, OpenAPI drift detection, compatibility gate — **not** domain engines or persistence adapters |

Sprint 23 must **not** take ownership of Sprints 1–22 domain logic.

Sprint 24 must **not** take ownership of Sprints 1–23 domain logic or persistence.

---

## 3. Protected architectural invariants

1. Sprint 5 remains the only DealScore owner.
2. Sprint 6 remains the only owner of organic recommendation decisions.
3. Affiliate metadata must be attached only after organic selection and ranking.
4. Affiliate commission, partner priority, or conversion value must never influence candidate inclusion, DealScore, Recommendation, organic ordering, or Shopping Assistant ordering.
5. Merchant data must not modify organic visibility, DealScore, Buy/Wait/Consider/Avoid, Marketplace Search ranking, or historical prices.
6. Sponsored merchant content must remain separate and clearly labeled.
7. Sprint 18 owns current synchronized offers.
8. Sprint 7 owns canonical historical prices.
9. Sprint 8 owns historical marketplace collection.
10. Sprint 19 is the canonical new alert-rule engine.
11. Sprint 10 legacy alert behavior must remain compatible until a later proven migration.
12. AI remains downstream from deterministic product identity, DealScore, and Recommendation.
13. Repositories persist domain state but must not contain domain decision logic.
14. Sprint 22 remains infrastructure only.
15. Persistence must not change domain output for identical inputs.

---

## 4. Allowed Sprint 23 changes

- Production persistence adapters implementing existing repository ports
- Deterministic Alembic migrations for operational tables
- Transaction / unit-of-work helpers for atomic repository operations
- Explicit environment-aware adapter selection via dependency injection
- Persistence-related readiness checks consumed by Sprint 22
- Production configuration hardening (fail-closed secrets/backends)
- Tests proving contract parity, restart recovery, concurrency, and neutrality
- Documentation of persistence, migrations, operations, and deferred work

---

## 5. Forbidden Sprint 23 changes

- Architecture redesign or domain ownership transfers
- Feature expansion, AI improvement, ranking improvement, marketplace feature expansion, or UI redesign
- Changing DealScore formulas, weights, or recommendation decisions
- Changing organic result ordering or Shopping Assistant ranking policy
- Letting affiliate or merchant data affect organic ranking
- Merging consumer and merchant identity systems
- Adding speculative abstractions without runtime use
- Deleting Sprint 10 compatibility paths without proven migration
- Silently changing API contracts
- Introducing a second ORM or migration system unless the existing stack is unusable (it is usable)

---

## 6. Repository rules

1. Services depend on **ports/interfaces**, not concrete ORM adapters.
2. Persistent adapters translate storage concerns only; they do not implement ranking, DealScore, or recommendation policy.
3. Production must use persistent adapters by default and must not silently fall back to in-memory storage.
4. In-memory adapters remain valid for tests and explicit development/demo configuration.
5. Uniqueness and ownership constraints should be enforced at the database where concurrent safety requires it.
6. Stable identifiers and existing API semantics must be preserved.

---

## 7. Ranking-neutrality rules

Persistence and operational data must not alter:

- Marketplace Search organic ordering (Sprint 4)
- DealScore computation (Sprint 5)
- Recommendation decisions (Sprint 6)
- Shopping Assistant ranking policy (Sprint 13)
- Personal AI ranking ownership (Sprint 16)

---

## 8. Affiliate-neutrality rules

- Affiliate attachment remains post-selection.
- Commission, partner priority, and conversion value are attribution/reporting concerns only.
- Affiliate tables and repositories must not be read by DealScore or Recommendation engines.

---

## 9. Merchant-neutrality rules

- Merchant catalog/offers/campaigns must not write into organic search, DealScore, Recommendation, or Sprint 7 historical prices.
- Sponsored rails remain separate and labeled.
- Cross-merchant access is denied; admin moderation remains explicit.

---

## 10. AI-boundary rules

- AI consumes deterministic identity, DealScore, and Recommendation outputs; it does not redefine them.
- Persistence of AI conversation/profile stores (if any) is out of Sprint 23 ownership unless already required by Sprints 17–21 operational durability (Sprint 23 focuses on 17–21 operational stores).

---

## 11. Compatibility and deprecation policy

- Existing APIs remain compatible unless a change is explicitly documented.
- Sprint 10 legacy alerts remain until a later sprint proves migration with callers and tests.
- Demo shortcuts may remain behind development/demo flags only.
- Deprecations require docs, dual-run or adapter selection, and tests before removal.

---

## 12. Change-control policy through Sprint 40

1. Propose ownership or invariant changes in architecture review before coding.
2. Prefer adapter and operations work over domain rewrites.
3. Keep scope controlled so the product can launch by Sprint 40.
4. Do not absorb deferred roadmap items (real connectors, distributed workers, billing, WAF/CDN, etc.) into persistence sprints without explicit re-scoping.
5. Document limitations rather than silently changing behavior.

**Remember:** Sprint 23 replaces adapters, not domain owners. Persistence must be behavior-preserving. Ownership changes require explicit architecture review. Launch roadmap hard endpoint: Sprint 40.

---

## 13. Sprint 24 — API contract ownership (additive)

Sprint 24 is an **additive** stability sprint. It freezes and documents HTTP contracts without redistributing domain or persistence ownership.

### 13.1 What Sprint 24 owns

- Public API contracts and OpenAPI as the implementation contract
- Shared pagination / filtering / sorting conventions at the HTTP boundary
- Error-response documentation (Sprint 22 `ErrorBody` envelope preserved)
- Dual-run collection compatibility (`named key` + optional `items` / `pagination`)
- OpenAPI drift detection and the compatibility gate
- API integration / contract test coverage matrix

### 13.2 Compatibility guarantees

- Existing clients must keep working without mandatory changes
- No path removals; no `/api/v2`
- No global success envelope (`{data, meta}`)
- Bare-list endpoints remain bare lists
- Named collection keys remain primary
- Pagination / sort / dual-run fields are **optional and additive**
- Caller `sort` never influences DealScore, Recommendation, Marketplace Search organic order, or Shopping Assistant ranking

### 13.3 Unchanged ownership

- **Persistence (Sprint 23):** adapters, migrations, and durable stores are unchanged by Sprint 24
- **Business / domain ownership (Sprints 1–22):** DealScore, Recommendation, Shopping Assistant ranking, affiliate attachment order, merchant neutrality, and all other locked domain owners remain as in §§2–10
- Sprint 24 may wrap HTTP presentation only; it must not change domain outputs for identical inputs
