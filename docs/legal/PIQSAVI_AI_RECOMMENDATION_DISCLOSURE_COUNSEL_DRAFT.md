# PiqSavi AI & Recommendation Disclosure

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**
**Not evidence that all AI/provider features are live**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary sources:
  - docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md
Supporting product/architecture docs inspected as needed:
  - docs/architecture/ARCHITECTURE_LOCK.md
  - docs/PERSONAL_DEALSCORE.md
  - docs/AI_PROVIDER_SETUP.md
  - docs/AI_SHOPPING_ASSISTANT_V1.md
  - docs/SHOPPING_ASSISTANT_SAFETY.md
  - docs/BUYING_ADVISOR.md
  - docs/PERSONAL_AGENT.md
  - docs/MARKETPLACE_DATA.md
  - docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md
Authoritative main at drafting: 7b1df9962a44937a998b20093fe89135a01d706a
Fact-spec audit HEAD noted in fact-spec: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
Internal technical codename: DealBrain (do not use in public-facing disclosure body)
Internal scoring names: DealScore / PersonalDealScore (public name remains PiqScore)
This draft does not claim EXT-19 written approval, EXT-20/21 publication, Sprint 28 start,
automated-decision compliance, production merchant/data-provider approval, live AI-provider
traffic, or legal sufficiency.
-->

---

**Effective Date:**
[COUNSEL TO CONFIRM]

**Last Updated:**
[COUNSEL TO CONFIRM]

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**General support:** support@piqsavi.com
**Privacy / data contact:** privacy@piqsavi.com

---

## 1. Purpose of This Disclosure

This AI & Recommendation Disclosure is intended to explain, in plain language:

- what **PiqScore** means;
- how **Recommendations** differ from PiqScore;
- how **personalization** may affect recommendations;
- how **AI** may assist with explanations; and
- important **limitations** users should understand before relying on scores, recommendations, or AI-assisted narratives.

PiqSavi (“PiqSavi,” “we,” “us,” or “our”) is marketed as **Your AI Personal Shopper**. This disclosure focuses on scoring, recommendation, personalization, and AI transparency. It does **not** replace the Terms of Service, Privacy Policy, or Affiliate & Advertising Disclosure.

This document is a **counsel draft**. It is not published, not final, and not legal advice. It does **not** claim that PiqSavi complies with any particular AI, automated-decision, profiling, consumer-protection, advertising, or privacy law. It is **not** evidence of:

- legal approval;
- that every AI or provider feature is live in production;
- automated-decision-making compliance;
- production merchant or data-provider approval; or
- that every explanation is complete or human-reviewed.

---

## 2. Important Product Distinctions

Preserve these distinctions when reading or finalizing this disclosure:

| Concept | Meaning (product architecture) |
|---------|--------------------------------|
| **PiqScore** | Objective offer evaluation based on available offer attributes that PiqSavi actually evaluated. Internal technical name: DealScore. |
| **Recommendation** | Separate customer-action layer (for example Buy / Wait / Consider / Avoid style guidance). Not the same thing as PiqScore. |
| **Personalization** | May influence the personally recommended Piq / personalized PiqScore-style result **without rewriting** canonical objective PiqScore / DealScore. |
| **AI** | Explanation / reasoning / narrative assistance where that path is enabled. AI must **not** rewrite canonical objective scoring. |
| **Affiliate compensation** | Must **not** increase PiqScore, canonical DealScore, or organic Recommendation ranking. |

Do **not** collapse these concepts. A high PiqScore, a personal recommendation, an AI explanation, and an affiliate-linked destination are related product surfaces with different rules.

---

## 3. What PiqScore Is

**PiqScore** is PiqSavi’s public name for an **objective offer-evaluation score**.

Based on the product architecture reviewed for this draft:

- PiqScore evaluates offers using information available to PiqSavi for that evaluation;
- it is scoped to offers PiqSavi actually evaluated;
- it does **not** imply complete coverage of the market;
- unavailable, unknown, incomplete, fixture, imported, simulated, or stale inputs may affect evaluation quality;
- the canonical objective score is designed to remain deterministic according to implemented scoring rules; and
- AI and affiliate economics are **not** designed to rewrite canonical PiqScore.

