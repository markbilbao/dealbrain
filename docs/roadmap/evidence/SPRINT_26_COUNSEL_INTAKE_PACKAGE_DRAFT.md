# DRAFT — INTERNAL PREPARATION ONLY
# NOT LEGAL ADVICE
# NOT YET REVIEWED BY LEGAL COUNSEL
# DOES NOT ADVANCE EXT-01…05 OR EXT-19

**Document type:** Internal counsel intake package (preparation only)  
**Public brand:** PiqSavi  
**Internal codename:** DealBrain  
**Authority sources:**  
[`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md) ·  
[`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md) ·  
[`../GAP_INVENTORY.md`](../GAP_INVENTORY.md) ·  
[`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md) ·  
[`SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md) ·  
[`SPRINT_26_COMPLETION_DRAFT.md`](SPRINT_26_COMPLETION_DRAFT.md) ·  
[`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md) ·  
[`../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md) ·  
[`../sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md`](../sprints/SPRINT_31_MERCHANT_PLATFORM_UNIFICATION.md)

**Register snapshot at draft time (unchanged by this document):**  
EXT-01…EXT-05 `not_started` · EXT-19 `not_started` · EXT-08 `applied` · EXT-09 `applied` (DNS prep only) · EXT-10 `approved` · EXT-17 `provisioned` · EXT-18 `provisioned`

**Purpose:** Assemble repository-supported product facts and counsel questions so a future external briefing can be prepared quickly. This file is **not** an engagement, application, legal opinion, compliance certificate, or Sprint 26 close.

---

## A. PiqSavi product facts

Repository-supported facts only:

| Item | Locked / documented value |
|------|---------------------------|
| Public brand | **PiqSavi** |
| Public tagline | **Your AI Personal Shopper** |
| Internal engineering codename | **DealBrain** |
| Primary public domain | **piqsavi.com** (canonical URL `https://piqsavi.com`) |
| Public consumer score name | **PiqScore** |
| Internal scoring contract / engine | **DealScore** (e.g. `WeightedDealScoreEngine`; machine fields remain `deal_score` / related) |
| Personalized display naming | Consumer-visible PersonalDealScore may be shown as **Personalized PiqScore** |
| Support contact (bootstrap) | `support@piqsavi.com` (EXT-17 `provisioned`) |
| Privacy contact (bootstrap) | `privacy@piqsavi.com` (EXT-18 `provisioned`) |

### Intended product flow (architecture boundary)

```text
merchant / product data
  → normalization
  → objective DealScore / PiqScore
  → Recommendation (customer action)
  → optional personalization
  → AI explanation
  → affiliate link attachment after ranking
```

### Architecture boundaries (product facts, not legal conclusions)

| Concern | Repository boundary |
|---------|---------------------|
| **PiqScore / DealScore** | Objective offer evaluation. Public feature name is PiqScore; internal contract remains DealScore. |
| **Recommendation** | Customer action / recommendation outcome — distinct from objective score ownership. |
| **Personalization** | May affect the personally recommended choice without rewriting the canonical objective score. |
| **AI Personal Shopper** | Explains evidence, tradeoffs, risks, and alternatives (with deterministic fallback concepts in later UI/email sprints). |
| **Affiliate attachment** | Occurs **after** ranking; must not feed objective score or organic rank. |
| **Sponsored** | Must remain separate from organic ranking / objective score. |

These are engineering/product boundaries from roadmap and brand policy. They are **not** legal advice and do **not** prove contractual permission for any merchant use.

---

## B. Affiliate neutrality

Repository-locked product/engineering rules (questions for counsel when reviewing merchant/affiliate programs — **not** legal conclusions):

