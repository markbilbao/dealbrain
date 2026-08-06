# Sprint 32 — Philippines Merchant Certification

**Status:** Planned
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name PH

## Objective

Certify at least one real, legally usable, operationally validated merchant-data path for the Philippines.

## Included requirements

- Full market path: provider selection, access application, legal/terms, credentials, sandbox (where available), real endpoint, mapping, matching, rate/quota/timeout/retry, failure modes, circuit-breaker hooks, provenance/freshness, shipping/availability, affiliate validation, monitoring, staging, limited rollout, production validation prep, public disclosure row
- Implement and validate Sprint 31 minimum reliability contracts on the PH real path (timeout, bounded retry, backoff, quota/credential/partial-failure types, health, kill switch, breaker baseline)

## Explicit non-goals

- US/SG/UK/CA certification
- Claiming complete PH retail coverage
- Cross-connector production hardening suite (38)

## External dependencies

- EXT-01
- EXT-06
- EXT-07

## Implementation deliverables

- PH connector/feed integration on unified platform

## Documentation deliverables

- PH coverage row
- Provider status notes
- Certification report

## Required tests

- Certification suite against real/sandbox
- Failure injection using Sprint 31 contracts
- Freshness label tests

## Required staging evidence

- Real current-data response evidenced

## Required production evidence

- Prod validation may complete in 45 if dry-run in 41/44

## Acceptance criteria

- At least one real, legally usable merchant path with current-data validation
- Market-specific normalization and product/variant matching evidenced
- Staging certification complete; limited production validation prepared/executed as required by gate
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**
- PH may be named only after this gate + claims approval

## Predecessor sprints

31 (unification + minimum reliability contracts) — **strict**

## Parallelizable work

33–36 (after 31)

## Go / no-go gate

Go for PH naming iff AC met; else remove PH from supported list

## Rollback or contingency

Disable PH merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
