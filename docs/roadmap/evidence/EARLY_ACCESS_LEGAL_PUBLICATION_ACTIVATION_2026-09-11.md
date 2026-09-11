# Early Access — legal publication activation attempt

**Date recorded:** 2026-09-11
**Audited `origin/main` SHA:** `efa430c4962dee90e325fffbf84f475dc1883f12`
**Scope:** Early Access acquisition / signup legal publication + link activation only
**Not in scope:** public shopping beta, Sprint 32 merchant certification, Shopee/Lazada/BuyWhere integrations, live merchant research, Sprints 31–38 research execution, PiqScore / Recommendation logic, affiliate monetization, production shopping Results, production infrastructure cutover

**Authority:** [`EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) · [`EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md`](EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md) · [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md) · [`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md)

This record does **not** rewrite the 2026-09-10 reconciliation. PR #128 remains the truthful history that signed counsel review exists, all eight prepared documents were reviewed, overall disposition is **conditional**, EXT-19 remains `applied`, Privacy/Terms remain unpublished, `/privacy` and `/terms` fail closed, Early Access footer links remain gated, and Early Access assent remained unresolved because the prior agent did not have the revised August 25 package.

This 2026-09-11 attempt was the publication + activation step. It searched again for the August 25 revised package and compared available texts against current main. It does **not** infer privileged advice.

---

## Resulting state

**EARLY ACCESS LEGAL ACTIVATION BLOCKED — COUNSEL CONDITION REMAINS UNRESOLVED**

This is **not**:

`EARLY ACCESS LEGAL PUBLICATION READY — PRODUCTION INFRASTRUCTURE CUTOVER REMAINS`

Publication, footer-link activation, and signup-assent copy were **not** implemented. Doing so would guess missing counsel conditions, serve unpublished counsel drafts, or invent assent language.

---

## 1. Source-document versions actually inspected

| Identifier / document | Version available in this workspace | Date / markers | Used as publication source? |
|-----------------------|-------------------------------------|----------------|-----------------------------|
| Signed Aug 19 counsel record (PDF) | **No** — sanitized facts only | Review date 2026-08-19 | No. Sanitized record only. |
| `EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md` | Yes — repository sanitized record | Recorded 2026-09-10 | Yes, as counsel-disposition authority |
| `PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_COOKIE_TRACKING_NOTICE_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_ACCOUNT_DELETION_DATA_EXPORT_RETENTION_POLICY_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_CONSUMER_MARKETPLACE_DISCLAIMER_WORKING_DRAFT` (Aug 25) | **No** | Owner-stated 2026-08-25 | **Cannot use — absent** |
| `PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT` (Aug 25 revised) | **No distinct Aug 25 copy** | Owner-stated identifier exists outside Git | **Cannot use as revised package** |
| `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md` | Yes — earlier counsel-draft markdown | `DRAFT — COUNSEL REVIEW REQUIRED`; `Not for publication`; many `[COUNSEL TO CONFIRM]` | **No — not for publication** |
| `docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md` | Yes — earlier counsel-draft markdown | Same draft markers; assent still `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]` | **No — not for publication** |
| Remaining six `docs/legal/*_COUNSEL_DRAFT.md` files | Yes | Same draft markers | **No — not for publication** |
| Owner prompt summary of Aug 25 content | Prompt paraphrase only | 2026-09-11 task text | **No — not a source document** |

### Search performed in this workspace

Searched and found **zero** `*WORKING_DRAFT*` files, **zero** August 25 Privacy/Terms HTML/DOCX/PDF copies, and **zero** attachments under `/workspace`, `/home`, `/tmp`, `/opt`, `/mnt`, GitHub `docs/legal/`, prior-agent transcripts (`bc-89a3f6dd`, `bc-3c7a29b5`), and this run’s upload/attachment paths.

The owner prompt described intended Aug 25 topics (public identity “Your AI Personal Shopper,” account/session/search data, tracking posture, deletion/export, PiqScore neutrality). That description is **not** treated as the revised legal text. The in-repo counsel drafts already use the same public tagline; that overlap does **not** prove the drafts are the August 25 package.

---

## 2. Privacy / Terms reconciliation matrix

