# Early Access — owner-authorized legal/content-layer activation

**Date recorded:** 2026-09-11
**Audited `origin/main` SHA:** `5eadebda0ea6952ab37d6fb34825beff0e6c2ea7`
**Scope:** PiqSavi Early Access signup legal publication + acknowledgement only
**Not in scope:** public shopping beta, merchant launch, live research launch, Sprint 32 completion, Shopee/Lazada/BuyWhere activation, affiliate monetization, production infrastructure cutover

**Authority:** owner decision to proceed with Early Access legal publication without requesting another paid counsel review, subject to conservative factual-currentness rules. Source package: August 25 working-draft markdown ingested from `origin/cursor/legal-working-draft-reconciliation-d013` (PR #130, not merged by this agent).

This record does **not** rewrite:

- [`EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md)
- [`EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md`](EARLY_ACCESS_LEGAL_RECONCILIATION_AND_LAUNCH_READINESS_2026-09-10.md)
- [`EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md)
- [`EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md`](EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md)

Those records remain truthful for the workspaces and decisions they describe.

This does **not** mean counsel gave new unconditional approval.

Final factual-currentness corrections and the Early Access assent mechanism were **owner-authorized implementation decisions** based on counsel-reviewed source documents.

---

## Resulting state

**EARLY ACCESS LEGAL/CONTENT LAYER READY — STAGING VERIFICATION REQUIRED — PRODUCTION INFRASTRUCTURE CUTOVER REMAINS**

---

## 1. Source-document versions actually used

| Identifier / document | Version used | Date / markers | Used as publication source? |
|-----------------------|--------------|----------------|-----------------------------|
| Signed Aug 19 counsel record | Sanitized repository record only | Review date 2026-08-19 | Counsel-disposition authority only |
| `PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT` | Yes — [`../../legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md`](../../legal/PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT.md) | Last Updated August 25, 2026 | **Yes**, after factual-currentness corrections |
| `PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT` | Yes — [`../../legal/PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT.md`](../../legal/PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT.md) | Last Updated August 25, 2026 | **Yes**, after factual-currentness corrections |
| `PIQSAVI_COOKIE_TRACKING_NOTICE_WORKING_DRAFT` | Yes | Last Updated August 25, 2026 | Reconciled only; not a public `/cookies` page |
| Remaining August 25 working drafts | Yes, inspected | Last Updated August 25, 2026 | Inspected. Not published as public pages |
| `docs/legal/*_COUNSEL_DRAFT.md` | Yes, inspected | Draft markers remain | **Not published** |

PR #130 ingested the August 25 package without publishing. This activation uses those markdown transcriptions as the August 25 source. It does **not** merge PR #130.

---

## 2. Factual-currentness corrections

Every published-document modification is classified below. No wording was changed merely because a different formulation sounded better.

| Location | August 25 wording | Current implementation verified | Classification | Why factual rather than substantive legal rewriting |
|----------|-------------------|----------------------------------|---------------|-----------------------------------------------------|
| Privacy §9; Terms §4.4 | Self-service account deletion and automated personal-data export “may not be available” | `POST /api/v1/auth/account/delete` and `GET /api/v1/auth/account/export` exist for **User** accounts. Early Access rows are a separate store and are not deleted by that path. Export schema is `piqsavi.account_owned_export.v1`. Instant purge from every backup/log/third-party system is still not claimed. | **Objective factual correction** | Replaces a now-false availability statement with the implemented User-account tools and preserves the August 25 manual `privacy@piqsavi.com` path and backup/third-party limits. Does not invent a legal DSAR, retention schedule, or Early Access erasure rule. |
| Privacy §5; Cookie Notice §§2, 4, 5 | No `localStorage` / `sessionStorage` continuity; cookies mentioned only as a future possibility | Consumer app uses first-party HTTP cookies `piqsavi_decision_owner`, `piqsavi_delivery`, `piqsavi_shopping_market` and first-party `sessionStorage`/`localStorage` keys `piqsavi_access_token`, `piqsavi_remember_me`, `piqsavi_ask_conversation`. Auth remains Bearer token. Early Access landing uses none of those stores. | **Objective factual correction** | Describes current first-party necessary/functional storage. Does not reclassify legal bases, add a CMP, or change advertising/analytics posture. |
| Privacy §6; Terms §4.3 email | Third-party email services may process messages; some verification/recovery features may not be available at all times | Staging User-account identity email uses Resend when configured. Early Access confirmation remains `NullEmailSender` / `not_sent`. | **Unchanged counsel-reviewed substance** | August 25 wording is still accurate. No change. |
| Support / privacy contacts | `support@piqsavi.com` / `privacy@piqsavi.com` | EXT-17 / EXT-18 `provisioned`; `/support` wires those aliases | **Unchanged counsel-reviewed substance** | No change. |
| Age / children | No DOB field; no coded age gate; use only when legally permitted | Still true for Early Access and User registration | **Unchanged counsel-reviewed substance** | No numbered minimum-age rule invented. |
| Tracking absences | No advertising/analytics cookies, pixels, GA, GTM, or CMP | `tracking_mode=essential_only`; `non_essential_tracking_allowed=false`; no CMP vendor; no analytics provider; `banner_implemented=false` | **Unchanged counsel-reviewed substance** | Absences remain. The storage correction above does **not** authorize advertising/analytics tracking. |
| Governing law, venue, liability cap, indemnification, legal bases, operator/entity | Absent from August 25 source | Still absent | **Unchanged counsel-reviewed substance** | Not invented. Publication proceeds with the August 25 omission. |

No independent change was made to governing law, jurisdiction/forum, liability limitations, indemnification, warranties/disclaimers, intellectual-property provisions, dispute provisions, substantive data-sharing rights, substantive age/minor rules, material retention obligations, legal bases for processing, or merchant liability allocation.

---

## 3. Owner-authorized Early Access assent

Owner authorized a conservative explicit acknowledgement for Early Access only.

Preferred copy implemented:

> I agree to the Terms of Service and acknowledge the Privacy Policy.

`Terms of Service` and `Privacy Policy` are links to the published policies.

| Requirement | Implementation |
|-------------|----------------|
| Unchecked by default | Native checkbox, no `checked` attribute |
| Registration cannot complete without acknowledgement | Client validation + server `policies_acknowledged=true` required |
| Accessible label | `<label for="ea-policies-acknowledged">` wraps the control and copy |
| Keyboard accessible | Native checkbox |
| Clear error state | `aria-invalid`, visible `#err-policies-acknowledged` |
| No dark patterns | No pre-checked box; no bundled marketing |
| No marketing consent | “No spam. Just important PiqSavi early-access updates.” remains a separate note |
| Not consent to analytics / affiliate / advertising / data sale | Acknowledgement is Terms/Privacy only |

This is an **owner-authorized implementation decision**. It is not new counsel approval of a clickwrap doctrine.

---

## 4. Persistence / audit evidence

Successful Early Access registrations persist, on the existing `EarlyAccessRegistration` / `early_access.registrations` store only:

- `terms_version_id`
- `privacy_version_id`
- `policies_acknowledged_at`
- existing Early Access registration `id`

Server stamps the currently published version IDs. Client-supplied version IDs are ignored.

Historical rows without those fields decode as `null` and are **not** backfilled. Duplicate signups do not rewrite historical null assent.

Early Access registrations are **not** converted into User accounts. Acceptance logs are not public. Operator CSV export remains private and now includes the three audit fields.

No extra PII fields were added.

---

## 5. Publication

| Check | Result |
|-------|--------|
| Approved HTML | `docs/legal/published/privacy-2026-09-11.html` · `docs/legal/published/terms-2026-09-11.html` |
| Privacy version | `privacy-2026-09-11` |
| Terms version | `terms-2026-09-11` |
| Effective / publication date | 11 September 2026 |
| `[COUNSEL TO CONFIRM]` | **Absent** from published HTML |
| Draft banners | **Absent** from published HTML |
| `GET /privacy` | HTTP **200** when the published file and version id are valid |
| `GET /terms` | HTTP **200** when the published file and version id are valid |
| Working drafts / counsel drafts served? | **No** |
| Cookie Notice public page | **Not published.** Reconciled at [`../../legal/PIQSAVI_COOKIE_TRACKING_NOTICE_FACTUAL_CURRENTNESS_2026-09-11.md`](../../legal/PIQSAVI_COOKIE_TRACKING_NOTICE_FACTUAL_CURRENTNESS_2026-09-11.md). No CMP/banner added. |

Fail-closed behavior remains: empty version ids, unusable paths, or draft-marker HTML still 404.

---

## 6. Early Access links and UX

Footer Privacy/Terms links are enabled. `aria-disabled`, `data-legal-gated`, and click `preventDefault` were removed only for those published policies. Approved visual design is otherwise unchanged.

The acknowledgement checkbox sits above the existing “No spam…” note. That note remains separate and is not treated as promotional marketing consent.

`/demo` remains unlinked. Unfinished shopping remains hidden from Early Access chrome.

---

## 7. EXT status

| Row | Previous | Result | Why |
|-----|----------|--------|-----|
| EXT-19 | `applied` | **`applied`** | Taxonomy reserves `approved` for unconditional counsel approval of published-scope documents. This owner-authorized publication is not that. |
| EXT-20 | `not_started` | **`applied`** | Privacy is published through the fail-closed catalog. Staging deploy and production live URL remain. |
| EXT-21 | `not_started` | **`applied`** | Terms are published through the fail-closed catalog. Staging deploy and production live URL remain. |
| EXT-22 | `not_started` | **`not_started`** | No CMP / banner. Unrelated; not touched. |

Unrelated EXT rows were not changed. Sprint 28 is not marked COMPLETE/CLOSED.

---

## 8. Remaining infrastructure blockers

Unchanged and separate from this legal/content layer:

| Gate | Ready? |
|------|--------|
| Isolated production AWS (EXT-13) | **No** |
| Production secrets (EXT-14) | **No** |
| `piqsavi.com` → production app (EXT-11) | **No** |
| Production ALB TLS / HTTPS redirect (EXT-12) | **No** |
| Production deploy workflow / GitHub `production` environment | **No** |
| Production rollback / backup restore / CloudWatch paging | **No** |
| Shared / edge rate limiting | **No** |
| Founder production-launch authorization | **No** |
| Affiliate monetization | **Off** |

This PR does **not** deploy production, modify Cloudflare DNS, provision production AWS, create production secrets, or activate affiliate links.

A **staging deploy is required** to verify the published pages and Early Access acknowledgement on staging.

---

## 9. Explicit non-claims

- Not a public beta launch
- No shopping launch
- No merchant certification
- No live research
- No affiliate monetization
- No production deploy
- No new unconditional counsel approval
- Do **not** merge from the agent — owner controls merges
