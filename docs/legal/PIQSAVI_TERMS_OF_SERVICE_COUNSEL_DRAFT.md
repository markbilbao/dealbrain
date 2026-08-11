# PiqSavi Terms of Service

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary source: docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
Also used: docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md
Authoritative main at drafting: 93f89d1ed716db784e0b5c1da0fd2135d2176854
Fact-spec audit HEAD noted therein: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
Internal technical codename: DealBrain (do not use in public-facing Terms body)
Internal scoring names: DealScore / PersonalDealScore (public name remains PiqScore)
This draft does not claim EXT-19 approval, EXT-21 completion, Sprint 28 start, merchant/provider authorization, or legal sufficiency.
-->

---

**Effective Date:**
[COUNSEL TO CONFIRM]

**Last Updated:**
[COUNSEL TO CONFIRM]

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**Legal address:**
[COUNSEL TO CONFIRM: required operator/business address]

**General support:** support@piqsavi.com
**Privacy contact:** privacy@piqsavi.com

---

## 1. Acceptance and Scope of These Terms

These Terms of Service (“Terms”) govern access to and use of PiqSavi (“PiqSavi,” “we,” “us,” or “our”), including the shopping-intelligence features offered under the PiqSavi brand (public tagline: **Your AI Personal Shopper**).

By accessing or using PiqSavi, you are asked to understand and follow these Terms. The exact method by which assent is obtained and recorded is not finalized in this draft.

[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]

These Terms apply to the consumer-facing PiqSavi service. Merchant-organization tooling is a separate product context and is not the focus of this consumer draft.

[COUNSEL TO CONFIRM: whether merchant-platform terms must be covered here, in a separate agreement, or later]

### Related policies and notices

Additional policies and notices may apply, including (as drafted, finalized, or published over time):

- **Privacy Policy** (counsel draft exists; not treated here as a published final policy)
- **Affiliate & Advertising Disclosure** (draft/future; not yet a finalized published disclosure)
- **AI / Recommendation Disclosure** (draft/future; not yet a finalized published disclosure)
- **Cookie / Tracking Notice** (draft/future; not currently required by an active cookie/analytics implementation in the reviewed product state)

If there is a conflict between this draft and a later counsel-approved published policy, the published counsel-approved version controls once it exists.

This document is a **counsel draft**. It is not published, not final, and not legal advice. It does not claim that PiqSavi complies with any particular consumer, advertising, privacy, or platform law.

---

## 2. The PiqSavi Service

PiqSavi is an AI-assisted shopping and recommendation service intended to help users evaluate products and offers and make purchasing decisions. Among other features, PiqSavi may:

- evaluate offers using **PiqScore**;
- present separate **Recommendations** (for example Buy / Wait / Consider / Avoid style guidance);
- apply **personalization** where account preferences or related signals are available;
- provide **AI-assisted explanations or narratives** where that path is enabled; and
- link or redirect users toward third-party merchants or offer destinations where such paths exist.

### Important architecture distinctions (product facts)

- **PiqScore** is an **objective offer-evaluation** score based on available product/offer evidence that PiqSavi actually evaluated.
- **Recommendation** is a **separate** customer-action layer and is not the same thing as PiqScore.
- **Personalization** may influence a personally recommended choice or personalized PiqScore-style result **without rewriting** the canonical objective PiqScore.
- **AI** is designed for explanation/reasoning support and is **not** designed to rewrite canonical objective PiqScore.
- **Affiliate compensation must not increase** PiqScore or organic Recommendation ranking under current product architecture rules.

### What PiqSavi does **not** currently claim

Based on the current product implementation reviewed for this draft, you should **not** assume that PiqSavi:

- searches every marketplace or provides universal market coverage;
- shows every available price or offer;
- guarantees that every price or offer is live or current;
- guarantees the lowest price;
- guarantees savings;
- guarantees product suitability for your needs; or
- currently operates live certified merchant marketplace feeds for named supported markets.