Depending on available evidence, inputs may include cost-related signals, seller rating, shipping, availability, official-store indicators, warranty-related attributes, returns-related attributes, and similar offer factors where present.

### What PiqScore does **not** mean

This draft does **not** claim that a PiqScore result means:

- universal market completeness;
- a guaranteed best deal;
- a lowest-price guarantee;
- guaranteed savings;
- perfect product quality;
- guaranteed merchant reliability; or
- a guaranteed future purchasing outcome.

This section does **not** disclose proprietary scoring formulas, weights, or implementation details.

[COUNSEL TO CONFIRM: final consumer-facing PiqScore limitation wording]

---

## 4. What Recommendation Is

**Recommendation** is separate from objective PiqScore.

Recommendation is the **action-oriented** layer that helps a user decide what they may want to do—for example Buy, Wait, Consider, or Avoid style guidance—together with related explanations, tradeoffs, warnings, confidence indicators, or alternatives where implemented.

### Highest PiqScore vs personally recommended Piq

The listing with the **highest objective PiqScore** may **not** always equal the **personally recommended Piq**, where relevant personalization, thresholds, tradeoffs, warnings, confidence, or related recommendation logic legitimately change the recommendation.

Recommendations are intended to **assist**—not replace—your own purchasing judgment. This draft does **not** imply that a Recommendation is guaranteed to be correct, suitable, or outcome-optimal for every user or purchase.

[COUNSEL TO CONFIRM: appropriate reliance/disclaimer wording]

---

## 5. Personalization

Based on the product architecture reviewed for this draft, personalization may use user preferences or context **where implemented**.

Examples of preference/context signals that may exist for authenticated accounts include budget, currency, country preference, category/goal preferences, favorite brands/marketplaces, and related account settings. Anonymous callers may use the service without a persisted guest preference profile.

### Personalization rule (preserve exactly)

Personalization may influence the **personally recommended Piq** / personalized PiqScore-style result.

Personalization does **not** rewrite **canonical PiqScore / DealScore**.

### Current-state caution

Based on the current implementation reviewed for this draft:

- account preferences can be stored and applied where those features are used;
- some personal-agent / buying-advisor profile paths remain **fixture/mock-oriented**;
- past-search / click / purchase behavioral learning is **not** described here as a fully implemented production learning system; and
- this draft does **not** claim sensitive profiling categories unless actually implemented.

Do **not** assume that every personalization surface described in roadmap materials is live production personalization.

[COUNSEL TO CONFIRM: profiling/personalization disclosure requirements by market]

---

## 6. How AI Is Used

Based on repository-backed product architecture reviewed for this draft, AI may be used for:

- explanation;
- narrative;
- summarization;
- reasoning assistance; and
- conversational presentation,

where those roles are implemented and the relevant path is enabled.

### Clear AI boundary

**AI does NOT determine or rewrite canonical PiqScore.**

AI is designed to sit **downstream** of deterministic product identity, objective scoring, and (where applicable) recommendation outputs. AI must **not** be described as autonomously controlling objective scoring.

### Current production-use posture

Repository evidence indicates that AI provider **adapters exist**, while **live external HTTP may be disabled by default**. When AI paths are unavailable, deterministic fallbacks may be used.

Public brand positioning as **Your AI Personal Shopper** is a brand/product positioning fact. It is **not**, by itself, evidence that live third-party AI providers are currently handling production traffic.

Do **not** overstate current production AI use beyond repository evidence.

---

## 7. AI Providers

Provider adapters may include technologies for providers such as OpenAI, Anthropic, or Google/Gemini, together with deterministic fallback paths.

Distinguish carefully:

| Concept | Meaning |
|---------|---------|
| **Adapter / support availability** | Code paths exist that can talk to a provider when configured and enabled. |
| **Live production use** | Actual production traffic being handled by that provider under enabled transport and approved configuration. |

This draft does **not** assert that any specific provider is currently handling production traffic unless current repository/config evidence proves it. At the current reviewed state, live external AI HTTP is **disabled by default**.

