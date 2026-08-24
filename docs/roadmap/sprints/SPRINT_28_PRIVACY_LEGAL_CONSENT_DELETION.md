# Sprint 28 — Privacy, Legal, Consent & Account Deletion

**Status:** Planned
**Primary owner / domain:** Legal + privacy engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-4

## Objective

Ship the consumer legal and privacy minimum: policies, consent records, deletion, export, retention, and contacts.

## Included requirements

- Terms of Service draft + Privacy Policy draft
- Cookie/tracking disclosure; analytics consent hooks
- Registration consent + policy-version acceptance records
- Account deletion + confirmation + propagation checklist
- Data export
- Data retention policy; PII inventory; vendor/DPA register
- Privacy contact + support contact published internally
- Minimum age policy; country-specific notice placeholders
- Start formal legal review (EXT-19)
- Search-index privacy policy: personalized/private decision URLs must not become public SEO pages
- Final counsel/approval gate remains Sprint 44/45; this sprint produces the package, not the launch signature

## Explicit non-goals

- Final marketing claim approval (44)
- Analytics provider full wiring (39)
- Native app store privacy questionnaires

## External dependencies

- EXT-17
- EXT-18
- EXT-19
- EXT-20
- EXT-21
- EXT-22

## Implementation deliverables

- Deletion/export APIs
- Consent/acceptance persistence
- Policy versioning fields

## Documentation deliverables

- Privacy/retention docs
- PII inventory
- Vendor register
- Deletion propagation runbook

## Required tests

- Deletion removes/obscures required PII
- Export completeness tests
- Consent required on register

## Required staging evidence

- Delete account E2E
- Export download E2E
- Consent records visible to admin/audit

## Required production evidence

- Publication URLs may wait for 44/45 after counsel approval

## Acceptance criteria

Launch acceptance explicitly covers:

- Terms of Service
- Privacy Policy
- cookie / consent policy
- consent persistence
- account deletion
- data export
- retention policy
- PII inventory
- vendor/data-processor register
- support/privacy contacts
- age/legal notices where applicable
- final counsel/approval gate in Sprint 44/45
- explicit search-index privacy policy: personalized/private decision URLs must not become public SEO pages

Also:

- Staging deletion and export pass
- Consent and policy-version records persisted
- Legal review engaged with dated packet
- Support and privacy contacts assigned

### Additive PiqSavi brand criteria (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Terms identify the consumer product as PiqSavi
- Privacy Policy identifies PiqSavi
- Public legal/privacy/support addresses use approved `@piqsavi.com` identities
- Legal copy does not expose DealBrain as the consumer product
- Technical/internal DealBrain references may remain where legally or operationally necessary and non-consumer-facing

## Predecessor sprints

27

## Parallelizable work

29 UI can consume consent/deletion endpoints

## Go / no-go gate

Go if staging privacy flows pass and counsel review started

## Rollback or contingency

Disable self-serve registration if policies not publishable

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
