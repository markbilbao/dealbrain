# Sprint 31 — Merchant Platform Unification

**Status:** Formally owner-closed. Historical gate satisfied; Sprint 32 is now in progress and is **not complete**. The research execution router / provider contract remains merged (planning-only). Provider capability, trusted certification, and trusted routing policy remain distinct authorities (production catalogs empty). Live execution remains **not implemented**. Sprints 32–36 still own provider/market certification evidence.

**Architecture:** [`../../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md`](../../architecture/SPRINT_31_RESEARCH_EXECUTION_ROUTER.md)
**Unification ADR / 4/18 review:** [`../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md)
**Onboarding runbook:** [`../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)
**Primary owner / domain:** Marketplace platform (coordinates Sprint 4 + 18; no silent ownership theft)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P1-1A

## Objective

Establish one canonical connector contract, registry, and market router, plus the shared minimum connector reliability contracts and the shared merchant contractual capability/policy model required before market certification sprints begin.

## Included requirements

### P1-1A — Canonical merchant registration/routing unification

- One canonical MerchantConnector boundary
- One MerchantRegistry
- One MarketRouter
- Sprint 4 / Sprint 18 routing reconciliation (dual-run allowed with hard end date)
- Duplicate-registration prevention
- Connector / credential configuration authority
- MerchantCapability + supported-market metadata hooks (unsupported-market product policy decisions finalize in 37)
- Merchant contractual capability/policy model (see below; distinct from technical `ConnectorCapability`)
- Merchant-country mapping hooks
- Query-time and background-sync routing through one authority
- Normalized listing/offer contracts preserved
- Provenance + freshness required fields retained from Sprint 18
- Connector certification suite (sandbox/real gates), including capability-policy harness expectations
- Canonical connector registry
- Router / orchestrator
- Capability-policy enforcement
- Source eligibility
- Fail-closed provider selection
- Research execution contracts
- Kill-switch hooks
- Provenance / execution-trace contracts
- Merchant onboarding runbook; legal/terms checklist hooks (non-secret evidence references only)
- Preserve DealScore / Recommendation / affiliate / sponsored boundaries
- No unsupported provider may be presented as searched

### Merchant contractual capability / policy model (shared predecessor of 32–36)

Sprint 31 owns the **shared contractual/policy layer** that market certification sprints populate with provider-specific evidence. Implementation design (types, names, storage shape) is owned by Sprint 31 and must not be conflated with technical adapter capabilities.

**Principles (roadmap-locked):**

1. **Affiliate permission ≠ product-data permission.** A provider relationship may authorize affiliate monetization without authorizing every form of data ingestion, display, transformation, comparison, AI processing, caching, or scoring. An authorized data path may participate organically when affiliate monetization is unavailable.
2. **Provider approval ≠ blanket capability approval.** Account/API/partner approval alone must not automatically enable every connector capability. Each production capability requires relevant merchant/API/program terms or other evidence.
3. **Technical ability ≠ contractual permission.** Existing technical `ConnectorCapability` (and equivalent operation declarations) describe what an adapter can perform. The contractual/policy layer describes whether PiqSavi is **authorized** to perform, use, or expose that function for the relevant merchant/market.
4. **Fail closed.** Unknown or unverified merchant permission must not silently enable production functionality. Conceptual policy states include `allowed`, `restricted`, `prohibited`, and `unknown` (final names/types are Sprint 31 design decisions).
5. **Affiliate neutrality remains locked.** Affiliate commission, partner priority, conversion economics, or affiliate availability must never increase DealScore / PiqScore or objective ranking. Capability policy must not couple monetization into scoring.
6. **Upstream payload presence ≠ permission.** The unified platform must not treat presence of upstream fields (reviews, images, ratings, etc.) as authorization to expose or use them.

**Policy model must be able to represent, as applicable (not every provider must support every item):**

- product / offer retrieval; product search
- price display; availability display
- image / rating / review display
- product caching; offer caching; TTL / freshness constraints
- normalization / transformation
- AI summarization / explanation use of merchant content
- cross-merchant comparison; derived scoring inputs from merchant content
- affiliate links; affiliate redirect / attribution
- source attribution; branding / disclosure obligations
- country / market scope
- post-termination disablement or deletion obligations

**Reduced modes remain possible** and must be representable:

- Data/compare permitted, affiliate not permitted → organic comparison/ranking may operate without monetization.
- Affiliate permitted, product-data comparison not permitted → provider may serve only as an affiliate destination in a permitted flow; it must not be represented as a real current-data comparison path and cannot independently satisfy EC-09 market naming.

