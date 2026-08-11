# PiqSavi Affiliate & Advertising Disclosure

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**
**Not evidence of affiliate-program approval**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary sources:
  - docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md
Supporting product docs inspected as needed:
  - docs/AFFILIATE_LINK_SERVICE.md
  - docs/AFFILIATE_ATTRIBUTION.md
  - docs/AFFILIATE_REVENUE_ENGINE.md
  - docs/AFFILIATE_DISCLOSURE.md
  - docs/SPONSORED_CAMPAIGNS.md
  - docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md
Authoritative main at drafting: 8dbf2064778d883f56bda2de31b6ea228f5fba46
Fact-spec audit HEAD noted in fact-spec: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
Internal technical codename: DealBrain (do not use in public-facing disclosure body)
Internal scoring names: DealScore / PersonalDealScore (public name remains PiqScore)
This draft does not claim EXT-19 written approval, EXT-20/21 publication, Sprint 28 start,
merchant/provider authorization, affiliate-provider approval, credentials, tracking IDs,
contractual capability certification, production-certified markets, or legal sufficiency.
-->

---

**Effective Date:**
[COUNSEL TO CONFIRM]

**Last Updated:**
[COUNSEL TO CONFIRM]

**Operator:**
[COUNSEL TO CONFIRM: legal operator/entity name]

**General support:** support@piqsavi.com
**Privacy / tracking contact:** privacy@piqsavi.com

---

## 1. Purpose of This Disclosure

This Affiliate & Advertising Disclosure is intended to explain, in plain language, how PiqSavi (“PiqSavi,” “we,” “us,” or “our”) may earn revenue from affiliate relationships and any future advertising or sponsored commercial relationships.

PiqSavi is marketed as **Your AI Personal Shopper** and may evaluate offers using **PiqScore** and present separate purchase recommendations. This disclosure focuses on monetization transparency. It does **not** replace the Terms of Service or Privacy Policy.

This document is a **counsel draft**. It is not published, not final, and not legal advice. It does not claim that PiqSavi complies with any particular advertising, endorsement, affiliate, consumer-protection, or privacy law. It is **not** evidence of:

- legal approval;
- affiliate-program approval;
- merchant-data permission;
- completion of external merchant/affiliate dependencies; or
- public monetization launch.

### Forms of monetization addressed in this draft

This disclosure distinguishes the following categories. **Not all are currently active production capabilities.**

| Category | Current posture (repository-backed) | Treatment in this draft |
|----------|-------------------------------------|-------------------------|
| **1. Affiliate links / affiliate attribution** | Foundations exist; behavior is **demo/fixture-oriented**; real network IDs / live payouts **not** implemented as production programs | Described as implemented foundations with demo/fixture limits |
| **2. Advertising** (third-party display / programmatic) | **Not** represented as an active production capability | Future-facing only |
| **3. Sponsored placements** | Merchant-platform **draft framework** only; no real sponsored billing; not described as live consumer sponsored results | Future-facing only for consumer surfaces |
| **4. Merchant partnerships** | Separate from affiliate permission; live certified merchant feeds **not** current (EXT-01…05 `not_started`) | Limited factual note; future/partner-dependent |
| **5. Subscriptions / paid PiqSavi services** | Not described as current retail checkout/payment or consumer subscription billing | Future-facing only if introduced |

[COUNSEL TO CONFIRM: whether all five categories must appear in the first published consumer disclosure, or whether a narrower affiliate-only disclosure should ship first]

---

## 2. Important Architecture and Permission Distinctions

Preserve these distinctions when reading or finalizing this disclosure:

- **Technical capability ≠ contractual permission.**
- **Affiliate permission ≠ product-data permission.**
- **Provider approval ≠ blanket capability permission.**
- **Application submitted ≠ provider approval.**
- **Provider approval ≠ credentials.**
- **Credentials ≠ tracking IDs.**
- **Tracking IDs ≠ contractual capability certification.**
- **Contractual capability certification ≠ production-certified market.**
- **Unknown capability fails closed.**