**Current catalog posture:** Marketplace/product data may be fixture, mock, imported, or simulated during development and public-beta preparation. Live certified merchant integrations for intended markets are planned separately and are **not** described here as current production claims.

[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]

---

## 3. Eligibility and Age

Based on the current product implementation reviewed for this draft, PiqSavi does **not** currently publish or enforce a coded minimum-age policy, age gate, date-of-birth collection, or parental-consent flow.

[COUNSEL TO CONFIRM: minimum age and any parental-consent requirements by market]

You must be able to form a binding contract with the Operator under applicable law, subject to the age and consent rules counsel adopts.

[COUNSEL TO CONFIRM: capacity / eligibility wording beyond age]

---

## 4. Accounts

### 4.1 Registration and account information

PiqSavi currently supports consumer account registration using:

- **email address** (login identity);
- **password** (stored as a password hash, not plaintext); and
- **display name**.

You are responsible for providing information that is accurate and kept reasonably up to date for the account features you use.

Based on the current implementation reviewed for this draft, consumer registration does **not** currently collect phone number, date of birth, or separate first/last name fields.

### 4.2 Credentials and account security

You are responsible for maintaining the confidentiality of your credentials and for activity that occurs under your account where you control those credentials. Notify us promptly at support@piqsavi.com if you believe your account has been compromised.

Current security-related product facts include password hashing, hashed session/token storage, rate limiting, and related controls described in the Privacy Policy draft. No security measure is perfect.

### 4.3 Sessions

Authentication currently uses a **Bearer token** model rather than browser cookie-based sessions. Sessions may expire (for example after a shorter default period, or a longer period if remember-me behavior is used). Logout revokes the relevant session where that path is used.

### 4.4 Email verification and password recovery (current limitations)

Based on the current product implementation reviewed for this draft:

- email-verification state fields and related request architecture may exist, but **complete confirmation and live transactional email delivery are not fully implemented**;
- password-reset request architecture may exist, but **complete confirm-reset / live email recovery flows are not fully implemented**;
- multi-factor authentication (MFA) and OAuth / external identity providers are **not** currently implemented as live consumer login methods.

Do not assume that self-serve email verification or password recovery currently works end-to-end as a production email workflow.

### 4.5 Account status

Accounts may include an active/disabled-style state in the product model. Complete user-facing account-termination or self-service disable flows are not fully described here as finished consumer features.

[COUNSEL TO CONFIRM: suspension/termination grounds, notice and appeal requirements]

### 4.6 Account deletion and data export (current limitations)

Based on the current product implementation reviewed for this draft:

- an **in-product account-deletion workflow is not currently implemented**;
- an **automated personal-data export / DSAR download workflow is not currently implemented**;
- privacy-related requests may be directed to **privacy@piqsavi.com** and may be handled manually.

You should **not** assume that you can currently delete or export your full account data through an in-product self-serve control. See the **PiqSavi Privacy Policy** for related privacy wording.

[COUNSEL TO CONFIRM: required deletion/export wording cross-consistency with Privacy Policy]

---

## 5. Permitted Use

Subject to these Terms and applicable law, you may use PiqSavi for lawful personal shopping research, offer evaluation, and related consumer purposes for which the service is offered.

[COUNSEL TO CONFIRM: whether commercial/reseller use requires a separate license or prohibition]

---

## 6. Prohibited Use

You must not misuse PiqSavi. Without limiting counsel’s final wording, the following are examples of conduct that may be restricted:

- unlawful use of the service;
- fraud, deception, or attempts to obtain unauthorized benefits;
- attempts to interfere with, disrupt, overload, or degrade the service;
- abuse of, or circumvention of, rate limits or security controls;
- unauthorized access to accounts, systems, or non-public data;
- malicious automation intended to harm or unfairly burden the service;
- scraping PiqSavi itself in a manner that violates these Terms or applicable law;
- reverse engineering where restriction is legally permitted;
- misuse of merchant, marketplace, or other third-party source content beyond authorized use of the service;
- impersonation of another person or entity;
- introduction of malware, harmful code, or similar threats.

