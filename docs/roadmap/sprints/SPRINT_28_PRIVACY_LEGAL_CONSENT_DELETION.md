# Sprint 28 — Privacy, Legal, Consent & Account Deletion

**Status:** In progress — 28.1 engineering foundations implemented; 28.2 staging export/delete HTTP evidence recorded. Sprint 28 is **not complete**. Counsel drafts remain unpublished. EXT-19 written approval is absent. EXT-20 / EXT-21 publication remains `not_started`. Sprint 44/45 publication gates remain open.
**Primary owner / domain:** Legal + privacy engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-4

## 28.1 record (owner slice)

| Area | Status |
|------|--------|
| Legal publication gate (`/privacy`, `/terms` fail closed) | implemented — no published production versions |
| Counsel markdown never auto-served as public HTML | implemented |
| Policy-version model (type, version, status, timestamps, acceptance-required) | implemented |
| Consent / policy-version persistence | implemented — records only when a published version exists |
| Registration does not fabricate unpublished acceptances | implemented |
| Account deletion API + password re-auth + confirmation + session revoke | implemented (engineering foundation) |
| Personal-data export API | implemented (engineering foundation) |
| Deletion propagation checklist | implemented — [`../../privacy/ACCOUNT_DELETION_PROPAGATION.md`](../../privacy/ACCOUNT_DELETION_PROPAGATION.md) |
| Engineering PII inventory | implemented — [`../../privacy/ENGINEERING_PII_INVENTORY.md`](../../privacy/ENGINEERING_PII_INVENTORY.md) |
| Engineering vendor inventory | implemented — [`../../privacy/ENGINEERING_VENDOR_INVENTORY.md`](../../privacy/ENGINEERING_VENDOR_INVENTORY.md) |
| Cookie factual refresh for counsel | implemented — [`../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md`](../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md); counsel draft **not** approved |
| Private UUID Results/Compare/Why noindex | implemented (`X-Robots-Tag` + meta robots) |
| Public landing indexability | unchanged (not noindex) |
| EXT-19 legal review | `applied` — written approval **not** present |
| EXT-20 Privacy Policy publication | `not_started` |
| EXT-21 Terms publication | `not_started` |
| EXT-22 cookie-consent / CMP | `not_started` — banner **not** implemented |
| Analytics providers | **not** added |
| Age gate / minimum age | **not** activated |
| Staging delete/export E2E | recorded — [`../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md); HTTP evidence only, not legal certification |
| Sprint 28 / P0-4 closure | **not closed** |

28.1 implements the engineering privacy foundation that can be completed before legal publication approval. It does **not** complete Sprint 28. It does **not** publish counsel drafts. It does **not** record acceptance of an unpublished policy. Deletion/export are engineering APIs, not legal-compliance certification.

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

- Delete account E2E — recorded in [`../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md)
- Export download E2E — recorded in the same package (`piqsavi.account_owned_export.v1`)
- Consent records visible to admin/audit — **not done** (no published policy version in staging; `/privacy` and `/terms` are 404)

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

- Staging deletion and export pass — 28.2 HTTP evidence recorded; not legal certification
- Consent and policy-version records persisted — still empty until a published version exists
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
