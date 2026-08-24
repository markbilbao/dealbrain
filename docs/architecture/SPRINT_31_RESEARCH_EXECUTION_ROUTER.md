# Sprint 31 — Research Execution Router / Certified Provider Contract

**Status:** Implemented for planning only. Live provider execution is **not implemented**.

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
3. evaluates certified providers
4. produces a bounded `ResearchExecutionPlan`
5. returns the plan
6. **stops**

It never calls `execute`. `execute_research_plan(...)` exists as an unimplemented interface for Sprint 38.

Ask PiqSavi is unchanged. Planning is server-side and is not a shopper-facing “Researching…” state.

## Provider contract

`StaticResearchProvider` is metadata-only. It exposes server-known fields:

- provider ID and type
- supported markets (ISO 3166-1 alpha-2, explicit)
- supported research capabilities
- supported source/merchant identities
- certification status and version
- operational status, kill-switch, and circuit-breaker snapshot
- whether it may expand the evaluated set
- whether it can provide pricing, shipping/taxes, product evidence, or review evidence

Technical Sprint 18 `ConnectorCapability` remains adapter operations. The Sprint 31 contractual/policy layer is separate: a connector that *can* fetch prices is not thereby *authorized* to do so.

`supports(capability, market, source)` returns an eligibility audit. `execute(step)` raises `NotImplementedError`.

This contract does not replace Sprint 4 `MarketplaceConnector` or Sprint 18 `MarketplaceDataConnector`. Future certified adapters may satisfy this routing contract without collapsing those ownerships.

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

## Certification

A provider is not eligible merely because it exists in code.

Eligibility requires all of:

- `certification_status = certified`
- capability-level certification for the requested capability
- contractual policy `allowed` for that capability
- explicit market match
- explicit source match when the frozen scope names a source
- operational availability
- kill-switch not engaged
- circuit breaker not open

Conceptual states:

- `registered` — known, not executable
- `certified` — may become an executable plan step
- `unavailable` / `disabled` — not executable

`enabled=true` is not a substitute. Policy `unknown`, `restricted`, or `prohibited` fails closed. Upstream payload presence is not permission.

Sprints 32–36 own populating provider/market evidence. This phase does not certify Amazon, Shopee, Lazada, TikTok Shop, or any production merchant.

Certification versions are copied onto selected plan steps so later execution can prove the certification basis.

## Market and source rules

Market support is explicit. A US-certified provider is not eligible for the Philippines or Singapore.

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

Plan digest is SHA-256 over authorization identity, scope digest, selected provider IDs, capability assignments, market, certification versions, blocked reasons, status, and registry fingerprint.

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

Production `production_research_provider_registry()` is empty. It does not fall back to Product Foundation fixtures or generic model knowledge.

`execution_available` remains false even when `plan_ready` is true, because invocation is not implemented.

Planning does not mutate PiqScore, Recommendation, session Best Piq, evaluated set, economics, or the canonical decision. A plan is not a new canonical decision.

## Fixture isolation

Test providers must set `test_fixture=True` and `provider_type="test"`. They register only through `research_provider_registry_for_tests(...)`.

The production registry raises if a test fixture is registered.

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

The next bounded implementation step is provider/market certification (Sprint 32 Philippines first, then 33–36 as needed) — not uncontrolled live research.