This draft does **not** invent provider retention, training, subprocessors, or international-transfer policies.

[COUNSEL / PROVIDER REVIEW REQUIRED: final production AI provider disclosures, terms, retention, training, international transfer and processor/controller treatment]

---

## 8. AI Limitations

AI-generated explanations may:

- be incomplete;
- contain errors;
- misunderstand context;
- summarize source information imperfectly; and
- become outdated where underlying information changes.

Users should verify material purchase information with relevant merchant and/or manufacturer sources before purchasing.

This draft does **not** state that AI is always accurate. It does **not** imply that a person reviews every AI response unless such human review is actually implemented (current repository evidence does **not** show a human-review workflow for every AI output).

[COUNSEL TO CONFIRM: AI accuracy / error disclaimer wording]

---

## 9. Product / Offer Data Limitations

AI explanations and recommendations depend on underlying product and offer information.

Potential information may include:

- product specifications;
- price;
- availability;
- seller / source information;
- reviews / ratings;
- shipping;
- returns; and
- warranty.

These fields may be:

- incomplete;
- unavailable;
- unknown;
- stale; or
- supplied by third parties, imports, fixtures, mocks, or simulated sources.

**Not all of these fields are always available or live.** Freshness, coverage, and accuracy can vary. Based on the current implementation reviewed for this draft, marketplace/product data may be fixture, mock, imported, or simulated during development and public-beta preparation. Live certified merchant marketplace feeds for named supported markets are **not** current production claims while related external dependencies remain unfinished.

[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]

---

## 10. Source / Market Coverage

PiqSavi evaluates the sources and offers **available to it** for a request.

This draft does **not** say that:

- all internet retailers were checked;
- all merchants were checked;
- every marketplace was queried; or
- a result is globally best.

### Product-behavior principle for source naming

If the UI eventually names sources being checked, source names should appear only when the execution trace proves those sources were actually attempted. That is a product-behavior principle for future consumer honesty. It is **not** a claim that current UI source-transparency is complete.

[COUNSEL TO CONFIRM: source-transparency and market-coverage disclaimer wording]

---

## 11. Personal Recommendation vs Objective Score (Example)

The following is a **conceptual**, consumer-friendly illustration. It does **not** disclose proprietary scoring formulas and does **not** claim that any specific live catalog example currently ships exactly as written.

**Example**

- Offer A may have the **highest objective PiqScore** based on available offer attributes that PiqSavi evaluated.
- Offer B may still be the **personally recommended Piq** if known user preferences (for example preferred brand, budget fit, or category priorities) make Offer B more suitable for that user.
- In that situation, the **canonical objective PiqScore** for Offer A and Offer B remains unchanged. Personalization influences the personal recommendation layer, not the rewrite of objective scoring.

Users remain free to disregard any personal recommendation and inspect objective scores, alternatives, tradeoffs, and merchant details.

---

## 12. Affiliate Neutrality

Cross-reference: **PiqSavi Affiliate & Advertising Disclosure** (counsel draft; not treated here as a published final disclosure).

**Affiliate compensation must not increase:**

- **PiqScore**;
- **canonical DealScore** / objective scoring; or
- **organic Recommendation ranking**.

Affiliate attachment is designed to occur **after** selection/ranking.

If future sponsored placements exist, they must be distinguished from organic recommendations and must **not** be presented as organic PiqScore or organic Recommendation winners. This draft does **not** claim that sponsored placements currently exist as live consumer production surfaces.

[COUNSEL TO CONFIRM: AI-specific disclosure requirements for sponsored or affiliate-influenced content]

---

## 13. Automated Decision-Making / Profiling Issues

This section states product facts only. It does **not** decide legal classification.

Factually, PiqSavi may:

- compute objective PiqScore evaluations;
- produce Recommendation outputs;
- apply personalization where implemented; and
- present AI-assisted explanations where enabled.

Whether those functions constitute “profiling,” “automated decision-making,” or related regulated processing under any particular law—and whether additional disclosure, consent, opt-out, human review, or other rights are required—is **for counsel to determine by market**.

This draft does **not** assert GDPR, CCPA/CPRA, Philippine, Singapore, UK, Canadian, or other legal conclusions.