[COUNSEL TO CONFIRM: enforceability and market-specific limitations]

We do not claim in this draft that every listed restriction is enforceable in every market without counsel review.

---

## 7. PiqScore

**PiqScore** is PiqSavi’s public name for an objective evaluation of a product or offer based on available offer attributes that PiqSavi actually evaluated. Depending on available evidence, inputs may include cost-related signals, seller rating, shipping, availability, official-store indicators, warranty-related attributes, returns-related attributes, and similar offer factors where present.

Important limitations:

- PiqScore is scoped to offers PiqSavi actually evaluated. It does **not** imply universal market completeness.
- Missing, unknown, incomplete, fixture, imported, or stale data may affect evaluation quality.
- PiqScore is distinct from Recommendation.
- Personalization is designed **not** to rewrite canonical objective PiqScore.
- Affiliate or advertising compensation must **not** increase PiqScore under current architecture rules.
- This section does not disclose proprietary scoring formulas, weights, or implementation details.

[COUNSEL TO CONFIRM: appropriate consumer-facing scoring disclaimer]

---

## 8. Recommendations

Recommendations are intended to **assist**—not replace—your own purchasing judgment.

PiqSavi may present recommendation outputs such as Buy, Wait, Consider, or Avoid style guidance, together with related explanations, tradeoffs, warnings, confidence indicators, or alternatives where implemented.

A personally recommended option may differ from the listing with the highest objective PiqScore where personalization, thresholds, tradeoffs, warnings, confidence, or related recommendation logic cause them to differ.

Recommendations are **not** professional financial, legal, medical, investment, or other regulated advice, and they do not guarantee purchase outcomes, savings, suitability, or merchant performance.

[COUNSEL TO CONFIRM: appropriate reliance/disclaimer language]

---

## 9. AI-Assisted Features

PiqSavi’s public positioning includes AI-assisted shopping help. Based on the current product implementation reviewed for this draft:

- AI may be used for explanations, narratives, or similar assistance where that path is implemented;
- AI is **not** designed to rewrite canonical objective PiqScore;
- AI outputs may contain errors, omissions, or incomplete information;
- live external AI provider HTTP calls are **disabled by default** at the current state;
- when AI paths are unavailable, deterministic fallbacks may be used;
- you should review relevant merchant and product details before purchasing.

Exact production AI provider use may vary over time and may remain optional.

[COUNSEL / PROVIDER REVIEW REQUIRED: production AI provider terms, data-handling disclosures and required AI disclaimers]

---

## 10. Product, Offer, and Merchant Information

PiqSavi may display or derive information that can include prices, availability, specifications, seller/source information, ratings/review information, shipping, returns, warranty, and related shopping attributes.

These fields may sometimes be:

- unavailable;
- incomplete;
- stale;
- unknown; or
- supplied by third parties, imports, fixtures, mocks, or simulated sources.

**Not all of these fields are currently live production merchant data.** Freshness, coverage, and accuracy can vary. PiqSavi does **not** guarantee that product or offer information is complete, current, or error-free.

Before completing a purchase, you should verify material purchase terms—including price, taxes, shipping, payment, returns, warranty, and seller identity—on the merchant’s own service.

[COUNSEL TO CONFIRM: required catalog-accuracy and consumer-protection wording]

---

## 11. Merchants and Third-Party Services

PiqSavi may link or redirect you to third-party merchants, marketplaces, or other external services.

Based on the intended product model reviewed for this draft:

- PiqSavi is generally designed as a shopping-intelligence / referral-oriented service rather than the retail seller of the underlying goods;
- the merchant (or other third party) typically controls the transaction;
- the merchant may control final price, inventory, checkout/payment, shipping, returns, and warranty terms, where applicable; and
- the merchant’s own terms, privacy policy, and consumer notices may apply to the purchase.

