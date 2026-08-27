# DealBrain — External Dependency Register

**Status:** Authoritative register for Global Public Beta
**Master roadmap:** [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Reconciled:** 2026-08-24 against current register evidence. Statuses below were **not guessed** and were not advanced by this lock.
**Historical inventory HEAD:** `fd25cc927236807ae1fe412fa0c4eac2429fbc50`
**Current approved engineering baseline:** `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0`
**Owner target:** Controlled Global Public Beta Launch no later than September 30, 2026
**Rule:** No external dependency is guaranteed. Fallbacks must be honest (delay market naming, disable self-serve feature, or delay launch).

## Status legend

| Status | Meaning |
|--------|---------|
| `not_started` | No application / purchase / request yet |
| `applied` | Request submitted; awaiting decision |
| `approved` | Access granted; credentials pending or received |
| `provisioned` | Usable in target environment |
| `blocked` | Denied or stalled; fallback required |
| `n_a_beta` | Not required for Global Public Beta |

## Scope legend

| Scope | Meaning |
|-------|---------|
| `global launch` | Blocks overall public beta cutover |
| `identity` | Blocks self-serve authentication / account recovery |
| `production infrastructure` | Blocks production environment / public hostname |
| `Philippines market` | Blocks naming PH as supported |
| `United States market` | Blocks naming US as supported |
| `Singapore market` | Blocks naming SG as supported |
| `United Kingdom market` | Blocks naming UK as supported |
| `Canada market` | Blocks naming CA as supported |
| `optional beta capability` | Degrades a beta capability; not whole launch |
| `post-beta` | Out of Global Public Beta scope |
| `seo / indexing` | Blocks ranking claims and Search Console proof; private-route noindex remains a separate NON-WAIVABLE engineering gate |

### September 30 risk legend

Derived from current evidence only. Do not mark external approvals green without proof.

| Risk | Meaning |
|------|---------|
| **GREEN** | Controllable/internal and on path, or already evidenced for the stated claim |
| **AMBER** | External or schedule-sensitive |
| **RED** | Currently blocks the September 30 target unless resolved or scope-reduced |

---

## Register

| ID | Dependency | Owner | Target sprint | Scope | Application date | Expected decision window | Current status | Sept 30 risk | Evidence required | Fallback | Blocks |
|----|------------|-------|---------------|-------|------------------|--------------------------|----------------|--------------|-------------------|----------|--------|
| EXT-01 | PH merchant/API or affiliate access | Marketplace eng + legal | 32 | Philippines market | Sprint 26 kickoff | 2–8 weeks | `not_started` | **RED** to name PH; shopping launch **RED** until ≥1 market is certified | Counsel clearance obtained for Shopee, Lazada, TikTok Shop, Amazon, and Temu applications (2026-08-25; merchant/program labels are separate from these market-row IDs — see notes). Still required: application submission evidence for this market; then signed terms + sandbox/live credential proof + live normalized offer | Delay PH as named supported market; site may still launch with other markets | Market PH |
| EXT-02 | US merchant/API or affiliate access | Marketplace eng + legal | 33 | United States market | Sprint 26 kickoff | 2–8 weeks | `not_started` | **RED** to name US | Same counsel-clearance note as EXT-01. Still required: application submission evidence for this market; then same as EXT-01 for US | Delay US market naming | Market US |
| EXT-03 | SG merchant/API or affiliate access | Marketplace eng + legal | 34 | Singapore market | Sprint 26 kickoff | 2–8 weeks | `not_started` | **RED** to name SG | Same counsel-clearance note as EXT-01. Still required: application submission evidence for this market; then same for SG | Delay SG market naming | Market SG |
| EXT-04 | UK merchant/API or affiliate access | Marketplace eng + legal | 35 | United Kingdom market | Sprint 26 kickoff | 2–8 weeks | `not_started` | **RED** to name UK | Same counsel-clearance note as EXT-01. Still required: application submission evidence for this market; then same for UK | Delay UK market naming | Market UK |
| EXT-05 | CA merchant/API or affiliate access | Marketplace eng + legal | 36 | Canada market | Sprint 26 kickoff | 2–8 weeks | `not_started` | **RED** to name CA | Same counsel-clearance note as EXT-01. Still required: application submission evidence for this market; then same for CA | Delay CA market naming | Market CA |
| EXT-06 | Merchant credentials (all markets) | Ops + marketplace | 32–36 | global launch *(per named market)* | After approval | 1–2 weeks | `not_started` | **RED** per named market | Secrets Manager entries; no plaintext in git | Market cannot certify | Market(s) |
| EXT-07 | Affiliate tracking IDs | Growth + marketplace | 32–36 | optional beta capability | After partner approval | 1–4 weeks | `not_started` | **AMBER** (optional) | Valid tracked redirect in staging/prod | Organic links without monetization claims; disclose | Monetized affiliate claims |
| EXT-08 | Transactional email provider (Resend) | Identity eng | 27 | identity | evidence verified 2026-08-08 | 3–10 days | `applied` | **AMBER** | Sanitized Resend dashboard/account-establishment proof retained at [`evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png) (see EXT-08 notes); delivery/reset+verify remains Sprint 27 | Invite-only with self-serve reset disabled (demotes public beta) | Public self-serve auth |
| EXT-09 | Sender-domain authentication (SPF/DKIM/DMARC) | Ops + identity | 27 | identity | evidence verified 2026-08-08 | 3–14 days | `applied` | **AMBER** | Sanitized Resend sender-domain DNS-authentication plan retained at [`evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png) (see EXT-09 notes); DNS apply/verify + delivery remain Sprint 27 | Same as EXT-08 | Public self-serve auth |
| EXT-10 | Domain registration (`piqsavi.com`) | Ops | 41 | production infrastructure | evidence verified 2026-08-08 | 1–3 days | `approved` | **GREEN** for ownership | Sanitized Cloudflare registration/control proof retained at [`evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png) (see EXT-10 notes) | Delay public hostname | Public web access |
| EXT-11 | DNS for public hostname | Ops | 41 | production infrastructure | After EXT-10 | 1–3 days | `not_started` | **AMBER** | Records resolving to ALB | Delay public access | Public web access |
| EXT-12 | TLS certificate (ACM or equivalent) | Ops | 41 | production infrastructure | After DNS | 1–7 days | `not_started` | **AMBER** | HTTPS synthetics green | Delay public access | Public web access |
| EXT-13 | AWS production account/resources | Ops | 41 | production infrastructure | Ongoing | Continuous | Partial TF only; not applied | **AMBER** | Applied TF + live `/ready` | Cannot launch production | Entire production launch |
| EXT-14 | Production secrets populated | Ops | 41 | production infrastructure | With EXT-13 | 1–5 days | `not_started` | **AMBER** | Redacted env dump; deploy fail-closed test | Cannot deploy prod | Entire production launch |
| EXT-15 | Analytics provider | Product eng | 39 | optional beta capability | Sprint 28 | 3–14 days | `not_started` | **AMBER** (optional) | Consent-gated events in staging | Privacy-safe first-party minimal events only; disclose limited learning | Beta learning (not whole launch) |
| EXT-16 | Error-tracking provider | Ops | 42 | optional beta capability | Sprint 39 | 3–10 days | `not_started` | **AMBER** (optional) | Sample error event + PII-safe config | CloudWatch logs-only (weaker) | Ops quality (launch if CW paging OK) |
| EXT-17 | Support email inbox | Ops + support | 28 / 39 | global launch | 2026-08-09 | 1–3 days | `provisioned` | **GREEN** for bootstrap reachability | Sanitized Gmail inbound receipt proof retained at [`evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png`](evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png) (see EXT-17 notes); public address `support@piqsavi.com` monitored | Delay public launch | Support obligation |
| EXT-18 | Privacy contact | Legal / DPO-equivalent | 28 | global launch | 2026-08-09 | 1–3 days | `provisioned` | **GREEN** for bootstrap reachability | Sanitized Gmail inbound receipt proof retained at [`evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png`](evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png) (see EXT-18 notes); public address `privacy@piqsavi.com` designated and reachable | Delay public launch | Legal |
| EXT-19 | Legal review (ToS/Privacy/disclosures) | Legal counsel | 28 / 44 | global launch | 2026-08-10 | 2–6 weeks | `applied` | **AMBER** | Sanitized counsel engagement + schedule confirmation retained at [`evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png) and [`evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png) (see EXT-19 notes); written approval still required before `approved` | Delay public launch | Entire launch |
| EXT-20 | Privacy Policy publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `not_started` | **AMBER** | Live URL | Delay public launch | Entire launch |
| EXT-21 | Terms of Service publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `not_started` | **AMBER** | Live URL | Delay public launch | Entire launch |
| EXT-22 | Cookie-consent solution | Product + legal | 28 / 39 | optional beta capability | Sprint 28 | 1–3 weeks | `not_started` | **AMBER** (optional) | Consent gate before non-essential analytics | First-party essential-only cookies; no third-party analytics | Analytics / tracking claims |
| EXT-23 | FX provider | Marketplace eng | 37 | optional beta capability | Sprint 31 | 1–3 weeks | `not_started` | **AMBER** (optional) | Rates + timestamps; fail-closed tests | No cross-currency compare; disclose | Multi-currency compare |
| EXT-24 | Monitoring / paging destination | Ops / on-call | 42 | production infrastructure | Sprint 41 | 3–10 days | `not_started` | **AMBER** | Page + ack ≤15m evidence | Delay production launch | Entire production launch |
| EXT-25 | AI-provider production quota | AI eng + ops | 38 / 43 | optional beta capability | Sprint 29 | 1–3 weeks | Unknown | **AMBER** (optional) | Quota letter / console proof | Deterministic explanation fallback only; disclose | AI explanation claims |
| EXT-26 | Payment provider | — | — | post-beta | — | — | `n_a_beta` | **GREEN** (out of scope) | — | Not required for beta | — |
| EXT-27 | Apple App Store account | — | — | post-beta | — | — | `n_a_beta` | **GREEN** (out of scope) | — | Native app out of scope | — |
| EXT-28 | Google Play account | — | — | post-beta | — | — | `n_a_beta` | **GREEN** (out of scope) | — | Native app out of scope | — |
| EXT-29 | Google Search Console | Product / SEO | 39 / 45 | seo / indexing | Not started | 1–14 days | `not_started` | **AMBER** | Property verified; sitemap submitted; intended public URLs visible; private UUID routes absent | Launch without ranking claims; private-route noindex remains mandatory | Ranking/indexability claims |

---

## Application bootstrap (Sprint 26)

Sprint 26 must open applications for EXT-01…EXT-05, EXT-08, EXT-10, EXT-17, EXT-18, and schedule legal engagement (EXT-19) even though those sprints execute later. Decision latency is on the critical path.

**Action checklist (statuses unchanged until real evidence):** [`evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)

**Merchant application counsel clearance (2026-08-25):** sanitized record at [`evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md); owner application preparation at [`evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md). Counsel clearance has been obtained for merchant/program applications covering Shopee, Lazada, TikTok Shop, Amazon, and Temu. These counsel-form merchant labels are separate from the authoritative EXT market-row identifiers. That does **not** make register EXT-01…EXT-05 `applied`.

Technical current-main staging proof does **not** advance any EXT row. Remaining Sprint 26 bootstrap rows stay `not_started` until real application/purchase/engagement evidence is retained. EXT-08 is now `applied` on sanitized Resend provider-selection/account-establishment evidence (see EXT-08 notes). EXT-09 is now `applied` on sanitized Resend sender-domain DNS-authentication **preparation** evidence (see EXT-09 notes). EXT-10 is now `approved` on sanitized ownership/control evidence (see EXT-10 notes). EXT-17 is now `provisioned` on sanitized support-inbox receipt evidence (see EXT-17 notes). EXT-18 is now `provisioned` on sanitized privacy-contact designation and receipt evidence (see EXT-18 notes). EXT-19 is now `applied` on sanitized counsel engagement and schedule-confirmation evidence (see EXT-19 notes). EXT-29 is newly registered as `not_started` for Search Console; this lock does not invent setup evidence.

### September 30, 2026 — items that can threaten the target

**RED (unless resolved or scope-reduced):**

- EXT-01…EXT-06 — no merchant applications or credentials evidenced. Counsel clearance has been obtained for merchant/program applications covering Shopee, Lazada, TikTok Shop, Amazon, and Temu (2026-08-25; see merchant-application notes under EXT-01…EXT-05). Those counsel-form merchant labels are separate from these market-row identifiers. Applications are **not** submitted. Naming any of PH/US/SG/UK/CA is blocked. Public shopping launch remains blocked until **at least one** market is certified. Individual markets may be omitted.

**AMBER (schedule-sensitive / external):**

- EXT-08 / EXT-09 — Resend account and DNS plan only; delivery and domain verification remain Sprint 27
- EXT-11 / EXT-12 / EXT-13 / EXT-14 — public DNS/TLS/production AWS/secrets not applied
- EXT-19 / EXT-20 / EXT-21 — counsel engaged; written approval and live policy URLs missing
- EXT-24 — paging destination not started
- EXT-29 — Search Console not started
- EXT-07 / EXT-15 / EXT-16 / EXT-22 / EXT-23 / EXT-25 — optional; reduce claims rather than delay launch

**GREEN (for the stated claim only):**

- EXT-10 ownership
- EXT-17 / EXT-18 bootstrap reachability
- EXT-26…28 out of beta scope

Do not treat counsel’s scheduled 2026-08-19 consultation as written approval of consumer legal documents (EXT-19 remains `applied`, not `approved`). Merchant-program **application** clearance dated 2026-08-25 is recorded in EXT-01…EXT-05 notes and does **not** move those rows to `applied`.

### EXT-08 notes (transactional email provider — applied)

| Field | Value |
|-------|-------|
| Current status | `applied` |
| Provider | Resend |
| Evidence / action date | 2026-08-08 |
| Evidence type | Sanitized Resend dashboard/account-establishment proof |
| Evidence path | [`evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png) |
| What the evidence shows | Resend dashboard onboarding (“Send your first email”); “Add an API key” step visible; recipient email redacted; placeholder `re_xxxxxxxxxx` only (not a real credential) |
| Signup / provider approval date | Not evidenced by the screenshot — **not inferred**; Application date recorded as `evidence verified 2026-08-08` |
| `approved` / `provisioned` reserved for | Later — only after credentials are truly granted for use and/or staging delivery proof exists. Do **not** use `approved` or `provisioned` for EXT-08 from account-establishment proof alone |
| Explicit non-claims | Does **not** prove API key created, API integration complete, email sent, transactional delivery verified, `piqsavi.com` added to Resend, sender domain verified, SPF/DKIM/DMARC configured, DNS changed, production credentials provisioned, or production email enabled |
| Separation | EXT-08 = provider selection / account establishment; EXT-09 = sender-domain authentication (SPF/DKIM/DMARC) — do not merge; Sprint 27 owns integration and delivery proof |

### EXT-09 notes (sender-domain authentication preparation — applied)

| Field | Value |
|-------|-------|
| Current status | `applied` |
| Interpretation | Sender-domain authentication **preparation** completed for Sprint 26. This does **not** mean DNS verification is complete. Do **not** use `approved` or `provisioned` for EXT-09 from plan evidence alone |
| Provider | Resend |
| Domain | `piqsavi.com` |
| Preparation / evidence date | 2026-08-08 |
| Evidence type | Sanitized Resend sender-domain DNS-authentication preparation showing provider-generated DKIM, Return-Path/SPF, and optional DMARC plan |
| Evidence path | [`evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png) |
| What the evidence shows | Resend “Fill in your DNS Records” plan UI; Domain Verification (DKIM) TXT `resend._domainkey`; Enable Sending MX/TXT for Return-Path subdomain `send` (intended `send.piqsavi.com` namespace); optional DMARC TXT `_dmarc` with displayed policy `v=DMARC1; p=none;`; Cloudflare Auto configure / Verify actions still available |
| Provider-generated values | Some Content fields are visually abbreviated with ellipsis / `[…]` in the Resend UI. Full provider-generated values are **not** transcribed here. Provider-generated value retained in Resend dashboard; full value must be copied directly from Resend at Sprint 27 DNS execution time |
| Return-Path clarification | `send` is the selected Resend custom Return-Path subdomain for the `send.piqsavi.com` namespace. This does **not** create a user mailbox and is **not** PiqSavi support/privacy inbox MX configuration. Receiving remains outside this task |
| DMARC clarification | Planned provider configuration currently shows `v=DMARC1; p=none;` only — not enforcement. Do not upgrade to quarantine/reject from this evidence |
| Explicit non-claims | Does **not** prove Cloudflare DNS records added, DKIM/SPF/DMARC/MX published, DNS propagation, Resend domain verification, sender domain verified, authenticated email delivery, email sent, production email enabled, or Sprint 27 complete. “Plan generated” ≠ “DNS applied”. “EXT-09 `applied`” ≠ “domain verified” |
| Separation | EXT-09 = sender-domain authentication preparation / later DNS auth verification; EXT-11 = DNS hosting for public hostname; EXT-12 = TLS — do not merge. Sprint 27 owns DNS application/verification, Resend integration, and delivery proof |

**DNS records have NOT been applied or verified.**

### EXT-10 notes (domain ownership — approved)

| Field | Value |
|-------|-------|
| Current status | `approved` |
| Evidence date | 2026-08-08 |
| Evidence type | Sanitized Cloudflare registration/control proof |
| Evidence path | [`evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png) |
| What the evidence shows | Cloudflare Registrations lists `piqsavi.com` with status **Active**; displayed expiration Aug 7, 2027; account email redacted |
| Purchase / original registration date | Not evidenced by the screenshot — **not inferred**; Application date recorded as `evidence verified 2026-08-08` |
| `provisioned` reserved for | Later — only after the public hostname is genuinely usable (DNS/TLS/routing evidenced separately). Do **not** use `provisioned` for EXT-10 from ownership proof alone |
| Explicit non-claims | Ownership/control evidence does **not** prove DNS configured, Cloudflare proxy enabled, PiqSavi app routing, production/staging routing, TLS/ACM/HTTPS listener configured, email sender-domain authentication (SPF/DKIM/DMARC), or public website/API hostname availability |
| Separation | EXT-10 = domain ownership; EXT-11 = DNS; EXT-12 = TLS/certificate — do not merge |
| Brand policy | [`PIQSAVI_PUBLIC_BRAND_POLICY.md`](PIQSAVI_PUBLIC_BRAND_POLICY.md) |

**EXT-11 and EXT-12 status remain `not_started` and are unchanged by this evidence.**

### EXT-17 notes (support email inbox — provisioned)

| Field | Value |
|-------|-------|
| Current status | `provisioned` |
| Public support address | `support@piqsavi.com` |
| Receiving architecture | Google Workspace / Gmail for `piqsavi.com`; `support@piqsavi.com` configured as an alternate email alias routed to the monitored PiqSavi Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox |
| Monitoring owner | PiqSavi Operations / Mark |
| Response expectation | within 1 business day |
| Evidence / action date | 2026-08-09 |
| Evidence type | Sanitized Gmail inbound receipt of an external message addressed to `support@piqsavi.com` |
| Evidence path | [`evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png`](evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png) |
| What the evidence shows | Gmail Inbox receipt; To `support@piqsavi.com`; subject `EXT-17 Support Inbox Verification — 2026-08-09`; date Aug 9, 2026, 8:39 PM; mailed-by/signed-by `gmail.com`; Standard encryption (TLS); personal external sender address redacted |
| Explicit non-claims | Does **not** prove Resend sender-domain authentication, EXT-09 DNS application/verification, Google Workspace DKIM/DMARC completion, production transactional email delivery, public support UI publication, larger support-team staffing, Sprint 26 closure, or Sprint 27 start/completion |
| Separation | EXT-17 = monitored support receiving inbox; EXT-08/EXT-09 = transactional sending / sender-domain auth (Sprint 27); EXT-18 = privacy contact — do not merge |

### EXT-18 notes (privacy contact — provisioned)

| Field | Value |
|-------|-------|
| Current status | `provisioned` |
| Public privacy address | `privacy@piqsavi.com` |
| Role | PiqSavi Privacy |
| Designation / monitoring owner | Mark / PiqSavi Privacy |
| Designation date | 2026-08-09 |
| Owner acknowledgment | Mark / PiqSavi Privacy designates `privacy@piqsavi.com` as the PiqSavi public privacy contact for Sprint 26 EXT-18 bootstrap purposes (2026-08-09) |
| Receiving architecture | Google Workspace / Gmail for `piqsavi.com`; `privacy@piqsavi.com` configured as an alternate email alias routed to the monitored PiqSavi Workspace Gmail inbox (`mark@piqsavi.com`) — **not** an independent dedicated mailbox |
| Escalation path | Privacy/legal matters requiring professional legal advice, legal interpretation, regulatory review, or counsel approval escalate to the future counsel relationship represented by EXT-19 |
| Reachable | Yes — external message addressed to `privacy@piqsavi.com` received in the monitored PiqSavi Workspace Gmail inbox |
| Evidence / action date | 2026-08-09 |
| Evidence type | Sanitized Gmail inbound receipt of an external message addressed to `privacy@piqsavi.com` |
| Evidence path | [`evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png`](evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png) |
| What the evidence shows | Gmail Inbox receipt; To `privacy@piqsavi.com`; subject `EXT-18 Privacy Contact Verification — 2026-08-09`; date Aug 9, 2026, 9:19 PM; mailed-by/signed-by `gmail.com`; Standard encryption (TLS); personal external sender address redacted |
| Explicit non-claims | Does **not** prove formal statutory DPO appointment, Privacy Policy legal sufficiency, lawyer/counsel engagement, EXT-19 completion, GDPR / Philippine Data Privacy Act / CCPA/CPRA / global privacy compliance, public Privacy Policy publication, Sprint 26 closure, or Sprint 27 start/completion |
| Separation | EXT-18 = privacy contact designation and reachability; EXT-17 = support inbox (`support@piqsavi.com`) — do not merge; EXT-19 = legal counsel engagement; EXT-20 = Privacy Policy publication |

### EXT-19 notes (legal counsel engagement — applied)

| Field | Value |
|-------|-------|
| Current status | `applied` |
| Counsel identity | Pauline Anne Sambuang |
| Firm affiliation | Not shown in retained evidence — **not invented** |
| Evidence / engagement date | 2026-08-10 |
| Confirmed consultation | 2026-08-19, 10:00 AM, Philippines local time |
| Evidence type | Sanitized Gmail engagement acceptance + schedule confirmation |
| Evidence paths | [`evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png); [`evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png) |
| What the engagement evidence shows | Counsel email accepting “the legal consultation and review for PiqSavi”; engagement scope covering Terms of Service; Privacy Policy and data-handling disclosures; affiliate and advertising disclosures; AI/recommendation-related disclosures and disclaimers; consumer-protection considerations; account deletion / data export / retention; cookie and tracking disclosures; applicable country-specific considerations for intended markets; weekday availability noted; request for additional materials beforehand |
| What the schedule evidence shows | Counsel reply: “Confirming the date and time. Please send a calendar invite.”; request to send supporting documents beforehand for comparison/mapping of restrictions |
| Consultation scope (engagement + owner-stated merchant review expansion) | Consumer legal topics above; focused merchant/affiliate terms-review discussion for research shortlist Shopee, Lazada, TikTok Shop, Amazon, Temu (comparison, PiqScore/derived scoring, affiliate neutrality, affiliate vs product-data permission, transformation/AI use, caching/ratings/reviews/retention, redirect/attribution, provider-specific restrictions) |
| Supporting materials | Counsel requested supporting contracts/documents before the consultation |
| Merchant-program application clearance (separate from EXT-19 `approved`) | Signed counsel application-authorization record dated 2026-08-25: Shopee, Lazada, TikTok Shop, Amazon, and Temu merchant/program applications counsel-cleared to proceed; consolidated conditions N/A; no hold. Sanitized engineering record: [`evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md). Signed PDF retained outside Git. Counsel-form row labels on that PDF are **not** register IDs. This does **not** approve Terms/Privacy, launch, or register EXT-01…EXT-05 `applied`. |
| `approved` reserved for | Later — only after **written approval** evidence exists for the EXT-19 consumer-legal scope. Do **not** use `approved` from engagement, schedule confirmation, or merchant-application clearance alone |
| Explicit non-claims | Does **not** prove Terms/Privacy approved; launch legally approved; GDPR / Philippine Data Privacy Act / CCPA/CPRA / global privacy compliance; Sprint 26 closure; or Sprint 27 start/completion. Merchant-application clearance does **not** mean merchants approved PiqSavi or that register EXT-01…EXT-05 are `applied`. |
| Separation | EXT-19 = counsel engagement / later written approval of consumer legal documents; merchant-program **application** clearance for Shopee, Lazada, TikTok Shop, Amazon, and Temu is noted here without changing EXT-01…EXT-05 market-row lifecycle status; EXT-18 = privacy contact; EXT-20/EXT-21 = policy publication; EXT-01…EXT-05 = market merchant/API bootstrap rows — do not merge |

### EXT-01…EXT-05 notes (market rows — merchant application counsel clearance; lifecycle unchanged)

Counsel clearance has been obtained for merchant/program applications covering Shopee, Lazada, TikTok Shop, Amazon, and Temu. These counsel-form merchant labels are separate from the authoritative EXT market-row identifiers. Do not rename these rows. Do not map Shopee to PH, Lazada to US, TikTok Shop to SG, Amazon to UK, or Temu to CA from the signed form’s numbering.

| Field | Value |
|-------|-------|
| Current status (register lifecycle) | `not_started` for EXT-01 (PH), EXT-02 (US), EXT-03 (SG), EXT-04 (UK), and EXT-05 (CA) |
| Counsel-clearance status | Shopee, Lazada, TikTok Shop, Amazon, and Temu applications are counsel-cleared to proceed |
| Counsel-review / signed-record date | 2026-08-25 |
| Counsel | Pauline Anne Sambuang |
| Consolidated conditions / exceptions | N/A |
| Hold items | None |
| Application submitted? | **No** — no submission evidence |
| Merchant-approved? | **No** |
| Product-data / API rights | **unknown** |
| Credentials | **No** |
| Market assignment | **OWNER INPUT REQUIRED** per merchant/program |
| Evidence type | Sanitized engineering record only |
| Evidence path | [`evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md) |
| Signed PDF | Received and retained **outside** the repository |
| `applied` reserved for | Later — only after real application **submission** evidence for the affected **market** row. Do **not** use `applied` from counsel clearance alone |
| Next action | Owner identifies merchant/program, official portal, and intended market(s); supplies missing application fields; submits; retains evidence using [`evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md) |
| Explicit non-claims | Does **not** select a provider on any market row; does **not** prove affiliate, catalog, display, cache, AI, or production permission; does **not** issue credentials or tracking IDs; does **not** start Sprint 32 or create a `ResearchProviderCertification` |

## Market naming rule

A market may be named as **supported** in public materials only when:

1. Its EXT merchant/affiliate dependency is `approved` or `provisioned`
2. Its certification sprint exit gate passes with a real, legally usable, current-data response **and** Sprint 31 capability-policy evidence (declared, evidence-backed, fail-closed enforced)
3. Coverage disclosure is published

Failure of a market dependency removes that market from the supported list without necessarily blocking global site access.

## Merchant / affiliate EXT boundary (capability policy — statuses unchanged)

These clarifications do **not** change any EXT row’s `Current status`. They separate relationship progress from contractual capability certification (see Sprint 31 / 32–36 / EC-09).

| Dependency | Proves | Does **not** prove |
|------------|--------|--------------------|
| EXT-01…EXT-05 (`applied`) | Relationship / access **application submitted** (when evidence exists) | That all connector capabilities are authorized |
| EXT-01…EXT-05 (`approved` / `provisioned`) | Partner/API access granted or usable credentials path | Blanket permission for every data-use, display, cache, AI, comparison, or affiliate capability |
| EXT-06 | Technical credentials available in the target environment | Contractual/policy authorization for every capability |
| EXT-07 | Affiliate tracking / monetized redirect where applicable | Product-data comparison rights, or that affiliate economics may influence ranking |

**Rules:** Provider approval alone must not automatically enable every policy capability. Capability population and production certification occur later when actual terms, policies, credentials, and provider-specific evidence are available (market certification sprints). Affiliate permission and product-data permission remain independent. Unknown permissions fail closed.
