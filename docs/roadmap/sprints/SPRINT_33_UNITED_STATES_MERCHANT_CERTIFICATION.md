# Sprint 33 — United States Merchant Certification

**Status:** Planned
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name US

## Objective

Certify at least one real US merchant-data path under the same bar as Sprint 32.

## Included requirements

- Same certification checklist as Sprint 32 applied to US (provider selection through disclosure), including Sprint 32’s merchant capability / authorization evidence bar
- Implement and validate Sprint 31 minimum reliability contracts on the US real path
- Populate and certify Sprint 31 merchant contractual capability/policy metadata for the US real path (provider/market-scoped; fail-closed when unknown)

## Explicit non-goals

- Completing all US retailers
- Cross-connector hardening suite (38)
- Owning the shared capability/policy contract design (Sprint 31)

## External dependencies

- EXT-02
- EXT-06
- EXT-07

## Implementation deliverables

- US connector/feed on unified platform

## Documentation deliverables

- US coverage row
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

- At least one real, legally usable US merchant path with current-data validation
- Market-specific normalization evidenced
- Sprint 31 contractual capability/policy metadata populated, evidence-backed, and enforcement-validated for that path (fail-closed for unknown; stages not collapsed — see Sprint 32)
- Staging certification complete; limited production validation prepared/executed as required
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**

## Predecessor sprints

31 (unification + reliability + capability/policy model) — **strict**; may parallelize with 32/34/35/36 after 31

## Parallelizable work

32, 34–36 if staffing allows

## Go / no-go gate

Go for US naming iff AC met; else remove US from supported list

## Rollback or contingency

Disable US merchant flag

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
