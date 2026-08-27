# Sprint 26 — External Dependency Bootstrap Checklist

**Document type:** Action checklist (preparation only)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Related evidence:** [`SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Rule:** Do **not** change register status from `not_started` until real external action evidence exists. Do **not** invent dates. Do **not** claim an application was submitted from this document alone.

**Register snapshot:** EXT-08 is `applied` on retained sanitized Resend provider-selection/account-establishment evidence (2026-08-08). EXT-09 is `applied` on retained sanitized Resend sender-domain DNS-authentication **preparation** evidence (2026-08-08) — DNS not applied/verified. EXT-10 is `approved` on retained sanitized ownership evidence (2026-08-08). EXT-17 is `provisioned` on retained sanitized support-inbox receipt evidence (2026-08-09). EXT-18 is `provisioned` on retained sanitized privacy-contact designation and receipt evidence (2026-08-09). EXT-19 is `applied` on retained sanitized counsel engagement + schedule confirmation evidence (2026-08-10) — consumer ToS/Privacy written approval still pending. Remaining listed bootstrap rows (EXT-01…EXT-05) remain `not_started`. Counsel-cleared to **apply** for Shopee, Lazada, TikTok Shop, Amazon, and Temu (signed record 2026-08-25; sanitized: [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md)); applications **not** submitted.

---

## How to use

1. Perform the **exact action** for a dependency.
2. Retain the **evidence** listed for that row.
3. Update only the named **register fields** in `EXTERNAL_DEPENDENCY_REGISTER.md` after evidence exists.
4. Record the real application/action date — never a fabricated one.

---

## Readiness classes

| Class | Dependencies |
|-------|--------------|
| Legal counsel engagement accepted (applied; not approved) | EXT-19 (Pauline Anne Sambuang; engagement 2026-08-10; consultation 2026-08-19 10:00 Philippines local time; supporting docs requested; written approval still required) |
| Privacy contact provisioned | EXT-18 (`privacy@piqsavi.com` / PiqSavi Privacy; alias → monitored Workspace Gmail; sanitized inbound receipt, 2026-08-09) |
| Support inbox provisioned | EXT-17 (`support@piqsavi.com` alias → monitored Workspace Gmail; sanitized inbound receipt, 2026-08-09) |
| Provider account established (applied; not approved/provisioned) | EXT-08 (Resend selected; sanitized account-establishment proof, 2026-08-08) |
| Ownership evidence retained (approved; not provisioned) | EXT-10 (`piqsavi.com` sanitized Cloudflare registration/control proof, 2026-08-08) |
| Requires provider selection | EXT-01…EXT-05 (merchant/API partner per market; counsel-cleared merchant programs are Shopee, Lazada, TikTok Shop, Amazon, Temu — owner still selects market mapping and submits) |
| Sender-domain auth plan prepared (applied; DNS not applied/verified) | EXT-09 (Resend DKIM / Return-Path MX+SPF / DMARC `p=none` plan for `piqsavi.com`, 2026-08-08) |
| Requires a purchased/configured domain | EXT-11/12 later (DNS/TLS — out of Sprint 26 bootstrap list; still `not_started`, separate from EXT-10 ownership) |
| Legal gate to submit merchant applications | EXT-01…EXT-05 — **cleared** 2026-08-25 for Shopee, Lazada, TikTok Shop, Amazon, Temu (application clearance only). Owner submission + submission evidence still required. EXT-18 privacy-contact bootstrap still coordinates with EXT-19 for consumer-legal advice. |
| Market-specific dependencies | EXT-01 PH, EXT-02 US, EXT-03 SG, EXT-04 UK, EXT-05 CA |

---

## EXT-01 — Philippines merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Counsel-clearance status | Counsel-cleared to **apply** (Shopee among five merchant programs; signed record 2026-08-25). Does **not** select Shopee as the PH provider in this register row. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Identify official program/portal and intended PH merchant mapping; submit access/application. Counsel legal gate to apply is satisfied; owner still submits. See [`SPRINT_26_EXT01_05_APPLICATION_PREPARATION.md`](SPRINT_26_EXT01_05_APPLICATION_PREPARATION.md). |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope PH; technical contact — **OWNER INPUT REQUIRED** where not already evidenced |
| Evidence that must be retained | Application confirmation (ticket/email/portal ID); submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay PH as named supported market; site may still launch with other markets |
| Launch impact | Blocks naming Philippines as a supported shopping market (Sprint 32) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, `Evidence required` notes / links (non-secret), decision-window if known |

---

## EXT-02 — United States merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Counsel-clearance status | Counsel-cleared to **apply** to the five merchant programs (2026-08-25). Does **not** map any merchant onto this US row by ID coincidence. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Identify official program/portal and intended US merchant mapping; submit access/application. Counsel legal gate to apply is satisfied; owner still submits. |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope US; technical contact — **OWNER INPUT REQUIRED** where not already evidenced |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay US market naming |
| Launch impact | Blocks naming United States as a supported shopping market (Sprint 33) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-03 — Singapore merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Counsel-clearance status | Counsel-cleared to **apply** to the five merchant programs (2026-08-25). Does **not** map any merchant onto this SG row by ID coincidence. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Identify official program/portal and intended SG merchant mapping; submit access/application. Counsel legal gate to apply is satisfied; owner still submits. |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope SG; technical contact — **OWNER INPUT REQUIRED** where not already evidenced |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay SG market naming |
| Launch impact | Blocks naming Singapore as a supported shopping market (Sprint 34) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-04 — United Kingdom merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Counsel-clearance status | Counsel-cleared to **apply** to the five merchant programs (2026-08-25). Does **not** map any merchant onto this UK row by ID coincidence. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Identify official program/portal and intended UK merchant mapping; submit access/application. Counsel legal gate to apply is satisfied; owner still submits. |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope UK; technical contact — **OWNER INPUT REQUIRED** where not already evidenced |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay UK market naming |
| Launch impact | Blocks naming United Kingdom as a supported shopping market (Sprint 35) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-05 — Canada merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Counsel-clearance status | Counsel-cleared to **apply** to the five merchant programs (2026-08-25). Does **not** map any merchant onto this CA row by ID coincidence. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Identify official program/portal and intended CA merchant mapping; submit access/application. Counsel legal gate to apply is satisfied; owner still submits. |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope CA; technical contact — **OWNER INPUT REQUIRED** where not already evidenced |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay CA market naming |
| Launch impact | Blocks naming Canada as a supported shopping market (Sprint 36) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-08 — Transactional email provider

| Field | Value |
|-------|-------|
| Current documented status | `applied` (provider selected + account established; **not** `approved` / **not** `provisioned`) |
| Responsible owner | Identity eng |
| Selected provider | Resend |
| Evidence / action date | 2026-08-08 |
| Evidence type | Sanitized Resend dashboard/account-establishment proof |
| Evidence path | [`external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](external/EXT-08_RESEND_ACCOUNT_2026-08-08.png) |
| What was retained | Resend onboarding (“Send your first email”); “Add an API key” step/button visible; recipient email redacted; only placeholder `re_xxxxxxxxxx` (not a real API credential); no username/account ID, billing, password, or live token |
| Signup / provider approval date | Not evidenced by the screenshot — **not inferred**; register Application date = `evidence verified 2026-08-08` |
| Not yet | API key created/retained; API integration; email send; transactional delivery proof; `piqsavi.com` in Resend; sender-domain verification; SPF/DKIM/DMARC; DNS changes; production credentials; production email |
| Separation | EXT-09 sender-domain authentication preparation is tracked separately (now `applied` for Sprint 26 prep only); Sprint 27 owns integration, DNS apply/verify, and delivery proof |
| Fallback | Invite-only with self-serve reset disabled (demotes public beta) |
| Launch impact | Provider bootstrap no longer blocks Sprint 26 status for EXT-08; Sprint 27 still requires integration + EXT-09 DNS verification + delivery proof |
| Register fields updated | `Application date` → `evidence verified 2026-08-08`; `Current status` → `applied`; provider Resend; evidence path retained |

