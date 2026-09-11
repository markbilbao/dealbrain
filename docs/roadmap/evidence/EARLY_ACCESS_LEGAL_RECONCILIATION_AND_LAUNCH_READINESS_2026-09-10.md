# Early Access — legal reconciliation and production launch readiness

**Date recorded:** 2026-09-10
**Audited `origin/main` SHA:** `6666bb26f40255b9fece39e94bc5ca2b6e3ff2dd`
**Follow-up (does not rewrite this record):** [`EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md) — August 25 package still absent in that workspace; publication/activation not performed. Later same-day intake: [`EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md`](EARLY_ACCESS_LEGAL_WORKING_DRAFT_RECONCILIATION_2026-09-11.md).
**Scope:** Early Access acquisition / signup surface only
**Not in scope:** public shopping beta, Sprint 32 merchant certification, Shopee/Lazada integration, BuyWhere, live merchant/product research, Sprints 31–38 live research execution, affiliate monetization, public shopping Results launch

**Authority:** [`EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) · [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md) · [`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md)

This record uses only the signed approval facts supplied by the owner, the repository counsel-draft text, and current-main engineering evidence. It does **not** infer privileged legal advice.

---

## 1. Legal reconciliation matrix

| Document | Counsel disposition | Aug 25 revision present? | Material revision vs reviewed version | Remaining explicit condition found? | Publication / use status |
|----------|---------------------|--------------------------|---------------------------------------|-------------------------------------|--------------------------|
| Data Processing & Product Behavior Spec | Reviewed — approved as drafted | **No** in this repository / agent workspace. Owner states `PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT` is the current revised identifier. Repo copy remains `docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | condition not explicitly documented in sanitized record | **Internally used fact spec only.** Not a published policy. Not served on `/privacy` or `/terms`. |
| Privacy Policy / Privacy Notice | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_PRIVACY_POLICY_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md` (`DRAFT — COUNSEL REVIEW REQUIRED`, `Not for publication`). | Cannot compare. August 25 package is not in the agent workspace. Repo copy still contains `[COUNSEL TO CONFIRM]` placeholders (effective date, operator/entity, merchant-platform coverage). | Written edits/conditions are named as the disposition, but the exact wording is **condition not explicitly documented in sanitized record**. | **Not published.** `docs/legal/published/` has no approved HTML. `GET /privacy` fail-closed 404. EXT-20 `not_started`. |
| Terms of Service | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_TERMS_OF_SERVICE_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. Repo copy still contains `[COUNSEL TO CONFIRM]` including **required acceptance mechanism and evidence of assent**. | Exact wording is **condition not explicitly documented in sanitized record**. | **Not published.** `GET /terms` fail-closed 404. EXT-21 `not_started`. |
| Affiliate & Advertising Disclosure | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | condition not explicitly documented in sanitized record | **Not published.** Affiliate monetization remains `n_a_beta` / not activated. Early Access landing has no affiliate links. |
| AI & Recommendation Disclosure | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | condition not explicitly documented in sanitized record | **Not published.** Early Access signup does not require PiqScore / shopping AI. Live AI HTTP remains off by default. |
| Cookie & Tracking Notice | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_COOKIE_TRACKING_NOTICE_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_COOKIE_TRACKING_NOTICE_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | condition not explicitly documented in sanitized record | **Not published.** Tracking remains `essential_only`. EXT-22 `not_started`. No CMP / banner. |
| Account Deletion / Export / Retention | Reviewed — approved as drafted | **No** in this repository / agent workspace. Owner states `PIQSAVI_ACCOUNT_DELETION_DATA_EXPORT_RETENTION_POLICY_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_ACCOUNT_DELETION_DATA_EXPORT_RETENTION_POLICY_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | No extra document-level hold is visible beyond “approved as drafted.” Remaining implementation conditions for Early Access signup PII are **condition not explicitly documented in sanitized record**. | **Not published as a public page.** Engineering deletion/export APIs exist for **User accounts**. Early Access rows are a separate store and are exportable only via private CLI. |
| Consumer & Marketplace Disclaimer | Reviewed — approved subject to written edits/conditions | **No** in this repository / agent workspace. Owner states `PIQSAVI_CONSUMER_MARKETPLACE_DISCLAIMER_WORKING_DRAFT` dated 2026-08-25 exists outside Git. Repo copy remains `docs/legal/PIQSAVI_CONSUMER_MARKETPLACE_DISCLAIMER_COUNSEL_DRAFT.md`. | Cannot compare. August 25 package is not in the agent workspace. | condition not explicitly documented in sanitized record | **Not published.** Early Access does not present live merchant / fixture-as-live shopping claims. |

### Distinctions preserved

| State | Current truth |
|-------|---------------|
| Legally reviewed | **Yes** — all eight prepared documents, 2026-08-19 |
| Revised | Owner states August 25 working drafts exist **outside Git**. They are **not** in this repository. |
| Technically implemented | Early Access signup / persistence / publication **fail-closed** machinery exists. Published Privacy/Terms HTML does **not**. |
| Publicly published | **No** — `/privacy` and `/terms` 404 |
| Unresolved because the sanitized record does not show the exact condition | **Yes** — exact written edits / implementation conditions, and Early Access assent mechanism, are not in the sanitized record |

August 25 revisions **do not** satisfy every objectively verifiable counsel condition in this repository, because the revised texts are absent here and the exact conditions are not in the sanitized record.

---

## 2. Conditional Early Access gate assessment

Objectively verifiable implementation conditions only.

| Topic | Legally reviewed | Revised | Technically implemented | Publicly published | Remaining |
|-------|------------------|---------|-------------------------|--------------------|-----------|
| Privacy / Terms publication mechanism | Yes | Aug 25 package not in repo | Fail-closed catalog + `/privacy` `/terms` + `GET /api/v1/legal/publication-status` | No | Owner publication action (EXT-20 / EXT-21) after conditions are actually satisfied |
| Early Access signup disclosure | Review record does not specify Early Access form wording | Not in repo | Current copy is only “No spam. Just important PiqSavi early-access updates.” | N/A | Unresolved legal decision — see §7 |
| Affirmative assent / clickwrap | Terms counsel draft still has `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]`. Sanitized record is silent. | Not in repo | User-account clickwrap exists **only when published**. Early Access has **no** checkboxes / consent persistence. | No | Unresolved because the sanitized record does not show the exact condition |
| Policy versioning | Reviewed as part of publication architecture, not as a named counsel condition | N/A | `PolicyVersion` with version id, status, timestamps, `acceptance_required` | No published versions | Empty production catalog is correct until owner publication |
| Consent / acknowledgement persistence | Sanitized record silent for Early Access | N/A | `PolicyAcceptanceRecord` is User-account only | No | Do not fabricate Early Access consent rows |
| Support / privacy contacts | Contacts appear in counsel drafts | N/A | EXT-17 / EXT-18 `provisioned`; `/support` wires `support@piqsavi.com` and `privacy@piqsavi.com` | Support page yes; policies no | Not a remaining Early Access inbox blocker |
| Account deletion / export support | Deletion/export policy reviewed — approved as drafted | Aug 25 package not in repo | User-account delete/export APIs exist. Early Access private CLI export exists. No public PII list. | No public DSAR page | Counsel-owned Early Access erasure rule is **condition not explicitly documented in sanitized record** |
| Retention disclosure | Reviewed as drafted | Aug 25 package not in repo | Engineering retention map exists; not a legal schedule | No | Legal retention schedule remains counsel-owned |
| Cookies / tracking posture | Cookie notice reviewed subject to conditions | Aug 25 package not in repo | `tracking_mode=essential_only`; `non_essential_tracking_allowed=false`; no CMP | Cookie notice unpublished | EXT-22 remains `not_started`. Acceptable for essential-only Early Access only if counsel later confirms; sanitized record does not say. |
| Minimum-age / minors posture | Sanitized record silent | Repo drafts still have `[COUNSEL TO CONFIRM]` age placeholders | Fail-closed eligibility placeholder; no invented age; no DOB on Early Access form | No | Unresolved because the sanitized record does not show the exact condition |
| Country / jurisdiction limitations | Sanitized record silent | Repo drafts still have market placeholders | Early Access collects ISO country; production certified shopping markets remain empty | No | Unresolved because the sanitized record does not show the exact condition |
| Affiliate disclosure posture | Reviewed subject to conditions | Aug 25 package not in repo | EXT-07 `n_a_beta`; Early Access has no affiliate links or merchant logos | No | Monetization not activated |
| AI / recommendation disclosure posture | Reviewed subject to conditions | Aug 25 package not in repo | Early Access does not expose PiqScore shopping | No | Not required for Early Access signup |
| Consumer / marketplace disclaimer | Reviewed subject to conditions | Aug 25 package not in repo | Early Access does not claim live merchants or fixture-as-live catalog | No | Required for public shopping beta (Sprint 44/45), not for waitlist signup chrome |

**Gate conclusion:** the conditional Early Access legal gate is **not** satisfied for publication or footer-link activation. Internally controllable work completed here is evidence reconciliation and a current launch matrix. Publication, legal-link enablement, and signup assent were **not** implemented because doing so would guess missing counsel conditions or serve unpublished counsel drafts.

---

## 3. EXT-19 status reconciliation

Previous current-main wording that “EXT-19 written approval is absent” is now **too coarse**.

| Claim | Current truth |
|-------|---------------|
| Written counsel review record | **Present** — signed 2026-08-19 comprehensive review, sanitized in [`EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) |
| Written **conditional** approval | **Present** — proceed only after specified revisions / implementation conditions |
| Written **unconditional** approval of published consumer documents | **Absent** |
| Register lifecycle status | remains **`applied`** |

The External Dependency Register closed status set is:

`not_started` | `applied` | `approved` | `provisioned` | `blocked` | `n_a_beta`

There is **no** existing status for “written conditional approval.”
`approved` is reserved for access granted / published-scope written approval and is explicitly forbidden for a conditional “proceed after revisions” review.

Closest truthful existing status: **`applied`**.

No new status was invented. Unrelated EXT rows were not changed.

---

## 4. Publication readiness decision

The existing fail-closed publication architecture is preserved.

| Check | Result |
|-------|--------|
| August 25 Privacy / Terms revised text in this workspace | **No** |
| Repo Privacy / Terms still marked `Not for publication` / counsel-draft markers | **Yes** |
| Unresolved explicit blocker in sanitized record | Exact written edits / conditions **not documented** |
| Approved HTML under `docs/legal/published/` | **None** (README + `.gitkeep` only) |
| `LEGAL_*_PUBLISHED_VERSION_ID` defaults | Empty |
| Action taken | **Do not publish.** Do not copy counsel markdown into web-serving paths. Do not set version IDs. |

Counsel drafts remain unpublished. Sprint 44/45 remain the publication / public-beta gates.

---

## 5. Early Access legal-link activation decision

Existing footer links stay gated because `/privacy` and `/terms` do not resolve:

```html
<a href="/privacy" class="legal-gated" aria-disabled="true" data-legal-gated="true">Privacy</a>
<a href="/terms" class="legal-gated" aria-disabled="true" data-legal-gated="true">Terms</a>
```

`aria-disabled` / `data-legal-gated` and the click `preventDefault` remain. Approved visual design is unchanged.

---

## 6. Early Access signup assent / consent conclusion

| Question | Evidence |
|----------|----------|
| Is a simple linked notice sufficient? | Sanitized record does not say. |
| Is explicit Terms assent required? | Sanitized record does not say. Repo Terms draft still has `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]`. |
| Is explicit Privacy acknowledgement required? | Sanitized record does not say. |
| Is versioned acceptance evidence required for Early Access? | Sanitized record does not say. Existing consent architecture is User-account only. |

**Conclusion:** do **not** guess. Keep the current anti-spam note. Do **not** add checkboxes, clickwrap, or Early Access consent persistence. Launch status remains **conditional** on this unresolved legal decision.

User-account registration clickwrap remains available **only if** a later owner publication action creates published versions. That path is unchanged and is not Early Access account registration.

---

## 7. Current Early Access production-launch matrix

Historical checklist: [`../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_CHECKLIST.md`](../../runbooks/EARLY_ACCESS_PRODUCTION_CUTOVER_CHECKLIST.md) (2026-08-18 HOLD). Re-evaluated against current main `6666bb26f40255b9fece39e94bc5ca2b6e3ff2dd` on 2026-09-10.

| Gate | Old status (Aug 2026 checklist / report) | Current evidence | Still required? | Owner | Action |
|------|------------------------------------------|------------------|-----------------|-------|--------|
| Privacy Policy approved for publication | Open | Written **conditional** approval recorded. Exact edits not in sanitized record. Aug 25 working draft not in repo. Repo draft unpublished. | **Yes** | Legal + owner | Supply Aug 25 / counsel-cleared publication text; owner EXT-20 action |
| Terms approved for publication | Open | Same as Privacy. Assent mechanism still `[COUNSEL TO CONFIRM]` in repo draft. | **Yes** | Legal + owner | Same; owner EXT-21 action |
| Approved legal URLs / files; no placeholders | Open | `/privacy` `/terms` 404. Published root empty. | **Yes** | Legal + eng | Publish through existing catalog only |
| Founder Early Access production authorization | Open | No recorded GO | **Yes** | Owner | Required before any cutover |
| Isolated production AWS | Open / deferred | TF modeled (`infra/terraform/environments/production/`); **not applied**. EXT-13 `Partial TF only; not applied`. GitHub Environment `production` absent. | **Yes** | Ops (Sprint 41) | Apply isolated prod; do not use staging as prod |
| Production database / persistence | Open | Prod RDS is Terraform-only. Live app DB is staging. Signup uniqueness is implemented and tested; not proven on a production RDS. | **Yes** | Ops + eng | Provision, migrate, readiness-test prod DB |
| Signup uniqueness / restart durability | Implemented on staging / SQLAlchemy tests | `EarlyAccessRegistration` + `create_if_absent` + tests remain. | **Yes** to verify on prod | Eng | Re-verify after prod persist exists |
| Least-privilege private export | CLI hardened; rehearsal open | `scripts/export_early_access.py` + runbook exist. No public list. Operator prod rehearsal not evidenced. | **Yes** | Ops + founder | Rehearse private export after prod DB exists |
| Backup / restore rehearsal | Open | Prod TF intends 30-day backup / final snapshot. No restore-drill evidence. Sprint 42 planned. | **Yes** | Ops (Sprint 42) | Restore rehearsal |
| Production secrets | Open | EXT-14 `not_started`. Staging assembly refuses production prefix. | **Yes** | Ops (Sprint 41) | Populate `dealbrain/production/*` |
| CORS / trusted hosts / fail-closed security | Code present; prod values not applied | Production CORS cannot be `*`. `TRUSTED_HOSTS` warning-only. Examples still use `dealbrain.example` placeholders. | **Yes** | Ops + eng | Set PiqSavi prod origins/hosts |
| Public LB / target health without exposing staging | Staging live; prod absent | `staging.piqsavi.com` → staging ALB. `piqsavi.com` is a Cloudflare static page; `/health` 404. | **Yes** | Ops | Prod ALB + health; keep staging isolated |
| DNS `piqsavi.com` → production app | Open | EXT-11 `not_started` for production public hostname. Staging DNS **is** live. Apex is **not** the app. | **Yes** | Ops + owner | Authorized DNS window only. Agent must not change DNS. |
| Production TLS + HTTPS redirect | Open | EXT-12 `not_started` for prod ALB. Staging HTTPS + ACM live; staging HTTP still 200. Apex TLS is Cloudflare, not prod ALB. | **Yes** | Ops | Prod ACM + HTTP→HTTPS + HTTPS `/ready` |
| Production deploy workflow | Absent | **No** `.github/workflows/deploy-production.yml`. Tests still require it absent. | **Yes** | Ops (Sprint 41) | Environment-gated prod workflow |
| Immutable digest deploy + release evidence | Staging yes | Build Image + Deploy Staging exist. Latest recorded staging success Deploy Staging #34 / SHA `fc8be5fe…`. | **Yes** for prod | Ops | Prod equivalent after workflow exists |
| `/live` `/ready` HTTPS smoke | Staging yes; prod no | Staging `/ready` ready; apex probes 404. | **Yes** | Ops + eng | Prod HTTPS probes |
| Production rollback | Staging only | `Rollback Staging` only; no DB downgrade; no prod rollback workflow. | **Yes** | Ops | Prod rollback + signup-data preserve |
| Centralized privacy-safe logs / alerts | App redaction yes; destination no | Structured logs omit EA email/name. No proven CloudWatch / paging destination. EXT-16 / EXT-24 `not_started`. | **Yes** | Ops (Sprint 42) | Durable destination + alarms |
| Shared / edge rate limiting | In-process only | Registration 5/min/IP; events 20/min/IP. Documented as not a production WAF. | **Yes** for public prod | Ops + eng (Sprint 40) | Shared/edge control at prod concurrency |
| Privacy/Terms footer resolve | Intentionally gated | Still `aria-disabled` + JS preventDefault; routes 404. | **Yes** before public EA | Legal + eng | Enable only after published 200s |
| Signup disclosure / consent UI matches approved guidance | Open | Current note only. Assent decision unresolved. | **Yes** | Legal + product | Owner/counsel decision required |
| Retention / deletion / incident handling for signup PII | Partial | Private CLI export exists. User-account delete does not remove Early Access rows. Counsel erasure rule not in sanitized record. | **Yes** | Legal + ops | Confirm EA retention/erasure |
| Desktop / mobile visual smoke | PASS 2026-08-18 on `a1879a2` | Locked CSS/logo tests remain. No production smoke. Restage visual check prudent on current digest. | **Yes** for prod GO | Eng + founder | Prod visual smoke against masters |
| Signup / duplicate / validation / loading / error UX | PASS on staging + tests | Implementation preserved. | **Yes** to re-smoke on prod | Eng | Prod functional smoke |
| UTM / referrer capture | Implemented | Client + API + CSV fields present. Device-info still not stored (privacy decision). | Capture: no. Device-info policy: optional. | Eng / legal | Keep capture; do not invent device fields |
| Production analytics / event destination | First-party hooks only | Events exist. EXT-15 `not_started`. No approved prod log destination. | **Yes** if the gate means visible prod evidence | Product + ops | First-party logs to approved destination; no third-party analytics without EXT-22 |
| Support / privacy inboxes | Open in Aug checklist | EXT-17 / EXT-18 `provisioned` | **No** as an inbox bootstrap | Ops / legal | Monitor; not an infra reopen |
| `/demo` unlinked | Required | EA HTML has no `/demo`. Route still mounted and reachable if guessed. | Unlink: done. Public hide of guessable `/demo`: owner call. | Eng | Keep unlinked. Do not advertise. |
| Unfinished shopping hidden | Required | EA has no `/search` / merchant claims. Production certified markets empty. Staging `/search` can still show fixtures. | EA chrome: done. Public shopping: out of scope / hidden. | Eng | Do not expose shopping as live |
| Affiliate monetization | Must stay off | EXT-07 `n_a_beta`. EA has no affiliate links. | **Yes** to keep off | Growth + eng | Do not activate |
| Live merchant research | Must not be introduced | EXT-01 `applied` only. No certification. This change introduces none. | **Yes** to keep out of EA | Marketplace | Sprint 32 remains separate |

---

## 8. Early Access scope confirmation

| Requirement | Current truth |
|-------------|----------------|
| `/demo` unlinked from Early Access | **Yes** |
| Unfinished shopping product hidden from Early Access chrome | **Yes** |
| No live merchant claims on Early Access | **Yes** |
| No fixture product data presented as live on Early Access | **Yes** |
| No affiliate links on Early Access | **Yes** |
| PiqScore shopping not required for signup | **Yes** |
| Usable with zero certified PH merchant-data paths | **Yes** |
| Registrations remain separate from User accounts | **Yes** — `EarlyAccessRegistration` / `early_access.registrations` |
| No public registration list or PII endpoint | **Yes** — private CLI only |
| Abuse controls preserved | **Yes** — registration 5/min/IP; events 20/min/IP; no automated signup added |
| Involve Asia traction purpose | Genuine signup capture + private export remain the intended path. No fake registrations created. |

---

## 9. Remaining blockers

### Legal / publication (blocks public Early Access legal completeness)

1. Exact counsel written edits / implementation conditions are **not** in the sanitized record.
2. August 25 working-draft package is **not** in this repository.
3. Privacy / Terms are **not** published (`/privacy` `/terms` 404).
4. Early Access assent / disclosure mechanism is an **unresolved legal decision**.
5. EXT-19 remains `applied` — not `approved` for published-scope documents.
6. EXT-20 / EXT-21 remain `not_started`.
7. Sprint 44/45 publication / public-beta obligations remain.

### Production infrastructure (blocks production cutover)

1. No production deploy workflow; no GitHub `production` environment.
2. Production AWS not applied (EXT-13).
3. Production secrets not populated (EXT-14).
4. `piqsavi.com` does not route to the PiqSavi app (EXT-11).
5. Production ALB TLS / HTTPS redirect not applied (EXT-12).
6. No production rollback, backup restore rehearsal, CloudWatch destination, or paging (EXT-16 / EXT-24 / Sprint 41–42).
7. In-process rate limit only — not a production WAF / shared limiter.
8. Founder production-launch authorization is absent.

### Explicit non-claims

- Not a public beta launch
- No merchant certification
- No live shopping launch
- No affiliate monetization activation
- No production deploy
- No DNS change
- Do **not** merge from the agent — owner controls merges

---

## 10. Readiness statement

Unresolved legal and infrastructure gates remain.

This branch prepares and audits Early Access launch readiness. It does **not** claim:

`EARLY ACCESS CODE/LEGAL READINESS COMPLETE — OWNER PRODUCTION CUTOVER AUTHORIZATION REQUIRED`

After merge, a **staging deploy is required** only to restage documentation/tests; no public legal-page behavior changes. Production cutover is **not** technically ready.
