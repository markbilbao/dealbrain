# Sprint 26 — Staging Current-Main Proof & Roadmap Bootstrap

**Status:** **COMPLETE / CLOSED** (2026-09-08). Technical staging proof verified; EXT-01 PH product-data access request `applied`.
**Primary owner / domain:** Ops / release engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-6; P1-7 (primary)
**Technical evidence package:** [`../evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)
**External bootstrap checklist:** [`../evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](../evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)
**EXT-01 request evidence:** [`../evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](../evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md)
**Shopee affiliate evidence (historical; not EXT-01 approval):** [`../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md) — affiliate onboarding active / Open API access pending; does **not** by itself satisfy EXT-01
**Completion record:** [`../evidence/SPRINT_26_COMPLETION.md`](../evidence/SPRINT_26_COMPLETION.md)
**Historical 2026-09-07 draft:** [`../evidence/SPRINT_26_COMPLETION_DRAFT.md`](../evidence/SPRINT_26_COMPLETION_DRAFT.md)
**2026-09-07 verdict (historical):** **SPRINT 26 TECHNICAL COMPLETE — PH DATA-ACCESS BOOTSTRAP REMAINS**
**2026-09-08 verdict:** **SPRINT 26 COMPLETE / CLOSED**

## Objective

Prove the current launch candidate on staging and bootstrap the **current-scope** external dependency applications so Global Public Beta work can proceed on evidence, not assumptions.

**2026-09-07 launch-scope lock (documentation only):** PiqSavi will launch its initial public beta as a Philippines-first product-validation beta **without affiliate monetization**. September public beta supported-market target is Philippines only unless the owner later expands it. Affiliate revenue is not a launch acceptance requirement. This does **not** invalidate packaged staging proof at SHA `79bd03f`.

## Included requirements

- Deploy current main (or designated launch-candidate digest) to staging via existing deploy-staging architecture
- Smoke: /live, /ready, auth register/login, search→DealScore→recommendation on staging
- Record staging-deploy-evidence for the launch candidate
- Open EXT applications for merchant markets, email provider, domain, support/privacy contacts
- **Current-scope reconciliation (2026-09-07):** remaining Sprint 26 merchant bootstrap is EXT-01 PH **product-data** access only; EXT-02…EXT-05 are `n_a_beta` for this beta
- Publish initial entries in EXTERNAL_DEPENDENCY_REGISTER.md with owners and dates
- Confirm fixture/simulated offers cannot be labeled as live in staging responses

## Explicit non-goals

- Production AWS apply
- Real merchant HTTP
- Consumer SPA rewrite
- Legal publication

## External dependencies

- EXT-01 PH product-data access bootstrap (**complete for Sprint 26** — `applied` 2026-09-08; not `approved`)
- EXT-02…EXT-05 historical market bootstrap — now `n_a_beta` for this beta; not September blockers
- EXT-07 affiliate tracking — now `n_a_beta` / post-beta; not a September blocker
- EXT-08
- EXT-10
- EXT-17
- EXT-18
- EXT-19 engagement bootstrap (complete for Sprint 26; not unconditional legal approval)

## Implementation deliverables

- Staging deploy of launch candidate
- Smoke scripts/checklist execution notes
- Register updates

## Documentation deliverables

- Staging evidence artifact references
- Updated external dependency statuses
- Sprint 26 completion note

## Required tests

- Existing CI green on candidate
- Staging smoke checklist

## Required staging evidence

- staging_ok evidence for launch candidate
- /ready READY with sqlalchemy bindings

## Required production evidence

- None required

## Acceptance criteria

- Launch candidate digest is staging_ok
- Smoke journey recorded (pass/fail with links)
- External dependency register shows application dates for critical EXT rows
- No production resources mutated beyond read-only verification
- **P1-7 closed:** current launch-candidate staging promotion discipline is defined and evidenced here; Sprint 45 may only **re-verify** the same gate on the frozen candidate (not a second primary owner)

## Acceptance tracking (technical vs pending)

### Completed (technical)

