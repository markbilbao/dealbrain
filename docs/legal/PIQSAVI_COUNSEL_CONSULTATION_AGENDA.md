# PiqSavi Counsel Consultation Agenda

**Purpose:** Decision-focused guide for legal consultation
**Counsel:** Pauline Anne Sambuang (“Atty. Pau”)
**Consultation:** August 19, 2026 — 10:00 AM Philippines local time
**Status:** INTERNAL — FOUNDER / COUNSEL MEETING AID
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**

**Repository baseline:** `de207535dc556e6a355f2895adc5b58e9c500747`

This file is a meeting aid only. It does not answer legal questions, approve policies, publish documents, change Sprint/EXT status, or replace any counsel draft.

---

## 1. What PiqSavi Is

PiqSavi is an AI-assisted shopping/recommendation product (internal codename: DealBrain; public tagline: **Your AI Personal Shopper**). It evaluates available offers and presents **PiqScore**, **Recommendation**, and **AI explanation** layers. Purchases are generally expected to occur with third-party merchants. Affiliate monetization may be used where approved.

Current merchant integrations are **not** production-certified. Current legal documents are **founder/product drafts awaiting counsel review**.

| Layer | Product boundary (do not collapse) |
|-------|-------------------------------------|
| **PiqScore** | Objective evaluation of offers actually evaluated |
| **Recommendation** | Separate action-oriented recommendation layer |
| **Personalization** | May affect personally recommended Piq without rewriting canonical PiqScore |
| **AI** | Explanation/reasoning layer; does not rewrite canonical PiqScore |
| **Affiliate compensation** | Must not increase PiqScore or organic Recommendation ranking |

---

## 2. Decisions We Need From Counsel

Objective of this consultation: obtain **direction** sufficient to:

- determine legal operating structure and required disclosures;
- choose first public-beta jurisdictions;
- proceed safely with merchant/affiliate applications;
- finalize Terms / Privacy / supporting notices;
- identify mandatory launch controls; and
- unblock publication, assent, and account/privacy engineering decisions.

Counsel is **not** expected to complete all drafting in this meeting.

---

## 3. Primary Decision Table

