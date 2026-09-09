# Consent / publication audit inspection (Sprint 28)

**Audience:** operators inspecting whether consent records exist once a published policy version exists.
**Not:** a public admin dashboard, a complete legal DSAR, or permission to publish counsel drafts.

## Public publication-status API (unauthenticated)

`GET /api/v1/legal/publication-status` exposes product state only:

- `terms_published` / `privacy_published` and published version ids
- acceptance-required flags
- provisioned `support_contact` / `privacy_contact`
- `tracking_mode` / `non_essential_tracking_allowed`
- minimum-age policy published state

It does **not** expose EXT-*, Sprint ownership, counsel-workflow flags, or
`counsel_drafts_are_not_public`. Those remain operator/internal evidence.

`GET /health` still reports `checks.legal_terms_published` /
`legal_privacy_published` for operators.

## Operator snapshot

```text
python scripts/privacy/inspect_publication_status.py
```

The operator snapshot additionally records Sprint 28 closeout evidence:

- `counsel_drafts_are_not_public=true`
- `ext_22_status=not_started`
- `activation_owner=sprint_39`
- `counsel_owned=true`

Production/staging product truth today:

- `terms_published=false`
- `privacy_published=false`
- `tracking_mode=essential_only`
- `non_essential_tracking_allowed=false`
- `minimum_age_policy_published=false` (health) / `age_policy_published=false` (public API)

`/privacy` and `/terms` remain HTTP 404 until EXT-20 / EXT-21.

## Owner-scoped consent records (after authentication)

`GET /api/v1/auth/account/consents` returns the **caller's** records only.
Client-supplied `user_id` is ignored. When no published policy exists the
`records` array is empty and `unpublished=true`.

Account settings `/account#consents` renders the same payload after sign-in
using consumer wording. The engineering/DSAR boundary stays in this runbook:
the inspection is not a complete legal DSAR, and unpublished catalogs must
not fabricate acceptance records.

## Staging procedure (execute only after a published version exists)

Do **not** seed or publish counsel drafts to run this. Wait for owner
publication of approved HTML under `docs/legal/published/` plus env version ids.

1. Confirm `GET /privacy` and `GET /terms` return 200 for the approved HTML (not counsel-draft markers).
2. Confirm `GET /api/v1/legal/publication-status` reports the published version ids.
3. Register a synthetic `@example.invalid` account with required acceptance.
4. `GET /api/v1/auth/account/consents` with that account's bearer token.
5. Confirm `records` contain server-owned `terms` and `privacy` version ids and timestamps.
6. Confirm a second synthetic account cannot see the first account's records.
7. Record sanitized evidence in the template
   [`../roadmap/evidence/SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md`](../roadmap/evidence/SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md).

Until step 1 is possible, consent rows **must** remain empty. That empty state is correct, not a defect.

## Explicit non-claims

- Does not mark EXT-19 approved
- Does not publish Privacy/Terms
- Does not invent acceptance records
- Does not activate analytics or a CMP (EXT-22 / Sprint 39)