| Item | Status | Evidence |
|------|--------|----------|
| Current-main deployment to staging | Complete | Deploy Staging `#16`, run `31072785397`, job `92524021958`, result `success` |
| `staging_ok` host evidence | Complete | `final_status=staging_ok`; S3 evidence + checksum sidecar + validator OK |
| Identity/digest correlation | Complete | SHA `79bd03f9e3df99efe4a978c48bec79eceec46767`; release `rel-20260806T041533Z-79bd03f9e3df`; digest `sha256:c8f5610d9538bac17db42b456e96455adb59d5a113494e40fae32408f23d87b8`; manifest `fc529721c1f3c819da4ce250460520a5b44c366c133cafcb6b1f11a4e037b95b` |
| Migration before/after | Complete | `d4e5f6a7b8c9` → `d4e5f6a7b8c9` |
| Readiness with SQLAlchemy | Complete | `/ready` `200`, `ready=true`, `persistence_level=READY`; SQLAlchemy user-platform bindings selected |
| Health and OpenAPI | Complete | `/health` `200` `environment=staging`; `/openapi.json` `200` |
| Zero-mutation search/DealScore/recommendation smoke | Complete | Search, DealScore, Recommendation, affiliate disclosure, empty-query `422`, `X-Request-ID` |
| Authenticated lifecycle smoke | Complete | Register→duplicate→fail login→login→`/me`→DealScore→logout→post-logout `401`; residue recorded |
| Staging promotion discipline (P1-7 technical) | Complete | Current-candidate promotion path evidenced; Sprint 45 final re-verify only |
| No production mutation | Complete | Staging-only deploy and read-only probes |

### Explicitly pending as of 2026-09-07 — later closed 2026-09-08

| Item | Status after 2026-09-08 |
|------|--------|
| Required current-scope external dependency action | **EXT-01 `applied`** — Lazada PH and Shopee PH product-data access requests sent 2026-09-08. Evidence: [`../evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](../evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md). Shopee affiliate dashboard / Payment & Tax / Open API documentation still do **not** by themselves satisfy EXT-01. Lazada/Optimise affiliate approval (if any) is monetization permission only and does **not** certify a live research source. EXT-02…EXT-05 are `n_a_beta`. EXT-07 is `n_a_beta`. EXT-08/09/10/17/18/19 bootstrap rows unchanged. |
| Action/application dates | EXT-01 recorded as **2026-09-08**. EXT-08/09/10 recorded as evidence verified 2026-08-08; EXT-17/18 as 2026-08-09; EXT-19 engagement as 2026-08-10 with consultation 2026-08-19 10:00 Philippines local time. |
| External-dependency register status updates | EXT-01 **`applied`**; EXT-02…EXT-05 and EXT-07 `n_a_beta`; EXT-08 `applied`; EXT-09 later `approved` for Sprint 27 sender-domain evidence; EXT-10 `approved`; EXT-17 `provisioned`; EXT-18 `provisioned`; EXT-19 `applied` (not `approved`) |
| Final Sprint 26 completion note | Complete — [`../evidence/SPRINT_26_COMPLETION.md`](../evidence/SPRINT_26_COMPLETION.md). Historical draft retained. |
| Sprint 26 final go/no-go close | **CLOSED** — Sprint 26 COMPLETE / CLOSED |

Technical conclusion recorded in evidence package:

**SPRINT 26 CURRENT-MAIN STAGING PROOF VERIFIED**

2026-09-07 close question conclusion (historical):

**SPRINT 26 TECHNICAL COMPLETE — PH DATA-ACCESS BOOTSTRAP REMAINS**

2026-09-08 close question conclusion:

**SPRINT 26 COMPLETE / CLOSED**

The 2026-09-07 conclusion did **not** close Sprint 26. The 2026-09-08 EXT-01 request evidence does. Later `main` SHAs, including PR #114 (`1f66688`), do **not** invalidate the packaged staging proof. Sprint 45 will later re-prove the frozen launch candidate. Sprint 32 remains pending certification.

## Brand / domain bootstrap clarification

Additive clarification only — does **not** close Sprint 26:

- Public brand **PiqSavi** is locked ([`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md))
- `piqsavi.com` ownership/control evidenced via sanitized Cloudflare registration proof (2026-08-08)
- EXT-10 status: `approved` (not `provisioned`)
- Evidence path: [`../evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](../evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png)
- EXT-11 DNS and EXT-12 TLS remain separate and `not_started`
- No application branding or domain cutover is required to close the technical staging-proof portion already completed

## Transactional email provider bootstrap clarification

Additive clarification only — does **not** close Sprint 26 and does **not** start Sprint 27:

- Selected provider: **Resend**
- EXT-08 status: `applied` (not `approved`, not `provisioned`)
- Evidence / action date: 2026-08-08
- Evidence path: [`../evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](../evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png)
- Evidence shows sanitized Resend dashboard/account-establishment proof only
- No API key creation, email send, or delivery proof is claimed from EXT-08