| Priority | Decision Needed | Why It Matters | Primary Source | Engineering / Launch Unlock | Counsel Notes |
|----------|-----------------|----------------|----------------|-----------------------------|---------------|
| P0 | Legal operator / entity structure | Defines who contracts with users and providers | Terms header; Privacy header; Fact Spec | Operator wording across all public docs; contract party for merchant apps | |
| P0 | Public legal name and required business/address disclosure | Public notice / imprint obligations | Terms header; Privacy header | Legal notice / imprint fields; what may be published | |
| P0 | First public-beta jurisdictions | Sets which consumer/privacy/ad rules apply | Terms / Privacy jurisdiction placeholders; roadmap markets PH/US/SG/UK/CA | Supported-market claims; country-specific controls | |
| P0 | PiqSavi’s legal role relative to merchants | Intermediary vs seller-of-record wording drives consumer law | Terms merchant sections; Marketplace Disclaimer §§ on role | Consumer-facing role copy; liability framing | |
| P0 | Merchant / affiliate capability permissions | Blocks safe EXT-01…05 applications | Merchant Counsel Decision Worksheet (capability matrices) | Fail-closed capability model; what may be applied for | |
| P0 | Affiliate permission vs product-data permission | Need counsel direction on whether affiliate rights and product-data rights differ | Affiliate Disclosure §2; Merchant Worksheet; EXT register boundary | Keep product-data features fail-closed until rights are clear | |
| P0 | Terms acceptance / clickwrap / policy-version evidence | Assent mechanism not finalized; no version fields today | Terms §1 Acceptance | Registration assent UX + policy-version logging (Sprint 28) | |
| P0 | Minimum age / minors controls | No coded age gate / DOB today | Terms §3 Eligibility; Privacy children section | Age gate / eligibility controls | |
| P1 | Privacy legal bases by market | Needed before Privacy can be finalized/published | Privacy legal-basis placeholders | Consent vs other bases wiring; notices | |
| P0 | Data-subject deletion/export minimum launch requirement | Self-serve deletion/export not implemented; privacy@ exists | Deletion/Export/Retention Policy; Fact Spec §§ deletion/export | Manual vs self-serve launch bar; Sprint 28 scope | |
| P0 | Legal retention periods by data category | Technical TTLs ≠ approved legal retention | Deletion/Export/Retention INTERNAL schedule | Retention purge rules | |
| P1 | Identity verification / authorized-agent approach for privacy requests | Manual DSR path only today | Deletion/Export/Retention DSR sections | DSR workflow / verification steps | |
| P0 | Cookie/CMP requirement for current no-app-cookie posture | App: no cookies / localStorage analytics / pixels found | Cookie Notice; Fact Spec cookie findings | EXT-22 CMP yes/no for current stack | |
| P1 | Production CDN/infrastructure cookie considerations | App inventory ≠ edge/CDN cookies | Cookie Notice infra/CDN notes | Production cookie inventory / notice updates | |
| P0 | AI provider retention/training/transfer requirements before live AI | Live AI HTTP disabled by default | AI Disclosure provider section; Fact Spec AI | Gate before enabling live AI HTTP | |
| P1 | ADM/profiling characterization / opt-out or contest requirements | Recommendation/personalization may trigger extra rights | AI Disclosure ADM/profiling section | Opt-out / contest / human-review UX if required | |
| P0 / P2 | Affiliate disclosure wording / prominence if monetization ships | P0 if any monetized path at launch; else can follow | Affiliate Disclosure placement sections | Disclosure placement/labels; sponsored treatment | |
| P0 | Mock/imported/catalog limitation wording | Catalog is fixture/mock/imported/simulated today | Terms catalog note; Marketplace Disclaimer; AI Disclosure | Consumer wording before public beta | |
| P1 | Price / availability / shipping / returns / warranty limitation wording | Current product does not operate merchant checkout, returns, or warranties | Marketplace Disclaimer related sections; Terms purchases | Results/checkout disclaimer copy | |
| P1 | Consumer marketplace disclaimer placement | Prominence/enforceability open | Marketplace Disclaimer placement placeholder | Where disclaimer appears in UI/site | |
| P0 | Governing law / dispute resolution / venue/arbitration | Terms placeholders unresolved | Terms disputes / governing-law sections | Final Terms dispute block | |
| P0 | Warranty disclaimer / liability limitations | Core risk allocation for launch Terms | Terms warranty/liability sections | Publishable Terms liability framework | |
| P0 | Mandatory consumer-rights carve-outs | Market-specific non-waivable rights | Marketplace Disclaimer consumer-rights savings; Terms | Market carve-out language | |
| P1 | Publication structure for Terms / Privacy / disclosures | EXT-20/21 packaging unknown | All public-facing drafts; audit publication architecture | Which pages/URLs ship; EXT-20/21 | |
| P1 | Whether deletion/export/retention is public page, Privacy section, help-center, or combination | Avoid wrong public surface | Deletion/Export/Retention; Privacy rights | Public vs help-center vs internal schedule | |
| P1 | Whether any legal notice / imprint page is required | Depends on operator/address decision | Terms/Privacy operator headers | Separate imprint page vs footer fields | |

**Priority key:** P0 = MUST RESOLVE BEFORE PUBLIC BETA · P1 = IMPORTANT BEFORE PUBLIC BETA · P2 = CAN FOLLOW / FEATURE-DEPENDENT

All rows remain **unresolved** until counsel provides direction.

---

## 4. Merchant / Affiliate Decisions

Research shortlist only (no provider selected; no EXT-01…05 application submitted; no provider approval claimed):

- Shopee
- Lazada
- TikTok Shop
- Amazon
- Temu

**Preserve:**

- technical capability ≠ contractual permission
- affiliate permission ≠ product-data permission
- provider approval ≠ blanket capability permission
- unknown capability = fail closed

Ask counsel how the founder should interpret or obtain clarity on rights such as: search/access; display; comparison; caching/storage; price/product data use; AI-assisted processing; affiliate linking; review/rating reuse; market/geographic scope.

**Primary working source (do not reproduce here):**
`docs/roadmap/evidence/SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md`

---

## 5. Legal Draft Review Index