1. Affiliate commission must **never** raise DealScore / PiqScore.
2. Affiliate economics (commission, partner priority, conversion value, affiliate availability) must **not** alter organic ranking.
3. Affiliate link attachment occurs **after** ranking.
4. Sponsored treatment must remain **separate** from organic ranking / objective score.
5. Lack of affiliate permission must **not** suppress an otherwise legally usable organic offer when product-data comparison is authorized.
6. **Affiliate permission ≠ product-data permission.** A relationship may authorize monetized redirects without authorizing ingestion, display, caching, comparison, scoring inputs, or AI reuse of merchant content — and the reverse may also be true.

Engineering intends unknown contractual permissions to remain **fail-closed** in production. Whether a specific provider program allows a given use is a **counsel / provider** question (Sections E–F), not answered here.

---

## C. Target markets

Roadmap intended certification markets:

| Market | Roadmap EXT | Certification sprint |
|--------|-------------|----------------------|
| Philippines | EXT-01 | Sprint 32 |
| United States | EXT-02 | Sprint 33 |
| Singapore | EXT-03 | Sprint 34 |
| United Kingdom | EXT-04 | Sprint 35 |
| Canada | EXT-05 | Sprint 36 |

**Clarifications (repository authority):**

- These are **intended certification markets**, not currently legally approved or production-supported shopping markets.
- No market may be publicly named as **supported** until its certification gate is satisfied (merchant/affiliate EXT approved or provisioned **and** certification sprint exit criteria, including capability-policy evidence).
- Global site reachability (later production DNS/TLS) is distinct from naming supported shopping markets.
- EXT-01…EXT-05 remain `not_started` in the authoritative register at draft time.

---

## D. Merchant / provider shortlist

### Owner-review research shortlist (non-authoritative)

The following names are listed for **owner research / counsel discussion only**:

- Shopee
- Lazada
- TikTok Shop
- Amazon
- Temu

### Explicit non-selection statement

| Statement | Status |
|-----------|--------|
| This is a **research shortlist only** | Yes |
| Any provider is selected in `EXTERNAL_DEPENDENCY_REGISTER.md` | **No** |
| Any agreement, partnership, or approval exists because of this list | **No** — do not infer |
| Fixture / stub / placeholder marketplace names in engineering docs equal partner selection | **No** |
| EXT-01…EXT-05 advanced by this document | **No** — remain `not_started` until real application evidence |

Do **not** update the register to name a partner until the owner decides and real submission evidence exists.

---

## E. Merchant capability questions

Organize counsel review using the roadmap **merchant contractual capability / policy** model (Sprint 31 principles; implementation not started). For each applicable provider/program under consideration, ask whether PiqSavi may lawfully / contractually:

| # | Capability question |
|---|---------------------|
| 1 | Retrieve / search product data |
| 2 | Display price |
| 3 | Display availability |
| 4 | Display images |
| 5 | Display ratings |
| 6 | Display review counts |
| 7 | Reproduce individual reviews |
| 8 | Summarize reviews using AI |
| 9 | Cache offers |
| 10 | Cache product metadata |
| 11 | Retain price history |
| 12 | Normalize specifications |
| 13 | Standardize units |
| 14 | Transform factual product information |
| 15 | Generate comparison tables |
| 16 | Compare against competing marketplaces |
| 17 | Use facts as PiqScore / DealScore inputs |
| 18 | Retain independently derived PiqScore / DealScore |
| 19 | Use merchant facts in AI explanations |
| 20 | Create affiliate links |
| 21 | Use internal redirect / attribution tracking |
| 22 | Identify merchant / source in the UI |
| 23 | Operate in each target market (PH / US / SG / UK / CA as applicable) |
| 24 | Retain independently derived data after merchant content deletion |
| 25 | Satisfy termination / deletion obligations |

### Requested counsel classification per capability

Ask counsel (and, where needed, the provider) to distinguish:

| Classification | Production posture (engineering intent) |
|----------------|-----------------------------------------|
| **ALLOWED** | May be enabled only with evidence-backed declaration |
| **RESTRICTED** | May be enabled only within documented limits |
| **PROHIBITED** | Must not be enabled |
| **UNKNOWN / NEED PROVIDER CLARIFICATION** | Must remain **fail-closed** in production |

