# Sprint 38 — Connector Reliability & Honest Degradation

**Status:** IN PROGRESS (2026-09-26). Engineering foundation plus authorization/planning/execution handoff. Not COMPLETE / CLOSED. Live execution is NOT OPERATIONAL. No Shopify call. Routing stays 0. Public PH shopping coverage stays disabled.
**Primary owner / domain:** Marketplace reliability / ops
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes with live HTTP / multi-connector launch

## Current engineering foundation (2026-09-26)

Sprint 38 has started. It is not complete. Overall engineering status is IN PROGRESS. Live research operational status is NOT OPERATIONAL. Those are separate facts: `SPRINT_38_STATUS` is IN PROGRESS, and `SPRINT_38_LIVE_EXECUTION_STATUS` is NOT OPERATIONAL. The current public beta has one certified PH connector, `ph-shopify-global-catalog`, and that provider stays DISABLED. Routing stays 0. Public certified shopping markets stay 0. `SHOPPING_RESEARCH_EXECUTION_MODE` stays disabled. This foundation does not call Shopify and does not deploy.

The scripted circuit breaker is deterministic chaos-test state on one in-memory connector. It is not evidence of a persistent production breaker across separate shopper requests. Persistent production breaker hardening remains Sprint 38 work before closure.

Classification for the current PH-only scope:

- A. Reuse Sprint 31 timeout, retry, breaker, and kill-switch contracts, Sprint 31 planning-only execution, Sprint 32 reduced certification, and Sprint 37 fail-closed destination re-evaluation. Do not duplicate those systems.
- B. Implement now: execution identity and states, owner-bound idempotent confirmation, truthful non-live traces, the request-scoped live-mode fail-closed gate, a Shopify execution refusal that does not perform HTTP, scripted timeout / 429 / 5xx / retry / kill-switch behavior, an in-memory chaos-test breaker that is not a persistent production breaker, one-connector no-merchants-available behavior, prior-decision preservation, connector health distinct from `/ready`, and Shopify cache refusal.
- C. Owner validation after this foundation, not in this change: a real Shopify call once routing, operational eligibility, and a deployed profile exist.
- D. Sprint 41: production deploy, production UCP profile, AWS/DNS/TLS, and the deployed kill-switch drill.
- E. Sprint 42: alerts, paging, synthetic production probes, and incident-runbook proof. EXT-25 stays optional.
- F. Not a blocker for this one-connector beta: affiliate-provider failure, because affiliate monetization is out of launch scope.
- G. Preserved and not a close of this beta: multi-connector chaos, production evidence across multiple connectors and markets, and cross-merchant aggregation as a live shopper claim. Deterministic multi-provider tests may exercise the orchestration. Those tests are not live connectors and are not launch evidence.

One certified connector failing is no live merchant result. It is not a successful multi-merchant partial result. `DESTINATION_REEVALUATION_IMPLEMENTED` stays False until a validated evidence-backed executor exists.

## Authorization / planning / execution handoff (2026-09-26)

This slice connects the existing Ask PiqSavi chain to Sprint 38 preparation. It does not make live execution operational.

The server-authored `ResearchAuthorization` remains the confirmation authority. Explicit confirmation still creates that authorization. Sprint 38 does not parse a second confirmation token. Execution identity is derived from `authorization.idempotency_key`. A client confirmation token is not execution identity. The scripted `ResearchExecutionLedger.confirm` path remains chaos-test bookkeeping and is not the shopper authority.

A preparation binding pins that authorization to one current plan. The same authorization and the same plan reuse one execution. Silent plan drift is rejected as `authorization_plan_conflict` and does not replace the stored plan or create a second execution. `AuthorizedExecutionLedger` is an in-process preparation ledger, not durable live-execution storage. Explicit trusted replanning or rebinding, if later required before live execution, remains future Sprint 38 work.

Preparation accepts the trusted `ResearchExecutionPlan` built from the authorization handoff. Browser market, capability, source, and provider values cannot replace the plan step. The live-mode gate reads the plan step target and stays closed: mode disabled, provider disabled, routing absent, public market not activated.

`execute_research_plan` prepares or refuses without network I/O. A valid plan returns `prepared_but_live_unavailable` (or a blocked outcome when the plan has no eligible step). It does not mark a provider attempted, does not set `source_checked`, does not populate the authoritative trace, and does not mark execution completed. `mark_research_authorization_consumed` is not called. The authorization stays `authorized_pending_execution` because no live attempt started. Consumption remains the later single-logical-execution boundary, when a live connector attempt actually starts.

The authoritative production trace is `app.domain.entities.research_execution.ResearchExecutionTrace`. It stays empty. The scripted `ExecutionTrace` cannot be projected onto that model when it records an attempt, so the two cannot disagree.

The shopper confirmation answer still says execution is not available and that no sources were checked. No new canonical decision snapshot is created. Sprint 41 stays UNSTARTED.

## Objective