| Document | Primary Question for Counsel | Priority |
|----------|------------------------------|----------|
| Product/Data Behavior Spec (`PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md`) | Are the factual classifications and provider/data-processing assumptions sufficient for legal analysis? | P0 |
| Privacy Policy (`PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md`) | Please resolve entity, legal bases, transfers, rights-by-market, retention, age, and third-party disclosure placeholders. | P0 |
| Terms of Service (`PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md`) | Please resolve entity, assent, age, merchant role, governing law, liability, and dispute placeholders. | P0 |
| Affiliate & Advertising Disclosure (`PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md`) | What wording/placement is required if affiliate monetization ships, and what can wait until a live program exists? | P0 / P2 |
| AI & Recommendation Disclosure (`PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_COUNSEL_DRAFT.md`) | How should AI/provider, ADM/profiling, and PiqScore/Recommendation limitation wording be finalized? | P0 / P1 |
| Cookie & Tracking Notice (`PIQSAVI_COOKIE_TRACKING_NOTICE_COUNSEL_DRAFT.md`) | Is a cookie banner/CMP required given the current empty app cookie/pixel stack, and what about CDN/infra cookies? | P0 / P1 |
| Account Deletion / Data Export / Retention (`PIQSAVI_ACCOUNT_DELETION_DATA_EXPORT_RETENTION_POLICY_COUNSEL_DRAFT.md`) | What is the launch-minimum deletion/export workflow, and what legal retention periods apply by data category? | P0 |
| Consumer & Marketplace Disclaimer (`PIQSAVI_CONSUMER_MARKETPLACE_DISCLAIMER_COUNSEL_DRAFT.md`) | What intermediary role, catalog/price/returns/warranty limitations, placement, and consumer-rights carve-outs are required? | P0 / P1 |

---

## 6. Engineering / Product Decisions Waiting on Counsel

Evidence-backed blockers only. Do not start implementation from this agenda.

| Decision | Current State | Counsel Input Needed | What We Can Do After Answer |
|----------|---------------|----------------------|-----------------------------|
| Consent / CMP behavior | No app cookies/pixels/CMP found; EXT-22 `not_started` | Required now vs later | Scope EXT-22 / banner or defer |
| Registration assent / policy-version logging | No consumer ToS/privacy version fields; Sprint 28 planned | Required assent mechanism + evidence | Design register assent + version logging |
| Deletion UX | Account deletion not implemented; privacy@ provisioned | Manual vs self-serve launch minimum | Scope Sprint 28 deletion work |
| Export UX | Automated export/DSAR download not implemented | Launch-minimum export path/format | Scope export UX / process |
| Retention purge rules | Technical TTLs exist; no approved legal retention | Legal periods + exceptions | Implement purge/retention jobs to counsel schedule |
| Minor / age controls | No coded age policy / DOB / parental consent | Minimum age + controls by market | Add eligibility/age-gate controls |
| Affiliate disclosure placement | Draft only; live affiliate programs not started | Wording/prominence if monetization ships | Place labels/disclosure in UI |
| Marketplace disclaimer placement | Draft only; placement open | Required surfaces/prominence | Place disclaimer in site/results |
| Sponsored-result treatment | Framework/draft only; not live consumer sponsored surface | Labeling if/when introduced | Fail-closed labeling rules |
| Supported-market claims | EXT-01…05 `not_started`; no production-certified markets | Which markets may be named at first beta | Restrict market claims accordingly |
| Legal operator / imprint fields | Operator/address placeholders open | What must appear publicly | Footer/imprint/legal-notice fields |
| DSR workflow | Manual privacy@ path only | Verification, agents, timelines | Operationalize DSR SOP |
| Live AI HTTP enablement | Disabled by default (`DisabledTransport`) | Provider retention/training/transfer gates | Enable live AI only if/when cleared |
| Analytics / pixel enablement | No GA/GTM/Meta/TikTok pixels found; EXT-15 not activated here | Consent gate before enablement | Keep pixels off until cleared |

---

## 7. Can Follow After Initial Consultation

Not ignored — intentionally deferred until foundational answers exist (per legal-package audit):

- formal DSR SOP
- formal privacy/security incident-response procedure
- jurisdiction legal matrix
- standalone provider/subprocessor register
- provider-specific affiliate disclosure pages
- product takedown/recall workflows
- standalone minors policy
- accessibility statement
- DMCA/IP procedure
- consent-management policy documentation

