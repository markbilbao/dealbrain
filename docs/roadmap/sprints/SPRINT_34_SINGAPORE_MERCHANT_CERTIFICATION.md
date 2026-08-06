# Sprint 34 — Singapore Merchant Certification

**Status:** Planned
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name SG

## Objective

Certify at least one real Singapore merchant-data path under the same bar as Sprint 32.

## Included requirements

- Same certification checklist as Sprint 32 applied to SG
- Implement and validate Sprint 31 minimum reliability contracts on the SG real path

## Explicit non-goals

- Completing all SG retailers
- Cross-connector hardening suite (38)

## External dependencies

- EXT-03
- EXT-06
- EXT-07

## Implementation deliverables

- SG connector/feed on unified platform

## Documentation deliverables

- SG coverage row
- Certification report

## Required tests

- Certification suite
- Failure modes via Sprint 31 contracts
- Freshness label tests

## Required staging evidence

- Real current-data response

## Required production evidence

- As Sprint 32

## Acceptance criteria

- At least one real, legally usable SG merchant path with current-data validation
- Market-specific normalization evidenced
- Staging certification complete; limited production validation prepared/executed as required
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**

## Predecessor sprints

31 (strict); may parallelize with other market sprints after 31

## Parallelizable work

32–33, 35–36 if staffing allows

## Go / no-go gate

Go for SG naming iff AC met; else remove SG from supported list

## Rollback or contingency

Disable SG merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