**Rules counsel should treat as product constraints (not legal conclusions):**

- Provider account/API approval alone must not be treated as blanket capability approval.
- Technical ability to call an API ≠ contractual permission.
- Upstream payload presence (reviews, images, ratings, etc.) ≠ permission to display or reuse.
- Affiliate-only permission without product-data comparison rights must not be treated as satisfying EC-09 current-data market naming.

---

## F. Focused provider questions

The following are **questions for counsel** (and later provider clarification).  
**Do not treat any answer below as present — none are answered here as legal conclusions.**

### Shopee

1. Does affiliate participation authorize product-data use, or is a separate API / feed / data right needed?
2. Any restriction on cross-marketplace comparison?
3. Any restriction on independent scoring / PiqScore?
4. Any restriction on AI explanation from authorized product facts?
5. Any restriction on internal redirect attribution?

### Lazada

1. Do restrictions on modification of advertising materials apply to normalized factual data from an authorized API / feed?
2. Can PiqSavi create comparison tables from factual merchant data?
3. Can independently generated PiqScore remain after underlying content deletion?
4. What termination / deletion obligations apply?

### TikTok Shop

1. Which program is appropriate for an external AI shopping comparison website: external traffic affiliate, partner API, another program, or combination?
2. Does affiliate access include product-data rights?
3. Are external comparisons / rankings permitted?
4. What attribution / deeplink requirements apply?

### Amazon

1. Can authorized Program / API content appear beside competing marketplace offers?
2. Can factual data be used as PiqScore inputs?
3. What content can be transformed?
4. What restrictions apply to pricing, images, ratings, reviews, caching, TTL?
5. Can AI explanations use authorized factual inputs?
6. What redirect / source-identification requirements apply?
7. Can internally derived comparison conclusions be retained?

### Temu

1. Does the affiliate program itself grant product-data rights?
2. Is a separate API / feed / data license required?
3. Are cross-marketplace comparison and independent ranking permitted?
4. Are caching, AI use, or content-transformation rights specified?
5. What requires direct provider clarification?

**Note:** Provider names above mirror the owner-review research shortlist only. No program terms are invented or summarized as binding here.

---

## G. Consumer legal scope

Sprint 28 / launch topics counsel should review (scope list — **not** final clause drafts):

| Topic | Notes for counsel |
|-------|-------------------|
| Terms of Service | Consumer product naming: PiqSavi |
| Privacy Policy / Notice | Consumer product naming: PiqSavi; privacy contact path exists operationally (`privacy@piqsavi.com`) — not a DPO appointment claim |
| Affiliate disclosure | Placeholder disclosure exists in product; not legal-final |
| Advertising / sponsored disclosure | Sponsored must stay separate from organic rank |
| AI / recommendation disclosure | AI Personal Shopper explanation + recommendation vs objective score |
| PiqScore description / claims | Public PiqScore; avoid overclaiming “unbiased” without qualifier |
| Cookie / tracking consent | EXT-22 `not_started` |
| Analytics consent | EXT-15 `not_started` |
| Policy version acceptance | Registration consent / version records (Sprint 28) |
| Account deletion | Sprint 28 requirement; not claimed complete |
| Data export | Sprint 28 requirement; not claimed complete |
| Retention | Sprint 28 / PII inventory |
| Support contact | `support@piqsavi.com` (EXT-17 `provisioned`); public UI publication later |
| Privacy contact | `privacy@piqsavi.com` (EXT-18 `provisioned`); public policy publication later |
| Country-specific notices | Target markets PH / US / SG / UK / CA |
| Market availability claims | Only name certified markets; distinguish global reach vs supported markets |
| Governing law / jurisdiction approach | Owner + counsel decision |
| Limitation of liability | Counsel draft |
| Disclaimers | Counsel draft |
| Merchant / product accuracy disclaimers | Prices/availability may change; not guaranteed lowest price |

