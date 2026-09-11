# DealBrain — External Dependency Register

**Status:** Authoritative register for Global Public Beta
**Master roadmap:** [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Reconciled:** 2026-08-24 against current register evidence; **2026-09-07** Sprint 26 PH validation-beta launch-scope reconciliation; **2026-09-08** EXT-01 `applied` + Sprint 26 close; **2026-09-10** EXT-19 written conditional counsel-review record sanitized (status remains `applied`); **2026-09-11** Early Access legal publication-activation attempt remains blocked as history; later **2026-09-11** owner-authorized content-layer publication advances EXT-20 / EXT-21 to `applied` (EXT-19 remains `applied`).
**Historical inventory HEAD:** `fd25cc927236807ae1fe412fa0c4eac2429fbc50`
**Current approved engineering baseline:** `d62a6fb176a6a0e6947b453c6517d5b0e5570ce0` (historical suite evidence; later `main` including PR #114 does **not** invalidate packaged Sprint 26 staging proof)
**Owner target:** Controlled Global Public Beta Launch no later than September 30, 2026
**September 2026 supported-market target:** Philippines only unless the owner later expands it.
**Rule:** No external dependency is guaranteed. Fallbacks must be honest (delay market naming, disable self-serve feature, or delay launch).

## Status legend

| Status | Meaning |
|--------|---------|
| `not_started` | No application / purchase / request yet |
| `applied` | Request submitted; awaiting decision |
| `approved` | Access granted; credentials pending or received |
| `provisioned` | Usable in target environment |
| `blocked` | Denied or stalled; fallback required |
| `n_a_beta` | Not required for the current Global Public Beta scope (deferred / optional / post-launch). Does **not** mean applied, approved, provisioned, or submitted. |

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
| EXT-01 | PH merchant/product-data access (legitimate data path; affiliate permission is not sufficient) | Marketplace eng + legal | 32 | Philippines market | 2026-09-08 | 2–8 weeks | `applied` | **RED** to name PH; September shopping launch **RED** until ≥1 useful PH product-data path is certified | September launch-critical requirement is **at least one legitimate, useful PH merchant/product-data path** (official merchant API, authorized product feed, authorized retailer integration, partner/data feed, permitted public data source, or another documented legitimate path). Affiliate approval does **not** satisfy EXT-01 unless it independently provides product-data rights/capabilities sufficient for live PiqSavi research. Counsel clearance 2026-08-25 is application-to-apply only and is not submission. **Request submitted 2026-09-08** to Lazada PH and Shopee PH — see [`evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md). Still required for Sprint 32: provider decision; then signed terms + credential proof + live normalized offer. `applied` ≠ `approved` / `provisioned` / certified. | Delay PH as named supported market. September public beta supported-market target is Philippines only unless the owner later expands it. | Market PH |
| EXT-02 | US merchant/API or affiliate access | Marketplace eng + legal | 33 | United States market | Sprint 26 kickoff (historical) | 2–8 weeks | `n_a_beta` | **GREEN** (not required for initial PH-only beta) | Historical counsel-clearance note retained. No US application is required for the September PH validation beta. Do **not** mark submitted. Owner expansion of supported markets would reopen this row. | Omit US from September supported-market list | Market US (deferred) |
| EXT-03 | SG merchant/API or affiliate access | Marketplace eng + legal | 34 | Singapore market | Sprint 26 kickoff (historical) | 2–8 weeks | `n_a_beta` | **GREEN** (not required for initial PH-only beta) | Historical counsel-clearance note retained. No SG application is required for the September PH validation beta. Do **not** mark submitted. | Omit SG from September supported-market list | Market SG (deferred) |
| EXT-04 | UK merchant/API or affiliate access | Marketplace eng + legal | 35 | United Kingdom market | Sprint 26 kickoff (historical) | 2–8 weeks | `n_a_beta` | **GREEN** (not required for initial PH-only beta) | Historical counsel-clearance note retained. No UK application is required for the September PH validation beta. Do **not** mark submitted. | Omit UK from September supported-market list | Market UK (deferred) |
| EXT-05 | CA merchant/API or affiliate access | Marketplace eng + legal | 36 | Canada market | Sprint 26 kickoff (historical) | 2–8 weeks | `n_a_beta` | **GREEN** (not required for initial PH-only beta) | Historical counsel-clearance note retained. No CA application is required for the September PH validation beta. Do **not** mark submitted. | Omit CA from September supported-market list | Market CA (deferred) |
| EXT-06 | Merchant credentials (named markets) | Ops + marketplace | 32 (PH); 33–36 if later expanded | global launch *(per named market)* | After approval | 1–2 weeks | `not_started` | **RED** for naming/certifying PH; not a multi-market September blocker | Secrets Manager entries; no plaintext in git. September named-market target is PH only. | Market cannot certify | Named market(s) |
| EXT-07 | Affiliate tracking IDs | Growth + marketplace | post-launch / later 32–36 | post-beta | After partner approval (if monetization is later activated) | 1–4 weeks | `n_a_beta` | **GREEN** (not a September blocker) | Valid tracked redirect in staging/prod **when** monetization is later activated. Zero affiliate-enabled merchants is acceptable for September. Ordinary outbound merchant links are acceptable. Affiliate tracking IDs, cookies/attribution, and revenue are **not** required for launch. | Ordinary outbound merchant links without monetization claims; disclose only when an affiliate relationship is actually active | Later monetized affiliate claims — **not** September shopping launch |
| EXT-08 | Transactional email provider (Resend) | Identity eng | 27 | identity | evidence verified 2026-08-08 | 3–10 days | `applied` | **AMBER** | Sanitized Resend dashboard/account-establishment proof retained at [`evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png) (see EXT-08 notes). Staging delivery evidenced 2026-09-08; register status not upgraded from the 2026-08-08 screenshot alone. Production attach remains Sprint 41 | Invite-only with self-serve reset disabled (demotes public beta) | Public self-serve auth |
| EXT-09 | Sender-domain authentication (SPF/DKIM/DMARC) | Ops + identity | 27 | identity | evidence verified 2026-08-08; Resend **Verified** 2026-09-08 | 3–14 days | `approved` | **GREEN** for Sprint 27 sender-domain auth | Plan screenshot [`evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png`](evidence/external/EXT-09_RESEND_DNS_AUTH_PLAN_2026-08-08.png). Public DKIM/SPF/MX/DMARC resolvable 2026-09-08. Owner-observed Resend domain status **Verified** recorded in [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md). Production email attach remains Sprint 41. Runbook: [`../runbooks/EXT_09_RESEND_DNS.md`](../runbooks/EXT_09_RESEND_DNS.md) | Same as EXT-08 | Public self-serve auth |
| EXT-10 | Domain registration (`piqsavi.com`) | Ops | 41 | production infrastructure | evidence verified 2026-08-08 | 1–3 days | `approved` | **GREEN** for ownership | Sanitized Cloudflare registration/control proof retained at [`evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png) (see EXT-10 notes) | Delay public hostname | Public web access |
| EXT-11 | DNS for public hostname | Ops | 41 | production infrastructure | After EXT-10 | 1–3 days | `not_started` | **AMBER** | Records resolving to ALB | Delay public access | Public web access |
| EXT-12 | TLS certificate (ACM or equivalent) | Ops | 41 | production infrastructure | After DNS | 1–7 days | `not_started` | **AMBER** | HTTPS synthetics green | Delay public access | Public web access |
| EXT-13 | AWS production account/resources | Ops | 41 | production infrastructure | Ongoing | Continuous | Partial TF only; not applied | **AMBER** | Applied TF + live `/ready` | Cannot launch production | Entire production launch |
| EXT-14 | Production secrets populated | Ops | 41 | production infrastructure | With EXT-13 | 1–5 days | `not_started` | **AMBER** | Redacted env dump; deploy fail-closed test | Cannot deploy prod | Entire production launch |
| EXT-15 | Analytics provider | Product eng | 39 | optional beta capability | Sprint 28 | 3–14 days | `not_started` | **AMBER** (optional) | Consent-gated events in staging | Privacy-safe first-party minimal events only; disclose limited learning | Beta learning (not whole launch) |
| EXT-16 | Error-tracking provider | Ops | 42 | optional beta capability | Sprint 39 | 3–10 days | `not_started` | **AMBER** (optional) | Sample error event + PII-safe config | CloudWatch logs-only (weaker) | Ops quality (launch if CW paging OK) |
| EXT-17 | Support email inbox | Ops + support | 28 / 39 | global launch | 2026-08-09 | 1–3 days | `provisioned` | **GREEN** for bootstrap reachability | Sanitized Gmail inbound receipt proof retained at [`evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png`](evidence/external/EXT-17_SUPPORT_INBOX_RECEIPT_2026-08-09.png) (see EXT-17 notes); public address `support@piqsavi.com` monitored | Delay public launch | Support obligation |
| EXT-18 | Privacy contact | Legal / DPO-equivalent | 28 | global launch | 2026-08-09 | 1–3 days | `provisioned` | **GREEN** for bootstrap reachability | Sanitized Gmail inbound receipt proof retained at [`evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png`](evidence/external/EXT-18_PRIVACY_CONTACT_RECEIPT_2026-08-09.png) (see EXT-18 notes); public address `privacy@piqsavi.com` designated and reachable | Delay public launch | Legal |
| EXT-19 | Legal review (ToS/Privacy/disclosures) | Legal counsel | 28 / 44 | global launch | 2026-08-10 | 2–6 weeks | `applied` | **AMBER** | Sanitized counsel engagement + schedule confirmation retained at [`evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_ENGAGEMENT_2026-08-10.png) and [`evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png`](evidence/external/EXT-19_LEGAL_COUNSEL_SCHEDULE_CONFIRMATION_2026-08-10.png). Signed comprehensive review (2026-08-19) is sanitized at [`evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) (see EXT-19 notes). Disposition: **cleared to proceed only after specified revisions / implementation conditions**. This is written **conditional** approval, **not** unconditional written approval of published consumer documents. Register taxonomy has no status for written conditional approval; closest truthful status remains `applied`. Do **not** use `approved` until published-version approval evidence exists. | Delay public launch | Entire launch |
| EXT-20 | Privacy Policy publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `applied` | **AMBER** | Live URL | Delay public launch | Entire launch. Content-layer `/privacy` is published as `privacy-2026-09-11`; staging deploy still required; production live URL remains cutover. |
| EXT-21 | Terms of Service publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `applied` | **AMBER** | Live URL | Delay public launch | Entire launch. Content-layer `/terms` is published as `terms-2026-09-11`; staging deploy still required; production live URL remains cutover. |
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

Sprint 26 originally opened applications for EXT-01…EXT-05, EXT-08, EXT-10, EXT-17, EXT-18, and scheduled legal engagement (EXT-19). After the 2026-09-07 PH validation-beta lock, **the only remaining Sprint 26 bootstrap that could block Sprint 26 close was EXT-01** (a real PH product-data access application/request). That request evidence now exists (2026-09-08). Sprint 26 is **COMPLETE / CLOSED**. EXT-02…EXT-05 are `n_a_beta` for this beta scope and are **not** September critical-path blockers. EXT-07 is `n_a_beta` / post-beta and is **not** a September blocker. EXT-08, EXT-09, EXT-10, EXT-17, EXT-18, and EXT-19 bootstrap actions remain complete for Sprint 26 purposes; later DNS/delivery (27), publication (28/45), and public hostname (41) work stay with those owning sprints. Sprint 32 still owns PH certification.

**Action checklist:** [`evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)

**Merchant application counsel clearance (2026-08-25):** sanitized record at [`evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md); owner application preparation at [`evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](evidence/SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md). Counsel clearance has been obtained for merchant/program applications covering Shopee, Lazada, TikTok Shop, Amazon, and Temu. These counsel-form merchant labels are separate from the authoritative EXT market-row identifiers. That does **not** make register EXT-01 `applied`, and it does **not** convert affiliate permission into product-data permission.

Technical current-main staging proof does **not** advance any EXT row and is **not** invalidated because `main` later advanced. EXT-08 is `applied` (Resend account-establishment screenshot; staging delivery now separately evidenced 2026-09-08). EXT-09 is **`approved`** (public DNS + Resend domain **Verified**, 2026-09-08; production email attach remains Sprint 41). EXT-10 is `approved` (ownership). EXT-17/EXT-18 are `provisioned`. EXT-19 is `applied` (written **conditional** 2026-08-19 review recorded; not unconditional written approval). EXT-02…EXT-05 and EXT-07 are `n_a_beta` for the current PH-only beta. EXT-01 is **`applied`** (2026-09-08 PH product-data requests; not `approved` / not `provisioned`).


### September 30, 2026 — items that can threaten the target

**RED (unless resolved or scope-reduced):**

- EXT-01 / EXT-06 (PH) — EXT-01 is now `applied` on 2026-09-08 Lazada PH and Shopee PH product-data request evidence. That is **not** approval, credentials, a feed, or certification. EXT-06 remains `not_started`. Counsel clearance to apply (2026-08-25) is historical. Shopee Affiliate dashboard access and Payment & Tax pending do **not** make EXT-01 `approved`. Affiliate Open API access is **not granted**. Lazada/Optimise affiliate approval, if any, is monetization permission only and does **not** certify a live research source. Naming PH is blocked. September public shopping launch remains blocked until **at least one useful PH product-data path** is certified. US/SG/UK/CA are **not** September substitutes unless the owner later expands supported markets.

**AMBER (schedule-sensitive / external):**

- EXT-08 — remains `applied` (account-establishment screenshot). Staging identity delivery evidenced 2026-09-08. Production attach remains Sprint 41
- EXT-11 / EXT-12 / EXT-13 / EXT-14 — public DNS/TLS/production AWS/secrets not applied
- EXT-19 / EXT-20 / EXT-21 — counsel engaged; conditional review is not unconditional approval. EXT-19 remains `applied`. EXT-20 / EXT-21 are `applied` for owner-authorized content-layer publication (`/privacy` `/terms` 200 in this revision). Staging deploy and production live URL remain separate.
- EXT-24 — paging destination not started
- EXT-29 — Search Console not started
- EXT-15 / EXT-16 / EXT-22 / EXT-23 / EXT-25 — optional; reduce claims rather than delay launch. **EXT-07 is not a September launch blocker** (2026-09-07): public beta launches without affiliate monetization; EXT-07 is `n_a_beta` / GREEN for September.

**GREEN (for the stated claim only):**

- EXT-10 ownership
- EXT-09 sender-domain authentication (Resend **Verified** + public DNS, 2026-09-08; not production email live)
- EXT-17 / EXT-18 bootstrap reachability
- EXT-02…EXT-05 not required for the initial PH-only beta
- EXT-07 not required for September (post-launch optional monetization)
- EXT-26…28 out of beta scope

Do not treat counsel’s scheduled 2026-08-19 consultation, merchant-application clearance, or a later conditional comprehensive review as unconditional written approval of published consumer legal documents (EXT-19 remains `applied`, not `approved`). Shopee Sprint 26 operational evidence does **not** move EXT-01 / EXT-06. EXT-07 is no longer a launch blocker.

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

### EXT-08 2026-09-08 staging-delivery addendum

Owner/operator-observed real Gmail delivery from `PiqSavi <no-reply@piqsavi.com>` on staging (verify, reset, email-change) is recorded in [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md). Live `/health` reports `identity_email_adapter=resend`. Register status stays `applied` because the retained provider screenshot is still account-establishment only. Production credentials remain Sprint 41.

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
| Explicit non-claims | The **2026-08-08 plan screenshot** does **not** prove Cloudflare DNS records added, DKIM/SPF/DMARC/MX published, DNS propagation, Resend domain verification, sender domain verified, authenticated email delivery, email sent, production email enabled, or Sprint 27 complete. “Plan generated” ≠ “DNS applied”. “EXT-09 `applied`” ≠ “domain verified” |
| Separation | EXT-09 = sender-domain authentication preparation / later DNS auth verification; EXT-11 = DNS hosting for public hostname; EXT-12 = TLS — do not merge. Sprint 27 owns DNS application/verification, Resend integration, and delivery proof |

### EXT-09 2026-09-08 public DNS addendum

This addendum does **not** replace the 2026-08-08 plan notes. Independent `dig`/`nslookup` on 2026-09-08 showed the plan’s DKIM (`resend._domainkey`), return-path MX/SPF (`send.piqsavi.com`), and optional `_dmarc` `p=none` rows as publicly resolvable. Full DKIM key material is **not** transcribed here.

This still does **not** prove Resend reports the domain **Verified**. Gmail delivery is **not** EXT-09 closure. Register status remained `applied` after the public-DNS check alone.

### EXT-09 2026-09-08 Resend Verified addendum

Owner/operator observation of the Resend dashboard for `piqsavi.com` on 2026-09-08:

| Field | Value |
|-------|-------|
| Current status | **`approved`** / **PASS / VERIFIED** |
| Domain status | **Verified** |
| Provider message | `Domain verified: Your domain is ready to send emails.` |
| DNS provider shown | Cloudflare |
| Region | Tokyo (`ap-northeast-1`) |
| Public DNS | Plan DKIM / return-path SPF / return-path MX / optional DMARC rows resolvable the same day |
| Evidence record | [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md) (sanitized text; no invented screenshot) |
| Explicit non-claims | Does **not** prove production `RESEND_API_KEY` attached, production email live, or Sprint 27 / P0-5 closed (`identity_email_ready` still false) |

This **Verified** addendum's P0-5 non-claim was true when recorded (Deploy Staging #31). It is not rewritten. Sprint 27 / P0-5 later closed on staging after PR #121 / Deploy Staging #32; see the addendum below. Production email attach remains Sprint 41.

### Sprint 27 / P0-5 2026-09-08 Post-PR #121 closure addendum

This addendum does **not** replace the EXT-09 Verified notes above.

| Field | Value |
|-------|-------|
| Sprint 27 / P0-5 | **COMPLETE / CLOSED** |
| Git SHA | `a5468ecf65be40bb36a053a97869cec97e3a529c` (PR #121 merge) |
| Deploy Staging | #32 / run `34231964695` SUCCESS |
| Live `/health` | `identity_email_adapter=resend`, `identity_email_ready=true` at `https://staging.piqsavi.com/health` on 2026-09-08 |
| Production `RESEND_API_KEY` / production email live | **Not proven. Sprint 41.** |
| Evidence record | [`evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md) §9 |

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
| Comprehensive counsel review (owner-stated; retained outside Git) | Historical Sprint 26 note: owner stated a signed comprehensive counsel review record exists covering the eight consumer/legal counsel-draft documents. Disposition: **cleared to proceed only after specified revisions / implementation conditions are completed**. This is **not** unconditional legal approval. The 2026-09-10 addendum below now sanitizes that signed record in-repo. |
| `approved` reserved for | Later — only after **written approval** evidence exists for the EXT-19 consumer-legal **published** scope. Do **not** use `approved` from engagement, schedule confirmation, merchant-application clearance, or a conditional “proceed after revisions” review alone |
| Explicit non-claims | Does **not** prove Terms/Privacy approved for publication; launch legally approved; GDPR / Philippine Data Privacy Act / CCPA/CPRA / global privacy compliance; Sprint 26 closure; or Sprint 27 start/completion. Merchant-application clearance does **not** mean merchants approved PiqSavi or that register EXT-01 is `applied`. |
| Separation | EXT-19 = counsel engagement / later written approval of consumer legal documents; merchant-program **application** clearance for Shopee, Lazada, TikTok Shop, Amazon, and Temu is noted here without changing EXT-01 lifecycle status; EXT-18 = privacy contact; EXT-20/EXT-21 = policy publication; EXT-01 = PH product-data bootstrap — do not merge |

### EXT-19 2026-09-10 written conditional-approval addendum

This addendum does **not** rewrite the 2026-08-10 engagement notes or the 2026-08-25 merchant-application clearance. It records the signed comprehensive consumer-legal review now sanitized in-repo.

| Field | Value |
|-------|-------|
| Current status | remains **`applied`** |
| Signed record title | PiqSavi — Comprehensive Legal Document Review & Approval Record |
| Counsel | Atty. Pauline Anne Sambuang |
| Review date | 2026-08-19 |
| Evidence path | [`evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md`](evidence/EXT-19_COUNSEL_APPROVAL_RECORD_2026-08-19.md) |
| Source | owner-supplied signed counsel record, verified outside repository |
| What changed | “Written approval absent” is no longer accurate as a blanket statement. A signed written **conditional** approval record exists. |
| Why not `approved` | The register taxonomy has no status for written conditional approval. `approved` remains reserved for written approval of the EXT-19 consumer-legal **published** scope. Do **not** use `approved` from a conditional “proceed after revisions” review. |
| Overall disposition | Counsel-cleared to proceed **only after** specified revisions / implementation conditions are completed. This is **not** unconditional legal approval. |
| August 25 working drafts | Owner-stated revised package dated 2026-08-25 exists outside Git. Those files were **not** present in the 2026-09-10 agent workspace and are not treated as published. |
| Exact written conditions | condition not explicitly documented in sanitized record |
| EXT-20 / EXT-21 | remain `not_started` |
| Early Access publication | `/privacy` and `/terms` remain fail-closed 404. Footer links remain gated. |
| Explicit non-claims | Does **not** prove published Privacy/Terms; unrestricted public launch; public-beta launch; merchant certification; live shopping; or affiliate monetization |

### EXT-19 2026-09-11 publication-activation addendum

This addendum does **not** rewrite the 2026-08-10 engagement notes, the 2026-08-25 merchant-application clearance, or the 2026-09-10 sanitized conditional-approval record. It records a later attempt to publish Privacy/Terms and activate Early Access legal links.

| Field | Value |
|-------|-------|
| Current status | remains **`applied`** |
| Evidence path | [`evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md`](evidence/EARLY_ACCESS_LEGAL_PUBLICATION_ACTIVATION_2026-09-11.md) |
| Audited main | `efa430c4962dee90e325fffbf84f475dc1883f12` |
| August 25 working drafts | Still **absent** from this repository / agent workspace. Owner-stated identifiers are unchanged. Repo `docs/legal/*_COUNSEL_DRAFT.md` copies are **not** treated as the revised package and are **not** published. |
| Exact written conditions | remain **condition not explicitly documented in sanitized record** |
| Assent / consent | **ASSENT DECISION REMAINS COUNSEL-AMBIGUOUS** — no Early Access clickwrap, acknowledgement copy, or consent persistence added |
| Legal/content ready | **No** — Privacy and Terms not published |
| Production infrastructure ready | **No** — separate from legal/content. PR #128 infrastructure blockers remain open (EXT-11…14, no `deploy-production.yml`, no founder GO) |
| EXT-20 / EXT-21 | remain `not_started` |
| Early Access publication | `/privacy` and `/terms` remain fail-closed 404. Footer links remain gated. |
| Resulting state | `EARLY ACCESS LEGAL ACTIVATION BLOCKED — COUNSEL CONDITION REMAINS UNRESOLVED` |
| Explicit non-claims | Does **not** prove published Privacy/Terms; Early Access legal activation; unrestricted public launch; public-beta launch; merchant certification; live shopping; affiliate monetization; or production cutover |

### EXT-19 2026-09-11 owner-authorized content-layer addendum

This addendum does **not** rewrite the 2026-08-10 engagement notes, the 2026-08-25 merchant-application clearance, the 2026-09-10 sanitized conditional-approval record, or the earlier 2026-09-11 blocked activation attempt. It records a later owner-authorized Early Access legal/content-layer publication.

| Field | Value |
|-------|-------|
| Current EXT-19 status | remains **`applied`** — `approved` stays reserved for unconditional counsel approval of published-scope documents |
| Evidence path | [`evidence/EARLY_ACCESS_OWNER_AUTHORIZED_LEGAL_ACTIVATION_2026-09-11.md`](evidence/EARLY_ACCESS_OWNER_AUTHORIZED_LEGAL_ACTIVATION_2026-09-11.md) |
| Source documents | August 25 working-draft markdown ingested from PR #130 branch; not a merge of that PR |
| Exact written conditions | remain **condition not explicitly documented in sanitized record** |
| Factual-currentness corrections | Owner-authorized objective product-description updates only (User-account deletion/export; first-party cookies/browser storage) |
| Assent | Owner-authorized Early Access checkbox: “I agree to the Terms of Service and acknowledge the Privacy Policy.” |
| Legal/content ready | **Yes for staging verification** — `/privacy` and `/terms` return 200 from published HTML |
| Production infrastructure ready | **No** — separate from legal/content. PR #128 infrastructure blockers remain open |
| EXT-20 | **`applied`** — Privacy published as `privacy-2026-09-11`. Staging deploy still required. Production live URL remains cutover. |
| EXT-21 | **`applied`** — Terms published as `terms-2026-09-11`. Staging deploy still required. Production live URL remains cutover. |
| EXT-22 | remains `not_started` — no CMP / banner |
| Resulting state | `EARLY ACCESS LEGAL/CONTENT LAYER READY — STAGING VERIFICATION REQUIRED — PRODUCTION INFRASTRUCTURE CUTOVER REMAINS` |
| Explicit non-claims | Does **not** prove new unconditional counsel approval; public-beta launch; merchant certification; live shopping; affiliate monetization; or production cutover |

### EXT-01 notes (PH product-data access — `applied` 2026-09-08)

EXT-01 is the Philippines **product-data** bootstrap row. Historical wording “PH merchant/API or affiliate access” is too ambiguous under the 2026-09-07 launch decision and is superseded for launch-critical meaning.

September launch-critical requirement:

> At least one legitimate, useful PH merchant/product-data path.

Acceptable sources (when actually authorized and useful for live PiqSavi research): official merchant API; authorized product feed; authorized retailer integration; partner/data feed; permitted public data source; another documented legitimate path.

**Affiliate permission ≠ product-data permission.** Affiliate approval does **not** satisfy EXT-01 unless it independently provides product-data rights/capabilities sufficient for live PiqSavi research.

| Field | Value |
|-------|-------|
| Current status (register lifecycle) | `applied` |
| Application / request date | 2026-09-08 |
| Counsel-clearance status | Shopee, Lazada, TikTok Shop, Amazon, and Temu applications are counsel-cleared to proceed (historical 2026-08-25). This does **not** select a PH product-data provider and does **not** by itself make EXT-01 `applied`. |
| Application / request submitted for PH product-data access? | **Yes** — Lazada PH and Shopee PH product-data access requests sent 2026-09-08. Evidence: [`evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md) |
| Merchant-approved product-data path? | **No** — awaiting external provider response/decision |
| Product-data / API rights | **unknown / not established** |
| Credentials | **No** |
| `applied` meaning | Request submitted; awaiting decision. Do **not** use `applied` from counsel clearance, affiliate dashboard access, Payment & Tax, or affiliate-network approval alone. Those still do not satisfy this row. |
| `approved` / `provisioned` reserved for | Later — only after a provider grants a usable PH product-data path and/or credentials exist. Do **not** use `approved` or `provisioned` from the 2026-09-08 emails. |
| Next Sprint 26 action | None — Sprint 26 bootstrap for EXT-01 is satisfied. Sprint 26 is **COMPLETE / CLOSED**. |
| Next owner / Sprint 32 action | Await provider response. Sprint 32 still requires approval/access where required, credentials/feed/API availability, technical connectivity, legal/contractual capability confirmation, current PH product-data validation, normalized live offers, source/capability policy evidence, staging certification, monitoring/coverage disclosure, and kill-switch/fail-closed behavior where required. |
| Explicit non-claims | Does **not** mean Lazada or Shopee approved PiqSavi; does **not** grant credentials, feeds, or production use; does **not** certify any merchant; does **not** enable affiliate tracking; does **not** close Sprint 32; does **not** create a `ResearchProviderCertification` |

**Shopee current truth (repository evidence):** A 2026-09-08 product-data / Open API partnership request was sent to `affiliate_ph@shopee.com` and is retained as EXT-01 `applied` evidence. That is **not** Shopee approval, Open Platform access, Affiliate Open API access, or credentials. [`evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](evidence/SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md) remains the historical affiliate-onboarding record: affiliate dashboard access, Payment & Tax submitted/pending, Affiliate Open API documented but **not granted**, AppID/Secret **none**, Seller/ISV Open Platform **held**. Dashboard access / Payment & Tax / affiliate membership ≠ product-data API access.

**Lazada current truth:** A 2026-09-08 authorized product-data / product-feed request was sent to `affiliate@lazada.com.ph` and is retained as EXT-01 `applied` evidence. That is **not** Lazada approval, a product feed, Open Platform access, or credentials. Historical owner-stated operational observation (no new affiliate screenshot added here): Optimise/Lazada affiliate access may be approved. That is **monetization permission only** unless separate product-data rights exist. An observed Optimise campaign showed Product Feed: **0 items**. Do **not** certify Lazada as a live research source from affiliate approval or from the 2026-09-08 request email.

**TikTok Shop current truth:** September integration is **not required**. Do not include a Singapore/paused campaign as PH launch evidence. No TikTok engineering is required pre-launch. Counsel clearance to apply remains historical.

### EXT-02…EXT-05 notes (optional markets — `n_a_beta` for this beta; rows retained)

These rows are **not deleted**. Historical counsel-clearance and `not_started` bootstrap intent remain true as history. Under the 2026-09-07 lock they are **not required for the initial PH-only public beta**, which matches `n_a_beta`.

| Field | Value |
|-------|-------|
| Current status (register lifecycle) | `n_a_beta` for EXT-02 (US), EXT-03 (SG), EXT-04 (UK), and EXT-05 (CA) |
| Historical bootstrap status | `not_started` — no application submission evidence |
| Application submitted? | **No** — do **not** mark submitted |
| September 2026 critical path | **No** |
| Reopen condition | Owner later expands supported markets beyond Philippines |
| Counsel-form warning | Do not map Shopee→PH, Lazada→US, TikTok Shop→SG, Amazon→UK, or Temu→CA from the signed form’s numbering |

**Shopee Sprint 26 operational evidence does not assign US/SG/UK/CA.** Payment & Tax pending is not a Philippines product-data application and is not Affiliate Open API approval.

## Market naming rule

A market may be named as **supported** in public materials only when:

1. Its EXT merchant/**product-data** dependency is `approved` or `provisioned` (affiliate-only approval is not enough)
2. Its certification sprint exit gate passes with a real, legally usable, current-data response **and** Sprint 31 capability-policy evidence (declared, evidence-backed, fail-closed enforced)
3. Coverage disclosure is published

Failure of a market dependency removes that market from the supported list without necessarily blocking global site access. For September 2026, the supported-market **target** is Philippines only unless the owner later expands it. EXT-02…EXT-05 being `n_a_beta` means those markets are omitted from the initial beta, not that they are certified.

## Merchant / affiliate EXT boundary (capability policy — statuses unchanged)

These clarifications do **not** change any EXT row’s `Current status`. They separate relationship progress from contractual capability certification (see Sprint 31 / 32–36 / EC-09).

| Dependency | Proves | Does **not** prove |
|------------|--------|--------------------|
| EXT-01 (`applied`) | PH product-data access **application/request submitted** (when evidence exists) | That all connector capabilities are authorized, or that affiliate tracking exists |
| EXT-01 (`approved` / `provisioned`) | A usable PH product-data path | Blanket permission for every data-use, display, cache, AI, comparison, or affiliate capability |
| EXT-02…EXT-05 (`n_a_beta`) | Not required for the current PH-only beta scope | That a US/SG/UK/CA application was submitted or that those markets are certified |
| EXT-06 | Technical credentials available in the target environment | Contractual/policy authorization for every capability |
| EXT-07 (`n_a_beta`) | Affiliate tracking is not required for September launch | Product-data comparison rights, or that affiliate economics may influence ranking |

**Rules:** Provider approval alone must not automatically enable every policy capability. Capability population and production certification occur later when actual terms, policies, credentials, and provider-specific evidence are available (market certification sprints). Affiliate permission and product-data permission remain independent. Unknown permissions fail closed.

### 2026-09-06 owner lock addendum (statuses unchanged)

This addendum does **not** move any EXT row. Counsel-clearance and Shopee operational facts above remain historical.

- Philippines is the initial commercial/product validation focus.
- Shopee Philippines and Lazada Philippines were recorded here as September PH beta **initial affiliate-monetization targets**. That 2026-09-06 monetization targeting is **historical**. The 2026-09-07 lock launches without affiliate monetization (see addendum below). They were never exclusive search coverage and are not certified by this lock.
- Search/recommendation **eligibility** depends on a legitimate product-data path, not EXT-07 affiliate tracking. Affiliate status must never exclude or privilege an otherwise relevant legitimate source. Eligibility is not a requirement to query every integrated merchant on every request.
- **TikTok Shop PH is not September-launch-critical.** Counsel clearance to apply to TikTok remains historical and does not make TikTok a Sprint 45 prerequisite. Do not represent TikTok as searched or supported unless an authorized path actually exists.
- Provider approval and affiliate approval still do not imply technical field exposure or policy permission for listing-price, discount, voucher, shipping, or checkout-cost fields. Policy states remain `allowed` / `restricted` / `prohibited` / `unknown` and are not technical availability.

### 2026-09-07 owner lock addendum — public beta without affiliate monetization + PH validation-beta scope

This addendum **does** change current-scope status for EXT-02…EXT-05 and EXT-07 to `n_a_beta`. It does **not** delete those rows, does **not** mark any application submitted as of 2026-09-07, did **not** move EXT-01 off `not_started` on that date, and does **not** delete historical affiliate/network evidence. The 2026-09-08 addendum below later moved EXT-01 to `applied`.

- Public beta launches **without affiliate monetization**. Affiliate revenue is not a launch requirement and is not a launch acceptance requirement. Ordinary outbound merchant links are valid launch behavior.
- PiqSavi will launch its initial public beta as a **Philippines-first product-validation beta without affiliate monetization**. September public beta supported-market target: **Philippines only** unless the owner later expands it.
- **EXT-07 is `n_a_beta` and optional.** It is **not** a September launch blocker. Shopee affiliate approval, Lazada/Optimise affiliate approval, tracking access, payout setup, and network credentials must not block Sprint 45. Zero affiliate-enabled merchants is acceptable.
- **EXT-01** remains launch-critical and means legitimate PH **product-data** access. As of this 2026-09-07 addendum it was `not_started`. Affiliate approval alone cannot satisfy it. At least one real useful PH data path is still required for Sprint 32 / September shopping launch. Affiliate approval is not product-search, API, feed, pricing, shipping, or voucher-data permission. Do not represent affiliate approval as product-data permission.
- **EXT-02…EXT-05** are deferred / not required for the initial PH beta (`n_a_beta`).
- Shopee Philippines and Lazada Philippines are **no longer September affiliate launch dependencies**. The 2026-09-06 “initial affiliate-monetization targets” note above remains historical.
- Affiliate architecture, attribution models, neutrality tests, and provider/network support must remain available for later activation. Future attachment is downstream of organic decision → winning merchant. Do **not** delete affiliate architecture or affiliate-neutrality tests.
- Mixed affiliate/non-affiliate runtime comparison is not required while zero affiliate-enabled merchants are active. Architecture/tests must still prove affiliate economics are absent from organic scoring/recommendation paths and cannot influence source eligibility, evaluated set, PiqScore, Recommendation, Best Piq, or organic ordering. Effective-cost requirements are unchanged.
- Sprint 26 technical staging proof remains intact. As of this 2026-09-07 addendum, Sprint 26 stayed **open** solely because EXT-01 still lacked a real PH product-data access application/request.
- EXT-19 remains `applied`. Conditional counsel review is not unconditional legal approval.

### 2026-09-08 EXT-01 applied / Sprint 26 close addendum

This addendum does **not** rewrite the 2026-09-07 lock. It records later owner-supplied PH product-data request evidence.

- EXT-01 moved `not_started` → **`applied`**. Application/request date: **2026-09-08**.
- Providers contacted: Lazada Philippines (`affiliate@lazada.com.ph`, 11:09 PM PH) and Shopee Philippines (`affiliate_ph@shopee.com`, 11:11 PM PH).
- Evidence: [`evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](evidence/EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md) plus sanitized Sent screenshots under [`evidence/external/`](evidence/external/).
- Sprint 26 is **COMPLETE / CLOSED**. See [`evidence/SPRINT_26_COMPLETION.md`](evidence/SPRINT_26_COMPLETION.md).
- EXT-01 is **not** `approved`, **not** `provisioned`, **not** certified. No credentials, feeds, or live PH offers are claimed.
- Sprint 32 remains in progress / blocked on external certification. A submitted email request alone does not satisfy Sprint 32.
- Affiliate monetization remains deferred. EXT-07 stays `n_a_beta`. Do not reactivate EXT-07 as a Sprint 26/32 acceptance requirement.
