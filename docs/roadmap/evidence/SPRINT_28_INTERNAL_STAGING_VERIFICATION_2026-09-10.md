# Sprint 28 — Internal engineering + staging verification (2026-09-10)

**Document type:** Dated reconciliation / evidence record (not a new feature design)  
**Sprint definition:** [`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md)  
**Prior engineering evidence (not rewritten):** [`SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md)  
**Consent-audit populated-row template (still blank):** [`SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md`](SPRINT_28_CONSENT_AUDIT_STAGING_TEMPLATE.md)  
**Reconciliation date:** 2026-09-10  
**Verified `origin/main` SHA:** `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0`  
**Final deployed SHA:** `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0`  
**Merge source:** PR #125 — Sprint 28: remove duplicate consent empty-state message  
**Production code changed by this record:** No  
**Merge performed:** No

**Resulting Sprint 28 maturity:** **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.**  
Sprint 28 is **not** COMPLETE/CLOSED.

This record does **not** rewrite 28.1 engineering foundations, 28.2 export/delete HTTP evidence, or the 2026-09-09 internal-engineering closeout as if those documents had always contained this verification.

No screenshots are invented or committed here. No owner personal email, account UUID, password, token, cookie, or other account-identifying data is recorded.

---

## 1. Verdict

| Question | Verdict |
|----------|---------|
| Close Sprint 28 / P0-4 now? | **No** |
| Internal engineering | **Complete** for currently controllable Sprint 28 requirements |
| Internal staging verification | **Complete** 2026-09-10 — owner-observed browser checks on `https://staging.piqsavi.com` |
| Automated host deploy evidence | `status=staging_ok` for this SHA (distinct from owner browser checks) |
| EXT-19 written unconditional approval | **Absent** — remains `applied`, not `approved` |
| EXT-20 / EXT-21 publication | **`not_started`** — `/privacy` and `/terms` remain HTTP 404 |
| EXT-22 CMP / analytics activation | **`not_started`** — no CMP/banner; Sprint 39 owns activation |
| Counsel drafts public? | **No** — no counsel draft was served |
| Further staging deploy after this docs PR? | **Not required** — this record is documentation/evidence only |

Do **not** treat internal engineering complete, host `staging_ok`, or owner fail-closed browser checks as legal compliance, publication, DSAR completeness, or P0-4 launch closure.

---

## 2. Evidence layers (do not collapse)

| Layer | What it proves | What it does not prove |
|-------|----------------|------------------------|
| Immutable build / release | PR #125 SHA was built as Build Image #106 and released as `rel-20260910T030346Z-fc8be5fe2abb` | Live browser behavior; legal publication |
| Authoritative host deployment | Deploy Staging #34 reported `status=staging_ok` for this SHA | Owner-observed consumer surfaces; counsel approval |
| Owner-observed browser checks | Live `https://staging.piqsavi.com` fail-closed legal/privacy state on 2026-09-10 | Automated host evidence; populated consent rows; legal DSAR |
| Engineering completion | 28.1 foundations + 28.2 export/delete HTTP + remaining internal readiness remain in force | EXT-19/20/21/22 closure |
| External legal/publication gates | Still open — see §7 | Nothing in this record closes them |

---

## 3. Immutable build / deployment evidence

Record only the owner-supplied identifiers. No other CI, job, S3, instance, or smoke-field identifiers are invented here.

| Field | Value |
|-------|-------|
| Final deployed `main` SHA | `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0` |
| Merge source | PR #125 — Sprint 28: remove duplicate consent empty-state message |
| Build Image | **#106** |
| Build Image workflow run | `34431847533` |
| Build Image status | `success` |
| Release ID | `rel-20260910T030346Z-fc8be5fe2abb` |
| Image digest | `sha256:7fadbea3c41fce984bb430bf18b320fd15eacedff10a6e212e72b1af2ea58534` |
| Manifest SHA-256 | `e57d424b9b8c0c50976fdac56fe9064e81e33634ce4e56ae6edf332094f71450` |

