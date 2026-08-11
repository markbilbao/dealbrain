# PiqSavi Privacy Policy

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary source: docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
Authoritative main at drafting: e539af8765ec3deab36bb835e31bd595e657b1d8
Fact-spec audit HEAD noted therein: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
This draft does not claim EXT-19 approval, EXT-20 completion, Sprint 28 start, or legal sufficiency.
-->

---

**Effective Date:**
[COUNSEL TO CONFIRM]

**Last Updated:**
[COUNSEL TO CONFIRM]

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**Privacy contact:** privacy@piqsavi.com
**General support:** support@piqsavi.com

---

## 1. Introduction

PiqSavi (“PiqSavi,” “we,” “us,” or “our”) is a shopping-intelligence service marketed as **Your AI Personal Shopper**. Among other features, PiqSavi may evaluate offers using **PiqScore** and may present separate purchase recommendations.

This Privacy Policy explains, in plain language, what information PiqSavi currently processes based on the product implementation reviewed for this draft, how that information is used, and how you can contact us about privacy matters.

This document is a **counsel draft**. It is not published, not final, and not legal advice. It does not claim that PiqSavi complies with any particular privacy law.

**Scope.** This draft is intended to describe personal and related information processed in connection with the PiqSavi consumer service (accounts, shopping-intelligence features, support/privacy contacts, and related operations). Merchant-organization tooling is a separate product context and is not the focus of this consumer-facing draft.

[COUNSEL TO CONFIRM: whether merchant-platform privacy must be covered in this policy, a separate notice, or later]

---

## 2. Information We Collect

### 2.1 Information you provide

Depending on how you use PiqSavi, you may provide:

- **Email address** — used as your login identity.
- **Password** — used to create and access an account. PiqSavi stores a **password hash**, not your plaintext password.
- **Display name** — a name shown in account/profile contexts.
- **Account preferences and settings** — for example budget, currency, country preference, category/goal preferences, theme/language settings, AI-mode preference flags, and notification preference flags (such as email/newsletter-related toggles).
- **Search and shopping inputs** — such as search/query text and filters you submit when using shopping or offer-evaluation features.
- **Saved-product and related account activity** — such as saved products, comparisons, searches, recommendation history, recently viewed items, favorites, wishlist, owned products, or accessories, where those features are used.
- **Support or privacy request content** — messages you send to support@piqsavi.com or privacy@piqsavi.com, and information needed to respond.

Based on the current product implementation, consumer registration does **not** currently collect phone number, date of birth, or separate first/last name fields.

### 2.2 Information generated through use

When you use PiqSavi, the service may generate or record:

- **Account and user identifiers**
- **Session identifiers** and related session metadata (for example creation/expiry times, remember-me behavior, last-seen time, and revocation state)
- **Timestamps** associated with account and activity records
- **Personalization / recommendation-related state** tied to an authenticated account where those features are used
- **Authentication and security audit events** (which may include normalized email on certain login-failure or rate-limit paths)
- **Request identifiers** and technical request metadata used for operations and troubleshooting
- **Client IP address** where request logging or rate limiting captures it
- **Optional device/browser hints** on sessions where supported (current login path may not always populate these)

Authentication currently uses a **Bearer token** model rather than browser cookie-based sessions.

### 2.3 Shopping and product-related information

PiqSavi processes product, offer, price, availability, seller, and related shopping attributes in order to evaluate offers and present recommendations.

**Important current-state note:** Based on the current implementation reviewed for this draft, marketplace/product data may be **fixture, mock, imported, or simulated** during development and public-beta preparation. PiqSavi does **not** currently claim live certified merchant marketplace feeds for supported markets.

Future live merchant or catalog integrations, if introduced, may process additional merchant/product data under separate product and legal review.

[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]

### 2.4 Affiliate and attribution-related information

PiqSavi may process affiliate or attribution-related identifiers in connection with demo/fixture affiliate link and click-tracking behavior. Depending on the request, this may include click identifiers, optional user or session identifiers supplied by the client, merchant/product identifiers, campaign/source/referrer fields, device/country fields, and simulated conversion or commission fields.

Based on the current implementation reviewed for this draft, affiliate behavior is **demo/fixture-oriented**. Real affiliate-network identifiers, live conversion postbacks, and production payout tracking are **not** currently implemented as live production programs.

---