**Evidence / legal boundary (non-secret only):**

- Evidence may come from official published merchant/API documentation, contract/program terms, provider confirmation, and legal counsel confirmation for contested/high-risk interpretations.
- Engineering may conservatively mark capabilities `unknown` or `prohibited` without counsel.
- Engineering interpretation is **not** professional legal approval.
- Sensitive/high-risk uses (reviews; AI reuse of merchant content; comparison where terms are ambiguous; caching beyond explicit documentation; material transformation rights) remain `unknown` / `restricted` unless supported by suitable evidence.
- Do not store privileged legal advice in Git — only non-secret operational conclusions and evidence references.

**Enforcement / harness expectations:**

- Fail-closed policy enforcement interface/hooks for production paths
- Per-provider / per-market policy metadata
- Certification harness expectations so 32–36 can validate declared capabilities against real paths
- No scoring-model coupling; affiliate attachment remains outside DealScore / Recommendation

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

Sprint 38 remains responsible for cross-connector production hardening and honest-degradation product behavior — not for inventing basic timeout/retry/failure handling, and not for owning merchant legal-policy interpretation.

## Explicit non-goals

- Redesigning DealScore/Recommendation
- Completing all five market live integrations (32–36)
- Unsupported-market product policy (P1-1B → 37)
- Shipping-cost honesty implementation (P1-2 → 37; 44 verifies wording)
- Cross-connector production hardening suite (38)
- Populating provider-specific capability evidence (32–36)
- Billing

## External dependencies

- None

## Implementation deliverables

- Unified registry/router
- Adapter shims if needed
- Reliability contract package + certification test harness
- Kill-switch / feature-flag hooks
- Contractual capability/policy model + fail-closed enforcement hooks (design owned here; provider evidence later)

## Documentation deliverables

- CONNECTOR_ARCHITECTURE unification ADR (must distinguish technical capabilities from contractual/policy authorization) — recorded in [`../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md). “4/18” means Sprint 4 search versus Sprint 18 sync, not “4 of 18 items.” Dual-run remains. September 15, 2026 disposition recorded 2026-09-05: retain intentional dual implementations. Sprint 31 remains formally closed.
- Reliability contract reference for market sprints — exported types plus router / ADR notes
- Onboarding runbook including legal/terms evidence checklist (non-secret) — [`../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)
- Architecture Lock additive note if required — see Architecture Lock §15

## Required tests

- Registry uniqueness
- Router market selection
- Reliability contract unit tests (timeout/retry/failure result types)
- Neutrality protected-module tests remain green
- Certification suite smoke
- Capability-policy contract / fail-closed harness tests (unknown/prohibited must not enable production features; upstream payload presence alone insufficient)

## Required staging evidence

- Unified path serves search/sync without fixture-as-live
- Kill-switch interface demonstrable
- Capability-policy enforcement hooks demonstrable on unified path (provider-specific population may remain deferred to 32–36)

## Required production evidence

- Flags ready for later

## Acceptance criteria

- Single registration path enforced in code (P1-1A)
- Reliability contracts exported and documented for 32–36
- Contractual capability/policy model exported and documented for 32–36, explicitly separated from technical `ConnectorCapability`
- Fail-closed unknown/unverified permission behavior defined and harness-tested
- Unified platform cannot treat presence of upstream data as permission to expose/use that data
- Certification suite runnable, including capability-policy expectations
- Architecture review recorded for 4/18 boundary
- Neutrality tests green (affiliate/monetization remains outside DealScore / objective ranking)
- Canonical registry/router/orchestrator is the only production selection path
- Source eligibility and fail-closed provider selection are enforced
- Research execution, provenance, and execution-trace contracts are exported for Sprint 38
- No unsupported provider may be presented as searched
- Shared ownership of live owner-bound decision creation: this sprint owns routing/eligibility; Sprint 29 owns snapshot presentation; Sprint 38 owns live execution

## Predecessor sprints

26

## Parallelizable work

29 late, EXT merchant follow-ups

## Go / no-go gate

Go if unification merged, reliability contracts published, capability/policy model + fail-closed harness expectations published, and suite exists — else 32–36 blocked.

Closure evidence for the remaining documentation P0 items was implemented and later owner-closed. Sprint 32 is now in progress; it remains blocked on external merchant certification, not on Sprint 31.

## Rollback or contingency

Feature-flag unified router; keep dual-run

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