[COUNSEL TO CONFIRM: whether PiqSavi recommendation/personalization functions constitute profiling or automated decision-making requiring additional disclosure, consent, opt-out, human review, or other rights in any launch market]

---

## 14. High-Impact / Professional Decisions

PiqSavi is intended for shopping / product-purchase assistance.

PiqSavi should **not** be presented as:

- a financial adviser;
- a medical adviser; or
- a legal adviser.

Recommendations and AI explanations are assistive shopping tools, not professional advice in those regulated fields.

[COUNSEL TO CONFIRM: whether certain product categories require additional warnings, exclusions, or restrictions]

---

## 15. Explainability

Where explanations are provided, they may summarize why an offer or recommendation appears favorable based on available information (for example tradeoffs, warnings, confidence indicators, or preference fit where implemented).

This draft does **not** promise:

- complete explanation of every internal algorithmic factor;
- disclosure of proprietary scoring formulas; or
- source citations for every AI statement unless such citations are actually implemented.

[COUNSEL TO CONFIRM: required explanation/transparency standard]

---

## 16. User Control

Based on the current product implementation reviewed for this draft, users may be able to:

- set or update account preferences and settings where those features are implemented;
- provide search / shopping context or filters when using shopping features;
- disregard a recommendation and choose a different option; and
- contact support@piqsavi.com or privacy@piqsavi.com for help or privacy-related requests.

### Controls **not** claimed as currently implemented

This draft does **not** invent the following as currently available product controls unless separately implemented and evidenced:

- a universal personalization opt-out;
- an automated-decision opt-out;
- an explanation-appeal workflow;
- a human-review request workflow for AI outputs; or
- a complete data-correction / account-deletion / export workflow beyond currently evidenced APIs and manual privacy contact.

[COUNSEL TO CONFIRM: required user controls, opt-outs, contest/appeal mechanisms and notice wording by market]

---

## 17. Children / Age

Based on the current product implementation reviewed for this draft, PiqSavi does **not** currently publish or enforce a coded minimum-age policy, age gate, date-of-birth collection, or parental-consent flow.

This draft does **not** invent a minimum age.

[COUNSEL TO CONFIRM: minimum age and whether AI/personalization requires additional protections for minors]

Keep this section consistent with the Privacy Policy and Terms of Service counsel drafts.

---

## 18. Data Sent to AI Services

Cross-reference: **PiqSavi Privacy Policy** (counsel draft; not treated here as a published final policy).

Based on repository evidence reviewed for this draft:

- data sent to an AI provider, if live transport is enabled, may depend on the feature and implementation;
- adapters are designed around product/review/shopping evidence-style payloads for explanation/narrative assistance;
- secrets are intended to be stripped in builders where that path is used;
- this draft does **not** claim that all user account data is sent to AI providers; and
- this draft does **not** claim that no personal data is ever sent unless evidenced for a specific production path.

Exact production prompt composition is **not** invented here. Whether account personal data is included in any specific production payload depends on the enabled path and should be reviewed before live enablement.

[COUNSEL / PROVIDER REVIEW REQUIRED: production prompt contents, personal-data handling, provider retention, training/use, subprocessors and transfer mechanisms]

---

## 19. Logging / Retention

Based on the fact specification and repository evidence reviewed for this draft:

- no deliberate durable AI prompt/response log store was found as an implemented product capability;
- shopping-assistant conversation memory may use a short in-memory TTL where that path is used (default on the order of 30 minutes / 1800 seconds);
- no final general privacy retention policy for AI interactions was found in the product; and
- AI provider-side retention/training behavior is **unknown** from the repository alone and requires provider/counsel review.

State this cautiously: absence of an app-side durable prompt log is **not** the same as a complete privacy retention guarantee across providers, infrastructure logs, or future product changes.

[COUNSEL TO CONFIRM: production AI interaction retention, logging, security-monitoring and deletion requirements]

---

## 20. Human Review / Oversight

Based on the current product implementation reviewed for this draft, PiqSavi does **not** claim that every recommendation or AI output is reviewed by a person before it is shown to a user.