**Internal placeholders only:** This package does **not** draft final legal clauses. Any future placeholder copy must remain labeled non-final and unapproved.

---

## H. Data / privacy questions

Ask counsel to review the following categories (inventory questions — **not** compliance claims):

| Category | Question for counsel |
|----------|----------------------|
| Account / profile PII | What notices, bases, and safeguards are required for public beta? |
| Search / query history | Retention, access, and deletion expectations? |
| Personalization data | Limits for Personalized PiqScore / preferences? |
| Watchlists | Treatment as user content / account data? |
| Price-history data | Interaction with merchant caching / retention rules? |
| Analytics events | Consent gating vs essential operations? |
| Cookies / tracking | Essential-only vs non-essential; consent UX? |
| Merchant click attribution | First-party vs partner tracking; disclosure? |
| Affiliate tracking | Disclosure and partner requirements? |
| AI prompt / context usage | Merchant facts and user context in prompts; logging? |
| Retention periods | Minimum / maximum for account, logs, derived scores? |
| Deletion / export obligations | Scope, timing, subprocessors? |
| Service-provider / DPA requirements | Email (Resend), hosting, AI, analytics vendors? |
| Cross-border considerations | PH / US / SG / UK / CA user and vendor paths? |

**Explicit non-claims:** This document does **not** claim GDPR, Philippine Data Privacy Act, CCPA/CPRA, or any other privacy-regime compliance.

---

## I. EXT-19 engagement scope

### Proposed engagement scope (for later counsel briefing)

1. PiqSavi Terms of Service  
2. Privacy Policy / Notice  
3. Affiliate / advertising disclosures  
4. AI / recommendation / PiqScore disclosures  
5. Cookie / analytics consent  
6. Account deletion / export / retention  
7. Merchant / affiliate terms review (aligned with Sections E–F and EXT-01…05)  
8. Target-market legal issue spotting (PH / US / SG / UK / CA)  
9. Final launch claims review  
10. Written launch approval **or** clearly identified unresolved issues  

### Sprint 26 status rule (register authority)

| Status | What repository requires |
|--------|---------------------------|
| Current | EXT-19 = `not_started` |
| Next (`applied`) | Real counsel engagement / scheduling evidence: counsel identity or firm; engagement or confirmed consultation; date; scope summary |
| Later (`approved`) | **Written approval** evidence — engagement alone is insufficient |

Creating or retaining this intake package **does not** advance EXT-19.

---

## J. EXT-01…05 application prep

Reusable application-field template. Populate only non-sensitive, known values when preparing a future packet. Leave blanks for owner / provider / counsel.

