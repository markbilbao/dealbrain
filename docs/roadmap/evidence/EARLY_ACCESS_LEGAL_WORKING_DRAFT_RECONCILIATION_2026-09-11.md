# Early Access — August 25 working-draft reconciliation

**Date recorded:** 2026-09-11
**Audited `origin/main` SHA:** `5eadebda0ea6952ab37d6fb34825beff0e6c2ea7`
**Scope:** Ingest the owner-supplied August 25 working-draft package and decide whether Early Access Privacy/Terms publication + link activation is now evidence-supported
**Not in scope:** public shopping beta, Sprint 32 merchant certification, Shopee/Lazada/BuyWhere integrations, live merchant research, Sprints 31–38 research execution, PiqScore / Recommendation logic, affiliate monetization, production shopping Results, production infrastructure cutover

**Authority:** [`EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) · [`EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md`](EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md) · [`EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md) · [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md) · [`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md)

This record does **not** rewrite the 2026-09-10 reconciliation or the earlier 2026-09-11 activation attempt. Those records remain truthful for the workspaces that did **not** have the August 25 package. This follow-up starts from the actual owner-supplied files now present in this agent workspace.

This record does **not** infer privileged advice. Exact written edits / implementation conditions remain **condition not explicitly documented in sanitized record**.

---

## Resulting state

**EARLY ACCESS LEGAL ACTIVATION BLOCKED — COUNSEL CONDITION REMAINS UNRESOLVED**

This is **not**:

`EARLY ACCESS LEGAL PUBLICATION READY — PRODUCTION INFRASTRUCTURE CUTOVER REMAINS`

The August 25 package is now in the repository as review-only markdown. Privacy and Terms were **not** published. Early Access legal links were **not** activated. Assent copy was **not** added. EXT-19/20/21 statuses are unchanged.

---

## 1. Source documents actually inspected

| Identifier / document | Version available in this workspace | Date / markers | Used as publication source? |
|-----------------------|-------------------------------------|----------------|-----------------------------|
| Signed Aug 19 counsel record (PDF) | **No signed PDF.** Owner also uploaded a blank unsigned review-form PDF (`PiqSavi Comprehensive Legal Document Review and Approval Record`) with empty disposition checkboxes. Extractable text includes the overall line “Cleared to proceed only after specified revisions / implementation conditions are completed.” | Form title matches the sanitized record. Checkboxes are unmarked in extractable text. | **No.** Sanitized Aug 19 record remains counsel-disposition authority. Blank form is **not** treated as a new signed approval. |
| `EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md` | Yes — repository sanitized record | Recorded 2026-09-10 | Yes, as counsel-disposition authority |
| `PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT` | **Yes** — owner-supplied DOCX transcribed to [`../../legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md`](../../legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md) | Body Last Updated: August 25, 2026. DOCX last modified 2026-09-04 by Sambuang, Pauline Anne S. Tracked insertions present. | **Inspected. Not published.** |
| `PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT` | **Yes** — [`../../legal/PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT.md`](../../legal/PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT.md) | Same Last Updated. DOCX last modified 2026-09-04 by Sambuang, Pauline Anne S. Tracked insertions and one deletion present. | **Inspected. Not published.** |
| `PIQSAVI_COOKIE_TRACKING_NOTICE_WORKING_DRAFT` | **Yes** | Same Last Updated. Counsel last-modified 2026-09-04. | **Inspected. Not published.** |
| `PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_WORKING_DRAFT` | **Yes** | Same Last Updated. Counsel last-modified 2026-09-04. | **Inspected. Not published.** |
| `PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_WORKING_DRAFT` | **Yes** | Same Last Updated. Counsel last-modified 2026-09-04. | **Inspected. Not published.** |
| `PIQSAVI_ACCOUNT_DELETION_DATA_EXPORT_RETENTION_POLICY_WORKING_DRAFT` | **Yes** | Body Last Updated August 25, 2026. No tracked revisions in the DOCX. | **Inspected. Not a public page.** |
| `PIQSAVI_CONSUMER_MARKETPLACE_DISCLAIMER_WORKING_DRAFT` | **Yes** | Same Last Updated. Counsel last-modified 2026-09-04. | **Inspected. Not published.** |
| `PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT` (Aug 25 copy) | **Yes** — owner-supplied DOCX inspected. Intake note: [`../../legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_AUG25_INTAKE.md`](../../legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_AUG25_INTAKE.md). Structured engineering copy remains the existing counsel-draft markdown. | DOCX last modified 2026-08-25 by Mark Bilbao. Still labeled counsel-draft fact spec / not a published policy. | **Internal fact spec only.** |
| `docs/legal/*_COUNSEL_DRAFT.md` | Yes — earlier counsel-draft markdown | `DRAFT — COUNSEL REVIEW REQUIRED`; many `[COUNSEL TO CONFIRM]` | **Not treated as the August 25 package. Not published.** |

Owner-supplied DOCX files were **not** copied into `docs/legal/published/` or any web-serving path. Transcriptions are markdown review copies only.

---

## 2. Privacy / Terms reconciliation matrix

| Document | Reviewed disposition (Aug 19 sanitized record) | Material changes in Aug 25 working draft vs in-repo counsel draft | Condition addressed? | Remaining ambiguity | Publishable now? |
|----------|-----------------------------------------------|------------------------------------------------------------------|----------------------|---------------------|------------------|
| Privacy Policy / Privacy Notice | Reviewed — approved subject to written edits/conditions | Removes draft-only / `[COUNSEL TO CONFIRM]` markers. Sets Last Updated August 25, 2026. Adds a third-party-received-information section and third-party use-limitation wording. Keeps public identity as PiqSavi / “Your AI Personal Shopper.” Still states no advertising/analytics cookies, pixels, GA, or GTM. Still states no `localStorage`/`sessionStorage` continuity and token-based rather than cookie sessions. Still says self-service deletion and automated personal-data export **may not be available**. No operator/entity, legal bases, or jurisdiction supplement. | Exact written edits remain **condition not explicitly documented in sanitized record**. Visible drafting changes exist, but those exact conditions cannot be verified as satisfied. | Age, jurisdiction, policy version, Privacy acknowledgement mechanism, and consumer-storage wording vs current main remain unresolved. | **No** — materially stale storage/deletion statements vs current main; exact conditions unverified |
| Terms of Service | Reviewed — approved subject to written edits/conditions | Removes `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]`. Replaces it with “Your use of PiqSavi is subject to these Terms and applicable law.” Adds a detailed Prohibited Use list and expanded third-party / affiliate / IP wording (counsel tracked insertions). Still says self-service deletion and automated full-account export **may not be available**. No operator/entity, governing law, venue, liability cap, or numbered minimum age. | Exact written edits remain **condition not explicitly documented in sanitized record**. The draft does **not** choose a required Early Access assent UI (linked notice vs checkbox vs versioned records). | Assent mechanism, Early Access vs User-account registration, age, supported jurisdiction, and policy-version evidence remain unresolved. | **No** — assent still counsel-ambiguous; deletion/export wording stale vs User-account APIs |
| Cookie & Tracking Notice | Reviewed — approved subject to written edits/conditions | Counsel insertions add third-party tracking scope and affiliate-provider tracking after leaving PiqSavi. Still denies advertising/analytics cookies, pixels, GA/GTM, CMP/banner, and `localStorage`/`sessionStorage` continuity. Auth still described as token-based rather than cookie sessions. | condition not explicitly documented in sanitized record | Consumer-app first-party cookies and `localStorage`/`sessionStorage` post-date this wording. Early Access landing still has none. No GA/GTM/pixels/CMP remains true. | **No** (not required to publish `/privacy`/`/terms`, and not treated as cleared) |
| AI & Recommendation Disclosure | Reviewed — approved subject to written edits/conditions | Tightens Recommendation / “Best Piq” limitation and affiliate-neutrality wording. No publication instruction. | condition not explicitly documented in sanitized record | Early Access does not expose PiqScore shopping. | **No** |
| Affiliate & Advertising Disclosure | Reviewed — approved subject to written edits/conditions | Adds program-participation / labeling wording. Monetization still described as possible, not live. | condition not explicitly documented in sanitized record | Affiliate monetization remains off. Early Access has no affiliate links. | **No** |
| Account Deletion / Export / Retention | Reviewed — approved as drafted | Working draft keeps conservative “complete self-service account-deletion workflow / complete automated archive **may not be available**” and no final public retention schedule. Manual `privacy@piqsavi.com` path remains. | No extra document-level hold is visible beyond “approved as drafted.” Early Access erasure rule remains **condition not explicitly documented in sanitized record**. | User-account delete/export APIs now exist; they are engineering account-owned paths, not a complete legal DSAR or backup-wide purge. | **Not published as a public page.** Not used to authorize Privacy/Terms publication. |
| Consumer & Marketplace Disclaimer | Reviewed — approved subject to written edits/conditions | Counsel insertions expand intermediary / third-party / unknown-cost wording. | condition not explicitly documented in sanitized record | Early Access does not present live merchant / fixture-as-live shopping. | **No** |
| Data Processing & Product Behavior Spec | Reviewed — approved as drafted | Owner-supplied Aug 25 DOCX is the same named internal fact spec. Existing structured markdown remains the engineering copy. | Internally used fact spec only. | Not a consumer publication. | **Internally used only.** Not served on `/privacy` or `/terms`. |

### Distinctions preserved

| State | Current truth |
|-------|---------------|
| Legally reviewed | **Yes** — all eight prepared documents, 2026-08-19 |
| Revised (Aug 25 package in this workspace) | **Yes** — owner-supplied DOCX now transcribed under `docs/legal/` |
| Technically implemented | Fail-closed catalog + routes + publication-status + User-account consent architecture exist |
| Publicly published | **No** |
| Unresolved because sanitized record does not show the exact condition | **Yes** |
| Unresolved because revised texts contain statements that are now factually stale vs current main | **Yes** |

August 25 revisions **do not** satisfy every objectively verifiable counsel condition in this repository. The revised texts are now present, but the exact Aug 19 written conditions are still not in the sanitized record, and Privacy/Terms/Cookie wording is not factually current enough to publish.

---

## 3. Factual-currentness audit (August 25 working drafts vs current main)

Compared the **August 25 working-draft wording** against current main `5eadebda0ea6952ab37d6fb34825beff0e6c2ea7`.

Do **not** silently rewrite counsel-edited substance. No publication occurred.

| Statement in August 25 Privacy / Terms / Cookie / Deletion drafts | Current main behavior | Classification |
|------------------------------------------------------------------|----------------------|----------------|
| Privacy / Terms: self-service account deletion and automated personal-data export “may not be available” | `POST /api/v1/auth/account/delete` and `GET /api/v1/auth/account/export` exist for **User** accounts. Early Access rows are **not** deleted by that path. Export is an engineering account-owned package, not a complete legal DSAR. | **Factual update required before publication.** Publishing Privacy/Terms as-is would be misleading for User accounts. The Deletion working draft’s narrower “complete workflow / complete archive / instant purge may not be available” is closer to current engineering limits. **Legal re-review required** for replacement Privacy/Terms wording and for Early Access erasure. |
| Cookie / Privacy: no `localStorage` / `sessionStorage` continuity in “the consumer experience reflected by these documents” | Consumer app uses `sessionStorage`/`localStorage` for access token, remember-me, and shopping-assistant conversation id. Three first-party HTTP cookies exist (`piqsavi_decision_owner`, `piqsavi_delivery`, `piqsavi_shopping_market`). Early Access landing still uses none. Already recorded in [`../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md`](../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md). | **Factual update required before publication** of consumer Privacy / Cookie Notice. **Legal re-review required** for cookie/storage classification. Early Access-only wording would still be accurate if scoped. |
| Authentication designed around token-based sessions rather than browser cookie-based sessions | Still true. Cookies are not session-auth cookies. Bearer `Authorization` remains. | **Harmless conservative wording** (auth transport) |
| No advertising/analytics cookies, pixels, Google Analytics, GTM, or CMP/banner | `tracking_mode=essential_only`; `non_essential_tracking_allowed=false`; no CMP vendor; no analytics provider; `banner_implemented=false` | **Harmless conservative wording** for those absences. Does **not** authorize saying PiqSavi uses no cookies or no browser storage. |
| Support / privacy contacts `support@piqsavi.com` / `privacy@piqsavi.com` | EXT-17 / EXT-18 `provisioned`; `/support` wires those aliases | **Harmless conservative wording** |
| No date of birth field / no coded age gate | Still true for Early Access and User registration | **Harmless conservative wording** of the implementation fact. Minimum-age **rule** remains counsel-owned. |
| No operator / legal entity / address | Still unresolved in sanitized record and in the working drafts | **Legal re-review required** — not inventable |
| No governing law / venue / liability cap in Terms | Working draft has general consumer-rights savings language only | **Legal re-review required** if counsel still requires those clauses before publication |
| No final public retention schedule | Still true as an engineering/legal gap | **Harmless conservative wording** of the gap. Not a publication authorization. |
| Policy version / effective date | Working drafts have Last Updated August 25, 2026 only. No published `PolicyVersion` rows; `LEGAL_*_PUBLISHED_VERSION_ID` empty | Cannot invent a public version from unpublished working drafts |

**Publication rule applied:** do not publish a document containing materially stale/false consumer statements, and do not silently rewrite counsel-edited substance.

---

## 4. Assent / consent decision

Inspected: sanitized Aug 19 record; August 25 Terms/Privacy working drafts; existing User-account consent architecture; current Early Access signup UX.

| Option | Evidence |
|--------|----------|
| A. Linked Privacy + Terms notice only | Sanitized record does not say. August 25 Terms say use is “subject to these Terms and applicable law” but do **not** require footer-link activation, a signup sentence, or a specific notice UI. |
| B. Explicit Terms checkbox / clickwrap | Sanitized record does not say. August 25 Terms removed the earlier `[COUNSEL TO CONFIRM]` placeholder but did **not** replace it with a required checkbox/clickwrap instruction. |
| C. Explicit Terms + Privacy acknowledgement | Sanitized record does not say. |
| D. Versioned Terms/Privacy acceptance records | Sanitized record does not say. Existing `PolicyAcceptanceRecord` is **User-account only** and activates only after a **published** version. Early Access has no consent persistence path. |

**ASSENT DECISION REMAINS COUNSEL-AMBIGUOUS**

The August 25 “use is subject to these Terms” sentence is **not** treated as an instruction to invent Early Access clickwrap, a “By joining Early Access…” sentence, or versioned consent rows.

Actions taken:

- Did **not** add “By joining Early Access, you agree to the Terms and acknowledge the Privacy Policy.”
- Did **not** add checkboxes, clickwrap, or Early Access consent rows.
- Did **not** set `acceptance_required` on any published version (none exist).
- Did **not** convert Early Access registrations into User accounts.
- Kept current copy: “No spam. Just important PiqSavi early-access updates.”
- User-account registration clickwrap remains available **only if** a later owner publication action creates published versions. That path is unchanged.

Because assent remains counsel-ambiguous, this record does **not** claim Early Access legal activation complete.

---

## 5. Publication mechanism — unchanged fail-closed

| Check | Result |
|-------|--------|
| Approved HTML under `docs/legal/published/` | **None** (README + `.gitkeep` only) |
| Working-draft markdown under `docs/legal/` | **Present** — review copies only; banners include `Not for publication` |
| Privacy published? | **No** — no version id |
| Terms published? | **No** — no version id |
| `LEGAL_*_PUBLISHED_VERSION_ID` defaults | Empty |
| `GET /privacy` | HTTP **404** |
| `GET /terms` | HTTP **404** |
| Draft markdown served? | **No** |
| `GET /api/v1/legal/publication-status` | `terms_published=false`, `privacy_published=false`, version ids null, `*_acceptance_required=false` |
| Catalog bypassed? | **No** |

---

## 6. Early Access link activation — not performed

Footer links remain gated because the corresponding policies are **not** published:

```html
<a href="/privacy" class="legal-gated" aria-disabled="true" data-legal-gated="true">Privacy</a>
<a href="/terms" class="legal-gated" aria-disabled="true" data-legal-gated="true">Terms</a>
```

`aria-disabled` / `data-legal-gated` and the click `preventDefault` remain. Approved visual design is unchanged.

**Early Access links activated?** **No**

---

## 7. Early Access user model — unchanged

Registrations remain `EarlyAccessRegistration` / `early_access.registrations`. Duplicate protection, attribution capture, rate limiting, and private CLI export remain. This attempt did not redesign accounts.

---

## 8. EXT status reconciliation

Valid closed-status taxonomy (register legend only):

`not_started` | `applied` | `approved` | `provisioned` | `blocked` | `n_a_beta`

There is **no** status for “written conditional approval,” “working drafts ingested,” or “publication blocked pending factual update.”

| Row | Previous | Result after this attempt | Why |
|-----|----------|---------------------------|-----|
| EXT-19 | `applied` | **`applied`** (unchanged) | Conditional written approval remains recorded. Working-draft intake is **not** published-scope written approval. |
| EXT-20 | `not_started` | **`not_started`** | Privacy is **not** published. |
| EXT-21 | `not_started` | **`not_started`** | Terms are **not** published. |
| EXT-22 | `not_started` | **`not_started`** | No CMP / banner. Unrelated; not touched. |

Sprint 28 remains **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. Unrelated EXT rows and Sprints 31–38 / 32 were not changed.

---

## 9. Legal/content ready vs production-infrastructure ready

These gates are **separate**.

### Legal / content ready

| Gate | Ready? |
|------|--------|
| Aug 25 revised Privacy/Terms in workspace | **Yes** — transcribed under `docs/legal/` |
| Exact counsel written edits / implementation conditions visible in sanitized record | **No** |
| Privacy publishable without material falsehoods or remaining counsel-owned decisions | **No** |
| Terms publishable, including assent mechanism | **No** |
| `/privacy` `/terms` 200 with approved HTML | **No** |
| Early Access Privacy/Terms links active | **No** |
| Early Access assent/disclosure decided from evidence | **No — counsel-ambiguous** |
| EXT-19 `approved` for published consumer documents | **No** |
| EXT-20 / EXT-21 advanced | **No** |

**Legal/content ready: No**

### Production infrastructure ready

PR #128 / #129 production-infrastructure blockers remain separate and remain open unless later repo evidence says otherwise:

| Gate | Ready? |
|------|--------|
| Isolated production AWS applied (EXT-13) | **No** |
| Production secrets populated (EXT-14) | **No** |
| `piqsavi.com` → production app (EXT-11) | **No** |
| Production ALB TLS / HTTPS redirect (EXT-12) | **No** |
| Production deploy workflow / GitHub `production` environment | **No** — `deploy-production.yml` still absent |
| Production rollback / backup restore / CloudWatch paging (EXT-16 / EXT-24 / Sprint 41–42) | **No** |
| Shared / edge rate limiting (not in-process only) | **No** |
| Founder production-launch authorization | **No** |

**Production infrastructure ready: No**

This PR does **not** apply production Terraform, change Cloudflare DNS, populate production secrets, deploy production, or create affiliate links.

---

## 10. Unresolved legal conditions

1. Exact counsel written edits / implementation conditions are **not** in the sanitized record.
2. August 25 Privacy / Cookie wording still denies consumer `localStorage`/`sessionStorage` continuity that now exists on current main.
3. August 25 Privacy / Terms wording still says self-service deletion and automated export “may not be available” even though User-account APIs exist.
4. Assent / consent mechanism for Early Access is **counsel-ambiguous**.
5. Operator/entity, age/minors rule, supported jurisdiction, retention schedule, and Early Access erasure rule remain counsel-owned.
6. EXT-19 remains `applied`. EXT-20 / EXT-21 remain `not_started`.
7. Sprint 44/45 publication / public-beta obligations remain.

---

## 11. Early Access scope confirmation

| Requirement | Current truth |
|-------------|----------------|
| `/demo` unlinked from Early Access | **Yes** |
| Unfinished shopping hidden from Early Access chrome | **Yes** |
| No live merchant claims / no fixture-as-live catalog on Early Access | **Yes** |
| No affiliate links / no affiliate monetization activated | **Yes** |
| Registrations remain separate from User accounts | **Yes** |
| No public registration list or PII endpoint | **Yes** |
| Legal links remain gated | **Yes** |

---

## 12. Explicit non-claims

- Not a public beta launch
- No shopping launch
- No merchant certification
- No live research
- No affiliate monetization
- No production deploy
- Not Early Access legal-publication ready
- Do **not** merge from the agent — owner controls merges

After merge, a **staging deploy is required** only to restage this documentation/test lock; public legal-page behavior does not change. Production deployment is **not** required by this PR and remains a later owner-controlled cutover.
