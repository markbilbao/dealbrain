# PiqSavi Cookie & Tracking Notice

**Status:** DRAFT — COUNSEL REVIEW REQUIRED
**Not for publication**
**Not legal advice**
**Not evidence of legal approval**
**Not evidence that all cookies/tracking technologies described are currently in use**

<!--
INTERNAL FACTUAL BASIS (remove or relocate before any public use):
Primary sources:
  - docs/legal/PIQSAVI_DATA_PROCESSING_PRODUCT_BEHAVIOR_SPEC_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_PRIVACY_POLICY_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_TERMS_OF_SERVICE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md
  - docs/legal/PIQSAVI_AI_RECOMMENDATION_DISCLOSURE_COUNSEL_DRAFT.md
Supporting product / security docs inspected as needed:
  - docs/SECURITY_MODEL.md
  - docs/SESSION_MANAGEMENT.md
  - docs/AFFILIATE_LINK_SERVICE.md
  - docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md
  - docs/roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md
Authoritative main at drafting: 4fb6f46dcbbec32b12f909c95984d214534a6a0d
Fact-spec audit HEAD noted in fact-spec: 7e1adaf01b46ba3029778f0b2eebe70737e1ef56
Internal technical codename: DealBrain (do not use in public-facing notice body)
Internal scoring names: DealScore / PersonalDealScore (public name remains PiqScore)
This draft does not claim EXT-19 written approval, EXT-20/21 publication, EXT-15 analytics
activation, EXT-22 CMP implementation, Sprint 27/28 start, production affiliate-provider
tracking, or legal sufficiency.
Repository re-verification at drafting (current main): no application-code evidence of
document.cookie / localStorage / sessionStorage in consumer UI; no GA/GTM/Meta/TikTok
pixel stack; no CMP/banner; Bearer-token auth; affiliate cookie_days = registry metadata
only; Cloudflare evidenced as domain registrar/control, not as proven proxy cookie setter.
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

## 1. Purpose of This Notice

This Cookie & Tracking Notice is intended to describe, in plain language, how PiqSavi (“PiqSavi,” “we,” “us,” or “our”) may use cookies, similar technologies, local browser storage, analytics, affiliate tracking, or advertising-related technologies in connection with the PiqSavi consumer service marketed as **Your AI Personal Shopper**.

This document is a **counsel draft**. It is not published, not final, and not legal advice. It is **not** evidence of:

- legal approval;
- that a consent-management platform is implemented;
- that analytics or advertising cookies are currently active; or
- that affiliate-provider tracking is currently live in production.

### Currently evidenced vs possible future use

This draft distinguishes:

| Posture | Meaning in this draft |
|---------|------------------------|
| **Currently evidenced** | Behavior or absence supported by repository / product evidence reviewed for this draft |
| **Possible future use** | Planned, contemplated, or provider-dependent technology that is **not** described as currently active |

This is **not** a generic cookie policy that assumes every common tracking technology is active. Technologies are described only where repository evidence supports current use, or clearly labeled as future/possible.

For personal-data handling more broadly, see the **PiqSavi Privacy Policy** (counsel draft; not treated here as a published final policy). For affiliate monetization transparency, see the **PiqSavi Affiliate & Advertising Disclosure** (counsel draft).

---

## 2. What Cookies and Similar Technologies Are

Online services may use several kinds of technologies to operate, remember settings, measure usage, or attribute referrals. These technologies may be used by online services, including PiqSavi where implemented. This section is explanatory and does **not** claim that PiqSavi currently uses each technology.

### Browser cookies

Cookies are small text files that a website or related service may store in a browser. They can help keep a session secure, remember choices, or—where used—support analytics or advertising.

### Local storage

Local storage is browser storage that can persist information on a device beyond a single page load. It is not the same as a cookie, but it can serve overlapping functional purposes where implemented.

### Session storage

Session storage is browser storage that typically lasts for a browsing session (for example, until a tab or window is closed). Where implemented, it may hold temporary interface state.

### Pixels / tags

Pixels or tags are small pieces of code or image requests that can record that a page was viewed or an action occurred. They are often associated with analytics or advertising providers where used.

### SDKs or similar technologies

Software development kits (SDKs) and similar embedded technologies can collect device or usage signals inside apps or web experiences where integrated.

Again: describing these categories does **not** mean each category is currently deployed by PiqSavi.

---

## 3. Current PiqSavi Storage and Session Posture