## 3. Information We Do Not Currently Collect or Provide

Based on the current product implementation reviewed for this draft, the following were **not found** or **not implemented** as consumer product capabilities:

- Phone number collection for consumer accounts
- Date of birth collection
- Separate legal first/last name fields for consumer accounts
- A durable guest-account identity system or guest ID cookie
- Advertising pixels (for example Meta/TikTok-style pixels)
- Analytics cookies or Google Analytics / Google Tag Manager integration
- Browser `localStorage` / `sessionStorage` continuity in the reviewed demo consumer UI
- An in-product account-deletion workflow
- An automated personal-data export / DSAR download workflow
- A published cookie-consent banner / consent-manager integration
- A coded minimum-age gate

This section describes the **current** implementation. It does **not** promise that these features will never be introduced. If they are introduced, this Policy should be updated.

---

## 4. How We Use Information

We use information for purposes such as:

- Creating and authenticating accounts
- Managing sessions and access controls
- Storing and applying account preferences/settings
- Generating, evaluating, and presenting offers and shopping results
- Producing **PiqScore** evaluations and related explanations
- Producing **Recommendations** (for example Buy / Wait / Consider / Avoid style guidance) as a separate decision layer
- Personalizing personally recommended results where account personalization is available
- Providing AI-assisted explanations or narratives where that path is enabled
- Security, fraud prevention, abuse prevention, and rate limiting
- Responding to support and privacy requests
- Affiliate attribution and monetization-related processing where applicable (currently demo/fixture-oriented)
- Operating, logging, troubleshooting, and maintaining the service

### Important product architecture (privacy-relevant)

- **PiqScore** (internal technical name: DealScore) is an **objective offer-evaluation** score.
- **Recommendation** is a **separate** customer-action layer and is not the same thing as PiqScore.
- **Personalization** may influence a personally recommended choice or personalized PiqScore-style result **without rewriting** the canonical objective PiqScore / DealScore.
- **Affiliate compensation must not increase** PiqScore / DealScore or organic Recommendation ranking. Affiliate attachment is designed to occur after selection/ranking.

[COUNSEL TO CONFIRM: whether legal bases (consent, contract, legitimate interests, or other) must be stated for intended markets]

---

## 5. PiqScore, Recommendations, and Automated Processing

### PiqScore

PiqScore is PiqSavi’s public name for an objective evaluation of a product/offer based on available offer attributes (for example cost-related signals, seller rating, shipping, availability, official-store indicators, warranty, and returns-related attributes, where available). It is designed to be deterministic and is not rewritten by affiliate economics.

### Recommendation

Recommendation is a separate layer that indicates what a shopper might do (for example Buy, Wait, Consider, or Avoid). A recommendation can differ from simply choosing the highest PiqScore listing, because recommendation logic may weigh thresholds, tradeoffs, warnings, and confidence.

### Personalization

If you use an account with preferences, personalization may influence which option is personally recommended to you. Personalization is designed **not** to rewrite the canonical objective PiqScore.

### AI explanations

AI features, where enabled, are oriented toward explanation/narrative assistance. They are **not** designed to rewrite canonical objective scoring.

### Affiliate neutrality

Affiliate or advertising economics are not permitted to increase objective PiqScore or organic Recommendation ranking under current product architecture rules.

[COUNSEL TO CONFIRM: whether and how automated decision-making/profiling disclosures are legally required in each intended market]

---

## 6. AI Processing

PiqSavi’s public positioning includes AI-assisted shopping help. Based on the current implementation reviewed for this draft:

- Optional AI provider adapters exist in the product architecture.
- Live external AI HTTP calls are **disabled by default** at the current state.
- When AI paths are used, they are designed for explanation/narrative-style assistance, with deterministic fallbacks when AI is off.
- AI is **not** used to rewrite canonical objective PiqScore.
- Exact production AI provider use may vary over time and may remain optional.

If live AI provider processing is enabled, product, review, or shopping-related evidence payloads may be sent to third-party AI services. Whether account personal data is included in any specific production payload depends on the enabled path and should be reviewed before enablement.

[COUNSEL / PROVIDER REVIEW REQUIRED: final AI provider data-handling, retention, training and international-transfer disclosures]

---

## 7. Affiliate Links and Advertising-Related Processing

PiqSavi may use affiliate links or attribution mechanisms so that merchants or affiliate programs can recognize referrals.