| Document | Reviewed disposition (Aug 19 sanitized record) | Material changes in Aug 25 | Condition addressed? | Remaining ambiguity | Publishable now? |
|----------|-----------------------------------------------|----------------------------|----------------------|---------------------|------------------|
| Privacy Policy / Privacy Notice | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 `PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT` is not in this workspace. Repo draft still has `[COUNSEL TO CONFIRM]` for operator/entity, effective date, age, retention, legal bases, market rights, transfers, and draft-only headers. | Exact written edits are **condition not explicitly documented in sanitized record**. Cannot verify whether Aug 25 addressed them. | Public identity is stated in the repo draft as PiqSavi / “Your AI Personal Shopper,” but Early Access waitlist scope, age, jurisdiction, policy version, and Privacy acknowledgement mechanism remain unresolved. Repo draft also contains stale “not implemented” deletion/export/email/storage statements vs current main. | **No** |
| Terms of Service | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 `PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT` is not in this workspace. Repo draft still has `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]` plus empty liability / governing-law placeholders. | Exact written edits are **condition not explicitly documented in sanitized record**. | Terms assent, Early Access vs User-account registration, age, supported jurisdiction, and policy-version evidence remain unresolved. | **No** |
| Cookie & Tracking Notice | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 copy absent. | condition not explicitly documented in sanitized record | Consumer-app first-party cookies/`localStorage`/`sessionStorage` post-date the repo draft. Early Access landing still has no cookies/storage. No GA/GTM/pixels/CMP remains true. | **No** (not required to publish `/privacy`/`/terms`, but not treated as cleared) |
| AI & Recommendation Disclosure | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 copy absent. | condition not explicitly documented in sanitized record | Early Access does not expose PiqScore shopping. Neutrality language in repo drafts is not a publication decision. | **No** |
| Affiliate & Advertising Disclosure | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 copy absent. | condition not explicitly documented in sanitized record | Affiliate monetization remains off. Early Access has no affiliate links. | **No** |
| Account Deletion / Export / Retention | Reviewed — approved as drafted | **Unknown.** Aug 25 copy absent. | No extra document-level hold is visible beyond “approved as drafted.” Early Access erasure rule remains **condition not explicitly documented in sanitized record**. | User-account delete/export now exist; Early Access is a separate store with private CLI export only. Repo Privacy/Terms drafts still deny in-product delete/export. | **Not published as a public page.** Not used to authorize Privacy/Terms publication. |
| Consumer & Marketplace Disclaimer | Reviewed — approved subject to written edits/conditions | **Unknown.** Aug 25 copy absent. | condition not explicitly documented in sanitized record | Early Access does not present live merchant / fixture-as-live shopping. | **No** |
| Data Processing & Product Behavior Spec | Reviewed — approved as drafted | **Unknown** whether a distinct Aug 25 revision exists here. Repo copy remains the counsel-draft fact spec. | Internally used fact spec only. | Not a consumer publication. | **Internally used only.** Not served on `/privacy` or `/terms`. |

### Distinctions preserved

| State | Current truth |
|-------|---------------|
| Legally reviewed | **Yes** — all eight prepared documents, 2026-08-19 |
| Revised (Aug 25 package in this workspace) | **No** |
| Technically implemented | Fail-closed catalog + routes + publication-status + User-account consent architecture exist |
| Publicly published | **No** |
| Unresolved because sanitized record / revised texts do not show the exact condition | **Yes** |

August 25 revisions **do not** satisfy every objectively verifiable counsel condition in this repository, because the revised texts are absent here and the exact conditions are not in the sanitized record.

---

## 3. Factual-currentness audit (before any publication)

Compared **available** legal text (in-repo counsel drafts, not the missing Aug 25 package) against current main `efa430c4962dee90e325fffbf84f475dc1883f12`.

Do **not** silently rewrite counsel-approved substance. No publication occurred.

| Statement in available Privacy/Terms counsel drafts | Current main behavior | Classification |
|-----------------------------------------------------|----------------------|----------------|
| In-product account-deletion “is not currently implemented” | `POST /api/v1/auth/account/delete` exists for **User** accounts. Early Access rows are **not** deleted by that path. | **Factual update required before publication.** Publishing the draft as-is would be materially false for User accounts. **Legal re-review required** for the replacement wording and for Early Access erasure. |
| Automated personal-data export / DSAR “is not currently implemented” | `GET /api/v1/auth/account/export` exists (`piqsavi.account_owned_export.v1`). Early Access export is private CLI only. | **Factual update required before publication.** **Legal re-review required** for Early Access vs User wording. |
| “Live transactional email delivery is not currently integrated” | Resend adapter is implemented. Staging requires `TRANSACTIONAL_EMAIL_PROVIDER=resend`. Staging inbox E2E is recorded. Early Access confirmation remains `NullEmailSender` / `not_sent`. | **Factual update required before publication** for User-account identity email. Early Access “no confirmation email” remains accurate. |
| No `localStorage` / `sessionStorage` continuity in reviewed consumer UI | Consumer app now uses `sessionStorage`/`localStorage` for access token, remember-me, and shopping-assistant conversation id. Three first-party HTTP cookies exist (`piqsavi_decision_owner`, `piqsavi_delivery`, `piqsavi_shopping_market`). Early Access landing still uses none. | **Factual update required before publication** of consumer Privacy / Cookie Notice. Already recorded in [`../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md`](../../privacy/COOKIE_STORAGE_FACTUAL_CHANGES.md). **Legal re-review required** for cookie/storage classification. Early Access-only wording would still be accurate if scoped. |
| Bearer-token auth rather than cookie sessions | Still true. Cookies are not session-auth cookies. | **Harmless conservative wording** (auth transport) |
| No advertising/analytics cookies, pixels, Google Analytics, GTM, or CMP/banner | `tracking_mode=essential_only`; `non_essential_tracking_allowed=false`; no CMP vendor; no analytics provider; `banner_implemented=false` | **Harmless conservative wording** for those absences. Does **not** authorize saying “PiqSavi uses no cookies” (consumer first-party cookies exist). |
| Support / privacy contacts `support@piqsavi.com` / `privacy@piqsavi.com` | EXT-17 / EXT-18 `provisioned`; `/support` wires those aliases | **Harmless conservative wording** |
| Operator / legal entity / address `[COUNSEL TO CONFIRM]` | Still unresolved in sanitized record | **Legal re-review required** — not inventable |
| Minimum age / minors `[COUNSEL TO CONFIRM]` | No coded age gate; no DOB on Early Access or User registration | **Legal re-review required** |
| Supported jurisdiction / governing law `[COUNSEL TO CONFIRM]` | Early Access collects ISO country; production certified shopping markets remain empty | **Legal re-review required** |
| Policy version / effective date `[COUNSEL TO CONFIRM]` | No published `PolicyVersion` rows; `LEGAL_*_PUBLISHED_VERSION_ID` empty | Cannot invent a public version from drafts |