Based on the product implementation reviewed for this draft:

- Authenticated access uses **bearer/session mechanisms** (a session token presented with requests) rather than a browser cookie-session model as the current authentication transport.
- No general production analytics-cookie stack was evidenced.
- No durable guest cookie or durable guest local-storage identity was evidenced.
- No browser `localStorage` / `sessionStorage` continuity was evidenced in the reviewed consumer experience.
- No consent-management platform or cookie-preference banner was evidenced as implemented.
- No Google Analytics, Google Tag Manager, Meta Pixel, TikTok Pixel, or similar advertising/analytics pixel stack was evidenced as an active production integration.

This draft does **not** state that “PiqSavi uses no cookies.” Hosting, CDN, security, or other infrastructure providers may set technical cookies outside the application itself. Those behaviors require separate infrastructure review before publication.

[COUNSEL / INFRASTRUCTURE REVIEW REQUIRED: identify any production cookies or similar technologies set by hosting/CDN/security providers such as Cloudflare before publication]

---

## 4. Strictly Necessary / Security Technologies

Where technologies are used to operate the service securely, purposes may include:

- authentication and session security;
- fraud or abuse prevention;
- request routing;
- security; and
- maintaining user-requested functionality.

### Currently evidenced (application layer)

| Topic | Current posture |
|-------|-----------------|
| Browser auth-session cookies | Not evidenced as the application auth transport; bearer/session mechanisms are used |
| Named first-party application cookies | No named application cookie inventory evidenced in reviewed consumer UI / application cookie-setting paths |
| CSRF prep token | A CSRF-related token may be issued with auth responses as preparation for a possible future cookie-based transport; cookie-based CSRF middleware is not described as currently wired |
| Security / request controls | Security headers, rate limiting, and related operational controls may process technical request information without requiring browser cookies |

This draft does **not** invent specific cookie names.

[COUNSEL / INFRASTRUCTURE REVIEW REQUIRED: identify any production cookies or similar technologies set by hosting/CDN/security providers such as Cloudflare before publication]

Cloudflare is evidenced in operational materials as domain registrar/control for `piqsavi.com`. This draft does **not** claim that Cloudflare currently sets any particular cookie for PiqSavi visitors, because public DNS/TLS/proxy configuration and production edge behavior were not treated as fully settled application facts at drafting.

---

## 5. Preferences / Functional Storage

Based on the product implementation reviewed for this draft:

- Account preferences, settings, and notification preferences (where used) are stored **server-side** in connection with an authenticated account.
- Browser-side preference cookies or preference local-storage keys were **not** evidenced in the reviewed consumer experience.
- Guest durable preference continuity via cookies or browser storage was **not** evidenced.

Future browser preference storage, if introduced, should be treated as future-facing and may require updated disclosure and consent analysis.

[COUNSEL TO CONFIRM: whether functional/preference storage requires consent or specific disclosure by launch market]

---

## 6. Analytics

Based on the product implementation reviewed for this draft, third-party analytics cookies or pixels are **not** currently represented as an active production capability.

This draft does **not** invent current use of Google Analytics, GA4, Google Tag Manager, Mixpanel, Amplitude, Segment, Hotjar, PostHog, Microsoft Clarity, or other analytics vendors.

Roadmap materials contemplate a future analytics provider and related consent work as **planned / not started** dependencies. Analytics, if enabled later, should be described only after implementation and legal review.

[COUNSEL TO CONFIRM: analytics consent / opt-out requirements before any analytics technology is enabled]

---

## 7. Advertising / Targeting

Cross-reference: **PiqSavi Affiliate & Advertising Disclosure** (counsel draft).

Based on the product implementation reviewed for this draft, third-party targeted or programmatic advertising cookies or pixels are **not** currently represented as an active production capability.

This draft does **not** claim current use of:

- Meta Pixel;
- TikTok Pixel;
- Google Ads remarketing;
- ad retargeting;
- cross-site behavioral advertising; or
- programmatic ad tags.

If advertising or targeting technologies are introduced later, separate legal review, disclosure updates, and any required consent or opt-out mechanisms should be addressed before enablement.

[COUNSEL TO CONFIRM: targeted-advertising consent, opt-out and disclosure requirements by market]

---

## 8. Affiliate Tracking

PiqSavi may in the future use affiliate links containing provider or program tracking information so that a merchant or affiliate program can recognize a referral.

Based on the product implementation reviewed for this draft:

- Affiliate link generation, click-recording, and attribution foundations exist and are **demo/fixture-oriented**.
- Real affiliate-network identifiers, live conversion postbacks, and production payout tracking are **not** currently implemented as live production programs.
- Merchant registry fields such as attribution-window metadata (for example “cookie days” style fields) are **product/registry metadata** in the current evidence base and are **not** evidenced as PiqSavi setting a browser cookie of that duration.
- No first-party affiliate redirect-cookie hop was evidenced as an active browser cookie implementation.

A third-party affiliate or merchant provider may use its **own** cookies or similar technologies after a user follows an eligible outbound link. Those mechanisms are subject to the provider’s or merchant’s own terms and privacy/cookie notices and may be outside PiqSavi’s direct control.

This draft does **not** claim that:

- every link is tracked;
- every click sets a cookie;
- PiqSavi sets the merchant’s cookie;
- any fixed cookie duration applies;
- any provider-specific live tracking behavior is currently approved; or
- any approved affiliate relationship currently exists.

[COUNSEL / PROVIDER REVIEW REQUIRED: actual tracking method, cookie duration, attribution behavior, consent requirements and disclosure wording for each approved affiliate provider]

Cross-reference: **PiqSavi Affiliate & Advertising Disclosure** (counsel draft).

---

## 9. Third-Party Services

Third-party service providers may operate their own technologies subject to their own privacy and cookie practices.

Potential categories may include, where eventually implemented or where infrastructure is used:

| Category | Current-vs-future language (repository-backed) |
|----------|-----------------------------------------------|
| Merchant sites | Future/live merchant destinations may apply their own cookies after outbound navigation |
| Affiliate providers | Future approved programs may apply provider tracking after eligible outbound links |
| Hosting / CDN / security providers | May set technical cookies outside application code; inventory requires infrastructure review |
| AI providers | Optional explanation/narrative paths; live external AI calls disabled by default at current state; not described here as browser cookie trackers |
| Email providers | Transactional email delivery not currently integrated in application code |
| Analytics providers | Planned / not currently represented as active |
| Advertising providers | Not currently represented as active |

This draft does **not** imply that every category currently receives browser tracking data from PiqSavi.

[COUNSEL TO CONFIRM: which third-party technologies must be disclosed now vs only when integrated]

---

## 10. Email Tracking

Current transactional email delivery is **not** yet fully implemented in application code. Preference flags for communications may exist server-side, but real marketing-email send and email open/click tracking are **not** described as active production capabilities in the evidence reviewed for this draft.

This draft does **not** invent marketing-email functionality or claim that email open/click tracking is active.

[COUNSEL / PROVIDER REVIEW REQUIRED: whether production transactional or marketing email will use open/click tracking and what disclosure/consent is required]

---

## 11. Logs vs Cookies

Server and security logs are not necessarily the same as browser cookies.

PiqSavi may record technical information in operational or security logs—for example request path, request/status information, a request identifier, and client IP—without that logging depending on browser cookies.

Logging does **not** mean a cookie was set. Cookie absence also does **not** mean no personal or technical data is processed server-side.

For personal-data handling, see the **PiqSavi Privacy Policy** (counsel draft).

---

## 12. User Choices / Consent

Based on the product implementation reviewed for this draft, PiqSavi does **not** currently provide a cookie preference center or consent banner in the consumer product.

This draft does **not** invent:

- an Accept All button;
- a Reject All button;
- implemented consent categories in a live CMP;
- Global Privacy Control handling;
- a Do Not Sell/Share link;
- browser preference-signal handling as an implemented product control; or
- a consent-withdrawal UI for cookies/tracking.

Current product reality: essential-style operation and account features may function without a published cookie banner because a general non-essential analytics/advertising cookie stack was not evidenced as active. Future non-essential technologies may require consent or other controls depending on market and design.

[COUNSEL TO CONFIRM: whether PiqSavi must implement a consent banner, preference center, opt-out mechanism, Global Privacy Control response or other tracking controls before launch in each target market]

---

## 13. Browser Controls

Most browsers allow users to block or delete cookies and, in some cases, to clear local storage or restrict third-party cookies. Browser settings vary by browser and device.

Browser controls may not prevent all third-party tracking after you leave PiqSavi for a merchant or affiliate destination, and they do not necessarily stop server-side processing that does not rely on cookies.

[COUNSEL TO CONFIRM: whether additional instructions or statutory opt-out methods must be provided]

---

## 14. Do Not Track / Global Privacy Control

