# Sprint 31 — Research Execution Router / Certified Provider Contract

**Status:** In progress. Planning-only router exists; provider capability and PiqSavi certification are separate authorities. Live provider execution is **not implemented**. This document does not mark Sprint 31 complete.

**Depends on:** Research Authorization / Execution Handoff Contract.

**Does not implement:** production Amazon/Shopee/Lazada/TikTok research, scraping, live re-evaluation, or a new canonical decision.

**Related roadmap:** [`../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md`](../roadmap/sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md). This document is the architecture for the authorized-research routing boundary. It does not close Sprint 31’s remaining 4/18 connector unification work.

## Purpose

A valid `ResearchAuthorization` does not mean any connector may run.

This phase creates the server-authoritative boundary between:

- a validated authorization handoff
- future certified provider execution (Sprints 32–36 certify; Sprint 38 executes)

Hard rule:

> Authorized ≠ planned ≠ attempted ≠ evidence obtained ≠ new Recommendation.

PiqSavi may internally conclude that an authorized request has a certified execution plan. It must not say “I checked Amazon” or “Research is underway” until a later sprint actually executes and the trace proves it.

## Validated authorization input

The router does not accept raw browser proposal data, client provider IDs, client markets, or client-defined scope.

`plan_authorized_research(...)` requires a server-held `ResearchAuthorization` and calls:

1. `validate_research_authorization_for_execution(...)`
2. `get_authorized_research_handoff(...)`

Only then does it build a `ResearchExecutionRequest`.

The request carries:

- authorization ID/version
- decision UUID and canonical context version
- conversation ID
- proposal ID/version
- frozen research scope and scope digest
- authorization idempotency key
- optional **server-trusted** market context
- a deterministic execution-request ID/version

Owner identifiers stay on the authorization. They are not copied onto provider implementations.

Wrong-owner planning raises the existing non-existence-leak error. Cancelled, invalidated, consumed, or context-stale authorizations return `planned=False` with no plan.

Replaced authorization A cannot later generate a plan. B needs its own proposal → confirmation → authorization → plan.

## Execution router

`plan_authorized_research(...)` then:

1. derives required capabilities from the frozen scope
2. resolves trusted market context (or honestly records that it is missing)
3. evaluates technical provider support **and** the trusted certification catalog
4. produces a bounded `ResearchExecutionPlan`
5. returns the plan
6. **stops**

It never calls `execute`. `execute_research_plan(...)` exists as an unimplemented interface for Sprint 38.

Ask PiqSavi is unchanged. Planning is server-side and is not a shopper-facing “Researching…” state.

## Provider contract

`StaticResearchProvider` declares **technical support only**. It must not certify itself for production execution.

A provider may expose:

- provider ID and type
- technically supported markets (ISO 3166-1 alpha-2, explicit)
- technically supported research capabilities
- technically supported source/merchant identities
- operational status, kill-switch, and circuit-breaker snapshot
- configured selection priority
- test-fixture flag
- whether it may expand the evaluated set
- whether it can provide pricing, shipping/taxes, product evidence, or review evidence

It must **not** own:

- certification status
- certification version
- contractual/policy approval (`allowed` / `restricted` / `prohibited` / `unknown`)

Technical support is not certification. A provider that technically supports `CURRENT_PRICING` for Amazon in PH is still **not eligible** until a trusted certification record exists for that exact combination.

Technical Sprint 18 `ConnectorCapability` remains adapter operations. The Sprint 31 contractual/policy layer lives on the certification catalog, not on the provider descriptor.

`supports(capability, market, source)` returns a **technical** eligibility audit. `execute(step)` raises `NotImplementedError`.

This contract does not replace Sprint 4 `MarketplaceConnector` or Sprint 18 `MarketplaceDataConnector`. Future certified adapters may satisfy this routing contract without collapsing those ownerships.

## Provider registry vs certification catalog

`ResearchProviderRegistry` answers: what provider implementations exist, and what can they technically do?

`ResearchProviderCertificationCatalog` answers: which exact provider / capability / source / market combinations has PiqSavi approved for production planning?