---

## 4. Authoritative host deployment evidence

This layer is host/workflow evidence. It is **not** the owner browser-verification layer in §5.

| Field | Value |
|-------|-------|
| Workflow | Deploy Staging |
| Deploy number | **#34** |
| Workflow run ID | `34432570543` |
| Status | `success` |
| Deployed SHA | `fc8be5fe2abb0c73e5db7389ce41c4d348f4ffa0` |
| Authoritative host status | `status=staging_ok` |
| Authoritative evidence SHA-256 | `7165c1ca36d3fd902d44a31ed7378aca1841105dadd6c9fb9199b957eb0b8365` |

---

## 5. Owner-observed browser checks (2026-09-10)

The owner manually verified the following on `https://staging.piqsavi.com` on 2026-09-10. These are **owner-observed browser checks**, distinct from automated host deployment evidence. No repository screenshots exist for this session.

Account-identifying data from the signed-in check is **not** recorded.

### 5.1 `/health`

Confirmed live staging returned:

| Field | Observed |
|-------|----------|
| `status` | `"up"` |
| `environment` | `"staging"` |
| `launch_readiness` | `true` |
| `identity_email_adapter` | `"resend"` |
| `identity_email_ready` | `true` |
| `legal_terms_published` | `false` |
| `legal_privacy_published` | `false` |
| `tracking_mode` | `"essential_only"` |
| `non_essential_tracking_allowed` | `false` |
| `minimum_age_policy_published` | `false` |

This proves the intended fail-closed legal/privacy state on the deployed SHA.

### 5.2 `/privacy`

Confirmed:

- HTTP 404 / Not Found
- No counsel draft was served

### 5.3 `/terms`

Confirmed:

- HTTP 404 / Not Found
- No counsel draft was served

### 5.4 `/api/v1/legal/publication-status`

Confirmed staging returned a truthful unpublished / privacy-safe state including:

| Field | Observed |
|-------|----------|
| `terms_published` | `false` |
| `privacy_published` | `false` |
| `terms_version_id` | `null` |
| `privacy_version_id` | `null` |
| `terms_acceptance_required` | `false` |
| `privacy_acceptance_required` | `false` |
| `cookie_notice_published` | `false` |
| `support_contact` | `"support@piqsavi.com"` |
| `privacy_contact` | `"privacy@piqsavi.com"` |
| `minimum_age_years` | `null` |
| `age_policy_published` | `false` |
| `collects_date_of_birth` | `false` |
| `country_notices_published` | `false` |
| `country_notice_count` | `0` |
| `enforced_at_registration` | `false` |
| `tracking_mode` | `"essential_only"` |
| `cmp_vendor` | `null` |
| `analytics_provider` | `null` |
| `essential_allowed` | `true` |
| `analytics_allowed` | `false` |
| `advertising_allowed` | `false` |
| `non_essential_tracking_allowed` | `false` |
| `banner_implemented` | `false` |

Also confirmed: the public response does **not** expose internal roadmap/engineering fields such as Sprint IDs, EXT IDs, `activation_owner`, or counsel workflow ownership.

### 5.5 `/support`

Confirmed the consumer-facing Support page is clean and exposes only:

- `support@piqsavi.com`
- `privacy@piqsavi.com`

It contains no Sprint / EXT / counsel / internal engineering terminology.

### 5.6 Signed-in `/account#consents`

Confirmed:

- account is authenticated
- Privacy and consent section loads
- zero policy acknowledgement records are displayed while no approved policies are published
- consumer empty state appears exactly once: `There are no policy acknowledgements recorded for this account yet.`

---

## 6. Existing Sprint 28 engineering evidence (preserved)

The following remain repository truth and are **not** reinterpreted by this record:

| Area | Status |
|------|--------|
| 28.1 engineering foundations | implemented |
| 28.2 staging export/delete HTTP evidence | recorded — [`SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md`](SPRINT_28_2_STAGING_EXPORT_DELETION_EVIDENCE.md) |
| Authenticated account deletion with password re-auth and `DELETE` confirmation | implemented + 28.2 HTTP |
| Session revocation | implemented + 28.2 HTTP |
| Account-owned engineering export | implemented + 28.2 HTTP (`piqsavi.account_owned_export.v1`) |
| Deletion propagation runbook | implemented — [`../../privacy/ACCOUNT_DELETION_PROPAGATION.md`](../../privacy/ACCOUNT_DELETION_PROPAGATION.md) |
| Engineering PII inventory | implemented — [`../../privacy/ENGINEERING_PII_INVENTORY.md`](../../privacy/ENGINEERING_PII_INVENTORY.md) |
| Engineering vendor inventory | implemented — [`../../privacy/ENGINEERING_VENDOR_INVENTORY.md`](../../privacy/ENGINEERING_VENDOR_INVENTORY.md) |
| Engineering retention map | implemented — [`../../privacy/ENGINEERING_RETENTION.md`](../../privacy/ENGINEERING_RETENTION.md) |
| Cookie/storage factual inventory | implemented — [`../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md`](../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md) |
| Private Results/Compare/Why noindex | implemented |
| Versioned policy architecture | implemented |
| Fail-closed legal publication | implemented and owner-verified live 2026-09-10 |
| No fabricated acceptance | implemented and owner-verified empty acknowledgements 2026-09-10 |
| Consent persistence | implemented — records only when a published version exists |
| Authenticated consent audit inspection | implemented |
| Essential-only tracking default | implemented and owner-verified live 2026-09-10 |
| No active analytics provider | implemented and owner-verified live 2026-09-10 |
| No CMP/banner | implemented and owner-verified live 2026-09-10 |
| Fail-closed age/country placeholders | implemented and owner-verified live 2026-09-10 |
| Provisioned support/privacy contacts | implemented and owner-verified on `/support` 2026-09-10 |

Engineering export is **not** a complete legal DSAR.  
Deletion is **not** universal destruction of every backup, log, vendor, or legal-retention record.

---

## 7. External dependency truth — remains open

| ID | Status | Meaning for this record |
|----|--------|-------------------------|
| EXT-17 | `provisioned` | Support inbox bootstrap remains provisioned. Unchanged. |
| EXT-18 | `provisioned` | Privacy contact bootstrap remains provisioned. Unchanged. |
| EXT-19 | `applied` | Written unconditional counsel approval is **absent**. Not `approved`. |
| EXT-20 | `not_started` | Privacy Policy is **not** publicly published. |
| EXT-21 | `not_started` | Terms are **not** publicly published. |
| EXT-22 | `not_started` | Cookie/CMP activation is **not** complete. |

No counsel draft is approved merely because engineering is ready or because staging fail-closed verification passed.

---

## 8. Legal publication boundary

Counsel drafts under `docs/legal/` remain unpublished. This record does **not**:

- move or copy drafts into a published state
- publish `.html` policy files
- make `/privacy` or `/terms` live
- fabricate policy versions
- fabricate publication dates
- fabricate user consent rows
- fabricate counsel approval
- claim production legal acceptance

`/privacy` and `/terms` must remain intentionally fail-closed until approved published policy HTML exists.

---

## 9. Non-claims

This 2026-09-10 record does **not** claim:

- Sprint 28 COMPLETE/CLOSED
- P0-4 launch closure
- EXT-19 `approved`
- EXT-20 / EXT-21 / EXT-22 complete
- published Privacy Policy or Terms
- CMP/banner implementation
- analytics provider activation
- legal DSAR completeness
- universal erasure of backups, logs, vendors, or statutory-retention records
- production legal acceptance
- that a further staging deploy is required after this documentation-only PR