Based on the current implementation reviewed for this draft:

- Affiliate link generation and attribution behavior are **demo/fixture-oriented**.
- Click/attribution records may store identifiers and related metadata as described in Section 2.4.
- Real affiliate-network IDs, live conversion tracking, and production payout systems are **not** currently implemented as live programs.
- Future merchant/provider tracking may process click or attribution identifiers if and when production affiliate programs are approved and integrated.
- Commissions or affiliate compensation **do not** influence objective PiqScore or organic Recommendation ranking under current architecture rules.

For advertising/affiliate consumer disclosures beyond privacy processing, see our **Affiliate & Advertising Disclosure** (draft/future document; not yet a published legal disclosure).

[COUNSEL TO CONFIRM: affiliate tracking disclosure language for current demo state vs future live programs]

---

## 8. Cookies, Local Storage, and Similar Technologies

Based on the current implementation reviewed for this draft:

- No advertising or analytics cookies were found.
- No tracking pixels were found.
- No Google Analytics / Google Tag Manager integration was found.
- No `localStorage` / `sessionStorage` continuity was found in the reviewed demo consumer UI.
- No cookie-consent banner was found.
- Authentication is currently Bearer-token based rather than cookie-session based.

This does **not** mean PiqSavi will never use cookies or similar technologies. If analytics, affiliate tracking, cookies, or similar technologies are introduced, this Policy should be updated and any required notices/consents addressed.

[COUNSEL TO CONFIRM: wording and consent requirements if analytics, affiliate tracking, cookies or similar technologies are introduced]

---

## 9. How We Share Information with Third-Party Services

We may use third-party service providers to help operate PiqSavi. Roles, contracts, and legal classifications (for example “processor” or “subprocessor”) are **not** asserted in this draft.

Based on repository-backed operational and product evidence, relevant third-party services/categories currently include or may include:

| Service / category | Current privacy-relevant posture |
|--------------------|----------------------------------|
| **AWS** | Hosting/infrastructure path for application data, secrets management pathways, and related operations (staging path evidenced; production posture may evolve). |
| **Resend** | Selected for future transactional email. Account/preparation exists; **live transactional email delivery is not currently integrated** in the application. |
| **Google Workspace / Gmail** | Used to receive support and privacy emails sent to provisioned aliases. |
| **Cloudflare** | Domain registrar/control for `piqsavi.com` (public DNS/TLS for the public hostname may still be incomplete). |
| **AI providers** (for example OpenAI, Anthropic, Gemini adapters) | Optional explanation/narrative paths; live external calls disabled by default at current state. |
| **Merchant / affiliate platforms** | Future / subject to separate approvals; live certified merchant feeds are not current. |
| **GitHub / CI** | Engineering/source and deployment operations; not an end-user account feature. |

We do not invent additional sharing categories beyond evidenced or clearly planned service use.

[COUNSEL TO CONFIRM: which third-party services must be disclosed now vs only when integrated, and whether any must be labeled processors/subprocessors]

Future analytics, error-tracking, cookie-consent, FX, payment, or app-store services are planned or out-of-scope depending on roadmap status and are not described here as currently active consumer data practices unless and until implemented.

---

## 10. International Data Transfers

PiqSavi may rely on third-party infrastructure and services that process information in countries other than your country of residence. For example, staging infrastructure evidence indicates a default AWS region of `us-east-1`; production applied region and residency guarantees are not treated as settled facts in this draft.

[COUNSEL TO CONFIRM: applicable international-transfer mechanism and country-specific disclosures]

---

## 11. Data Retention

Some technical expiries currently exist for security or operational reasons. These are **not** necessarily complete privacy retention policies.

### Technical expiries currently evidenced

- **Sessions:** approximately **1 hour** by default, or approximately **30 days** if remember-me behavior is used
- **Password-reset tokens:** approximately **1 hour** (reset confirmation/delivery flows are not fully implemented as live email workflows)
- **Email-verification tokens:** approximately **1 day** (confirmation/delivery flows are not fully implemented as live email workflows)
- **Shopping-assistant conversation memory:** short TTL (default on the order of **30 minutes** / 1800 seconds) where that in-memory path is used

### Where no privacy retention period is established in the product

For account records, profiles, saved activity, affiliate click/attribution records, auth audit events, backups, and similar stores, **no coded privacy retention/deletion schedule was found**.