This draft does **not** claim current contractual relationships, approvals, or live certified integrations with Shopee, Lazada, TikTok Shop, Amazon, Temu, or any other named merchant or affiliate program.

[COUNSEL TO CONFIRM: marketplace-intermediary / seller-of-record wording and consumer-law implications]

---

## 12. Affiliate Relationships

PiqSavi may use affiliate links or attribution mechanisms so that merchants or affiliate programs can recognize referrals. Not every link or destination is necessarily an affiliate link. If a qualifying purchase or other qualifying event occurs through an applicable affiliate path, PiqSavi may receive compensation.

Under current product architecture rules, such compensation must **not** increase PiqScore or organic Recommendation ranking. Affiliate attachment is designed to occur after selection/ranking.

Based on the current implementation reviewed for this draft:

- affiliate link generation and attribution behavior are **demo/fixture-oriented**;
- real affiliate-network IDs, live conversion postbacks, and production payout tracking are **not** currently implemented as live production programs;
- future live affiliate programs, if approved and integrated, may change operational detail but should preserve the affiliate-neutrality principle above unless architecture and counsel expressly revise it.

For advertising/affiliate consumer disclosures beyond these Terms, see the **Affiliate & Advertising Disclosure** (draft/future document; not yet a published legal disclosure).

[COUNSEL TO CONFIRM: required disclosure placement and wording]

---

## 13. Purchases and Payments

Based on the current architecture reviewed for this draft, PiqSavi does **not** currently process retail checkout or payment for third-party product purchases as a PiqSavi checkout/payment system.

Where you choose to buy a product reached through PiqSavi, the purchase is generally completed with the relevant merchant (or other third party), subject to that party’s terms and processes.

This draft does **not** invent or promise:

- PiqSavi payment processing for retail checkout;
- PiqSavi-managed refunds or chargebacks for merchant purchases;
- PiqSavi subscriptions or recurring billing for consumer retail checkout; or
- transaction guarantees for third-party purchases.

[COUNSEL TO CONFIRM: wording if future paid PiqSavi subscriptions or services are introduced]

---

## 14. Returns, Refunds, and Warranties for Purchases

PiqSavi does not, in this draft, promise that PiqSavi itself provides returns, refunds, or warranties for products purchased from third-party merchants.

Where applicable, merchant and/or manufacturer terms generally govern the underlying purchase. You should review those terms on the merchant’s service before buying.

[COUNSEL TO CONFIRM: consumer-protection obligations and required wording]

---

## 15. Intellectual Property

Subject to counsel confirmation of final ownership and licensing language:

- PiqSavi brand elements, product software, and PiqSavi-created service content are intended to be protected by applicable intellectual-property and related rights belonging to the Operator or its licensors;
- third-party merchant trademarks, product images, titles, reviews, and related content remain the property of their respective owners and are used only as permitted by applicable law, license, or program terms;
- nothing in these Terms grants you a right to use PiqSavi trademarks or to copy the service except as needed for ordinary permitted use of the service interface.

Public branding remains **PiqSavi** / **PiqScore**. Internal machine field names may differ and are not consumer-facing brand names.

[COUNSEL TO CONFIRM: final IP ownership, licensing and permitted-use language]

---

## 16. User Content and Feedback

Based on the current consumer product implementation reviewed for this draft, PiqSavi does **not** currently operate a broad public user-generated-content community (for example public reviews/comments forums) as a primary launched consumer feature.

If you send feedback, ideas, or suggestions to PiqSavi (including via support@piqsavi.com), we may use that feedback to operate and improve the service.

[COUNSEL TO CONFIRM: rights/license needed for feedback and any future reviews, comments or community content]

Do not submit content that you do not have the right to share, or that is unlawful, infringing, or harmful.

---

## 17. Third-Party Links and Services

PiqSavi may link to third-party websites, apps, merchants, or services. Those third parties are responsible for their own terms, privacy practices, and products.

This draft does **not** disclaim all responsibility in absolute terms. The enforceable scope of any third-party-service disclaimer is for counsel to confirm by market.

