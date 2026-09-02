# ADR — Sprint 31 connector unification (Sprint 4 / Sprint 18 dual-run)

**Status:** Accepted. Sprint 31 was formally owner-closed before Sprint 32 implementation began.
**Date:** 2026-08-25 (architecture review recorded); owner-close status reconciled 2026-09-02
**Baseline recorded:** `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` (PR #96 merge)
**Sprint 31 status:** Formally owner-closed. This ADR remains the recorded 2026-08-25 architecture review.
**Sprint 32 status:** In progress (foundation slices). Sprint 32 is **not complete**. Production certified providers remain zero.

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

**September 15, 2026** — dual-path disposition review (see above).

### Later-sprint ownership

| Work | Owner |
|------|-------|
| Country / merchant certification evidence; first planned market Philippines | Sprints 32–36 |
| MarketContext, currency, destination-sensitive behavior | Sprint 37 |
| Live execution, runtime reliability, retries / circuit breakers, truthful degradation, populated traces | Sprint 38 |
| Sprint 18 duplicate `connector_id` reject-on-register | P1; not a 31 closer |
| Optional thin identity mapping / adapters | Only after demonstrated need; review by September 15, 2026 |

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