---

## 8. Suggested Meeting Flow

Suggested agenda only; counsel need not follow it.

| Time | Focus |
|------|--------|
| 0–10 min | PiqSavi product / business model confirmation |
| 10–25 min | Legal operator + launch jurisdictions |
| 25–50 min | Merchant / affiliate contractual capability |
| 50–75 min | Terms + merchant/intermediary role + consumer framework |
| 75–100 min | Privacy + deletion/export/retention + cookies/consent |
| 100–115 min | AI / recommendation + affiliate disclosure + marketplace limitations |
| 115–120 min | Prioritize written follow-ups / confirm next actions |

---

## 9. Founder Questions

Ask verbally; leave answers to counsel.

1. Can I launch initially as an individual / sole proprietor, and what must be disclosed publicly?
2. If I later move PiqSavi into a corporation, what should I plan now to make contract/policy migration easier?
3. Which countries should I legally include in the first public beta?
4. Legally, how should PiqSavi describe its role relative to merchants?
5. What merchant/API/affiliate permissions do I need before PiqSavi can legally search, compare, display, cache, or use product data?
6. Is affiliate approval alone enough to use merchant product data?
7. What legal acceptance mechanism do we need at account registration?
8. What minimum age should we use?
9. Is manual deletion/export through privacy@ enough for beta, or must we build self-service before launch?
10. What retention periods should we use?
11. Do we need a cookie banner/CMP if the app itself currently has no cookies, localStorage analytics, or tracking pixels?
12. What must we confirm before enabling live AI providers?
13. What affiliate disclosure wording/placement is required?
14. What should we say about prices, availability, returns, warranties, and marketplace completeness?
15. Which documents can we publish after your review, and what must change first?

---

## 10. Desired Outputs From Counsel

Outcome checklist — **not** evidence that these decisions have already been made:

- [ ] Legal operator/entity wording confirmed
- [ ] First-beta markets confirmed
- [ ] Merchant/intermediary role wording confirmed
- [ ] Merchant capability interpretation / next questions confirmed
- [ ] Terms major placeholders resolved
- [ ] Privacy major placeholders resolved
- [ ] Age/minors direction confirmed
- [ ] Deletion/export launch minimum confirmed
- [ ] Retention framework confirmed
- [ ] Cookie/CMP decision confirmed
- [ ] AI provider legal gate confirmed
- [ ] Affiliate disclosure placement confirmed
- [ ] Marketplace disclaimer requirements confirmed
- [ ] Liability/dispute framework confirmed
- [ ] Publication / assent requirements confirmed
- [ ] Written follow-up items identified

---

## 11. After the Consultation

Do **not** change repository legal/EXT status based solely on memory or verbal interpretation if the project requires written evidence.

Preserve:

| Do not collapse | Meaning |
|-----------------|---------|
| consultation held ≠ written approval | Meeting alone does not close EXT-19 |
| legal guidance received ≠ document approved | Drafts remain drafts until written approval |
| merchant application allowed ≠ submitted | Permission to apply ≠ EXT applied |
| submitted ≠ provider approved | Application ≠ approval |
| provider approved ≠ contractual capability certified | Approval ≠ blanket capability |
| policy revised ≠ policy legally approved | Edits ≠ counsel approval |
| policy approved ≠ policy published | EXT-20/21 still require publication evidence |
| publication ≠ product capability implementation | Live URL ≠ feature built |

For any written legal approval or provider decision:

- preserve sanitized evidence;
- do **not** commit privileged advice;
- do **not** commit confidential counsel communications;
- do **not** commit private addresses;
- do **not** commit billing/payment details;
- do **not** commit credentials or tokens.

---

## Current Project State — Pre-Consultation

Sprint 26:
OPEN

Sprint 27:
NOT STARTED

Sprint 28:
NOT STARTED

EXT-01…05:
`not_started`

EXT-19:
`applied` *(engagement accepted / consultation scheduled; not legal review complete; not legal approval; not launch legal approval; not Terms/Privacy/merchant-terms approval; does not close Sprint 26)*

EXT-20/21/22:
`not_started`

Legal approval:
NOT CLAIMED

Policies published:
NO

Merchant/provider approval:
NOT CLAIMED

This agenda itself must not change any status.