[COUNSEL TO CONFIRM: retention period and deletion standard]

[COUNSEL TO CONFIRM: which technical TTLs should be described as privacy retention versus security/operational expiry]

---

## 12. Account Deletion and Data Export

Based on the current product implementation reviewed for this draft:

- An **account-deletion workflow is not currently implemented** in the product.
- An **automated data-export / DSAR download workflow is not currently implemented** in the product.
- Users may contact **privacy@piqsavi.com** to make privacy-related requests, which may be handled manually.
- Broader deletion, export, consent, and retention product work is **planned separately** (not described here as currently available self-serve product features).

You should **not** assume that you can currently delete or export your full account data through an in-product self-serve control.

[COUNSEL TO CONFIRM: required deletion/export workflow, response periods, exceptions and retention obligations]

---

## 13. Your Privacy Requests and Rights

You may contact **privacy@piqsavi.com** for privacy-related requests.

Depending on your situation, you may ask about:

- Access to personal information
- Correction of personal information
- Deletion
- Export / portability
- Objection to certain processing
- Withdrawal of consent where consent is the relevant basis

Requests are handled **subject to applicable law and verification requirements.**

This section is an operational contact path. It does **not** independently assert that any specific statutory right applies in every market.

[COUNSEL TO CONFIRM: market-specific rights language for PH / US / SG / UK / CA]

---

## 14. Children and Age Restrictions

Based on the current product implementation reviewed for this draft, PiqSavi does **not** currently publish or enforce a coded minimum-age policy, age gate, date-of-birth collection, or parental-consent flow.

[COUNSEL TO CONFIRM: minimum age, parental-consent rules and child-data restrictions for intended markets]

---

## 15. Security

We apply technical and organizational measures appropriate to the current service design. Based on the current implementation reviewed for this draft, examples include:

- Password hashing (not plaintext password storage)
- Hashed session/token storage (raw session tokens are not stored)
- Rate limiting for abuse resistance
- Security-related HTTP headers
- Production validation checks intended to fail closed on unsafe configuration
- Token/session expiry controls
- Secrets-handling pathways for staging/production operations

No security measure is perfect. We do **not** claim that PiqSavi is fully secure, bank-grade, or immune to unauthorized access, loss, or misuse.

[COUNSEL TO CONFIRM: security wording and any required breach-notification language]

---

## 16. Product and Merchant Data Accuracy

Merchant, product, price, availability, and related shopping data may come from third parties, imports, fixtures, or simulated sources and may be incomplete, delayed, or unavailable. Freshness and coverage can vary. This Privacy Policy does not guarantee complete market coverage or perfect catalog accuracy.

Consumer-protection disclaimers beyond privacy processing are expected to appear in separate terms or product notices.

[COUNSEL TO CONFIRM: cross-references to Terms of Service / consumer disclaimers for catalog accuracy]

---

## 17. Changes to This Privacy Policy

We may update this Privacy Policy as the service changes or as required by applicable law. When we update it, we will revise the “Last Updated” date (and Effective Date if applicable).

[COUNSEL TO CONFIRM: notice requirements for material changes]

---

## 18. Contact Us

**Privacy contact:** privacy@piqsavi.com

**General support:** support@piqsavi.com

**Operator / legal address:**
[COUNSEL TO CONFIRM: legal operator name and address disclosure]

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

This appendix is **internal only**. It must not appear in any future public Privacy Policy.

## Unresolved legal / product decisions

1. **Operator / legal entity** — exact contracting entity name, jurisdiction, and public disclosure form. Do not publish a personal home address unless counsel expressly approves that disclosure.
   Placeholder: `[COUNSEL TO CONFIRM: legal operator/entity name]`

2. **Effective Date / Last Updated** — publication timing after counsel approval.
   Placeholder: `[COUNSEL TO CONFIRM]`

3. **Minimum age / children** — no repository age policy exists.
   Placeholder: `[COUNSEL TO CONFIRM: minimum age, parental-consent rules and child-data restrictions for intended markets]`

4. **Retention periods** — no privacy retention policy found for accounts, logs, affiliate records, backups; only technical TTLs exist.
   Placeholders: `[COUNSEL TO CONFIRM: retention period and deletion standard]`; `[COUNSEL TO CONFIRM: which technical TTLs should be described as privacy retention versus security/operational expiry]`

