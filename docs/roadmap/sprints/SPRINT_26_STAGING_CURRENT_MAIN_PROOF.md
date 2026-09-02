# Sprint 26 — Staging Current-Main Proof & Roadmap Bootstrap

**Status:** Technical staging proof verified; external bootstrap pending — **Sprint open**
**Primary owner / domain:** Ops / release engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-6; P1-7 (primary)
**Technical evidence package:** [`../evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../evidence/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)
**External bootstrap checklist:** [`../evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](../evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)
**Shopee current evidence:** [`../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md) — affiliate onboarding active / Open API access pending; Sprint 26 remains open
**Completion draft (not a close):** [`../evidence/SPRINT_26_COMPLETION_DRAFT.md`](../evidence/SPRINT_26_COMPLETION_DRAFT.md)

## Objective

Prove the current launch candidate on staging and bootstrap external dependency applications so Global Public Beta work can proceed on evidence, not assumptions.

## Included requirements

- Deploy current main (or designated launch-candidate digest) to staging via existing deploy-staging architecture
- Smoke: /live, /ready, auth register/login, search→DealScore→recommendation on staging
- Record staging-deploy-evidence for the launch candidate
- Open EXT applications for merchant markets, email provider, domain, support/privacy contacts
- Publish initial entries in EXTERNAL_DEPENDENCY_REGISTER.md with owners and dates
- Confirm fixture/simulated offers cannot be labeled as live in staging responses

## Explicit non-goals

- Production AWS apply
- Real merchant HTTP
- Consumer SPA rewrite
- Legal publication

## External dependencies

- EXT-01…EXT-05 bootstrap
- EXT-08
- EXT-10
- EXT-17
- EXT-18

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

### Explicitly pending

| Item | Status |
|------|--------|
| Required external dependency actions/applications | Pending (remaining bootstrap rows EXT-01…EXT-05 — market rows still `not_started`; Shopee, Lazada, TikTok Shop, Amazon, and Temu applications counsel-cleared to proceed 2026-08-25; real application submission evidence still required; EXT-08 Resend account evidence retained; EXT-09 Resend sender-domain DNS-authentication preparation evidence retained; EXT-10 ownership evidence retained; EXT-17 support-inbox receipt evidence retained; EXT-18 privacy-contact designation/receipt evidence retained; EXT-19 counsel engagement/schedule evidence retained) |
| Action/application dates | Pending for remaining rows (none invented; EXT-08, EXT-09 preparation, and EXT-10 recorded as evidence verified 2026-08-08; EXT-17 and EXT-18 recorded as 2026-08-09; EXT-19 engagement recorded as 2026-08-10 with consultation 2026-08-19 10:00 Philippines local time) |
| External-dependency register status updates | Partial — EXT-08 `applied`; EXT-09 `applied` (preparation only — DNS not applied/verified); EXT-10 `approved`; EXT-17 `provisioned`; EXT-18 `provisioned`; EXT-19 `applied` (engagement/schedule only — not written approval); remaining Sprint 26 bootstrap rows (EXT-01…EXT-05) remain `not_started` (Shopee, Lazada, TikTok Shop, Amazon, and Temu applications counsel-cleared to proceed 2026-08-25; not submitted; no merchant-to-market assignment) |
| Final Sprint 26 completion note | Pending — draft only in evidence package |
| Sprint 26 final go/no-go close | Pending — Sprint remains open |

Technical conclusion recorded in evidence package:

**SPRINT 26 CURRENT-MAIN STAGING PROOF VERIFIED**

That conclusion does **not** close Sprint 26.

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
- Merchant/affiliate terms-review discussion for research shortlist (Shopee, Lazada, TikTok Shop, Amazon, Temu) is in consultation scope only — does **not** select providers in the register and does **not** advance EXT-01…EXT-05 to `applied`
- Merchant-program **application** clearance (signed record 2026-08-25) is recorded as sanitized engineering evidence only; applications are **not** submitted
- Does **not** prove written legal approval of Terms/Privacy, launch legal approval, or privacy-regime compliance

**Sprint 26 remains OPEN.**

## Shopee evidence clarification

Additive clarification only — does **not** close Sprint 26, does **not** start or close Sprint 32, and does **not** move EXT-01 / EXT-06 / EXT-07 off `not_started`:

- Authoritative Shopee Sprint 26 evidence: [`../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](../evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md)
- Counsel-cleared to apply (2026-08-25) remains true
- Affiliate dashboard access: observed
- Payment & Tax: submitted / pending review
- Affiliate Open API: documented; PiqSavi access **not granted**; AppID/Secret **none**
- Seller/ISV Open Platform: held; not submitted
- Do not collapse those tracks into one “Shopee application submitted” or “API-ready” claim

## Predecessor sprints

25b.3, 25b.5*

## Parallelizable work

Legal counsel scheduling, UI design spike

## Go / no-go gate

Go if staging smoke green; No-go blocks 27+ public-path work that assumes staging truth

**Technical staging gate:** satisfied for SHA `79bd03f9e3df99efe4a978c48bec79eceec46767` (see evidence package).

**Current approved engineering baseline (2026-08-24):** `ab23d29e5f303bd5ecdfed60f7e7defe598d84d0` is the latest approved merged baseline for completed canonical presentation work (2819 passed / 0 failed / 0 skipped / 168 warnings). It is **not** Sprint 26 close evidence, **not** a replacement for the packaged `79bd03f` staging proof, and **not** the final launch candidate. EC-01 still requires staging proof of the frozen launch candidate.

Do not close Sprint 26 merely because later Sprint 29 work proceeded under an approved sequencing exception.

**Sprint close gate:** still blocked on external bootstrap actions and register updates. EXT-01…EXT-05 remain `not_started` (Shopee, Lazada, TikTok Shop, Amazon, and Temu applications counsel-cleared to proceed; not submitted; no merchant-to-market assignment). EXT-08/09 remain `applied` (not provisioned). EXT-10 remains `approved` (not provisioned). EXT-17/18 remain `provisioned` for bootstrap reachability. EXT-19 remains `applied` (not written approval).

## Rollback or contingency

Use existing staging rollback workflow to last known good digest

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