The two catalogs are separate. Registration is not certification. Production both start empty and fail closed.

## Capability model

Bounded taxonomy:

- `product_discovery`
- `offer_discovery`
- `current_pricing`
- `availability`
- `shipping`
- `taxes_import`
- `promotion_evidence`
- `warranty_evidence`
- `product_specification`
- `review_community_evidence`

Derivation examples:

| Frozen scope | Required capabilities |
|---|---|
| “What about AirPods Max?” | product discovery + offer discovery |
| “Check today's Amazon price.” | offer discovery + current pricing; requested source remains Amazon |
| “Find something cheaper.” | product discovery + offer discovery; no invented source |
| “What if I ship it to Cebu?” | shipping + taxes/import, then blocked until Sprint 37 |

Outside-set names stay as typed. The plan carries `AirPods Max` and does not invent USB-C, year, or SKU variants.

## Certification authority

PiqSavi certification is a separate trusted server-controlled record (`ResearchProviderCertification`), not a field on the provider.

A certification record binds:

- provider ID
- capability
- exact ISO market
- source identity when `source_scope=exact`
- status (`certified` / `revoked` / `disabled` / `pending` / `expired`)
- contractual policy (`allowed` / `restricted` / `prohibited` / `unknown`)
- certification version

Only `status=certified` **and** `policy=allowed` may authorize planning. Unknown status fails closed. No matching record means **not certified**.

Matching is exact. Certification for provider A + current pricing + US + Amazon does **not** certify Philippines, shipping, Shopee, or another provider.

Source and market wildcards are not inferred:

- missing source on an `exact` record is invalid
- `source_agnostic` matches only unnamed-source requests, never every source
- missing market is invalid; US does not certify PH

Contractual/policy approval lives on this trusted record. A provider cannot declare that its use is contractually allowed.

Sprints 32–36 own populating provider/market evidence. This phase does not certify Amazon, Shopee, Lazada, TikTok Shop, or any production merchant. Production `production_research_provider_certification_catalog()` is empty.

Selected plan steps record the trusted certification ID and version. Catalog fingerprint is bound into the plan digest, so a version change or revocation changes the digest without using timestamps.

A provider is executable only when **all** of the following hold:

1. the provider technically supports the capability
2. the provider technically supports the requested source when the scope names one
3. the provider technically supports the requested market
4. a trusted certification record exists
5. certification status is `certified`
6. certification matches the exact capability
7. certification matches the exact market
8. certification matches the exact source where required
9. trusted policy is `allowed`
10. the provider is operationally available
11. kill-switch and circuit rules allow planning

If any fail, the provider is ineligible. Technical support alone cannot produce an eligible provider.

## Market and source rules

Market support is explicit at both layers. Technical US support is not PH support. A US certification record is not a PH certification record.

Until Sprint 37, the only market input is optional `TrustedMarketContext` from server-trusted data. Missing market is not fabricated; planning returns `blocked_market_context`.

If the frozen scope names Amazon, the router must not substitute Shopee. Alternative-source execution is not invented here.

If the scope is generic (“Find something cheaper.”), the router may choose among certified providers using capability, market, and the documented selection rule — never commission.

Destination-sensitive cost is owned by Sprint 37. If authorization requires shipping/tax to a named destination, the router blocks those capabilities with `destination_support_not_ready`. It does not call “price before shipping” a delivered price and does not invent client-side shipping estimates.

## Deterministic provider selection

When multiple providers are equally certified for the same requirement:

1. lower configured `selection_priority` wins
2. stable `provider_id` ascending is the tie-breaker

Affiliate payout, commission rate, and merchant commercial priority are never read by the selector. Affiliate processing remains downstream of Sprint 20.

## Execution plan

`ResearchExecutionPlan` includes:

- plan ID/version (deterministic; distinct from authorization ID and authorization idempotency key)
- authorization ID/version, decision, context version, proposal ID/version
- scope digest
- required capabilities
- eligible provider steps
- blocked requirements
- eligibility audit
- support status
- plan digest
- exact outside-set product names
- `plan_ready`
- `execution_available = false`
- `execution_implemented = false`
- `source_checked = false`
- `attempted = false`

