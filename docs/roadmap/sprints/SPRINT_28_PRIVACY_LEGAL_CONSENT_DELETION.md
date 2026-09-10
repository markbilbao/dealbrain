# Sprint 28 — Privacy, Legal, Consent & Account Deletion

**Status:** **SPRINT 28 INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** 28.1 engineering foundations and 28.2 staging export/delete HTTP evidence remain in force. Remaining internally controllable readiness (consent/audit inspection, engineering retention map, essential-only tracking hook, eligibility placeholders, provisioned contact wiring, publication-status mechanics) is implemented. Owner-observed browser verification of the fail-closed legal/privacy state on `https://staging.piqsavi.com` is recorded for deployed SHA `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0` (2026-09-10). Sprint 28 is **not** COMPLETE/CLOSED. Counsel drafts remain unpublished. EXT-19 written **conditional** approval is recorded ([`../evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](../evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md)); written unconditional published-scope approval is absent. Register status remains `applied`. EXT-20 / EXT-21 publication remains `not_started`. EXT-22 remains `not_started` (no CMP/banner; Sprint 39 owns analytics activation). Sprint 44/45 publication gates remain open. Evidence: [`../evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md`](../evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md); counsel record [`../evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](../evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md); Early Access re-audit [`../evidence/EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md`](../evidence/EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md).
**Primary owner / domain:** Legal + privacy engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-4

## Internal vs external closeout

| Layer | Status |
|-------|--------|
| Internal engineering | **Complete** for currently controllable Sprint 28 requirements |
| Internal staging verification | **Complete** 2026-09-10 — owner-observed browser checks on `https://staging.piqsavi.com`, distinct from automated host `staging_ok` evidence |
| Staging engineering evidence | 28.2 export/delete HTTP recorded. Fail-closed empty consent state owner-verified 2026-09-10. Populated consent-audit rows **cannot** be recorded until a published policy version exists |
| Counsel approval (EXT-19 `approved`) | **Open** — written **conditional** 2026-08-19 review recorded; written unconditional published-scope approval absent; status remains `applied` |
| Policy publication (EXT-20 / EXT-21) | **Open** — `not_started` |
| Cookie CMP / analytics activation (EXT-22) | **Open** — `not_started`; owned with Sprint 39 for activation |
| Production launch acceptance | Sprint 44/45 |

Do **not** treat internal engineering complete or 2026-09-10 staging verification as legal compliance, publication, or P0-4 launch closure.

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
| EXT-19 legal review | `applied` — written **conditional** approval recorded; not `approved` |
| EXT-20 Privacy Policy publication | `not_started` |
| EXT-21 Terms publication | `not_started` |
| EXT-22 cookie-consent / CMP | `not_started` — banner **not** implemented; essential-only fail-closed hook only |
| Analytics providers | **not** added |
| Age gate / minimum age | **not** activated — fail-closed placeholder only; no invented age / no DOB |
| Staging delete/export E2E | recorded — [`../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md); HTTP evidence only, not legal certification |
| Consent / audit inspection | implemented — `GET /api/v1/auth/account/consents` + `GET /api/v1/legal/publication-status`; empty until a published version exists |
| Engineering retention map | implemented — [`../../privacy/ENGINEERING_RETENTION.md`](../../privacy/ENGINEERING_RETENTION.md); not a legal schedule |
| Support / privacy contacts | provisioned identities wired on `/support` (`support@piqsavi.com`, `privacy@piqsavi.com`) |
| Sprint 28 / P0-4 closure | **not closed** — internal engineering + staging verification complete; external legal/publication gates remain |

28.1 implements the engineering privacy foundation that can be completed before legal publication approval. Later internal-readiness work on this branch does **not** complete Sprint 28 as a launch gate. It does **not** publish counsel drafts. It does **not** record acceptance of an unpublished policy. Deletion/export are engineering APIs, not legal-compliance certification.


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
| EXT-19 legal review | `applied` — written **conditional** approval recorded; not `approved` |
| EXT-20 Privacy Policy publication | `not_started` |
| EXT-21 Terms publication | `not_started` |
| EXT-22 cookie-consent / CMP | `not_started` — banner **not** implemented |
| Analytics providers | **not** added |
| Age gate / minimum age | **not** activated |
| Staging delete/export E2E | recorded — [`../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md); HTTP evidence only, not legal certification |
| Sprint 28 / P0-4 closure | **not closed** — internal engineering + staging verification complete; external legal/publication gates remain |

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
- Consent/audit inspection (`GET /api/v1/auth/account/consents`)
- Publication-status mechanics (`GET /api/v1/legal/publication-status`)
- Essential-only tracking permission hook (no banner, no analytics provider)
- Fail-closed minimum-age / country-notice placeholders (no invented age)

## Documentation deliverables

- Privacy/retention docs — engineering retention map in [`../../privacy/ENGINEERING_RETENTION.md`](../../privacy/ENGINEERING_RETENTION.md)
- PII inventory
- Vendor register
- Deletion propagation runbook
- Consent audit inspection runbook — [`../../runbooks/CONSENT_AUDIT_INSPECTION.md`](../../runbooks/CONSENT_AUDIT_INSPECTION.md)

## Required tests

- Deletion removes/obscures required PII
- Export completeness tests
- Consent required on register when a published version exists; unpublished register stores none
- Consent/audit inspection is owner-scoped and empty while unpublished
- `/privacy` and `/terms` fail closed while unpublished

## Required staging evidence

- Delete account E2E — recorded in [`../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](../evidence/SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md)
- Export download E2E — recorded in the same package (`piqsavi.account_owned_export.v1`)
- Consent records visible to admin/audit — **tooling implemented**; live staging rows remain empty until a published policy version exists. Owner-verified empty consumer state recorded 2026-09-10. Template: [`../evidence/SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md`](../evidence/SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md). Do not publish counsel drafts to create those rows.
- Internal fail-closed legal/privacy staging verification — recorded in [`../evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md`](../evidence/SPRINT_28_INTERNAL_STAGING_VERIFICATION_2026-09-10.md). Owner browser checks; not publication.

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
- Consent/audit inspection tooling exists; live admin evidence of populated rows waits for publication
- Legal review engaged with dated packet
- Support and privacy contacts assigned (`support@piqsavi.com`, `privacy@piqsavi.com`)

Launch acceptance of published Terms/Privacy/cookie policy remains Sprint 44/45 after EXT-19 written approval of the **published** consumer documents. The 2026-08-19 signed record is written **conditional** approval only and is **not** that published-scope approval. Internal engineering complete does **not** satisfy those launch criteria.

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
