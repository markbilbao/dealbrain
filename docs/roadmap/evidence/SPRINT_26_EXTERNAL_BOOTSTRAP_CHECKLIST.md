# Sprint 26 — External Dependency Bootstrap Checklist

**Document type:** Action checklist (preparation only)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Related evidence:** [`SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) · EXT-01 request evidence [`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md) · Shopee affiliate evidence [`SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md) (affiliate onboarding active / Open API access pending; does **not** by itself make EXT-01 `approved`) · Sprint 26 close [`SPRINT_26_COMPLETION.md`](SPRINT_26_COMPLETION.md)
**Rule:** Do **not** change register status from `not_started` until real external action evidence exists. Do **not** invent dates. Do **not** claim an application was submitted from this document alone. Do **not** treat affiliate approval as product-data permission.

**Register snapshot (2026-09-07 PH validation-beta reconciliation — historical):** EXT-01 remained `not_started` and was the **only remaining Sprint 26 bootstrap blocker** (legitimate PH product-data access application/request still missing on that date). EXT-02…EXT-05 are `n_a_beta` (not required for the initial PH-only beta; rows retained; not submitted). EXT-07 is `n_a_beta` / post-beta (not a September blocker). EXT-08 is `applied` on retained sanitized Resend provider-selection/account-establishment evidence (2026-08-08). EXT-09 is `applied` on retained sanitized Resend sender-domain DNS-authentication **preparation** evidence (2026-08-08) — DNS not applied/verified at that snapshot. EXT-10 is `approved` on retained sanitized ownership evidence (2026-08-08). EXT-17 is `provisioned` on retained sanitized support-inbox receipt evidence (2026-08-09). EXT-18 is `provisioned` on retained sanitized privacy-contact designation and receipt evidence (2026-08-09). EXT-19 is `applied` on retained sanitized counsel engagement + schedule confirmation evidence (2026-08-10) — later owner-stated comprehensive review is **conditional** (proceed after revisions / implementation conditions) and is **not** unconditional written approval. Shopee, Lazada, TikTok Shop, Amazon, and Temu merchant/program applications remain counsel-cleared to proceed (signed record 2026-08-25; sanitized: [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md)). Counsel-form row labels on that PDF are not register IDs.

**Register snapshot (2026-09-08 EXT-01 close):** EXT-01 is **`applied`**. Real PH product-data access requests were sent to Lazada Philippines and Shopee Philippines on 2026-09-08. Evidence: [`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md). Sprint 26 is **COMPLETE / CLOSED**. EXT-01 is not `approved` / not `provisioned`. Sprint 32 remains pending certification.

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
| Requires provider selection | EXT-01 (PH **product-data** path) — **submitted 2026-09-08** (`applied`). Counsel-cleared merchant/program applications are Shopee, Lazada, TikTok Shop, Amazon, and Temu. Affiliate approval is not enough and does not make EXT-01 `approved`. |
| Sender-domain auth plan prepared (applied; DNS not applied/verified) | EXT-09 (Resend DKIM / Return-Path MX+SPF / DMARC `p=none` plan for `piqsavi.com`, 2026-08-08) |
| Requires a purchased/configured domain | EXT-11/12 later (DNS/TLS — out of Sprint 26 bootstrap list; still `not_started`, separate from EXT-10 ownership) |
| Legal gate to submit merchant/program applications | Shopee, Lazada, TikTok Shop, Amazon, and Temu — **cleared** 2026-08-25 (application clearance only). Owner PH **product-data** submission + submission evidence now exists (2026-09-08). Register EXT-02…EXT-05 are `n_a_beta` for this beta. EXT-18 privacy-contact bootstrap still coordinates with EXT-19 for consumer-legal advice. |
| Market-specific dependencies | EXT-01 PH launch-critical; EXT-02 US, EXT-03 SG, EXT-04 UK, EXT-05 CA = `n_a_beta` for the initial PH-only beta |

---

## EXT-01 — Philippines merchant/product-data access

| Field | Value |
|-------|-------|
| Current documented status | `applied` (request submitted 2026-09-08; **not** `approved` / **not** `provisioned`) |
| Launch-critical meaning | At least one legitimate, useful PH **product-data** path. Affiliate permission ≠ product-data permission. `applied` satisfies Sprint 26 bootstrap only. |
| Acceptable path types | Official merchant API; authorized product feed; authorized retailer integration; partner/data feed; permitted public data source; another documented legitimate path |
| Counsel-clearance status | Shopee, Lazada, TikTok Shop, Amazon, and Temu applications are counsel-cleared to proceed (signed record 2026-08-25). This does **not** select any of those merchants as an approved PH product-data provider. |
| Responsible owner | Marketplace eng + legal |
| Exact action taken | Owner sent real PH **product-data** access requests to Lazada Philippines (`affiliate@lazada.com.ph`, 2026-09-08 11:09 PM PH) and Shopee Philippines (`affiliate_ph@shopee.com`, 2026-09-08 11:11 PM PH). Evidence: [`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md). Historical Shopee affiliate record: [`SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md). Payment & Tax pending, Affiliate dashboard access, and Lazada/Optimise affiliate approval do **not** make this row `approved`. An observed Optimise campaign with Product Feed: 0 items does **not** certify Lazada as a live research source. |
| Information/documents needed | Business identity; intended **product-data** use; market scope PH; technical contact — later Sprint 32 items remain **OWNER / PROVIDER INPUT REQUIRED** |
| Evidence retained | Sanitized Gmail Sent screenshots + this checklist / register notes (no secrets in git) |
| Fallback | Delay PH as named supported market until a path is certified. September public beta supported-market target is Philippines only unless the owner later expands it. |
| Launch impact | Sprint 26 bootstrap no longer pending. Naming Philippines as a supported shopping market (Sprint 32) and September PH shopping launch remain blocked until ≥1 useful PH product-data path is certified |
| Register fields updated | `Application date` → `2026-09-08`; `Current status` → `applied`; evidence paths retained |