Statuses:

- `ready` — every required capability has a certified step. This does **not** mean research started.
- `partially_supported` — some capabilities are assigned; others remain explicit unknowns/blocks
- `unsupported` — no required capabilities could be derived
- `blocked_missing_certified_provider`
- `blocked_market_context`
- `stale_authorization` — planning rejected; no plan object

There is no fake `researching`, `completed`, or `failed` status.

Plan digest is SHA-256 over authorization identity, scope digest, selected provider IDs, capability assignments (including certification ID/version), market, blocked reasons, status, technical registry fingerprint, and certification-catalog fingerprint.

Repeated planning of the same unchanged valid authorization and catalog produces the same plan ID and digest.

Shopper-facing `to_public_dict()` omits provider IDs, plan digest, idempotency keys, certification artifacts, and commission.

## Partial / blocked semantics

Unsupported capabilities remain unknown.

They are never converted into:

- zero shipping
- zero taxes
- available / unavailable
- no warranty
- no import fee

If a provider can certify current price but not shipping, the plan is `partially_supported`. Shipping stays an explicit blocked unknown. The plan must not claim complete final-cost coverage.

## No-execution boundary

A planned provider is not an attempted provider.

The Sprint 38 trace skeleton exists (`ResearchExecutionTrace`) but planning populates an empty trace. Presence of a provider step must never cause evidence/UI to say that source was checked.

Production `production_research_provider_registry()` is empty. Production `production_research_provider_certification_catalog()` is empty. Neither falls back to Product Foundation fixtures, test certifications, or generic model knowledge.

Kill-switch and circuit-open block planning without rewriting certification history. Runtime unavailability is not revocation.

`execution_available` remains false even when `plan_ready` is true, because invocation is not implemented.

Planning does not mutate PiqScore, Recommendation, session Best Piq, evaluated set, economics, or the canonical decision. A plan is not a new canonical decision.

## Fixture isolation

Test providers must set `test_fixture=True` and `provider_type="test"`. They register only through `research_provider_registry_for_tests(...)`.

Test certifications must set `test_fixture=True` and register only through `research_provider_certification_catalog_for_tests(...)`.

The production registry raises if a test fixture is registered. The production certification catalog raises if a test certification is registered. Production does not inherit test certifications.

## Reliability contracts

Sprint 31 exports minimum types for Sprints 32–36:

- timeout policy
- bounded retry policy
- exponential backoff policy
- quota / credential / partial-failure result types
- kill-switch hook
- circuit-breaker snapshot

Sprint 38 owns production hardening, honest degradation, and actual retries/breakers. This phase does not implement them as executors.

## Fixture / onboarding hooks (non-secret)

Future market certification (32–36) should record, per provider/market:

- provider identity and market
- program / agreement / API policy identifier
- review date
- capability policy (`allowed` / `restricted` / `prohibited` / `unknown`)
- TTL / freshness constraints
- attribution / disclosure requirements
- evidence source reference

Do not store privileged legal advice or credentials in Git. Affiliate permission remains independent of product-data permission.

Sprint 4 vs Sprint 18 dual-run is **not** retired in this phase. The research router is the fail-closed selection authority for **authorized research planning**. Marketplace search/sync connectors remain in place until remaining Sprint 31 unification work is explicitly executed.

## Relationship to Sprints 32–38

| Sprint | Ownership preserved |
|---|---|
| 32–36 | Country/merchant certification evidence; first certified real paths |
| 37 | MarketContext, currency, destination-sensitive economics |
| 38 | Live execution, execution trace population, truthful degradation |
| 45 | Launch gate no later than 2026-09-30 |
| 46 | Post-launch stabilization |
| 47 | Post-beta buying-action intelligence |

Sprint 32 is **not started** by this document. The next bounded implementation step remains provider/market certification (Sprint 32 Philippines first, then 33–36 as needed) after Sprint 31 acceptance — not uncontrolled live research.
