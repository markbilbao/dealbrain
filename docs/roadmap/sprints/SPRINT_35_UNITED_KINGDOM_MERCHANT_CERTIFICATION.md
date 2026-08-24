# Sprint 35 — United Kingdom Merchant Certification

**Status:** Planned
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name UK

## Objective

Certify at least one real United Kingdom merchant-data path under the same bar as Sprint 32.

## Included requirements

- Same certification checklist as Sprint 32 applied to UK, including Sprint 32’s merchant capability / authorization evidence bar
- Implement and validate Sprint 31 minimum reliability contracts on the UK real path
- Populate and certify Sprint 31 merchant contractual capability/policy metadata for the UK real path (provider/market-scoped; fail-closed when unknown)

## Explicit non-goals

- Completing all UK retailers
- Cross-connector hardening suite (38)
- Owning the shared capability/policy contract design (Sprint 31)

## External dependencies

- EXT-04
- EXT-06
- EXT-07

## Implementation deliverables

- UK connector/feed on unified platform

## Documentation deliverables

- UK coverage row
- Certification report including capability-policy evidence map (non-secret)

## Required tests

- Certification suite
- Failure modes via Sprint 31 contracts
- Freshness label tests
- Capability-policy enforcement validation (as Sprint 32)

## Required staging evidence

- Real current-data response

## Required production evidence

- As Sprint 32

## Acceptance criteria

- At least one real, legally usable UK merchant path with current-data validation
- Market-specific normalization evidenced
- Sprint 31 contractual capability/policy metadata populated, evidence-backed, and enforcement-validated for that path (fail-closed for unknown; stages not collapsed — see Sprint 32)
- Staging certification complete; limited production validation prepared/executed as required
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**
- Failure of UK certification removes/delays UK only; it does not necessarily delay Sprint 45 if another certified useful market exists
- Sprint 45 does not require all five planned markets

## Predecessor sprints

31 (unification + reliability + capability/policy model) — **strict**; may parallelize with other market sprints after 31

## Parallelizable work

32–34, 36 if staffing allows

## Go / no-go gate

Go for UK naming iff AC met; else remove UK from supported list

## Rollback or contingency

Disable UK merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