## Sender-domain authentication preparation clarification

Additive clarification only — does **not** close Sprint 26 and does **not** start Sprint 27:

- Provider: **Resend**; domain: **`piqsavi.com`**
- EXT-09 status: `applied` (sender-domain authentication **preparation** only — not DNS applied, not domain verified, not `approved`, not `provisioned`)
- Preparation / evidence date: 2026-08-08
- Evidence path: [`../evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](../evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png)
- Evidence shows sanitized Resend DNS-record plan (DKIM; Return-Path MX/SPF for `send` / intended `send.piqsavi.com`; DMARC `p=none`) with configuration/Verify actions still available
- DNS records have **not** been applied or verified; abbreviated provider Content values were **not** invented
- EXT-11 DNS hosting and EXT-12 TLS remain `not_started` and are separate from EXT-09 sender authentication

## Support inbox bootstrap clarification

Additive clarification only — does **not** close Sprint 26 and does **not** start Sprint 27:

- Public support address: **`support@piqsavi.com`**
- Receiving architecture: Google Workspace / Gmail for `piqsavi.com`; `support@piqsavi.com` is an alternate email alias routed to the monitored Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox
- Monitoring owner: PiqSavi Operations / Mark
- Response expectation: within 1 business day
- EXT-17 status: `provisioned`
- Evidence / action date: 2026-08-09
- Evidence path: [`../evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png`](../evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png)
- Evidence shows sanitized Gmail inbound receipt (To `support@piqsavi.com`; subject `EXT-17 Support Inbox Verification — 2026-08-09`; Aug 9, 2026, 8:39 PM; TLS); personal external sender address redacted
- Does **not** prove Resend/EXT-09 DNS apply/verify, Google Workspace DKIM/DMARC completion, transactional delivery, or public support-contact publication

## Privacy contact bootstrap clarification

Additive clarification only — does **not** close Sprint 26 and does **not** start Sprint 27:

- Public privacy address: **`privacy@piqsavi.com`**
- Role: **PiqSavi Privacy**
- Designation / monitoring owner: Mark / PiqSavi Privacy
- Designation date: 2026-08-09
- Owner acknowledgment: Mark / PiqSavi Privacy designates `privacy@piqsavi.com` as the PiqSavi public privacy contact for Sprint 26 EXT-18 bootstrap purposes
- Receiving architecture: Google Workspace / Gmail for `piqsavi.com`; `privacy@piqsavi.com` is an alternate email alias routed to the monitored Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox
- Escalation path: privacy/legal matters requiring professional legal advice escalate to the future counsel relationship represented by EXT-19
- EXT-18 status: `provisioned`
- Evidence / action date: 2026-08-09
- Evidence path: [`../evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png`](../evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png)
- Evidence shows sanitized Gmail inbound receipt (To `privacy@piqsavi.com`; subject `EXT-18 Privacy Contact Verification — 2026-08-09`; Aug 9, 2026, 9:19 PM; TLS); personal external sender address redacted
- Does **not** prove formal statutory DPO appointment, Privacy Policy legal sufficiency, EXT-19 written approval, or public Privacy Policy publication
- Separated from EXT-17 support contact (`support@piqsavi.com`)

## Legal counsel engagement bootstrap clarification

Additive clarification only — does **not** close Sprint 26 and does **not** start Sprint 27:

- Counsel identity: **Pauline Anne Sambuang** (firm affiliation not shown in retained evidence — not invented)
- EXT-19 status: `applied` (not `approved`)
- Evidence / engagement date: 2026-08-10
- Confirmed consultation: 2026-08-19, 10:00 AM, Philippines local time
- Evidence paths: [`../evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png`](../evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png); [`../evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png`](../evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png)
- Evidence shows counsel acceptance of PiqSavi legal consultation/review; scope covering ToS, Privacy/data-handling, affiliate/advertising disclosures, AI/recommendation disclosures/disclaimers, consumer-protection considerations, deletion/export/retention, cookie/tracking, and country-specific considerations for intended markets; counsel confirmation of date/time with calendar-invite request; supporting-document request before consultation
- Merchant/affiliate terms-review discussion for research shortlist (Shopee, Lazada, TikTok Shop, Amazon, Temu) is in consultation scope only — does **not** select providers in the register and does **not** advance EXT-01 to `applied`
- Merchant-program **application** clearance (signed record 2026-08-25) is recorded as sanitized engineering evidence only; applications are **not** submitted
- Owner-stated later comprehensive counsel review (eight documents; cleared to proceed only after specified revisions / implementation conditions) is **not** unconditional legal approval and does **not** make EXT-19 `approved`
- Does **not** prove written legal approval of published Terms/Privacy, launch legal approval, or privacy-regime compliance

**Sprint 26 is COMPLETE / CLOSED** as of 2026-09-08. The 2026-09-07 remaining blocker — a real PH product-data access application/request for EXT-01 — is now `applied`. EXT-01 is not `approved` and Sprint 32 is not complete.

## Shopee evidence clarification

Additive historical clarification — the 2026-09-08 product-data emails, not this affiliate record, moved EXT-01 to `applied`. This section still does **not** start or close Sprint 32 and does **not** make EXT-01 `approved`:

- Authoritative Shopee Sprint 26 evidence: [`../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md)
- Counsel-cleared to apply (2026-08-25) remains true
- Affiliate dashboard access: observed
- Payment & Tax: submitted / pending review
- Affiliate Open API: documented; PiqSavi access **not granted**; AppID/Secret **none**
- Seller/ISV Open Platform: held; not submitted
- Affiliate permission ≠ product-data permission. These facts do **not** satisfy EXT-01.