This draft does **not** invent current product support for Do Not Track or Global Privacy Control.

[COUNSEL TO CONFIRM: whether and how PiqSavi must respond to browser Do Not Track signals]

[COUNSEL TO CONFIRM: whether and how PiqSavi must recognize Global Privacy Control or similar legally recognized preference signals]

No legal conclusion is stated in this draft about whether response is mandatory in any market.

---

## 15. Data Retention

This draft does **not** invent cookie or tracking retention periods. No final general retention schedule for cookies, browser-storage items, analytics identifiers, affiliate identifiers, or advertising identifiers was found as a published privacy retention policy in the product evidence reviewed for this draft.

Where a technology is not currently active, this draft does **not** fabricate a duration.

[COUNSEL / PROVIDER REVIEW REQUIRED: retention period for each production cookie, browser-storage item, analytics identifier, affiliate identifier and advertising identifier]

---

## 16. Cookie / Tracking Inventory

### INTERNAL / REMOVE OR REPLACE BEFORE PUBLICATION

The following table is for **counsel and implementation planning only**. It is **not** a final public cookie table. Do not publish this inventory as-is.

| Technology / Identifier | Provider | Purpose | Category | First-party / Third-party | Current status | Duration | Data involved | Consent required? | User control | Evidence source | Counsel/provider status |
|-------------------------|----------|---------|----------|---------------------------|----------------|----------|---------------|-------------------|--------------|-----------------|-------------------------|
| Bearer / session token (auth transport) | PiqSavi (application) | Authenticated access | Strictly necessary / security (tentative) | First-party application mechanism (not evidenced as browser cookie) | Evidenced (application) | Session TTL / remember-me TTL (technical expiry; not a privacy retention policy) | Session identifier / token material | [COUNSEL TO CONFIRM] | Logout / session expiry | Security model / session docs; auth service | TO VERIFY for public wording |
| CSRF prep token (auth response field) | PiqSavi (application) | Future CSRF readiness | Strictly necessary / security (tentative) | First-party application field (not evidenced as Set-Cookie) | Evidenced as issued field; cookie CSRF middleware not wired | UNKNOWN / TO VERIFY | Token string | [COUNSEL TO CONFIRM] | UNKNOWN | Security model | TO VERIFY |
| Named first-party application cookies | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NOT FOUND in reviewed app/consumer UI | N/A | N/A | N/A | N/A | Fact-spec §12; consumer UI search | TO VERIFY infra separately |
| `localStorage` / `sessionStorage` keys | PiqSavi consumer UI | Continuity / preferences | Functional (if introduced) | First-party | NOT FOUND in reviewed demo consumer UI | N/A | N/A | N/A | Browser clear | Fact-spec §12; UI search | N/A today |
| Guest ID / anonymous durable identity | PiqSavi | Guest continuity | Functional / analytics (if introduced) | UNKNOWN | NOT FOUND | N/A | N/A | N/A | N/A | Fact-spec guest section | N/A today |
| Account preferences / settings | PiqSavi (server-side) | Functional personalization / settings | Functional | First-party server storage | Evidenced server-side for accounts | NO RETENTION POLICY FOUND | Preference/settings fields | [COUNSEL TO CONFIRM] | Account settings APIs where available | Fact-spec profile/preferences | TO VERIFY |
| Affiliate click/attribution records | PiqSavi (demo/fixture foundations) | Referral attribution foundations | Affiliate / functional (tentative) | First-party server records | Demo/fixture-oriented; not live network program | NO RETENTION POLICY FOUND; registry `cookie_days` ≠ browser cookie | Click/attribution identifiers and related metadata | [COUNSEL TO CONFIRM] | N/A (server records) | Affiliate entities / services; Affiliate Disclosure draft | Provider review for live programs |
| Affiliate URL tracking parameters | PiqSavi demo builder / future providers | Link attribution | Affiliate | First-party URL params; third-party after outbound | Demo templates evidenced; live provider IDs not started | N/A (URL params) | campaign/sub/click-style params in demos | [COUNSEL TO CONFIRM] | User choice not to follow link | Affiliate fixtures / link service | Provider review required |
| Merchant / affiliate-provider cookies after outbound link | Merchant / affiliate provider | Referral attribution on third-party sites | Affiliate / advertising (provider-dependent) | Third-party | Possible future / provider-dependent; not claimed live | UNKNOWN / TO VERIFY per provider | Provider-controlled | [COUNSEL / PROVIDER REVIEW REQUIRED] | Provider + browser controls | Affiliate Disclosure draft | REQUIRED before claims |
| Hosting / CDN / security cookies (e.g. Cloudflare or similar) | UNKNOWN / infrastructure | Security / routing / bot management (possible) | Strictly necessary / security (tentative) | Third-party or first-party via edge | UNKNOWN / TO VERIFY | UNKNOWN | UNKNOWN | [COUNSEL / INFRASTRUCTURE REVIEW REQUIRED] | Browser controls (limited) | Cloudflare evidenced as registrar/control; proxy cookie behavior not proven | REQUIRED before publication |
| Analytics cookies / pixels | Analytics provider (future) | Product analytics | Analytics | Third-party or first-party (design-dependent) | NOT FOUND / planned dependency not started | UNKNOWN | UNKNOWN | [COUNSEL TO CONFIRM] before enablement | Future CMP/controls if required | EXT analytics dependency `not_started` | Not active |
| Advertising / targeting pixels | Ad providers (future) | Advertising / targeting | Advertising/Targeting | Third-party | NOT FOUND / not active | UNKNOWN | UNKNOWN | [COUNSEL TO CONFIRM] before enablement | Future CMP/controls if required | Affiliate & Advertising Disclosure draft | Not active |
| Consent-management platform / banner | CMP vendor or first-party (future) | Consent capture | Consent UX | First-party UI / possible third-party CMP | NOT FOUND / planned dependency not started | N/A | Consent records (future) | N/A (the control itself) | Future preference center | EXT cookie-consent dependency `not_started`; Sprint 28 planned | Not implemented |
| Email open/click tracking | Email provider (future) | Delivery measurement / engagement | Analytics / functional (tentative) | Third-party provider-dependent | NOT FOUND; transactional email not fully integrated | UNKNOWN | Email engagement events | [COUNSEL / PROVIDER REVIEW REQUIRED] | Provider/unsubscribe controls if introduced | Fact-spec email section | Not active |