---

## EXT-02 — United States merchant/API (deferred / `n_a_beta`)

| Field | Value |
|-------|-------|
| Current documented status | `n_a_beta` |
| Historical bootstrap status | `not_started` — no application submitted |
| Counsel-clearance status | Historical 2026-08-25 clearance retained. This does **not** assign any merchant to this US market row. |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | **None for September PH beta.** Do not mark submitted. Reopen only if the owner later expands supported markets. |
| Fallback | Omit US from the September supported-market list |
| Launch impact | Does **not** block September PH beta |
| Register fields to update after action | None unless owner expands markets |

---

## EXT-03 — Singapore merchant/API (deferred / `n_a_beta`)

| Field | Value |
|-------|-------|
| Current documented status | `n_a_beta` |
| Historical bootstrap status | `not_started` — no application submitted |
| Exact action the user must take | **None for September PH beta.** TikTok Shop Singapore/paused campaign is **not** PH launch evidence. |
| Launch impact | Does **not** block September PH beta |

---

## EXT-04 — United Kingdom merchant/API (deferred / `n_a_beta`)

| Field | Value |
|-------|-------|
| Current documented status | `n_a_beta` |
| Historical bootstrap status | `not_started` — no application submitted |
| Exact action the user must take | **None for September PH beta.** |
| Launch impact | Does **not** block September PH beta |

---

## EXT-05 — Canada merchant/API (deferred / `n_a_beta`)

| Field | Value |
|-------|-------|
| Current documented status | `n_a_beta` |
| Historical bootstrap status | `not_started` — no application submitted |
| Exact action the user must take | **None for September PH beta.** |
| Launch impact | Does **not** block September PH beta |

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
| Merchant-program application clearance | Signed record 2026-08-25: Shopee, Lazada, TikTok Shop, Amazon, and Temu applications counsel-cleared to proceed (conditions N/A; no hold). Sanitized: [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md). Signed PDF outside Git. Counsel-form row labels on that PDF are not register IDs. |
| Not yet | Written legal approval of **published** consumer ToS/Privacy (EXT-19 `approved`); Terms/Privacy publication; PH product-data **approval**/credentials (EXT-01 remains `applied` only); merchant approval; launch legally approved; privacy-regime compliance claims |
| Fallback | Delay public launch |
| Launch impact | Sprint 26 EXT-19 engagement bootstrap no longer pending; merchant **application** legal gate is cleared; Sprint 28 / 44 still require published-version approval before EXT-19 `approved`. A later owner-stated comprehensive review (eight documents; proceed only after specified revisions / implementation conditions) is **not** unconditional approval. |
| Register fields updated | `Application date` → `2026-08-10`; `Current status` → `applied`; evidence paths + consultation notes retained. EXT-02…EXT-05 are `n_a_beta` for this beta. EXT-01 later became `applied` on 2026-09-08 (separate evidence). |

---

## Explicit non-claims

- Creating this checklist alone did not advance EXT statuses; EXT-08 later advanced to `applied` only after sanitized Resend account-establishment evidence was retained; EXT-09 later advanced to `applied` only after sanitized Resend DNS-authentication **plan** evidence was retained; EXT-10 later advanced to `approved` only after sanitized ownership evidence was retained; EXT-17 later advanced to `provisioned` only after sanitized inbound receipt evidence was retained; EXT-18 later advanced to `provisioned` only after privacy-contact designation, owner acknowledgment, and sanitized inbound receipt evidence were retained; EXT-19 later advanced to `applied` only after sanitized counsel engagement acceptance and schedule-confirmation evidence were retained.
- No signup/provider-approval date was invented for EXT-08 (evidence verified 2026-08-08 only).
- No purchase/registration date was invented for EXT-10 (evidence verified 2026-08-08 only).
- This documentation/evidence task did **not** create a Resend API key, send transactional email, click Auto Configure, apply Cloudflare DNS, verify a sending domain, or publish SPF/DKIM/DMARC/MX for Resend.
- EXT-09 `applied` means preparation only — DNS records have **not** been applied or verified; domain is **not** verified; delivery is **not** proven.
- EXT-17 `provisioned` proves monitored support receiving for `support@piqsavi.com` only; it does **not** prove Resend/EXT-09 DNS apply/verify, Google Workspace DKIM/DMARC completion, or transactional identity email readiness.
- EXT-18 `provisioned` proves privacy-contact designation and reachability for `privacy@piqsavi.com` only; it does **not** prove formal DPO appointment, Privacy Policy legal sufficiency, EXT-19 written approval, or privacy-compliance completion.
- EXT-19 `applied` proves counsel engagement acceptance and scheduled consultation only; it does **not** prove written legal approval of Terms/Privacy, launch approval, or privacy-compliance completion. EXT-19 is **not** `approved`. Merchant-program **application** clearance (2026-08-25) is recorded separately and did **not** by itself move EXT-01…EXT-05 to `applied`.
- EXT-11 / EXT-12 remain `not_started`; no DNS hosting / TLS claim is made from EXT-08 `applied`, EXT-09 `applied` (prep), EXT-10 `approved`, EXT-17 `provisioned`, EXT-18 `provisioned`, or EXT-19 `applied`.
- Sprint 26 checklist close action is **complete**: EXT-01 real PH product-data access application/request evidence exists (2026-09-08). EXT-01 is `applied` only. EXT-02…EXT-05 and EXT-07 are `n_a_beta` for this beta. Affiliate approval alone cannot satisfy EXT-01 `approved`. Sprint 32 certification remains pending.