[COUNSEL TO CONFIRM: enforceable third-party-service disclaimer by market]

---

## 18. Service Availability and Changes

PiqSavi may change features, be unavailable, or be temporarily interrupted for maintenance, capacity, security, product evolution, or other operational reasons.

This draft does **not** promise a specific uptime percentage or service-level agreement unless a separate counsel-approved commitment exists.

We may update, limit, or discontinue features as the service evolves, subject to applicable law and these Terms as counsel finalizes them.

[COUNSEL TO CONFIRM: required notice for material feature withdrawal affecting paid users, if any paid offering is later introduced]

---

## 19. Account Suspension and Termination

The product model may include active/disabled account state, but complete user-facing termination, notice, and appeal flows are not treated in this draft as finished consumer features.

Possible grounds that counsel may consider for suspension or termination include:

- material violation of these Terms;
- security or fraud risk;
- unlawful use; and
- protection of the service, other users, or third parties.

[COUNSEL TO CONFIRM: suspension/termination grounds, notice and appeal requirements]

This draft does **not** state that PiqSavi may terminate accounts “for any reason” unless counsel expressly approves that wording.

You may stop using PiqSavi at any time. Account-deletion product limitations are described in Section 4.6 and in the Privacy Policy.

---

## 20. Privacy

Your use of PiqSavi is also described in the **PiqSavi Privacy Policy**.

That Privacy Policy explains, among other things, what information is processed, current deletion/export limitations, AI and affiliate-related processing posture, and how to contact privacy@piqsavi.com.

This Terms draft does not repeat the full Privacy Policy. If counsel determines that a conflict exists, counsel should resolve the conflict before publication.

[COUNSEL TO CONFIRM: conflict-resolution hierarchy between Terms and Privacy Policy]

---

## 21. Disclaimers

PiqSavi is offered as an informational and recommendation-assistance service. Without finalizing warranty disclaimer language in this draft, you should understand that:

- recommendations and scores are assistive and may be imperfect;
- third-party product, price, availability, and merchant data may be wrong, incomplete, fixture-based, imported, simulated, or stale;
- prices and availability can change;
- AI explanations may contain errors;
- merchants control their own conduct, inventory, fulfillment, and post-purchase handling;
- suitability for your particular needs is not guaranteed; and
- uninterrupted or error-free service is not promised.

[COUNSEL TO CONFIRM: warranty disclaimer scope and mandatory consumer-law carve-outs by market]

---

## 22. Limitation of Liability

[COUNSEL TO DRAFT/CONFIRM: limitation of liability, exclusions, monetary cap and mandatory consumer-law carve-outs for PH / US / SG / UK / CA]

This draft intentionally contains **no** invented dollar amount, percentage, aggregate cap, consequential-damages waiver, or statutory exclusion presented as final.

---

## 23. Indemnification

[COUNSEL TO DRAFT/CONFIRM: whether user indemnification is appropriate, scope, exclusions and jurisdiction-specific enforceability]

This draft intentionally does **not** insert aggressive indemnification boilerplate as final wording.

---

## 24. Governing Law and Dispute Resolution

[COUNSEL TO CONFIRM: governing law]

[COUNSEL TO CONFIRM: venue / arbitration / court process]

[COUNSEL TO CONFIRM: consumer dispute rights and mandatory local-law exceptions]

This draft does **not** assume that Philippines law governs all global users, and does not invent arbitration or venue requirements.

---

## 25. Changes to These Terms

We may update these Terms as the service changes or as required by applicable law. When we update them, we will revise the “Last Updated” date (and Effective Date if applicable).

[COUNSEL TO CONFIRM: notice and re-consent requirements for material changes]

---

## 26. Contact

**General support:** support@piqsavi.com

**Privacy:** privacy@piqsavi.com

**Legal operator / entity:**
[COUNSEL TO CONFIRM: legal operator/entity]