---

## EXT-09 — Sender-domain SPF/DKIM/DMARC preparation

| Field | Value |
|-------|-------|
| Current documented status | `applied` (sender-domain authentication **preparation** complete for Sprint 26; **not** DNS applied; **not** domain verified; **not** `approved` / **not** `provisioned`) |
| Responsible owner | Ops + identity |
| Provider | Resend |
| Domain | `piqsavi.com` |
| Preparation / evidence date | 2026-08-08 |
| Evidence type | Sanitized Resend sender-domain DNS-authentication preparation |
| Evidence path | [`external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png) |
| What was retained | Resend “Fill in your DNS Records” plan: DKIM TXT `resend._domainkey` (TTL Auto); Return-Path / Enable Sending MX `send` priority 10 + TXT TXT `send` (TTL Auto) for intended `send.piqsavi.com` namespace; optional DMARC TXT `_dmarc` with displayed `v=DMARC1; p=none;` (TTL Auto); Cloudflare Auto configure / Verify actions still available |
| Provider-generated values | DKIM / MX / SPF Content fields are visually abbreviated in the UI. Full values were **not** invented or transcribed. Provider-generated value retained in Resend dashboard; full value must be copied directly from Resend at Sprint 27 DNS execution time |
| Prepared record categories | DKIM prepared; Return-Path MX prepared; SPF prepared; DMARC `p=none` plan displayed |
| Not yet | Cloudflare DNS records added; DKIM/SPF/DMARC/MX published; DNS propagation; Resend domain verification; sender domain verified; authenticated delivery; email sent; production email enabled |
| Separation | EXT-09 preparation ≠ EXT-11 DNS hosting ≠ EXT-12 TLS. Sprint 27 owns DNS application/verification and delivery proof |
| Fallback | Same as EXT-08 (invite-only demotion) |
| Launch impact | Sprint 26 EXT-09 preparation no longer pending; Sprint 27 still blocked until DNS apply/verify + delivery proof |
| Register fields updated | `Application date` → `evidence verified 2026-08-08`; `Current status` → `applied`; provider Resend; domain `piqsavi.com`; evidence path retained |

---

## EXT-10 — Public domain registration

| Field | Value |
|-------|-------|
| Current documented status | `approved` (ownership/control evidenced; **not** `provisioned`) |
| Responsible owner | Ops |
| Public brand / domain | PiqSavi / `piqsavi.com` (see [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)) |
| Evidence date | 2026-08-08 |
| Evidence type | Sanitized Cloudflare registration/control proof |
| Evidence path | [`external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png) |
| What was retained | Cloudflare Registrations shows `piqsavi.com`, status **Active**; account email redacted; no API tokens, account IDs, payment, or billing data |
| Purchase / original registration date | Not evidenced by the screenshot — **not inferred**; register Application date = `evidence verified 2026-08-08` |
| Not yet | `provisioned` — reserved until the public hostname is genuinely usable |
| Explicit non-claims | Does **not** prove DNS configured, Cloudflare proxy enabled, app/production/staging routing, TLS/ACM/HTTPS, email SPF/DKIM/DMARC, or public website/API availability |
| Separation | EXT-11 (DNS) and EXT-12 (TLS) remain independent and `not_started` |
| Fallback | Delay public hostname |
| Launch impact | Ownership no longer blocks the chain; Sprint 41 public access still requires EXT-11/EXT-12 |
| Register fields updated | `Application date` → `evidence verified 2026-08-08`; `Current status` → `approved`; evidence path retained |