Do **not** infer that because PiqSavi can generate demo affiliate links, click records, or attribution simulations, any named merchant or affiliate provider has approved PiqSavi for production use.

---

## 3. Current Affiliate Posture

Based on the product implementation and repository evidence reviewed for this draft:

- PiqSavi has **affiliate-link generation, click-tracking, and attribution foundations**.
- Affiliate attachment is designed to occur **after** selection / ranking (post-rank / post-selection).
- Current affiliate behavior remains **demo/fixture-oriented** (including demo templates and simulated attribution paths).
- Real affiliate-network identifiers, live conversion postbacks, and production payout tracking are **not** currently implemented as live production programs.
- Real affiliate tracking IDs (EXT-07) remain **`not_started`**.
- Merchant / marketplace access applications for intended markets (EXT-01…05) remain **`not_started`**.

### Named providers — no approved production affiliate claim

This draft does **not** state that PiqSavi is currently an approved affiliate of:

- Shopee;
- Lazada;
- TikTok Shop;
- Amazon; or
- Temu.

Repository evidence at drafting does **not** independently prove approved production affiliate status for those providers. Naming a provider in research, fixtures, shortlists, or technical connectors is **not** the same as provider approval, credentials, tracking IDs, contractual capability certification, or a production-certified market.

[COUNSEL TO CONFIRM: how to describe demo/fixture affiliate foundations vs future live programs in consumer-facing copy]

---

## 4. How Affiliate Links May Work

Conceptually, when production affiliate programs are approved and integrated:

- some outbound links from PiqSavi may contain affiliate tracking information;
- if a user follows an eligible affiliate link and completes a qualifying action or purchase under the applicable program rules, PiqSavi may receive compensation;
- compensation may vary by provider, program, product, category, and market;
- not every link is necessarily an affiliate link;
- not every merchant pays PiqSavi;
- not every purchase earns a commission;
- not every click creates attribution; and
- there is no universal fixed commission percentage, cookie/attribution window, or tracking behavior claimed in this draft.

PiqSavi’s current implementation includes demo/fixture link generation and related click/attribution records. Those foundations do **not** by themselves prove live monetized affiliate operation.

[COUNSEL TO CONFIRM: final consumer-facing affiliate explanation]

---

## 5. Ranking Neutrality (PiqScore and Organic Recommendations)

**Affiliate compensation must not increase:**

- **PiqScore** (public name for objective offer evaluation; internal technical name: DealScore);
- **canonical DealScore** / objective scoring; or
- **organic Recommendation ranking**.

### Objective PiqScore vs personally recommended Piq

- **PiqScore** is an **objective** offer-evaluation score based on available offer attributes that PiqSavi actually evaluated.
- **Recommendation** is a **separate** customer-action layer (for example Buy / Wait / Consider / Avoid style guidance) and is not the same thing as PiqScore.
- **Personalization** may influence a personally recommended choice or personalized PiqScore-style result **without rewriting** the canonical objective PiqScore.
- Affiliate compensation must **not** be used as an objective-score boost or an organic ranking boost.

Affiliate attachment is designed to occur **after** selection/ranking.

This section does **not** claim that compensation has zero influence on every possible future commercial surface. If sponsored or paid placements are introduced later, they must be treated as a **separate, labeled** commercial surface—not as organic PiqScore winners or organic Recommendation winners.

[COUNSEL TO CONFIRM: consumer-facing ranking-neutrality wording and whether additional examples are required]

---

## 6. Sponsored or Paid Placements (Future)

Based on the current product implementation reviewed for this draft, PiqSavi should **not** be described as currently offering live consumer sponsored placements as an active production monetization surface.

A merchant-platform **draft framework** for labeled sponsored campaigns exists in the repository (including a sponsored-label concept and organic-ranking independence flags). That framework is **not** evidence of:

- real sponsored billing;
- live consumer sponsored results as a launched production surface; or
- that a paid placement is an organic PiqScore or Recommendation winner.