| Field | Classification | Prep notes |
|-------|----------------|------------|
| market | **KNOWN** (template per PH/US/SG/UK/CA) | One packet per market EXT |
| candidate provider | **OWNER DECISION REQUIRED** | Research shortlist only until selected |
| program / API name | **PROVIDER-SPECIFIC** | Not selected in register |
| application type | **PROVIDER-SPECIFIC** | Affiliate / API / feed / combo — counsel + owner |
| applicant / legal business name | **OWNER DECISION REQUIRED** | Do not invent |
| public brand | **KNOWN** | PiqSavi |
| domain | **KNOWN** | piqsavi.com |
| product description | **KNOWN** draftable + **LEGAL REVIEW REQUIRED** | AI Personal Shopper; compare / score / recommend / explain / redirect |
| intended use | **KNOWN** draftable + **LEGAL REVIEW REQUIRED** | See Section A flow |
| merchant-data use | **LEGAL REVIEW REQUIRED** | Section E items 1–14 |
| comparison / scoring use | **LEGAL REVIEW REQUIRED** | Section E items 15–18 |
| AI explanation use | **LEGAL REVIEW REQUIRED** | Section E items 8, 19 |
| affiliate model | **LEGAL REVIEW REQUIRED** + **PROVIDER-SPECIFIC** | Post-rank attachment; neutrality rules |
| redirect / tracking model | **LEGAL REVIEW REQUIRED** + **PROVIDER-SPECIFIC** | EXT-07 tracking IDs not yet available |
| target market | **KNOWN** | PH / US / SG / UK / CA as applicable |
| public URLs required | **PROVIDER-SPECIFIC** + **NOT YET AVAILABLE** where live app/policies pending | Staging vs production TBD |
| screenshots required | **PROVIDER-SPECIFIC** + **NOT YET AVAILABLE** for final consumer UI | Sprint 29 UI not complete |
| Terms URL required | **NOT YET AVAILABLE** | EXT-21 `not_started` |
| Privacy URL required | **NOT YET AVAILABLE** | EXT-20 `not_started` |
| legal / business documents required | **OWNER DECISION REQUIRED** + **PROVIDER-SPECIFIC** + **LEGAL REVIEW REQUIRED** | No secrets in git |
| technical contact | **OWNER DECISION REQUIRED** | Placeholder only in prep |
| business contact | **OWNER DECISION REQUIRED** | Placeholder only in prep |
| tax / bank / payment fields | **OWNER DECISION REQUIRED** / **NOT YET AVAILABLE** in git | **Do not store** in repository |
| governing program terms / version | **PROVIDER-SPECIFIC** + **NOT YET AVAILABLE** until apply | Retain version ID after submit |
| counsel review status | **LEGAL REVIEW REQUIRED** | Pending until real review |
| application submission status | **NOT YET AVAILABLE** | Must remain unsubmitted until authorized |
| evidence artifact path | **NOT YET AVAILABLE** | Create only after real evidence |
| confirmation / reference ID | **NOT YET AVAILABLE** | Inventing IDs forbidden |
| application date | **NOT YET AVAILABLE** | Real date only; never fabricated |

### Classification legend

| Class | Meaning |
|-------|---------|
| **KNOWN** | Supported by current repository / brand lock |
| **OWNER DECISION REQUIRED** | Founder / business decision pending |
| **PROVIDER-SPECIFIC** | Depends on chosen program/portal |
| **LEGAL REVIEW REQUIRED** | Counsel (and often provider terms) must review before submit/enable |
| **NOT YET AVAILABLE** | Cannot truthfully populate yet |

Sensitive personal, banking, and tax identifiers must **not** be written into this repository.

---

## K. Evidence requirements

### EXT-19 → `applied` (sanitized, non-privileged)

Retain only:

- Counsel identity or firm name (as appropriate for ops evidence)
- Engagement / confirmed consultation evidence
- Date
- Scope summary (may reference this package’s Section I)

**Do not store in Git:**

- Privileged legal advice or counsel opinions
- Personal mobile numbers
- Private personal emails if unnecessary
- Payment information
- Billing records
- Home addresses
- Matter IDs
- Credentials / secrets

### EXT-01…EXT-05 → `applied` (sanitized)

Retain only non-secret:

- Provider / partner name (after real selection + submit)
- Market
- Real submission date
- Portal / email / ticket / application confirmation
- Confirmation / reference ID where available
- Terms / program version identifier
- Counsel review evidence or reference as appropriate (non-privileged)

**No secrets in Git** (API keys, passwords, full unredacted portal dumps, payment instruments).

### Explicit non-advancement

Retaining this draft, or planning evidence paths, does **not** change any EXT status and does **not** constitute submission or engagement.

---

## L. Stop conditions

This draft does **NOT** authorize:

- Merchant / affiliate application submission  
- Provider selection in the authoritative register  
- Any EXT status change (including EXT-01…05 and EXT-19)  
- Legal approval or compliance claims  
- Production capability enablement for unknown permissions  
- Sprint 26 closure  
- Sprint 27 start  
- Sprint 31 implementation  
- Contacting counsel or providers from this document alone  
- Inventing provider terms, application dates, or confirmation IDs  

**Sprint 26 remains OPEN** until real remaining bootstrap evidence exists and a final go/no-go close is recorded.

**End of internal counsel intake package draft.**