---

## EXT-17 — Support email

| Field | Value |
|-------|-------|
| Current documented status | `provisioned` (monitored inbox exists and receives mail) |
| Responsible owner | Ops + support |
| Public support address | `support@piqsavi.com` |
| Mailbox / receiving setup | Google Workspace / Gmail for `piqsavi.com`; `support@piqsavi.com` is an alternate email alias routed to the monitored PiqSavi Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox |
| Monitoring owner | PiqSavi Operations / Mark |
| Response expectation | within 1 business day |
| Evidence / action date | 2026-08-09 |
| Evidence type | Sanitized Gmail inbound receipt of an external message to `support@piqsavi.com` |
| Evidence path | [`external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png`](external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png) |
| What was retained | To `support@piqsavi.com`; subject `EXT-17 Support Inbox Verification — 2026-08-09`; date Aug 9, 2026, 8:39 PM; Gmail Inbox context; mailed-by/signed-by `gmail.com`; Standard encryption (TLS); personal external sender address redacted; no passwords, tokens, billing, or unrelated inbox contents |
| External receipt test | Succeeded — external Gmail message addressed to `support@piqsavi.com` received in the monitored PiqSavi Workspace Gmail inbox |
| Not yet | Public support contact publication in product/legal surfaces (Sprint 28 / 39); Resend/EXT-09 sender-domain DNS apply/verify; transactional delivery; Google Workspace DKIM/DMARC completion claims; larger support-team staffing |
| Fallback | Delay public launch |
| Launch impact | Support inbox bootstrap no longer blocks Sprint 26 for EXT-17; Sprint 28 / 39 / 45 still require publishing/using the contact path |
| Register fields updated | `Application date` → `2026-08-09`; `Current status` → `provisioned`; evidence path + operational notes retained |

