# Sprint 26 — External Dependency Bootstrap Checklist

**Document type:** Action checklist (preparation only)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Related evidence:** [`SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Rule:** Do **not** change register status from `not_started` until real external action evidence exists. Do **not** invent dates. Do **not** claim an application was submitted from this document alone.

**Register snapshot at packaging:** all listed bootstrap rows remain `not_started` (no status advanced by this checklist).

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
| Can be started immediately | EXT-08 (provider selection + apply), EXT-10 (domain purchase), EXT-17 (support inbox), EXT-18 (privacy contact), EXT-19 (legal engagement scheduling) |
| Requires provider selection | EXT-01…EXT-05 (merchant/API partner per market), EXT-08 (email provider) |
| Requires a purchased/configured domain | EXT-09 (SPF/DKIM/DMARC on sender domain); EXT-11/12 later (DNS/TLS — out of Sprint 26 bootstrap list but blocked on EXT-10) |
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
| Current documented status | `not_started` |
| Responsible owner | Identity eng |
| Exact action the user must take | Select a transactional email provider; create/apply for an account suitable for staging→production identity mail; record provider decision |
| Information/documents needed | Business contact; sender domain plan (ties to EXT-10/EXT-09); expected volume; privacy/DPA awareness |
| Evidence that must be retained | Provider name; account/application confirmation ID; application/signup date; decision note (no API keys in git) |
| Fallback | Invite-only with self-serve reset disabled (demotes public beta) |
| Launch impact | Blocks public self-serve auth completion (Sprint 27) |
| Register fields to update after action | `Application date`, `Current status` → `applied` (or `approved`/`provisioned` only when truly reached), evidence notes (non-secret) |

---

## EXT-09 — Sender-domain SPF/DKIM/DMARC preparation

| Field | Value |
|-------|-------|
| Current documented status | `not_started` |
| Responsible owner | Ops + identity |
| Exact action the user must take | After EXT-10 domain exists and EXT-08 provider is chosen, prepare DNS auth records (SPF/DKIM/DMARC) per provider instructions; do not claim DNS green until verified |
| Information/documents needed | Registered domain (EXT-10); provider DKIM values; DMARC policy intent; DNS admin access |
| Evidence that must be retained | Record names/types planned or applied; verification screenshots/logs with secrets redacted; date of verification attempt |
| Fallback | Same as EXT-08 (invite-only demotion) |
| Launch impact | Blocks reliable public self-serve auth mail (Sprint 27) |
| Register fields to update after action | `Application date` (or prep start date), `Current status` only when evidence matches legend (`applied`/`provisioned` as appropriate), evidence notes |

**Class note:** Cannot complete without purchased/configured domain (EXT-10) and provider selection (EXT-08). Preparation planning can start immediately.

---

## EXT-10 — Public domain registration

| Field | Value |
|-------|-------|
| Current documented status | `not_started` (unchanged — not provisioned) |
| Responsible owner | Ops |
| Public brand / domain | PiqSavi / `piqsavi.com` (see [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)) |
| Exact action the user must take | Purchase/register the public domain intended for Global Public Beta hostname |
| Information/documents needed | Desired domain name(s); registrant identity; registrar account; billing |
| Owner report | `piqsavi.com` purchased and controlled via Cloudflare |
| Required evidence | Sanitized registrar/Cloudflare domain-ownership proof (domain name; ownership confirmation; date) |
| Evidence that must be retained | Registrar confirmation; domain name; registration date; WHOIS/redacted ownership proof |
| Do not retain in git | Account IDs; billing data; payment information; API tokens; zone secrets; account email where unnecessary |
| Next status after acceptable proof | `approved` |
| Not yet | `provisioned` — reserved until the public hostname is genuinely usable |
| Explicit non-claims | Owner report alone does not prove DNS, TLS, Cloudflare proxy, production routing, email authentication, or application domain cutover |
| Separation | EXT-11 (DNS) and EXT-12 (TLS) remain independent and `not_started` |
| Fallback | Delay public hostname |
| Launch impact | Blocks public web access path (Sprint 41 DNS/TLS chain) |
| Register fields to update after action | `Application date` (purchase date), `Current status` → `approved` only after sanitized ownership proof is retained; `provisioned` only later when hostname is usable; evidence notes |

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

- No EXT row status was advanced by creating this checklist.
- No application dates were invented.
- No provider accounts were created by this documentation task.
- Completing this checklist’s actions is still required before Sprint 26 can close.
