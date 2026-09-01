# Sprint 32 — Philippines Merchant Certification

**Status:** In progress — 32.1 complete; 32.2 trusted certification decision path implemented. Sprint 32 is **not complete**.
**Primary owner / domain:** Marketplace eng + legal
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes to name PH
**32.1 inventory:** [`../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md`](../evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md)

## Objective

Certify at least one real, legally usable, operationally validated merchant-data path for the Philippines.

## Included requirements

- Full market path: provider selection, access application, legal/terms, credentials, sandbox (where available), real endpoint, mapping, matching, rate/quota/timeout/retry, failure modes, circuit-breaker hooks, provenance/freshness, shipping/availability, affiliate validation, monitoring, staging, limited rollout, production validation prep, public disclosure row
- Implement and validate Sprint 31 minimum reliability contracts on the PH real path (timeout, bounded retry, backoff, quota/credential/partial-failure types, health, kill switch, breaker baseline)
- Populate and certify Sprint 31 merchant contractual capability/policy metadata for the PH real path (provider/market-scoped; fail-closed when unknown)

### Merchant capability / authorization evidence (shared bar for 32–36)

Each real merchant/provider path used for certification must record non-secret operational facts for:

- provider identity
- market
- relevant program / agreement / API policy identifier
- review / evidence date
- capability policy (conceptual states: allowed / restricted / prohibited / unknown — final names per Sprint 31 design)
- restrictions and applicable TTL / freshness requirements
- attribution / disclosure requirements where relevant
- evidence source / reference
- enforcement validation against the Sprint 31 harness

Certification stages must remain distinct (do not collapse):

1. application submitted
2. provider approved
3. credentials issued
4. technical connection works
5. capabilities legally/contractually usable (evidence-backed; not inferred from approval alone)
6. production certified

**Rules:**

- Provider approval does **not** automatically authorize every capability.
- Affiliate permission and product-data permission are independent.
- Unknown / unverified permissions fail closed and do not enable production features.
- Sensitive/high-risk uses (reviews; AI reuse; ambiguous comparison rights; caching beyond explicit documentation; material transformation) remain unknown/restricted unless suitable evidence exists.
- Engineering interpretation ≠ professional legal approval; contested items need stronger evidence/counsel confirmation.
- Do not store privileged legal advice in Git.
- Reduced capability modes are allowed when explicitly certified (e.g. data/compare without affiliate; affiliate destination without current-data comparison). Affiliate-only paths cannot independently satisfy EC-09 market naming.
- **Fixtures, mocks, imported samples, or simulations cannot satisfy production merchant capability certification.**

## Explicit non-goals

- US/SG/UK/CA certification
- Claiming complete PH retail coverage
- Cross-connector production hardening suite (38)
- Owning the shared capability/policy contract design (Sprint 31)

## External dependencies

- EXT-01
- EXT-06
- EXT-07

## Implementation deliverables

- PH connector/feed integration on unified platform

## Documentation deliverables

- PH coverage row
- Provider status notes
- Certification report including capability-policy evidence map (non-secret)
- 32.1 PH source certification inventory (foundational; does not close this sprint)

## Required tests

- Certification suite against real/sandbox
- Failure injection using Sprint 31 contracts
- Freshness label tests
- Capability-policy enforcement validation (unknown/prohibited fail closed; reduced modes behave as declared)

## Required staging evidence

- Real current-data response evidenced

## Required production evidence

- Prod validation may complete in 45 if dry-run in 41/44

## Acceptance criteria

- At least one real, legally usable merchant path with current-data validation
- Market-specific normalization and product/variant matching evidenced
- Sprint 31 contractual capability/policy metadata populated, evidence-backed, and enforcement-validated for that path (fail-closed for unknown)
- Certification report distinguishes application / approval / credentials / technical connectivity / contractual usability / production certification
- Staging certification complete; limited production validation prepared/executed as required by gate
- Monitoring and public coverage disclosure published
- Kill switch tested
- **Fixtures, mocks, imported samples, or simulations cannot close this sprint**
- PH may be named only after this gate + claims approval
- Each named market requires: at least one legally usable real source path; current-data evidence; capability-policy evidence; credential/provider approval; truthful coverage definition; staging/limited production proof where required
- Failure of PH certification removes/delays PH only; it does not necessarily delay Sprint 45 if another certified useful market exists
- Sprint 45 does not require all five planned markets

## Predecessor sprints

31 (unification + minimum reliability contracts + capability/policy model) — **strict**; owner-closed. 32.1–32.2 do not reopen Sprint 31 contracts.

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
