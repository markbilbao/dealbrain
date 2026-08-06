# Sprint 31 — Merchant Platform Unification

**Status:** Planned
**Primary owner / domain:** Marketplace platform (coordinates Sprint 4 + 18; no silent ownership theft)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-1A

## Objective

Establish one canonical connector contract, registry, and market router, plus the shared minimum connector reliability contracts required before market certification sprints begin.

## Included requirements

### P1-1A — Canonical merchant registration/routing unification

- One canonical MerchantConnector boundary
- One MerchantRegistry
- One MarketRouter
- Sprint 4 / Sprint 18 routing reconciliation (dual-run allowed with hard end date)
- Duplicate-registration prevention
- Connector / credential configuration authority
- MerchantCapability + supported-market metadata hooks (policy decisions finalize in 37)
- Merchant-country mapping hooks
- Query-time and background-sync routing through one authority
- Normalized listing/offer contracts preserved
- Provenance + freshness required fields retained from Sprint 18
- Connector certification suite (sandbox/real gates)
- Merchant onboarding runbook; legal/terms checklist hooks
- Preserve DealScore / Recommendation / affiliate / sponsored boundaries

### Shared minimum connector reliability contracts (strict predecessor of 32–36)

Sprint 31 owns these contracts/interfaces (and a minimum baseline implementation where needed) so market sprints are not blocked waiting for Sprint 38:

- Timeout interface
- Bounded retry interface
- Exponential-backoff policy contract
- Quota / rate-limit result types
- Credential-failure result type
- Partial-failure result type
- Provenance / freshness contract
- Connector-health interface
- Kill-switch and feature-flag interface
- Circuit-breaker interface or minimum baseline implementation

Sprint 38 remains responsible for cross-connector production hardening and honest-degradation product behavior — not for inventing basic timeout/retry/failure handling.

## Explicit non-goals

- Redesigning DealScore/Recommendation
- Completing all five market live integrations (32–36)
- Unsupported-market product policy (P1-1B → 37)
- Shipping-cost honesty implementation (P1-2 → 37; 44 verifies wording)
- Cross-connector production hardening suite (38)
- Billing

## External dependencies

- None

## Implementation deliverables

- Unified registry/router
- Adapter shims if needed
- Reliability contract package + certification test harness
- Kill-switch / feature-flag hooks

## Documentation deliverables

- CONNECTOR_ARCHITECTURE unification ADR
- Reliability contract reference for market sprints
- Onboarding runbook
- Architecture Lock additive note if required

## Required tests

- Registry uniqueness
- Router market selection
- Reliability contract unit tests (timeout/retry/failure result types)
- Neutrality protected-module tests remain green
- Certification suite smoke

## Required staging evidence

- Unified path serves search/sync without fixture-as-live
- Kill-switch interface demonstrable

## Required production evidence

- Flags ready for later

## Acceptance criteria

- Single registration path enforced in code (P1-1A)
- Reliability contracts exported and documented for 32–36
- Certification suite runnable
- Architecture review recorded for 4/18 boundary
- Neutrality tests green

## Predecessor sprints

26

## Parallelizable work

29 late, EXT merchant follow-ups

## Go / no-go gate

Go if unification merged, reliability contracts published, and suite exists — else 32–36 blocked

## Rollback or contingency

Feature-flag unified router; keep dual-run

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
