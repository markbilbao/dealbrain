# Sprint 26 — External Dependency Bootstrap Checklist

**Document type:** Action checklist (preparation only)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Related evidence:** [`SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Rule:** Do **not** change register status from `not_started` until real external action evidence exists. Do **not** invent dates. Do **not** claim an application was submitted from this document alone.

**Register snapshot:** EXT-08 is `applied` on retained sanitized Resend provider-selection/account-establishment evidence (2026-08-08). EXT-09 is `applied` on retained sanitized Resend sender-domain DNS-authentication **preparation** evidence (2026-08-08) — DNS not applied/verified. EXT-10 is `approved` on retained sanitized ownership evidence (2026-08-08). All other listed bootstrap rows remain `not_started`.

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
| Can be started immediately | EXT-17 (support inbox), EXT-18 (privacy contact), EXT-19 (legal engagement scheduling) |
| Provider account established (applied; not approved/provisioned) | EXT-08 (Resend selected; sanitized account-establishment proof, 2026-08-08) |
| Ownership evidence retained (approved; not provisioned) | EXT-10 (`piqsavi.com` sanitized Cloudflare registration/control proof, 2026-08-08) |
| Requires provider selection | EXT-01…EXT-05 (merchant/API partner per market) |
| Sender-domain auth plan prepared (applied; DNS not applied/verified) | EXT-09 (Resend DKIM / Return-Path MX+SPF / DMARC `p=none` plan for `piqsavi.com`, 2026-08-08) |
| Requires a purchased/configured domain | EXT-11/12 later (DNS/TLS — out of Sprint 26 bootstrap list; still `not_started`, separate from EXT-10 ownership) |
| Requires legal engagement | EXT-01…EXT-05 (terms/affiliate review), EXT-19 (counsel), EXT-18 coordination |
| Market-specific dependencies | EXT-01 PH, EXT-02 US, EXT-03 SG, EXT-04 UK, EXT-05 CA |

---

## EXT-01 — Philippines merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Select a PH merchant/API or affiliate partner; submit access/application with legal review of terms |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope PH; technical contact |
| Evidence that must be retained | Application confirmation (ticket/email/portal ID); submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay PH as named supported market; site may still launch with other markets |
| Launch impact | Blocks naming Philippines as a supported shopping market (Sprint 32) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, `Evidence required` notes / links (non-secret), decision-window if known |

---

## EXT-02 — United States merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Select a US merchant/API or affiliate partner; submit access/application with legal review of terms |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope US; technical contact |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay US market naming |
| Launch impact | Blocks naming United States as a supported shopping market (Sprint 33) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-03 — Singapore merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Select a SG merchant/API or affiliate partner; submit access/application with legal review of terms |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope SG; technical contact |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay SG market naming |
| Launch impact | Blocks naming Singapore as a supported shopping market (Sprint 34) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-04 — United Kingdom merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Select a UK merchant/API or affiliate partner; submit access/application with legal review of terms |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope UK; technical contact |
| Evidence that must be retained | Application confirmation; submitted date; partner name; terms draft/version identifier (no secrets in git) |
| Fallback | Delay UK market naming |
| Launch impact | Blocks naming United Kingdom as a supported shopping market (Sprint 35) |
| Register fields to update after action | `Application date`, `Current status` → `applied`, evidence notes (non-secret) |

---

## EXT-05 — Canada merchant/API

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Marketplace eng + legal |
| Exact action the user must take | Select a CA merchant/API or affiliate partner; submit access/application with legal review of terms |
| Information/documents needed | Business identity; intended use; redirect/affiliate model; market scope CA; technical contact |
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
| Current documented status | `not_started` |
| Responsible owner | Ops + support |
| Exact action the user must take | Create a monitored support inbox address; define monitoring ownership and response expectation |
| Information/documents needed | Address choice (may use EXT-10 domain later); mailbox provider; on-call/monitoring owner |
| Evidence that must be retained | Address; monitoring owner; creation date; proof mailbox receives mail (non-secret) |
| Fallback | Delay public launch |
| Launch impact | Blocks support obligation for public launch (Sprint 28 / 39 / 45) |
| Register fields to update after action | `Application date`, `Current status` → `provisioned` when monitored inbox exists, evidence notes |

---

## EXT-18 — Privacy contact

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Legal / DPO-equivalent |
| Exact action the user must take | Designate a privacy contact address/role suitable for Privacy Policy publication |
| Information/documents needed | Contact identity/role; mailbox; escalation path; alignment with EXT-19 counsel |
| Evidence that must be retained | Contact address/role; designation date; owner acknowledgment |
| Fallback | Delay public launch |
| Launch impact | Blocks legal/privacy minimum (Sprint 28) |
| Register fields to update after action | `Application date`, `Current status` → `provisioned` when contact is designated and reachable, evidence notes |

---

## EXT-19 — Legal counsel engagement

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Legal counsel |
| Exact action the user must take | Engage/schedule legal counsel for ToS/Privacy/disclosures review (engagement can start before full drafts exist) |
| Information/documents needed | Scope of review; target markets; affiliate/disclosure model; draft timeline for Sprint 28 |
| Evidence that must be retained | Engagement confirmation; counsel identity/firm; engagement/start date; scope summary |
| Fallback | Delay public launch |
| Launch impact | Blocks legal approval path (Sprint 28 / 44) |
| Register fields to update after action | `Application date` (engagement date), `Current status` → `applied` (or later `approved` only with written approval evidence), evidence notes |

---

## Explicit non-claims

- Creating this checklist alone did not advance EXT statuses; EXT-08 later advanced to `applied` only after sanitized Resend account-establishment evidence was retained; EXT-09 later advanced to `applied` only after sanitized Resend DNS-authentication **plan** evidence was retained; EXT-10 later advanced to `approved` only after sanitized ownership evidence was retained.
- No signup/provider-approval date was invented for EXT-08 (evidence verified 2026-08-08 only).
- No purchase/registration date was invented for EXT-10 (evidence verified 2026-08-08 only).
- This documentation/evidence task did **not** create a Resend API key, send email, click Auto Configure, apply Cloudflare DNS, verify a sending domain, or publish SPF/DKIM/DMARC/MX.
- EXT-09 `applied` means preparation only — DNS records have **not** been applied or verified; domain is **not** verified; delivery is **not** proven.
- EXT-11 / EXT-12 remain `not_started`; no DNS hosting / TLS claim is made from EXT-08 `applied`, EXT-09 `applied` (prep), or EXT-10 `approved`.
- Remaining checklist actions (other than EXT-08 account bootstrap, EXT-09 DNS-auth preparation, and EXT-10 ownership evidence) are still required before Sprint 26 can close. This checklist is **not** complete.