5. **Deletion / export obligations** — product workflows not implemented; privacy mailbox exists for manual contact.
   Placeholder: `[COUNSEL TO CONFIRM: required deletion/export workflow, response periods, exceptions and retention obligations]`

6. **International transfers** — staging region evidence exists; production residency and legal transfer mechanism unresolved.
   Placeholder: `[COUNSEL TO CONFIRM: applicable international-transfer mechanism and country-specific disclosures]`

7. **Legal bases / consent requirements** — registration consent/version acceptance records not implemented.
   Placeholder: `[COUNSEL TO CONFIRM: whether legal bases (consent, contract, legitimate interests, or other) must be stated for intended markets]`

8. **Cookie / analytics consent** — none found today; future analytics/consent tooling planned separately.
   Placeholder: `[COUNSEL TO CONFIRM: wording and consent requirements if analytics, affiliate tracking, cookies or similar technologies are introduced]`

9. **Affiliate tracking disclosure** — demo/fixture only today; separate Affiliate & Advertising Disclosure not yet a published legal document.
   Placeholder: `[COUNSEL TO CONFIRM: affiliate tracking disclosure language for current demo state vs future live programs]`

10. **AI-provider disclosure** — adapters exist; live HTTP off by default; provider retention/training/transfer terms unknown.
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: final AI provider data-handling, retention, training and international-transfer disclosures]`

11. **Automated decision-making / profiling wording** — product has PiqScore, Recommendation, and personalization layers; legal classification unresolved.
    Placeholder: `[COUNSEL TO CONFIRM: whether and how automated decision-making/profiling disclosures are legally required in each intended market]`

12. **Market-specific rights language** — intended markets include PH / US / SG / UK / CA planning; no definitive statutory rights text asserted here.
    Placeholder: `[COUNSEL TO CONFIRM: market-specific rights language for PH / US / SG / UK / CA]`

13. **Merchant / affiliate sharing language** — live merchant/affiliate programs not started (EXT-01…05 `not_started`).
    Placeholder: `[COUNSEL TO CONFIRM: which third-party services must be disclosed now vs only when integrated, and whether any must be labeled processors/subprocessors]`

14. **Security wording / breach notice** — only evidenced controls described; no “industry-leading” claims.
    Placeholder: `[COUNSEL TO CONFIRM: security wording and any required breach-notification language]`

15. **Policy-change notice** — no invented statutory notice period.
    Placeholder: `[COUNSEL TO CONFIRM: notice requirements for material changes]`

16. **Legal address / contact requirements** — privacy@ and support@ provisioned; formal DPO appointment unknown.
    Placeholder: `[COUNSEL TO CONFIRM: legal operator name and address disclosure]`

17. **Mock/imported/simulated catalog consumer wording** before public beta.
    Placeholder: `[COUNSEL TO CONFIRM: consumer-facing wording for mock/imported/simulated catalog data before public beta]`

18. **Merchant-platform scope** in this consumer Privacy Policy vs separate notice.
    Placeholder: `[COUNSEL TO CONFIRM: whether merchant-platform privacy must be covered in this policy, a separate notice, or later]`

19. **Cross-reference to Terms / consumer disclaimers** for catalog accuracy and recommendation limitations.
    Placeholder: `[COUNSEL TO CONFIRM: cross-references to Terms of Service / consumer disclaimers for catalog accuracy]`

## Explicit non-claims for this drafting exercise

- Not legal advice
- Not legally approved
- Not published
- Not evidence of EXT-19 written approval
- Not evidence of EXT-20 Privacy Policy publication
- Not evidence of Sprint 28 start/completion
- Does not close Sprint 26
- Does not start Sprint 27
- Does not modify EXT statuses
- Does not invent retention periods, subprocessors, transfer mechanisms, cookies, consent flows, deletion/export product capabilities, live merchant feeds, or AI provider contractual behavior

## Drafting provenance

| Item | Value |
|------|-------|
| Public brand | PiqSavi |
| Public feature | PiqScore |
| Primary fact source | `docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md` |
| Drafting branch | `docs/piqsavi-privacy-policy-counsel-draft` |
| Authoritative main at drafting | `e539af8765ec3deab36bb835e31bd595e657b1d8` |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |

**End of PiqSavi Privacy Policy — Counsel Draft.**