---

## 17. Future Consent Categories (Planning Only)

If PiqSavi later implements a consent-management approach, counsel may consider categories such as:

- Strictly Necessary
- Functional
- Analytics
- Advertising/Targeting

These categories are **planning labels only**. This draft does **not** state that these categories are currently implemented in a consent-management platform.

[COUNSEL TO CONFIRM: final consent categories and whether category-based consent is legally required]

---

## 18. Children / Minors

This draft does **not** invent a minimum age.

Based on the current product implementation reviewed for related counsel drafts, PiqSavi does **not** currently publish or enforce a coded minimum-age policy, age gate, date-of-birth collection, or parental-consent flow.

[COUNSEL TO CONFIRM: whether tracking technologies require additional controls or restrictions for minors]

Keep this section consistent with the Privacy Policy, Terms of Service, and AI / Recommendation Disclosure counsel drafts.

---

## 19. Market-Specific Review

No legal conclusion is stated as final for any market.

[COUNSEL TO CONFIRM: Philippines cookie/tracking requirements]

[COUNSEL TO CONFIRM: United States state/federal requirements relevant to tracking, sale/share, targeted advertising and preference signals]

[COUNSEL TO CONFIRM: Singapore cookie/tracking requirements]

[COUNSEL TO CONFIRM: United Kingdom PECR / UK GDPR requirements]

[COUNSEL TO CONFIRM: Canada cookie/tracking/privacy requirements]

---

## 20. Changes to This Notice

Tracking technologies may change as PiqSavi evolves. If cookies, analytics, advertising, affiliate tracking, or similar technologies are introduced or materially changed, this notice (and related Privacy / Affiliate disclosures) should be reviewed and updated as appropriate.

This draft does **not** promise a specific notice period.

[COUNSEL TO CONFIRM: when changes require notice, renewed consent, or consent reset]

---

## 21. Contact

**Privacy:** privacy@piqsavi.com

**General support:** support@piqsavi.com

**Operator:**
[COUNSEL TO CONFIRM]

---

## 22. Related Documents

- **PiqSavi Privacy Policy** (counsel draft; not a published final policy)
- **PiqSavi Terms of Service** (counsel draft; not a published final agreement)
- **PiqSavi Affiliate & Advertising Disclosure** (counsel draft)
- **PiqSavi AI / Recommendation Disclosure** (counsel draft)
- **PiqSavi Data Processing & Product Behavior Specification** (internal counsel fact-spec; not a public policy)