**Publication rule applied:** do not publish a document containing materially false statements, counsel-draft markers, or unresolved `[COUNSEL TO CONFIRM]` legal decisions.

---

## 4. Assent / consent decision

Inspected: sanitized Aug 19 record; missing Aug 25 Terms/Privacy; existing User-account consent architecture; current Early Access signup UX.

| Option | Evidence |
|--------|----------|
| A. Linked Privacy + Terms notice only | Sanitized record does not say. Aug 25 Terms/Privacy absent. |
| B. Explicit Terms checkbox / clickwrap | Sanitized record does not say. Repo Terms draft still has `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]`. |
| C. Explicit Terms + Privacy acknowledgement | Sanitized record does not say. |
| D. Versioned Terms/Privacy acceptance records | Sanitized record does not say. Existing `PolicyAcceptanceRecord` is **User-account only** and activates only after a **published** version. Early Access has no consent persistence path. |

**ASSENT DECISION REMAINS COUNSEL-AMBIGUOUS**

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

`aria-disabled` / `data-legal-gated` and the click `preventDefault` remain. Approved visual design is unchanged. Keyboard/focus behavior is unchanged.

**Early Access links activated?** **No**

---

## 7. Early Access user model — unchanged

Registrations remain `EarlyAccessRegistration` / `early_access.registrations`. Duplicate protection, attribution capture, rate limiting, and private CLI export remain. This attempt did not redesign accounts.

---

## 8. EXT status reconciliation

Valid closed-status taxonomy (register legend only):

`not_started` | `applied` | `approved` | `provisioned` | `blocked` | `n_a_beta`

There is **no** status for “written conditional approval” or “publication blocked pending revised text.”

| Row | Previous | Result after this attempt | Why |
|-----|----------|---------------------------|-----|
| EXT-19 | `applied` | **`applied`** (unchanged) | Conditional written approval remains recorded. `approved` stays reserved for published-scope written approval. |
| EXT-20 | `not_started` | **`not_started`** | Privacy is **not** published. |
| EXT-21 | `not_started` | **`not_started`** | Terms are **not** published. |
| EXT-22 | `not_started` | **`not_started`** | No CMP / banner. Unrelated; not touched. |

Sprint 28 remains **INTERNAL ENGINEERING + STAGING VERIFICATION COMPLETE — EXTERNAL LEGAL/PUBLICATION GATES REMAIN.** Not COMPLETE/CLOSED. Unrelated EXT rows and Sprints 31–38 / 32 were not changed.

---

## 9. Legal/content ready vs production-infrastructure ready

These gates are **separate**. Legal publication being blocked does **not** clear or reopen infrastructure rows.

### Legal / content ready

| Gate | Ready? |
|------|--------|
| Aug 25 revised Privacy/Terms in workspace and reconcilable to Aug 19 conditions | **No** |
| Exact counsel written edits / implementation conditions visible in sanitized record | **No** |
| Privacy publishable without material falsehoods or remaining `[COUNSEL TO CONFIRM]` legal decisions | **No** |
| Terms publishable, including assent mechanism | **No** |
| `/privacy` `/terms` 200 with approved HTML | **No** |
| Early Access Privacy/Terms links active | **No** |
| Early Access assent/disclosure decided from evidence | **No — counsel-ambiguous** |
| EXT-19 `approved` for published consumer documents | **No** |
| EXT-20 / EXT-21 advanced | **No** |

**Legal/content ready: No**

### Production infrastructure ready

PR #128 production-infrastructure blockers remain separate and remain open unless later repo evidence says otherwise:

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

1. August 25 revised working-draft package is **still not** in this repository / agent workspace.
2. Exact counsel written edits / implementation conditions are **not** in the sanitized record.
3. Assent / consent mechanism for Early Access is **counsel-ambiguous**.
4. Operator/entity, age/minors, supported jurisdiction, retention schedule, and Early Access erasure rule remain counsel-owned.
5. In-repo counsel drafts contain statements that are now factually stale vs User-account deletion/export, staging Resend, and consumer storage. Those drafts still cannot be published, and this agent must not silently rewrite them.
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