### Future-facing language

PiqSavi may in the future offer clearly identified sponsored or paid placements. If used, they should be distinguished from organic PiqScore / Recommendation results. A paid placement must **not** be presented as an organic winner.

[COUNSEL TO CONFIRM: labeling requirements for sponsored results / paid placements by market]

---

## 7. Advertising (Future)

Based on the current product implementation reviewed for this draft, third-party display or programmatic advertising is **not** currently represented as an active production capability.

This draft does **not** invent Google Ads, Meta Ads, TikTok Ads, ad networks, advertising pixels, or ad servers as currently active PiqSavi production systems.

If advertising is introduced later:

- separate disclosures may be required;
- consent, notice, or opt-out mechanisms may be required depending on tracking behavior and market; and
- this disclosure (and related Privacy / Cookie notices) should be updated.

[COUNSEL TO CONFIRM: advertising disclosure requirements]

[COUNSEL TO CONFIRM: whether behavioral/targeted advertising requires additional consent or opt-out mechanisms by market]

---

## 8. Cookies, Tracking, and Attribution Technology

Cross-check with the Privacy Policy factual posture:

- No general production cookie/tracking stack was evidenced for analytics or advertising in the reviewed consumer product state.
- No advertising or analytics cookies were found.
- No tracking pixels were found.
- No Google Analytics / Google Tag Manager integration was found.
- Authentication is currently Bearer-token based rather than cookie-session based.

This disclosure does **not** claim active cookie-based advertising tracking by PiqSavi.

### Affiliate-provider tracking after outbound links

If and when production affiliate programs are approved, affiliate providers or merchants may use their **own** tracking mechanisms after a user follows an outbound link. Those mechanisms are subject to the provider’s or merchant’s own terms and privacy notices.

This draft does **not** claim a particular cookie duration, attribution window, or tracking technology unless provider-specific evidence supports it.

[COUNSEL / PROVIDER REVIEW REQUIRED: attribution technology and required consumer disclosure for each approved affiliate provider]

[COUNSEL TO CONFIRM: cookie/consent implications in PH / US / SG / UK / CA]

For privacy-processing detail, see the **PiqSavi Privacy Policy** (counsel draft; not treated here as a published final policy).

---

## 9. Third-Party Merchants and Affiliate Programs

Affiliate programs and merchants are **third parties**.

PiqSavi does **not**, by virtue of affiliate foundations or future affiliate participation, own or control:

- merchant pricing;
- inventory;
- checkout;
- payment;
- shipping;
- returns; or
- warranties,

except where a future counsel-approved product change expressly states otherwise.

Participation in an affiliate program (if and when approved) does **not** certify merchant quality, product suitability, or that every offer is the best available option.

[COUNSEL TO CONFIRM: required merchant/program disclaimer]

---

## 10. User Cost and Price

PiqSavi does **not** intentionally alter a merchant’s listed price in order to increase affiliate compensation.

Where a purchase occurs with a third-party merchant, the **final price remains controlled by the relevant merchant** (and applicable taxes, shipping, fees, or promotions on that merchant’s service), where applicable.

This draft does **not** make a universal claim that affiliate participation can never affect price in every possible provider arrangement. Provider-specific terms may differ and require counsel/provider review before stronger wording is used.

[COUNSEL TO CONFIRM: final price-impact wording]

---

## 11. Commission and Compensation

If PiqSavi earns affiliate compensation in the future under an approved program, the amount and terms may differ by program and may change over time.

This draft does **not** specify:

- a percentage;
- a fixed amount;
- a commission tier;
- payout timing;
- a qualifying-purchase definition; or
- a cookie / attribution window,

unless and until provider-specific evidence and counsel review support disclosing those details.

[COUNSEL TO CONFIRM: whether specific commission disclosures are required]

---

## 12. Editorial and Recommendation Independence

Monetization should not determine canonical **PiqScore** or **organic Recommendation** order.

More precisely:

- **PiqScore** objective scoring stays independent of commission.
- **Organic Recommendation ranking** stays independent of commission.
- A separate future sponsored surface, if introduced, must be **visibly labeled** and distinguishable from organic results.

This draft does **not** claim that PiqSavi has no commercial relationships at all. It claims ranking neutrality for objective scoring and organic recommendations under current product architecture rules, while allowing clearly labeled future commercial surfaces subject to counsel review.

[COUNSEL TO CONFIRM: editorial-independence wording for consumer publication]

---

## 13. AI and Affiliate Monetization

Based on the current product architecture reviewed for this draft:

- AI explanations are **not** designed to rewrite canonical PiqScore.
- AI should **not** be described as secretly optimizing recommendations for affiliate payout.
- Affiliate compensation must not increase objective PiqScore or organic Recommendation ranking.

If future sponsored commercial content is surfaced through AI or conversational interfaces, that path requires **explicit counsel review and labeling** before presentation as a consumer commercial surface.

[COUNSEL TO CONFIRM: AI-specific disclosure requirements for sponsored or affiliate-influenced content]

---

## 14. Merchant Availability and Market Coverage

Provider and program availability can vary by:

- country / market;
- merchant;
- product or category;
- account status;
- contractual approval; and
- capability permission.

This draft does **not** imply that:

- all merchants participate;
- all markets are covered;
- all providers are available in the Philippines (or any other market);
- all merchants have affiliate programs; or
- a provider available in one market is approved globally.

Unknown or uncertified capability fails closed. Live certified merchant integrations for intended markets (including PH / US / SG / UK / CA planning markets) are **not** current production claims while EXT-01…05 remain `not_started`.

[COUNSEL TO CONFIRM: market-coverage disclaimer wording]

---

## 15. Link Destination and Transaction

An outbound link from PiqSavi may take you to a third-party merchant or service.

Where a purchase is available, the merchant (or other third party) generally controls the purchase transaction. PiqSavi does **not** currently claim to be the seller-of-record for those third-party product purchases.

Based on the architecture reviewed for this draft, PiqSavi does **not** currently claim to operate PiqSavi checkout/payment for third-party retail purchases.

Cross-reference: **PiqSavi Terms of Service** (counsel draft) for merchant-intermediary, purchase, returns, and related consumer wording.

[COUNSEL TO CONFIRM: final merchant-intermediary wording]

---

## 16. Identifying Affiliate Links

PiqSavi may need to identify affiliate links or affiliate-related monetization to users. Possible example labels (illustrative only; **not** selected as final wording) include:

- “Affiliate link”
- “PiqSavi may earn a commission”
- “We may earn from qualifying purchases”

Final wording, prominence, proximity, and frequency are **not** decided in this draft. Provider terms may also impose their own mandatory wording.

[COUNSEL TO CONFIRM: required label wording, prominence, proximity, frequency, and platform-specific requirements]

---

## 17. Disclosure Placement

A footer-only disclosure is **not** assumed to be legally sufficient.

Potential placement surfaces for counsel review may include:

- near recommendation results;
- before an outbound merchant action;
- on merchant / offers pages;
- a persistent disclosure page;
- conversational AI results where relevant; and
- social / media / promotional content where relevant.

[COUNSEL TO CONFIRM: required disclosure placement and conspicuousness]

---

## 18. Social, Creator, and Media Disclosures (Future)

PiqSavi Studios and related promotional content may eventually promote products or offers. If and when such practices are used, counsel should review disclosure standards for:

- social posts;
- short-form videos;
- creator / influencer campaigns;
- affiliate links in captions or descriptions;
- sponsored content; and
- gifted or promotional products.

This draft does **not** state that these practices are currently active production marketing programs.

[COUNSEL TO CONFIRM: social media / creator endorsement disclosure standards by target market/platform]

---

## 19. Subscriptions and Other Paid PiqSavi Services (Future)

If PiqSavi later offers paid subscriptions or other paid PiqSavi services, those offerings should be disclosed separately and clearly distinguished from:

- affiliate compensation from third-party merchants/programs;
- sponsored placements; and
- third-party advertising.

This draft does **not** describe current PiqSavi retail checkout/payment or consumer subscription billing as active production capabilities.

[COUNSEL TO CONFIRM: wording if future paid PiqSavi subscriptions or services are introduced]

---

## 20. Changes to This Disclosure

Monetization methods may evolve as the service, partners, and applicable laws change. When this disclosure is updated, the “Last Updated” date (and Effective Date if applicable) should be revised.

This draft does **not** promise a particular notice period.

[COUNSEL TO CONFIRM: when disclosure updates require user notice]

---

## 21. Contact

**General support:** support@piqsavi.com

**Privacy / tracking:** privacy@piqsavi.com

**Legal operator / entity:**
[COUNSEL TO CONFIRM]

**Legal / business address:**
[COUNSEL TO CONFIRM]

Do not publish a founder home address unless counsel expressly approves that disclosure.

Related counsel drafts (not treated here as published final policies):

- **PiqSavi Privacy Policy**
- **PiqSavi Terms of Service**

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

This appendix is **internal only**. It must not appear in any future public Affiliate & Advertising Disclosure.

These are questions and placeholders only. **No privileged legal advice** is provided or recorded here.

## Unresolved issues (minimum set)

1. **Legal operator / entity**
   Placeholder: `[COUNSEL TO CONFIRM: legal operator/entity name]`

2. **Effective Date**
   Placeholder: `[COUNSEL TO CONFIRM]`

3. **Required affiliate disclosure wording**
   Placeholder: `[COUNSEL TO CONFIRM: final consumer-facing affiliate explanation]`
   Placeholder: `[COUNSEL TO CONFIRM: required label wording, prominence, proximity, frequency, and platform-specific requirements]`

4. **Disclosure placement / proximity / conspicuousness**
   Placeholder: `[COUNSEL TO CONFIRM: required disclosure placement and conspicuousness]`

