# Sprint 46 — Post-Launch Stabilization

**Status:** Planned
**Primary owner / domain:** Ops + product
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Program close

## Objective

Stabilize the Global Public Beta after an **approved** launch, complete learning reviews, and close the immediate post-launch program at Sprint 46. Sprint 47 is a later post-beta intelligence sprint and is **not** required to close Sprint 46.

**Hard rule:** Sprint 46 **cannot** be used to postpone unresolved Sprint 45 launch blockers until after public launch. Sprint 46 owns stabilization findings that arise after an approved launch, not pre-existing launch blockers.

## Included requirements

- Dedicated launch-monitoring handoff from Sprint 45
- Incident ownership handoff
- Sev 0/1/2 burn-down
- Product regressions; production incidents; UX blockers; connector failures; Recommendation trust problems; indexing/SEO problems; analytics sanity; capacity re-check; market coverage review; privacy/security post-check; launch-retrospective evidence
- Production error-budget review
- Connector health, freshness, and provenance review
- Merchant-data quality review
- Supported-market and merchant coverage review
- Rollback-readiness reaffirmation; verification that rollback evidence and authority remain valid
- Support-volume and support-response review
- Privacy deletion/export post-launch verification
- Analytics consent-state review
- Capacity re-check against actual beta traffic
- Public-claims drift review
- Monitor public brand/claim drift after launch (PiqSavi; not a new branding implementation sprint)
- Analytics learning cadence
- Post-beta backlog classification (WAF depth, Redis, multi-region, MFA/OAuth, more merchants, etc.)
- Program close report

## Explicit non-goals

- Expanding to new countries without new roadmap change-control
- Silent scope expansion
- **Using Sprint 46 to postpone unresolved Sprint 45 launch blockers until after public launch**
- Owning pre-existing launch blockers that should have failed Sprint 45 go/no-go
- Turning Sprint 46 into a new branding implementation sprint (brand authority remains [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md))
- Absorbing Sprint 47 buying-action intelligence as a launch prerequisite
- Observing SEO/indexing only as an optional extra — crawl errors, indexing failures, structured-data errors, page performance, organic traffic quality, unexpected private-route discovery, and claim/freshness problems are in scope

## External dependencies

- None

## Implementation deliverables

- Hotfixes only under IR
- Stabilization metrics pack

## Documentation deliverables

- Stabilization report covering all reviews above
- Rollback-readiness reaffirmation note
- Monitoring/incident handoff acceptance
- Endpoint closure note
- Post-beta backlog

## Required tests

- Regression on hotfixes
- Spot-check deletion/export still operable
- Consent-state sampling

## Required staging evidence

- Hotfix validation

## Required production evidence

- Stability window metrics
- Support volume/response stats
- Coverage and claims drift findings

## Acceptance criteria

- Agreed stability window completed without open Sev1
- All listed stabilization reviews filed (merchant-data quality; freshness/provenance; rollback readiness; support volume/response; privacy deletion/export; consent state; error budget; capacity vs actual; claims drift; market/merchant coverage)
- Launch-monitoring and incident ownership handoffs accepted
- Learning review minutes filed
- Post-beta backlog classified and approved
- Immediate post-launch program marked closed; Sprint 47 remains later/post-beta
- Explicit confirmation: no deferred Sprint 45 launch blockers were absorbed into Sprint 46

## Predecessor sprints

45 (approved launch)

## Parallelizable work

None

## Go / no-go gate

Close Global Public Beta program

## Rollback or contingency

Extend stabilization window; invoke rollback if Sev1 requires

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
- Sprint 46 owns stabilization findings that arise after an approved launch, not pre-existing launch blockers.
