# DealBrain — External Dependency Register

**Status:** Authoritative register for Global Public Beta
**Master roadmap:** [`GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Base HEAD:** `fd25cc927236807ae1fe412fa0c4eac2429fbc50`
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

---

## Register

| ID | Dependency | Owner | Target sprint | Scope | Application date | Expected decision window | Current status | Evidence required | Fallback | Blocks |
|----|------------|-------|---------------|-------|------------------|--------------------------|----------------|-------------------|----------|--------|
| EXT-01 | PH merchant/API or affiliate access | Marketplace eng + legal | 32 | Philippines market | Sprint 26 kickoff | 2–8 weeks | `not_started` | Signed terms + sandbox/live credential proof + live normalized offer | Delay PH as named supported market; site may still launch with other markets | Market PH |
| EXT-02 | US merchant/API or affiliate access | Marketplace eng + legal | 33 | United States market | Sprint 26 kickoff | 2–8 weeks | `not_started` | Same as EXT-01 for US | Delay US market naming | Market US |
| EXT-03 | SG merchant/API or affiliate access | Marketplace eng + legal | 34 | Singapore market | Sprint 26 kickoff | 2–8 weeks | `not_started` | Same for SG | Delay SG market naming | Market SG |
| EXT-04 | UK merchant/API or affiliate access | Marketplace eng + legal | 35 | United Kingdom market | Sprint 26 kickoff | 2–8 weeks | `not_started` | Same for UK | Delay UK market naming | Market UK |
| EXT-05 | CA merchant/API or affiliate access | Marketplace eng + legal | 36 | Canada market | Sprint 26 kickoff | 2–8 weeks | `not_started` | Same for CA | Delay CA market naming | Market CA |
| EXT-06 | Merchant credentials (all markets) | Ops + marketplace | 32–36 | global launch *(per named market)* | After approval | 1–2 weeks | `not_started` | Secrets Manager entries; no plaintext in git | Market cannot certify | Market(s) |
| EXT-07 | Affiliate tracking IDs | Growth + marketplace | 32–36 | optional beta capability | After partner approval | 1–4 weeks | `not_started` | Valid tracked redirect in staging/prod | Organic links without monetization claims; disclose | Monetized affiliate claims |
| EXT-08 | Transactional email provider (Resend) | Identity eng | 27 | identity | evidence verified 2026-08-08 | 3–10 days | `applied` | Sanitized Resend dashboard/account-establishment proof retained at [`evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png`](evidence/external/EXT-08_RESEND_ACCOUNT_2026-08-08.png) (see EXT-08 notes); delivery/reset+verify remains Sprint 27 | Invite-only with self-serve reset disabled (demotes public beta) | Public self-serve auth |
| EXT-09 | Sender-domain authentication (SPF/DKIM/DMARC) | Ops + identity | 27 | identity | With EXT-08 | 3–14 days | `not_started` | DNS auth green; test inbox delivery | Same as EXT-08 | Public self-serve auth |
| EXT-10 | Domain registration (`piqsavi.com`) | Ops | 41 | production infrastructure | evidence verified 2026-08-08 | 1–3 days | `approved` | Sanitized Cloudflare registration/control proof retained at [`evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png`](evidence/external/EXT-10_PIQSAVI_DOMAIN_OWNERSHIP_2026-08-08.png) (see EXT-10 notes) | Delay public hostname | Public web access |
| EXT-11 | DNS for public hostname | Ops | 41 | production infrastructure | After EXT-10 | 1–3 days | `not_started` | Records resolving to ALB | Delay public access | Public web access |
| EXT-12 | TLS certificate (ACM or equivalent) | Ops | 41 | production infrastructure | After DNS | 1–7 days | `not_started` | HTTPS synthetics green | Delay public access | Public web access |
| EXT-13 | AWS production account/resources | Ops | 41 | production infrastructure | Ongoing | Continuous | Partial TF only; not applied | Applied TF + live `/ready` | Cannot launch production | Entire production launch |
| EXT-14 | Production secrets populated | Ops | 41 | production infrastructure | With EXT-13 | 1–5 days | `not_started` | Redacted env dump; deploy fail-closed test | Cannot deploy prod | Entire production launch |
| EXT-15 | Analytics provider | Product eng | 39 | optional beta capability | Sprint 28 | 3–14 days | `not_started` | Consent-gated events in staging | Privacy-safe first-party minimal events only; disclose limited learning | Beta learning (not whole launch) |
| EXT-16 | Error-tracking provider | Ops | 42 | optional beta capability | Sprint 39 | 3–10 days | `not_started` | Sample error event + PII-safe config | CloudWatch logs-only (weaker) | Ops quality (launch if CW paging OK) |
| EXT-17 | Support email inbox | Ops + support | 28 / 39 | global launch | Sprint 26 | 1–3 days | `not_started` | Published address + monitored inbox | Delay public launch | Support obligation |
| EXT-18 | Privacy contact | Legal / DPO-equivalent | 28 | global launch | Sprint 26 | 1–3 days | `not_started` | Published contact | Delay public launch | Legal |
| EXT-19 | Legal review (ToS/Privacy/disclosures) | Legal counsel | 28 / 44 | global launch | Sprint 27 draft | 2–6 weeks | `not_started` | Written approval | Delay public launch | Entire launch |
| EXT-20 | Privacy Policy publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `not_started` | Live URL | Delay public launch | Entire launch |
| EXT-21 | Terms of Service publication | Legal + eng | 28 / 45 | global launch | After EXT-19 | 1–3 days | `not_started` | Live URL | Delay public launch | Entire launch |
| EXT-22 | Cookie-consent solution | Product + legal | 28 / 39 | optional beta capability | Sprint 28 | 1–3 weeks | `not_started` | Consent gate before non-essential analytics | First-party essential-only cookies; no third-party analytics | Analytics / tracking claims |
| EXT-23 | FX provider | Marketplace eng | 37 | optional beta capability | Sprint 31 | 1–3 weeks | `not_started` | Rates + timestamps; fail-closed tests | No cross-currency compare; disclose | Multi-currency compare |
| EXT-24 | Monitoring / paging destination | Ops / on-call | 42 | production infrastructure | Sprint 41 | 3–10 days | `not_started` | Page + ack ≤15m evidence | Delay production launch | Entire production launch |
| EXT-25 | AI-provider production quota | AI eng + ops | 38 / 43 | optional beta capability | Sprint 29 | 1–3 weeks | Unknown | Quota letter / console proof | Deterministic explanation fallback only; disclose | AI explanation claims |
| EXT-26 | Payment provider | — | — | post-beta | — | — | `n_a_beta` | — | Not required for beta | — |
| EXT-27 | Apple App Store account | — | — | post-beta | — | — | `n_a_beta` | — | Native app out of scope | — |
| EXT-28 | Google Play account | — | — | post-beta | — | — | `n_a_beta` | — | Native app out of scope | — |

---

## Application bootstrap (Sprint 26)

Sprint 26 must open applications for EXT-01…EXT-05, EXT-08, EXT-10, EXT-17, EXT-18, and schedule legal engagement (EXT-19) even though those sprints execute later. Decision latency is on the critical path.

**Action checklist (statuses unchanged until real evidence):** [`evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](evidence/SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)

Technical current-main staging proof does **not** advance any EXT row. Remaining Sprint 26 bootstrap rows stay `not_started` until real application/purchase/engagement evidence is retained. EXT-08 is now `applied` on sanitized Resend provider-selection/account-establishment evidence (see EXT-08 notes). EXT-10 is now `approved` on sanitized ownership/control evidence (see EXT-10 notes).

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

**EXT-09 status remains `not_started` and is unchanged by this evidence.**

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

## Market naming rule

A market may be named as **supported** in public materials only when:

1. Its EXT merchant/affiliate dependency is `approved` or `provisioned`
2. Its certification sprint exit gate passes with a real, legally usable, current-data response
3. Coverage disclosure is published

Failure of a market dependency removes that market from the supported list without necessarily blocking global site access.