---

## EXT-18 — Privacy contact

| Field | Value |
|-------|-------|
| Current documented status | `provisioned` (privacy contact designated and reachable) |
| Responsible owner | Legal / DPO-equivalent |
| Public privacy address | `privacy@piqsavi.com` |
| Role | PiqSavi Privacy |
| Designation / monitoring owner | Mark / PiqSavi Privacy |
| Designation date | 2026-08-09 |
| Owner acknowledgment | Mark / PiqSavi Privacy designates `privacy@piqsavi.com` as the PiqSavi public privacy contact for Sprint 26 EXT-18 bootstrap purposes (2026-08-09) |
| Mailbox / receiving setup | Google Workspace / Gmail for `piqsavi.com`; `privacy@piqsavi.com` is an alternate email alias routed to the monitored PiqSavi Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox |
| Escalation path | Privacy/legal matters requiring professional legal advice, legal interpretation, regulatory review, or counsel approval escalate to the future counsel relationship represented by EXT-19 |
| Evidence type | Sanitized Gmail inbound receipt of an external message to `privacy@piqsavi.com` |
| Evidence path | [`external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png`](external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png) |
| What was retained | To `privacy@piqsavi.com`; subject `EXT-18 Privacy Contact Verification — 2026-08-09`; date Aug 9, 2026, 9:19 PM; Gmail Inbox context; mailed-by/signed-by `gmail.com`; Standard encryption (TLS); personal external sender address redacted; no passwords, tokens, billing, or unrelated inbox contents |
| External receipt test | Succeeded — external Gmail message addressed to `privacy@piqsavi.com` received in the monitored PiqSavi Workspace Gmail inbox |
| Not yet | Formal statutory DPO appointment; Privacy Policy legal sufficiency / counsel written approval; public Privacy Policy publication (EXT-20 / Sprint 28); GDPR / Philippine DPA / CCPA/CPRA / global privacy-compliance claims |
| Fallback | Delay public launch |
| Launch impact | Privacy-contact bootstrap no longer blocks Sprint 26 for EXT-18; Sprint 28 / 45 still require publishing/using the contact path in Privacy Policy and related surfaces |
| Register fields updated | `Application date` → `2026-08-09`; `Current status` → `provisioned`; evidence path + operational notes retained |
| Separation | EXT-18 privacy contact (`privacy@piqsavi.com`) ≠ EXT-17 support contact (`support@piqsavi.com`) — do not merge |

---

## EXT-19 — Legal counsel engagement