**Legal / business address:**
[COUNSEL TO CONFIRM: required address]

Do not publish a founder home address unless counsel expressly approves that disclosure.

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

This appendix is **internal only**. It must not appear in any future public Terms of Service.

## Unresolved legal / product decisions

1. **Legal operator / entity** — exact contracting entity name and public disclosure form.
   Placeholder: `[COUNSEL TO CONFIRM: legal operator/entity name]`

2. **Effective Date / Last Updated** — publication timing after counsel approval.
   Placeholder: `[COUNSEL TO CONFIRM]`

3. **Assent / clickwrap mechanism** — no final registration consent/version acceptance records described as implemented.
   Placeholder: `[COUNSEL TO CONFIRM: required acceptance mechanism and evidence of assent]`

4. **Minimum age** — no repository age policy exists.
   Placeholder: `[COUNSEL TO CONFIRM: minimum age and any parental-consent requirements by market]`

5. **Consumer-law requirements** — PH / US / SG / UK / CA planning markets; no finalized multi-market consumer wording.
   Placeholder: `[COUNSEL TO CONFIRM: warranty disclaimer scope and mandatory consumer-law carve-outs by market]`

6. **PiqScore disclaimer** — objective scoring vs market-completeness risk.
   Placeholder: `[COUNSEL TO CONFIRM: appropriate consumer-facing scoring disclaimer]`

7. **Recommendation reliance disclaimer** — assistive, not professional advice; no outcome guarantee.
   Placeholder: `[COUNSEL TO CONFIRM: appropriate reliance/disclaimer language]`