Harden and consolidate certified connector behavior into production-grade cross-connector reliability and honest degradation — **not** introduce basic timeout/retry/failure handling for the first time (those minimum contracts are owned by Sprint 31 and validated per market in 32–36).

## Included requirements

- Shared production-grade circuit-breaker behavior across connectors
- Aggregated connector and market health
- Cross-merchant partial-result orchestration
- Stale-cache policy
- Stale-cache, degraded-mode, fallback, and refresh timing must **respect** merchant-specific certified TTL / freshness policy constraints from Sprint 31 model + 32–36 certification (must not override or weaken them)
- Connector synthetic probes
- Production alerting integration hooks
- Provider-status tracking
- Reliability consistency across all certified connectors
- No-merchants-available product behavior
- Incident runbook consolidation
- Production evidence across multiple connectors and markets
- Incomplete-coverage / degradation UI disclosures coordinated with Sprint 29 states
- AI-provider and affiliate-provider failure behavior
- Application readiness must not imply full merchant availability
- Fixture/simulated paths cannot be labeled live (release verification support for EC-21)
- Provide the production reliability and truthfulness contract for user-confirmed Conversational Continuity research.
- A research execution must have a real execution ID and evidence-backed queued, running, partial, completed, failed, or cancelled state.
- Connector, merchant, offer, price, review, freshness, and coverage statements must be derived from actual execution and certified provider capabilities.
- Repeated confirmations must not create duplicate research executions.
- Partial, stale, timeout, quota, connector-failure, and no-merchants-available outcomes must preserve the prior decision and degrade honestly.
- Own production live-research execution including: connector timeout behavior; retries where permitted; circuit breakers; partial failure; source health; degradation states; cache/freshness; research execution trace; attempted sources; succeeded sources; failed sources; timed-out sources; evaluated-offer count; truthful UI disclosure
- Shared ownership of live owner-bound decision creation: this sprint owns live execution; Sprint 31 owns routing; Sprint 29 owns snapshot presentation. Fixture-created UUIDs are not sufficient for Sprint 45.

### Hard live-mode rule

`SHOPPING_RESEARCH_EXECUTION_MODE=live` may not be production-enabled unless:

1. at least one relevant certified real connector exists for the requested supported market, and
2. truthful partial-failure/execution-trace handling is operational.

Mock remains non-production only.

## Explicit non-goals

- Owning the first appearance of timeout/retry/failure result types (31)
- Owning merchant contractual capability/policy interpretation or legal-terms mapping (31 model; 32–36 provider certification)
- Per-market legal certification (32–36)
- Multi-region active-active
- Guaranteeing provider SLOs

## External dependencies

- EXT-25

## Implementation deliverables

- Shared breaker/retry hardening wired across certified connectors
- Aggregated health model
- Probe jobs
- UI/API degradation fields for multi-connector failure
- Provider status process

## Documentation deliverables

- CONNECTOR_HEALTH updates
- Consolidated incident runbook RB-connector
- Provider status process

## Required tests

- Chaos across multiple connectors: timeout, 429, 5xx, credential fail
- Partial aggregation tests
- No-merchants-available path
- Fixture-as-live guard
- Cache/degradation/refresh paths do not exceed certified merchant TTL / freshness constraints

## Required staging evidence

- Probes green; multi-connector chaos drill recorded

## Required production evidence

- Alerts routed in 42

## Acceptance criteria

- Multi-connector chaos drill passes with honest user-visible degradation
- Aggregated health + kill switch disable merchants within agreed SLO
- `/ready` remains correct when merchants are down
- Consistency review across certified connectors signed
- Basic timeout/retry/failure handling is confirmed present from 31/32–36 — Sprint 38 evidence is hardening, not first introduction
- Stale-cache / degradation / fallback / refresh behavior respects certified merchant TTL/freshness policy constraints (does not invent or reinterpret merchant legal permissions)
- Confirmed Ask PiqSavi research uses the certified connector path and produces truthful, provenance-backed execution states.
- No research occurs before explicit confirmation.
- No timer, animation, fixture, or simulated count is accepted as evidence of live execution.
- Completed research returns a canonical updated-Results snapshot; failed or partial research does not silently replace the prior valid decision.
- `SHOPPING_RESEARCH_EXECUTION_MODE=live` is fail-closed unless a relevant certified real connector and truthful partial-failure/execution-trace handling exist
- Execution traces record attempted, succeeded, failed, and timed-out sources plus evaluated-offer count
- A real shopper request can create an owner-bound schema-current canonical decision from live certified evidence
- Mock remains non-production only

## Predecessor sprints

31 (contracts); ideally ≥1 market from 32–36 certified or in certification

## Parallelizable work

Remaining market certs; 39 analytics; 40 security prep

## Go / no-go gate

Go if multi-connector chaos + aggregated health + kill switch evidenced

## Rollback or contingency

Disable live connectors; fixture paths remain non-live

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