| Field | Value |
|-------|-------|
| Current documented status | `applied` (counsel engagement accepted + consultation scheduled; **not** `approved`) |
| Responsible owner | Legal counsel |
| Counsel identity | Pauline Anne Sambuang |
| Firm affiliation | Not shown in retained evidence — **not invented** |
| Evidence / engagement date | 2026-08-10 |
| Confirmed consultation | 2026-08-19, 10:00 AM, Philippines local time |
| Evidence type | Sanitized Gmail engagement acceptance + schedule confirmation |
| Evidence paths | [`external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png`](external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png); [`external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png`](external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png) |
| What was retained | Engagement acceptance for PiqSavi legal consultation/review; scope covering ToS, Privacy/data-handling, affiliate/advertising disclosures, AI/recommendation disclosures/disclaimers, consumer-protection considerations, deletion/export/retention, cookie/tracking, country-specific considerations for intended markets; counsel confirmation of date/time with calendar-invite request; supporting-document request before consultation |
| Merchant/affiliate terms review in consultation scope | Discussion expanded to focused review topics for research shortlist Shopee, Lazada, TikTok Shop, Amazon, Temu — **does not** select providers in the register and **does not** advance EXT-01…EXT-05 to `applied` |
| Merchant-program application clearance | Signed record 2026-08-25: counsel-cleared to **apply** for those five merchants (conditions N/A; no hold). Sanitized: [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md). Signed PDF outside Git. |
| Not yet | Written legal approval of consumer ToS/Privacy (EXT-19 `approved`); Terms/Privacy publication; merchant applications submitted; merchant approval; credentials; launch legally approved; privacy-regime compliance claims |
| Fallback | Delay public launch |
| Launch impact | Sprint 26 EXT-19 engagement bootstrap no longer pending; merchant **application** legal gate is cleared; Sprint 28 / 44 still require written approval before EXT-19 `approved`; EXT-01…EXT-05 still require real submission evidence before `applied` |
| Register fields updated | `Application date` → `2026-08-10`; `Current status` → `applied`; evidence paths + consultation notes retained. Merchant-application clearance recorded in EXT-01…EXT-05 **notes** only — lifecycle remains `not_started`. |

---

## Explicit non-claims

- Creating this checklist alone did not advance EXT statuses; EXT-08 later advanced to `applied` only after sanitized Resend account-establishment evidence was retained; EXT-09 later advanced to `applied` only after sanitized Resend DNS-authentication **plan** evidence was retained; EXT-10 later advanced to `approved` only after sanitized ownership evidence was retained; EXT-17 later advanced to `provisioned` only after sanitized inbound receipt evidence was retained; EXT-18 later advanced to `provisioned` only after privacy-contact designation, owner acknowledgment, and sanitized inbound receipt evidence were retained; EXT-19 later advanced to `applied` only after sanitized counsel engagement acceptance and schedule-confirmation evidence were retained.
- No signup/provider-approval date was invented for EXT-08 (evidence verified 2026-08-08 only).
- No purchase/registration date was invented for EXT-10 (evidence verified 2026-08-08 only).
- This documentation/evidence task did **not** create a Resend API key, send transactional email, click Auto Configure, apply Cloudflare DNS, verify a sending domain, or publish SPF/DKIM/DMARC/MX for Resend.
- EXT-09 `applied` means preparation only — DNS records have **not** been applied or verified; domain is **not** verified; delivery is **not** proven.
- EXT-17 `provisioned` proves monitored support receiving for `support@piqsavi.com` only; it does **not** prove Resend/EXT-09 DNS apply/verify, Google Workspace DKIM/DMARC completion, or transactional identity email readiness.
- EXT-18 `provisioned` proves privacy-contact designation and reachability for `privacy@piqsavi.com` only; it does **not** prove formal DPO appointment, Privacy Policy legal sufficiency, EXT-19 written approval, or privacy-compliance completion.
- EXT-19 `applied` proves counsel engagement acceptance and scheduled consultation only; it does **not** prove written legal approval of Terms/Privacy, launch approval, or privacy-compliance completion. EXT-19 is **not** `approved`. Merchant-program **application** clearance (2026-08-25) is recorded separately and does **not** move EXT-01…EXT-05 to `applied`.
- EXT-11 / EXT-12 remain `not_started`; no DNS hosting / TLS claim is made from EXT-08 `applied`, EXT-09 `applied` (prep), EXT-10 `approved`, EXT-17 `provisioned`, EXT-18 `provisioned`, or EXT-19 `applied`.
- Remaining checklist actions (other than EXT-08 account bootstrap, EXT-09 DNS-auth preparation, EXT-10 ownership evidence, EXT-17 support-inbox provisioning, EXT-18 privacy-contact provisioning, EXT-19 counsel engagement, and merchant-application **counsel clearance**) are still required before Sprint 26 can close — specifically EXT-01…EXT-05 **real application submission evidence**. This checklist is **not** complete.