8. **AI disclaimer** — adapters exist; live HTTP off by default; provider terms unknown.
   Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: production AI provider terms, data-handling disclosures and required AI disclaimers]`

9. **Merchant / intermediary status** — intended non-seller model; no current named merchant contracts claimed.
   Placeholder: `[COUNSEL TO CONFIRM: marketplace-intermediary / seller-of-record wording and consumer-law implications]`

10. **Affiliate disclosure** — demo/fixture only today; separate Affiliate & Advertising Disclosure not yet published.
    Placeholder: `[COUNSEL TO CONFIRM: required disclosure placement and wording]`

11. **Payment / subscription future scope** — no current PiqSavi retail checkout/payment; future paid PiqSavi services unresolved.
    Placeholder: `[COUNSEL TO CONFIRM: wording if future paid PiqSavi subscriptions or services are introduced]`

12. **Returns / refund / warranty wording** — merchant/manufacturer generally govern underlying purchase.
    Placeholder: `[COUNSEL TO CONFIRM: consumer-protection obligations and required wording]`

13. **IP ownership / license** — brand/software vs third-party merchant content.
    Placeholder: `[COUNSEL TO CONFIRM: final IP ownership, licensing and permitted-use language]`

14. **User-content / feedback rights** — no broad current UGC license fabricated; feedback license needed.
    Placeholder: `[COUNSEL TO CONFIRM: rights/license needed for feedback and any future reviews, comments or community content]`

15. **Third-party links** — no absolute all-responsibility disclaimer finalized.
    Placeholder: `[COUNSEL TO CONFIRM: enforceable third-party-service disclaimer by market]`

16. **Account termination** — active/disabled state exists; user-facing termination/appeal incomplete.
    Placeholder: `[COUNSEL TO CONFIRM: suspension/termination grounds, notice and appeal requirements]`

17. **Warranties** — factual disclaimer basis only; final warranty disclaimer pending.
    Placeholder: `[COUNSEL TO CONFIRM: warranty disclaimer scope and mandatory consumer-law carve-outs by market]`

18. **Limitation of liability** — no invented cap or exclusion presented as final.
    Placeholder: `[COUNSEL TO DRAFT/CONFIRM: limitation of liability, exclusions, monetary cap and mandatory consumer-law carve-outs for PH / US / SG / UK / CA]`

19. **Indemnification** — not inserted as aggressive final boilerplate.
    Placeholder: `[COUNSEL TO DRAFT/CONFIRM: whether user indemnification is appropriate, scope, exclusions and jurisdiction-specific enforceability]`

20. **Governing law** — not invented.
    Placeholder: `[COUNSEL TO CONFIRM: governing law]`

21. **Arbitration / dispute resolution** — not invented.
    Placeholder: `[COUNSEL TO CONFIRM: venue / arbitration / court process]`

22. **PH / US / SG / UK / CA mandatory-law differences** — open for counsel.
    Placeholder: `[COUNSEL TO CONFIRM: consumer dispute rights and mandatory local-law exceptions]`

23. **Terms-change notification** — no invented statutory notice period.
    Placeholder: `[COUNSEL TO CONFIRM: notice and re-consent requirements for material changes]`

24. **Legal address** — support@ and privacy@ provisioned; formal address disclosure pending.
    Placeholder: `[COUNSEL TO CONFIRM: required operator/business address]`

25. **Privacy Policy cross-reference** — keep consistent with `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md`; conflict hierarchy pending.
    Placeholder: `[COUNSEL TO CONFIRM: conflict-resolution hierarchy between Terms and Privacy Policy]`

26. **Merchant-program-specific restrictions** — EXT-01…05 `not_started`; no invented merchant rights or authorizations.
    Related: merchant counsel worksheet / capability-policy register; do not claim Shopee/Lazada/TikTok Shop/Amazon/Temu approvals.

## Additional open items (non-exhaustive)

- Capacity/eligibility wording beyond age: `[COUNSEL TO CONFIRM: capacity / eligibility wording beyond age]`
- Commercial/reseller use: `[COUNSEL TO CONFIRM: whether commercial/reseller use requires a separate license or prohibition]`
- Mock/imported/simulated catalog consumer wording: `[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]`
- Catalog-accuracy consumer-protection wording: `[COUNSEL TO CONFIRM: required catalog-accuracy and consumer-protection wording]`
- Merchant-platform Terms scope: `[COUNSEL TO CONFIRM: whether merchant-platform terms must be covered here, in a separate agreement, or later]`
- Material feature-withdrawal notice if paid offerings later exist: `[COUNSEL TO CONFIRM: required notice for material feature withdrawal affecting paid users, if any paid offering is later introduced]`
- Deletion/export Terms–Privacy consistency: `[COUNSEL TO CONFIRM: required deletion/export wording cross-consistency with Privacy Policy]`

## Explicit non-claims for this drafting exercise

- Not legal advice
- Not legally approved
- Not published
- Not evidence of EXT-19 written approval
- Not evidence of EXT-21 Terms of Service publication
- Not evidence of Sprint 28 start/completion
- Does not close Sprint 26
- Does not start Sprint 27
- Does not start Sprint 28
- Does not modify EXT statuses
- Does not invent live merchant integrations, provider approvals, complete market coverage, best-price/savings guarantees, PiqSavi checkout/payment, subscriptions, completed account deletion/export, completed transactional email, final minimum age, final legal entity, final governing law, final arbitration, final liability cap, or final AI-provider behavior
- Does not invent merchant rights or claim merchant/provider authorization

## Drafting provenance

| Item | Value |
|------|-------|
| Public brand | PiqSavi |
| Public tagline | Your AI Personal Shopper |
| Public feature | PiqScore |
| Primary fact source | `docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md` |
| Secondary fact source | `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md` |
| Drafting branch | `docs/piqsavi-terms-of-service-counsel-draft` |
| Authoritative main at drafting | `93f89d1ed716db784e0b5c1da0fd2135d2176854` |
| Sprint 26 | OPEN (unchanged) |
| Sprint 27 | NOT STARTED (unchanged) |
| Sprint 28 | PLANNED / NOT STARTED (unchanged) |
| EXT-01…05 | `not_started` (unchanged) |
| EXT-19 | `applied` (unchanged; written approval not claimed) |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |

**End of PiqSavi Terms of Service — Counsel Draft.**