[COUNSEL TO CONFIRM: whether any human-review, escalation, contest or appeal mechanism is legally required]

---

## 21. User Responsibility

Before purchasing, you should consider and verify relevant merchant and/or manufacturer information—including material terms such as price, taxes, shipping, payment, returns, warranty, and seller identity—on the merchant’s own service where applicable.

PiqScore, Recommendations, personalization, and AI explanations are assistive tools. Final purchase decisions remain yours.

Final reliance, warranty, and liability limitations remain for counsel to finalize in the Terms of Service and related notices. This disclosure intentionally avoids aggressive liability language.

[COUNSEL TO CONFIRM: cross-consistency of reliance wording with Terms of Service]

---

## 22. Changes

AI, scoring, recommendation, and personalization functionality may change over time as the service, data sources, providers, and applicable laws evolve.

When this disclosure is updated, the “Last Updated” date (and Effective Date if applicable) should be revised.

This draft does **not** promise a particular notice period.

[COUNSEL TO CONFIRM: whether material changes to scoring/recommendation/AI behavior require notice or renewed consent]

---

## 23. Contact

**General support:** support@piqsavi.com

**Privacy / data:** privacy@piqsavi.com

**Legal operator / entity:**
[COUNSEL TO CONFIRM]

**Legal / business address:**
[COUNSEL TO CONFIRM]

Do not publish a founder home address unless counsel expressly approves that disclosure.

Related counsel drafts (not treated here as published final policies):

- **PiqSavi Privacy Policy**
- **PiqSavi Terms of Service**
- **PiqSavi Affiliate & Advertising Disclosure**

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

This appendix is **internal only**. It must not appear in any future public AI & Recommendation Disclosure.

These are questions and placeholders only. **No privileged legal advice** is provided or recorded here.

## Unresolved matters (minimum set)

1. **Legal operator / entity**
   Placeholder: `[COUNSEL TO CONFIRM: legal operator/entity name]`

2. **Effective Date**
   Placeholder: `[COUNSEL TO CONFIRM]`

3. **PiqScore consumer disclaimer**
   Placeholder: `[COUNSEL TO CONFIRM: final consumer-facing PiqScore limitation wording]`

4. **Recommendation reliance wording**
   Placeholder: `[COUNSEL TO CONFIRM: appropriate reliance/disclaimer wording]`

5. **Personalization / profiling classification**
   Placeholder: `[COUNSEL TO CONFIRM: profiling/personalization disclosure requirements by market]`

6. **Automated-decision classification**
   Placeholder: `[COUNSEL TO CONFIRM: whether PiqSavi recommendation/personalization functions constitute profiling or automated decision-making requiring additional disclosure, consent, opt-out, human review, or other rights in any launch market]`

7. **Required user rights / opt-outs**
   Placeholder: `[COUNSEL TO CONFIRM: required user controls, opt-outs, contest/appeal mechanisms and notice wording by market]`

8. **Human review / contest requirements**
   Placeholder: `[COUNSEL TO CONFIRM: whether any human-review, escalation, contest or appeal mechanism is legally required]`

9. **AI-provider disclosure**
   Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: final production AI provider disclosures, terms, retention, training, international transfer and processor/controller treatment]`

10. **Provider retention / training**
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: final production AI provider disclosures, terms, retention, training, international transfer and processor/controller treatment]`

11. **Provider international transfers**
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: final production AI provider disclosures, terms, retention, training, international transfer and processor/controller treatment]`

12. **AI prompt / personal-data treatment**
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: production prompt contents, personal-data handling, provider retention, training/use, subprocessors and transfer mechanisms]`

13. **AI logging / retention**
    Placeholder: `[COUNSEL TO CONFIRM: production AI interaction retention, logging, security-monitoring and deletion requirements]`

14. **AI accuracy / error disclaimer**
    Placeholder: `[COUNSEL TO CONFIRM: AI accuracy / error disclaimer wording]`

15. **Explainability requirements**
    Placeholder: `[COUNSEL TO CONFIRM: required explanation/transparency standard]`

16. **Source transparency**
    Placeholder: `[COUNSEL TO CONFIRM: source-transparency and market-coverage disclaimer wording]`