## Predecessor sprints

25b.3, 25b.5*

## Parallelizable work

Legal counsel scheduling, UI design spike

## Go / no-go gate

Go if staging smoke green; No-go blocks 27+ public-path work that assumes staging truth

**Technical staging gate:** satisfied for SHA `79bd03f9e3df99efe4a978c48bec79eceec46767` (see evidence package).

**Current approved engineering baseline (2026-08-24):** `ab23d29e5f303bd5ecdfed60f7e7defe598d84d0` is the latest approved merged baseline for completed canonical presentation work (2819 passed / 0 failed / 0 skipped / 168 warnings). It is **not** Sprint 26 close evidence, **not** a replacement for the packaged `79bd03f` staging proof, and **not** the final launch candidate. EC-01 still requires staging proof of the frozen launch candidate.

Do not close Sprint 26 merely because later Sprint 29 work proceeded under an approved sequencing exception.

**Sprint close gate:** satisfied 2026-09-08. EXT-01 PH product-data access application/request evidence is retained and EXT-01 is `applied`. EXT-02…EXT-05 and EXT-07 are `n_a_beta` for this beta and do not block Sprint 26 close. EXT-08 remains `applied` (not provisioned). EXT-09 later became `approved` for Sprint 27 sender-domain evidence; production email attach remains Sprint 41. EXT-10 remains `approved` (not provisioned; Sprint 41 owns public hostname). EXT-17/18 remain `provisioned` for bootstrap reachability (publication remains 28/39/45). EXT-19 remains `applied` (not written published-version approval; Sprint 28/44 own remaining legal work). Sprint 32 remains pending certification.

## Rollback or contingency

Use existing staging rollback workflow to last known good digest

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
