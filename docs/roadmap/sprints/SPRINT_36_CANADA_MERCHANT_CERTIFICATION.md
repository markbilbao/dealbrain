# Sprint 36 — Canada Merchant Certification

**Status:** Planned
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name CA

## Objective

Certify at least one real Canada merchant-data path under the same bar as Sprint 32.

## Included requirements

- Same certification checklist as Sprint 32 applied to CA
- Implement and validate Sprint 31 minimum reliability contracts on the CA real path
- Record EN-only vs FR-CA scope dependency on Sprint 37 decision

## Explicit non-goals

- Completing all CA retailers
- Final FR-CA localization policy (37)
- Cross-connector hardening suite (38)

## External dependencies

- EXT-05
- EXT-06
- EXT-07

## Implementation deliverables

- CA connector/feed on unified platform

## Documentation deliverables

- CA coverage row
- Certification report
- FR-CA dependency note for Sprint 37

## Required tests

- Certification suite
- Failure modes via Sprint 31 contracts
- Freshness label tests

## Required staging evidence

- Real current-data response

## Required production evidence

- As Sprint 32

## Acceptance criteria

- At least one real, legally usable CA merchant path with current-data validation
- Market-specific normalization evidenced
- Staging certification complete; limited production validation prepared/executed as required
- Monitoring and public coverage disclosure published
- Kill switch tested
- FR-CA scope dependency recorded for Sprint 37
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**

## Predecessor sprints

31 (strict); may parallelize with other market sprints after 31

## Parallelizable work

32–35 if staffing allows

## Go / no-go gate

Go for CA naming iff AC met; else remove CA from supported list

## Rollback or contingency

Disable CA merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