17. **Affiliate / AI interaction**
    Placeholder: `[COUNSEL TO CONFIRM: AI-specific disclosure requirements for sponsored or affiliate-influenced content]`

18. **Sponsored AI responses**
    Placeholder: `[COUNSEL TO CONFIRM: AI-specific disclosure requirements for sponsored or affiliate-influenced content]`
    Note: do not claim sponsored AI responses currently live.

19. **Minors / age**
    Placeholder: `[COUNSEL TO CONFIRM: minimum age and whether AI/personalization requires additional protections for minors]`

20. **High-risk product categories**
    Placeholder: `[COUNSEL TO CONFIRM: whether certain product categories require additional warnings, exclusions, or restrictions]`

21. **PH requirements**
    Placeholder: `[COUNSEL TO CONFIRM: PH AI / recommendation / automated-decision / profiling disclosure requirements]`

22. **US requirements**
    Placeholder: `[COUNSEL TO CONFIRM: US AI / recommendation / automated-decision / profiling disclosure requirements]`

23. **SG requirements**
    Placeholder: `[COUNSEL TO CONFIRM: SG AI / recommendation / automated-decision / profiling disclosure requirements]`

24. **UK requirements**
    Placeholder: `[COUNSEL TO CONFIRM: UK AI / recommendation / automated-decision / profiling disclosure requirements]`

25. **CA requirements**
    Placeholder: `[COUNSEL TO CONFIRM: CA AI / recommendation / automated-decision / profiling disclosure requirements]`

26. **Material-change notice / consent**
    Placeholder: `[COUNSEL TO CONFIRM: whether material changes to scoring/recommendation/AI behavior require notice or renewed consent]`

## Additional open items

- Last Updated date: `[COUNSEL TO CONFIRM]`
- Legal / business address: `[COUNSEL TO CONFIRM]` (do not publish founder home address)
- Mock/imported/simulated catalog consumer wording: `[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]`
- Terms reliance cross-consistency: `[COUNSEL TO CONFIRM: cross-consistency of reliance wording with Terms of Service]`
- Processor/controller treatment of AI providers if/when live HTTP is enabled: included in provider-review placeholder above

## Explicit non-claims for this drafting exercise

- Not legal advice
- Not legally approved
- Not for publication
- Not evidence of legal approval
- Not evidence that all AI/provider features are live
- Not evidence of automated-decision compliance
- Not evidence of production merchant/data-provider approval
- Does not claim AI controls or rewrites canonical PiqScore
- Does not claim PiqScore guarantees best deal / lowest price / savings / complete market coverage
- Does not claim every merchant/source is searched
- Does not claim every product fact is live/current
- Does not claim all AI output is accurate or human-reviewed
- Does not claim any particular AI provider is currently live unless evidenced
- Does not invent final provider retention/training behavior
- Does not invent complete personalization opt-out, ADM appeal, or human-review mechanisms
- Does not assert a final legal classification of profiling/ADM
- Does not claim affiliate compensation affects organic ranking
- Does not claim sponsored AI responses currently live
- Does not close Sprint 26
- Does not start Sprint 27
- Does not start Sprint 28
- Does not modify EXT statuses
- Does not modify roadmap/register statuses

## Drafting provenance

| Item | Value |
|------|-------|
| Public brand | PiqSavi |
| Public tagline | Your AI Personal Shopper |
| Public feature | PiqScore |
| Primary fact sources | `docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md`; `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md`; `docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md`; `docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md` |
| Drafting branch | `docs/piqsavi-ai-recommendation-disclosure-counsel-draft` |
| Authoritative main at drafting | `7b1df9962a44937a998b20093fe89135a01d706a` |
| Sprint 26 | OPEN (unchanged) |
| Sprint 27 | NOT STARTED (unchanged) |
| Sprint 28 | NOT STARTED (unchanged) |
| EXT-01…05 | `not_started` (unchanged) |
| EXT-19 | `applied` (unchanged; written approval not claimed) |
| EXT-20 / EXT-21 | `not_started` (unchanged) |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |

**End of PiqSavi AI & Recommendation Disclosure — Counsel Draft.**
