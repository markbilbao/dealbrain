# Sprint 38 — Connector Reliability & Honest Degradation

**Status:** Planned
**Primary owner / domain:** Marketplace reliability / ops
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes with live HTTP / multi-connector launch

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