---

# INTERNAL COUNSEL REVIEW NOTES — REMOVE BEFORE PUBLICATION

Unresolved issues for counsel / provider / infrastructure review (questions and placeholders only; no privileged advice):

1. **Legal operator/entity** — confirm public operator name; do not publish a founder home address.
2. **Effective date** — confirm before any publication.
3. **Production infrastructure cookie inventory** — complete edge/hosting inventory outside application code.
4. **Cloudflare/CDN/security behavior** — confirm whether proxy/WAF/bot cookies are set in production; do not publish names without evidence.
5. **Authentication/session storage** — confirm public wording for bearer/session transport vs any future cookie-session redesign.
6. **Functional/preference storage** — confirm whether server-side preferences require cookie-notice treatment; confirm any future browser storage.
7. **Analytics implementation** — confirm vendor, events, and enablement gate (roadmap dependency currently not started).
8. **Analytics consent** — confirm consent / opt-out requirements before enablement.
9. **Advertising/targeting implementation** — confirm whether any ad stack will launch; currently not active.
10. **Advertising consent/opt-out** — confirm market-specific consent, opt-out, sale/share, and preference-signal requirements.
11. **Affiliate-provider tracking** — confirm method per approved provider; current foundations are demo/fixture-oriented.
12. **Affiliate cookie/attribution duration** — confirm per provider; do not treat registry metadata as a live browser cookie duration.
13. **Third-party merchant tracking** — confirm disclosure for post-click merchant/provider technologies outside PiqSavi control.
14. **Email open/click tracking** — confirm whether production transactional/marketing email will measure opens/clicks.
15. **CMP/banner requirement** — confirm whether a banner/CMP is required before launch in each target market (dependency currently not started).
16. **Consent categories** — confirm final taxonomy if category-based consent is used.
17. **Preference center** — confirm whether a preference center is required and its scope.
18. **Consent withdrawal** — confirm withdrawal UX and recordkeeping if consent is relied upon.
19. **Do Not Track** — confirm whether and how to respond.
20. **Global Privacy Control** — confirm whether and how to recognize GPC or similar signals.
21. **Retention periods** — confirm retention for each production cookie/storage/analytics/affiliate/advertising identifier.
22. **Minors** — confirm whether tracking requires additional minor-related controls; no coded age gate today.
23. **PH requirements** — Philippines cookie/tracking obligations.
24. **US requirements** — state/federal tracking, sale/share, targeted advertising, preference signals.
25. **SG requirements** — Singapore cookie/tracking obligations.
26. **UK requirements** — PECR / UK GDPR obligations.
27. **CA requirements** — Canada cookie/tracking/privacy obligations.
28. **Change/re-consent requirements** — when notice, renewed consent, or consent reset is required.
29. **Recordkeeping / consent evidence** — what consent evidence must be retained if a CMP is introduced.
30. **Final public cookie inventory/table** — replace the internal planning table with a counsel-approved public inventory only after technologies are actually deployed and verified.

### Unsupported-claim audit (drafting check)

This counsel draft intentionally does **not** claim:

- that PiqSavi currently uses Google Analytics;
- that PiqSavi currently uses GTM;
- that PiqSavi currently uses Meta Pixel;
- that PiqSavi currently uses TikTok Pixel;
- that PiqSavi currently runs programmatic ads;
- that PiqSavi currently runs targeted advertising;
- that a cookie banner currently exists;
- that a consent preference center currently exists;
- that specific affiliate cookies are live;
- a fixed affiliate cookie duration;
- that every merchant link is tracked;
- current email open/click tracking;
- complete GPC support;
- complete Do Not Track support;
- a final cookie retention schedule; or
- a final legal conclusion about consent requirements.

### Cross-document consistency notes

Aligned with Privacy Policy, Terms, Affiliate & Advertising Disclosure, AI / Recommendation Disclosure, and the Data Processing Product Behavior Spec on:

- bearer/session auth (not assumed browser cookie sessions);
- no evidenced durable guest cookie / localStorage continuity;
- no evidenced production analytics/advertising pixel stack;
- affiliate foundations demo/fixture-oriented; provider tracking after outbound links is third-party/future;
- AI providers are not described as browser cookie trackers in this notice;
- logs may include technical request data without being cookies;
- no final retention schedule invented;
- no invented CMP/banner/GPC/DNT product controls;
- no invented minimum age;
- current vs planned functionality kept distinct.