5. **Provider-specific mandatory statements**
   Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: attribution technology and required consumer disclosure for each approved affiliate provider]`

6. **Commission disclosure requirements**
   Placeholder: `[COUNSEL TO CONFIRM: whether specific commission disclosures are required]`

7. **Price-impact wording**
   Placeholder: `[COUNSEL TO CONFIRM: final price-impact wording]`

8. **Sponsored placement labeling**
   Placeholder: `[COUNSEL TO CONFIRM: labeling requirements for sponsored results / paid placements by market]`

9. **Ad disclosure requirements**
   Placeholder: `[COUNSEL TO CONFIRM: advertising disclosure requirements]`

10. **Behavioral / targeted advertising**
    Placeholder: `[COUNSEL TO CONFIRM: whether behavioral/targeted advertising requires additional consent or opt-out mechanisms by market]`

11. **Cookies / tracking consent**
    Placeholder: `[COUNSEL TO CONFIRM: cookie/consent implications in PH / US / SG / UK / CA]`

12. **Provider attribution mechanisms**
    Placeholder: `[COUNSEL / PROVIDER REVIEW REQUIRED: attribution technology and required consumer disclosure for each approved affiliate provider]`

13. **PH requirements**
    Placeholder: `[COUNSEL TO CONFIRM: PH affiliate / advertising / endorsement disclosure requirements]`

14. **US endorsement / affiliate requirements**
    Placeholder: `[COUNSEL TO CONFIRM: US endorsement / affiliate disclosure requirements]`

15. **SG requirements**
    Placeholder: `[COUNSEL TO CONFIRM: SG affiliate / advertising disclosure requirements]`

16. **UK affiliate / advertising requirements**
    Placeholder: `[COUNSEL TO CONFIRM: UK affiliate / advertising disclosure requirements]`

17. **CA requirements**
    Placeholder: `[COUNSEL TO CONFIRM: CA affiliate / advertising disclosure requirements]`

18. **AI / conversational affiliate disclosures**
    Placeholder: `[COUNSEL TO CONFIRM: AI-specific disclosure requirements for sponsored or affiliate-influenced content]`

19. **Social media / creator disclosures**
    Placeholder: `[COUNSEL TO CONFIRM: social media / creator endorsement disclosure standards by target market/platform]`

20. **Merchant-program restrictions**
    Placeholder: `[COUNSEL TO CONFIRM: required merchant/program disclaimer]`
    Related: do not invent merchant rights; EXT-01…05 remain `not_started`.

21. **Difference between affiliate permission and product-data permission**
    Preserve throughout: affiliate permission ≠ product-data permission; technical capability ≠ contractual permission; unknown capability fails closed.

22. **Production-provider certification requirements**
    Related EXT chain: EXT-01…05 (access) → approval/provisioning → EXT-06 (credentials) → EXT-07 (tracking IDs) → contractual capability certification → production-certified market. None of EXT-01…05 or EXT-07 are advanced by this document.

23. **Recordkeeping / evidence requirements**
    Placeholder: `[COUNSEL TO CONFIRM: recordkeeping and evidence retention for affiliate / advertising disclosures]`

24. **Disclosure-update requirements**
    Placeholder: `[COUNSEL TO CONFIRM: when disclosure updates require user notice]`

## Additional open items

- Whether the first published consumer disclosure should be affiliate-only or include advertising/sponsored/subscription categories now: `[COUNSEL TO CONFIRM: whether all five categories must appear in the first published consumer disclosure, or whether a narrower affiliate-only disclosure should ship first]`
- Demo/fixture vs live-program consumer wording: `[COUNSEL TO CONFIRM: how to describe demo/fixture affiliate foundations vs future live programs in consumer-facing copy]`
- Ranking-neutrality consumer wording: `[COUNSEL TO CONFIRM: consumer-facing ranking-neutrality wording and whether additional examples are required]`
- Editorial-independence wording: `[COUNSEL TO CONFIRM: editorial-independence wording for consumer publication]`
- Market-coverage disclaimer: `[COUNSEL TO CONFIRM: market-coverage disclaimer wording]`
- Merchant-intermediary wording consistency with Terms: `[COUNSEL TO CONFIRM: final merchant-intermediary wording]`
- Future paid PiqSavi subscriptions wording: `[COUNSEL TO CONFIRM: wording if future paid PiqSavi subscriptions or services are introduced]`
- Legal / business address: `[COUNSEL TO CONFIRM]` (do not publish founder home address)

## Explicit non-claims for this drafting exercise

- Not legal advice
- Not legally approved
- Not for publication
- Not evidence of legal approval
- Not evidence of affiliate-program approval
- Not evidence of merchant-data permission
- Not evidence of EXT completion (including EXT-01…05, EXT-07, EXT-20, EXT-21)
- Not evidence of public monetization launch
- Does not claim approved Shopee / Lazada / TikTok Shop / Amazon / Temu affiliate status
- Does not invent provider tracking IDs, fixed commissions, fixed attribution windows, live merchant/data API permission, universal market permission, live sponsored results, current display/programmatic advertising, advertising cookies/pixels currently active, or PiqSavi checkout/payment
- Does not claim affiliate revenue affects PiqScore or organic Recommendation ranking
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
| Primary fact sources | `docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md`; `docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md`; `docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md` |
| Drafting branch | `docs/piqsavi-affiliate-advertising-disclosure-counsel-draft` |
| Authoritative main at drafting | `8dbf2064778d883f56bda2de31b6ea228f5fba46` |
| Sprint 26 | OPEN (unchanged) |
| Sprint 27 | NOT STARTED (unchanged) |
| Sprint 28 | NOT STARTED (unchanged) |
| EXT-01…05 | `not_started` (unchanged) |
| EXT-07 | `not_started` (unchanged) |
| EXT-19 | `applied` (unchanged; written approval not claimed) |
| EXT-20 / EXT-21 | `not_started` (unchanged) |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |

**End of PiqSavi Affiliate & Advertising Disclosure — Counsel Draft.**
