# PiqSavi Data Processing & Product Behavior Specification

**Status:** DRAFT — COUNSEL INPUT
**Purpose:** Technical and product fact specification for legal drafting/review
**Not legal advice**
**Not a published policy**
**Not evidence of legal approval**

| Field | Value |
|-------|-------|
| Public brand | PiqSavi |
| Public tagline | Your AI Personal Shopper |
| Public feature name | PiqScore |
| Internal technical codename | DealBrain |
| Internal scoring names | DealScore / PersonalDealScore |
| Repository | `markbilbao/dealbrain` |
| Authoritative HEAD audited | `7e1adaf01b46ba3029778f0b2eebe70737e1ef56` |
| Branch at audit start | `main` (= `origin/main` = HEAD above) |
| Sprint 26 | OPEN |
| Sprint 27 | NOT STARTED (Planned) |
| EXT-01…05 | `not_started` |
| EXT-19 | `applied` (counsel engagement/schedule evidenced; written approval not claimed) |
| Counsel consultation (schedule evidence) | 2026-08-19 10:00 AM Philippines local time |
| Document type | Repository-backed factual specification only |

**Explicit non-claims:** This document does not draft Terms of Service, Privacy Policy, or any other published legal policy. It does not assert legal compliance, processor/subprocessor status, international-transfer legality, consent sufficiency, or counsel approval. Status labels describe engineering/product state only.

**Related internal prep (not this document):** [`docs/roadmap/evidence/SPRINT_26_COUNSEL_INTAKE_PACKAGE_DRAFT.md`](../roadmap/evidence/SPRINT_26_COUNSEL_INTAKE_PACKAGE_DRAFT.md); [`docs/roadmap/evidence/SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md`](../roadmap/evidence/SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md).

---

## 1. Executive factual summary

PiqSavi (internal DealBrain) is a shopping-intelligence API/platform with a demo static UI. At HEAD `7e1adaf`:

- **Accounts exist:** email + password hash + display name + sessions + profile/preferences can be registered and persisted (memory or PostgreSQL JSON `operational_entities`). Evidence: [`app/domain/entities/user_platform.py`](../../app/domain/entities/user_platform.py), [`docs/AUTHENTICATION.md`](../AUTHENTICATION.md), [`docs/PERSISTENCE.md`](../PERSISTENCE.md).
- **No live merchant marketplace feeds are shipped.** Product/offer search paths use fixture/mock/imported/simulated-live data. Evidence: [`docs/MARKETPLACE_DATA.md`](../MARKETPLACE_DATA.md); connectors under [`app/intelligence/marketplace/`](../../app/intelligence/marketplace/).
- **PiqScore (public) / DealScore (internal) is a deterministic objective score.** AI and affiliate economics do not rewrite it. Evidence: [`docs/architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md); [`app/intelligence/dealscore/engine.py`](../../app/intelligence/dealscore/engine.py).
- **Recommendation (Buy/Wait/Consider/Avoid) is a separate deterministic layer** from DealScore. Evidence: [`app/intelligence/recommendation/engine.py`](../../app/intelligence/recommendation/engine.py).
- **Personalization** may influence a personally recommended choice / Personalized PiqScore without rewriting canonical DealScore. Account prefs are persisted; Sprint 16 “Personal Agent” profiles remain fixture/mock. Evidence: [`docs/PERSONAL_DEALSCORE.md`](../PERSONAL_DEALSCORE.md); [`docs/PERSONAL_AGENT.md`](../PERSONAL_AGENT.md).
- **AI provider adapters exist** (OpenAI / Anthropic / Gemini + deterministic fallbacks) but **live external HTTP is disabled by default** (`DisabledTransport`). Evidence: [`docs/AI_PROVIDER_SETUP.md`](../AI_PROVIDER_SETUP.md); [`app/infrastructure/ai/transports.py`](../../app/infrastructure/ai/transports.py).
- **Affiliate/click/attribution is demo/fixture-oriented**; no browser redirect-cookie hop found; real affiliate network IDs not started (EXT-07). Evidence: [`docs/AFFILIATE_LINK_SERVICE.md`](../AFFILIATE_LINK_SERVICE.md); [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md).
- **Transactional email is not delivered.** `NullEmailSender` / mock notification providers; Resend account EXT-08 `applied` but **not integrated** in app code. Sprint 27 owns delivery. Evidence: [`app/auth/email.py`](../../app/auth/email.py); [`docs/roadmap/sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](../roadmap/sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md).
- **Account deletion, data export, consent records, published ToS/Privacy, cookie-consent, minimum-age policy:** Sprint 28 **PLANNED / NOT IMPLEMENTED** in application code. Evidence: [`docs/roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md).
- **Browser cookies / localStorage / analytics pixels:** **NOT FOUND** in repo consumer UI (`app/static/demo.html`). Auth is Bearer-token based. Evidence: [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md).
- **Support / privacy inboxes provisioned:** `support@piqsavi.com`, `privacy@piqsavi.com` (EXT-17/18). Domain `piqsavi.com` ownership approved (EXT-10); public DNS/TLS for hostname not started (EXT-11/12). Evidence: [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md).

---

## 2. Status legend

Every material finding uses one of:

| Status | Meaning |
|--------|---------|
| **IMPLEMENTED** | Present and wired in current repository behavior |
| **PARTIAL** | Some pieces exist; end-to-end behavior incomplete |
| **FIXTURE / MOCK ONLY** | Demo, fixture, simulated, or placeholder data/path |
| **PLANNED** | Roadmap/sprint intent; not current product behavior |
| **NOT IMPLEMENTED** | Explicitly absent from application behavior |
| **NOT FOUND** | Search found no repository evidence |
| **UNKNOWN** | Cannot be determined from repository alone |
| **NO RETENTION POLICY FOUND** | No coded/configured privacy retention period |
| **EXPIRY ONLY** | Technical TTL/expiry exists; not a privacy retention policy |
| **EXPLICIT RETENTION** | Coded/configured retention period for a data class |

For legal-facing phrasing in downstream drafting:

- Prefer “PiqSavi currently…” only for **IMPLEMENTED**.
- Prefer “PiqSavi is designed/planned to…” for **PLANNED**.
- Do not describe planned behavior as current behavior.

---

## 3. Account / identity data

**Persistence model:** No Prisma schema. Consumer identity lives in domain entities persisted via in-memory adapters or SQLAlchemy JSON rows in `operational_entities` (`store` + `entity_id` + `payload`). Evidence: [`alembic/versions/d4e5f6a7b8c9_sprint23_operational_entities.py`](../../alembic/versions/d4e5f6a7b8c9_sprint23_operational_entities.py); [`app/infrastructure/persistence/stores.py`](../../app/infrastructure/persistence/stores.py); [`docs/PERSISTENCE.md`](../PERSISTENCE.md).

**Auth API (IMPLEMENTED):** `POST /api/v1/auth/register`, `login`, `logout`; `GET /api/v1/auth/me`, `demo`, `meta` — [`app/api/v1/endpoints/auth.py`](../../app/api/v1/endpoints/auth.py).

### 3.1 Consumer `User` fields

Source entity: [`app/domain/entities/user_platform.py`](../../app/domain/entities/user_platform.py) (`class User`).

| Exact name | Purpose | Source | Persistence | Required/optional | Status | Deletion | Export |
|------------|---------|--------|-------------|-------------------|--------|----------|--------|
| `user_id` | Account primary id | Generated (`uuid4`) at register | `user_platform.users` | Required | IMPLEMENTED | NOT FOUND (account-level) | NOT FOUND |
| `email` | Login identity (normalized lower/trim) | Register/login request | same; secondary key = email | Required | IMPLEMENTED | NOT FOUND | NOT FOUND |
| `password_hash` | Credential storage (PBKDF2-HMAC-SHA256) | Derived from password at register | same; excluded from public `to_dict()` by default | Required | IMPLEMENTED | NOT FOUND | NOT FOUND |
| `display_name` | Display name | Register / profile update | users + mirrored on `UserProfile` | Required at register | IMPLEMENTED | NOT FOUND | NOT FOUND |
| `is_active` | Soft disable flag | Default `True` | users | Optional (default True) | IMPLEMENTED (flag); deactivate API NOT FOUND | NOT FOUND | NOT FOUND |
| `email_verified` | Verification state | Default `False` at register | users | Optional (default False) | PARTIAL — field exists; confirm flow does not set it | NOT FOUND | NOT FOUND |
| `created_at` / `updated_at` | Timestamps | Clock at register/update | users | Optional | IMPLEMENTED | NOT FOUND | NOT FOUND |
| `data_status` | mock/imported/live marker | Default `"mock"` | users | Optional | IMPLEMENTED (marker) | NOT FOUND | NOT FOUND |

**NOT FOUND on consumer User:** first/last name, phone, date of birth, username (separate from `display_name`), timezone, formal ToS/privacy acceptance version fields.

**Password plaintext:** not persisted. Evidence: [`app/auth/password.py`](../../app/auth/password.py); [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md).

### 3.2 Sessions

Entity: `UserSession` in [`app/domain/entities/user_platform.py`](../../app/domain/entities/user_platform.py).

| Exact name | Purpose | Status | Notes |
|------------|---------|--------|-------|
| `session_id` | Session id | IMPLEMENTED | |
| `user_id` | Owner | IMPLEMENTED | |
| `token_hash` | SHA-256 of bearer token | IMPLEMENTED | Raw token returned once; not stored |
| `created_at` / `expires_at` | Lifetime | IMPLEMENTED | Default TTL 3600s; `remember_me` 2_592_000s (30 days) — [`app/auth/service.py`](../../app/auth/service.py) |
| `remember_me` | Longer TTL flag | IMPLEMENTED | |
| `last_seen_at` | Activity refresh | IMPLEMENTED | |
| `user_agent` | Device/browser hint | PARTIAL | Entity supports; login API does not pass HTTP headers |
| `ip_hint` | IP hint | PARTIAL | Same as `user_agent` |
| `csrf_token` | CSRF prep token | IMPLEMENTED (issued) | No cookie CSRF middleware wired — [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md) |
| `revoked` | Revocation | IMPLEMENTED | Logout / expiry |

Auth transport: **Bearer token in Authorization header**, not cookie sessions. Evidence: [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md); [`docs/SESSION_MANAGEMENT.md`](../SESSION_MANAGEMENT.md).

### 3.3 Password-reset / email-verification records

| Item | Status | Evidence |
|------|--------|----------|
| `PasswordResetRequest` create + 1h expiry + hashed token | PARTIAL | [`app/auth/service.py`](../../app/auth/service.py) |
| Confirm reset / set new password HTTP | NOT IMPLEMENTED | No confirm routes in [`app/api/v1/endpoints/auth.py`](../../app/api/v1/endpoints/auth.py); Sprint 27 PLANNED |
| `EmailVerificationRequest` create + 1-day expiry | PARTIAL | Service only |
| Confirm verification / flip `email_verified=True` | NOT IMPLEMENTED | Sprint 27 PLANNED |
| Real email delivery | NOT IMPLEMENTED | `NullEmailSender` — [`app/auth/email.py`](../../app/auth/email.py) |

### 3.4 Profile / settings / saved activity (account-linked)

Bootstrapped at register (`_bootstrap_profile`). Stores under `user_platform.*`. Evidence: [`app/domain/entities/user_platform.py`](../../app/domain/entities/user_platform.py); [`docs/USER_PLATFORM.md`](../USER_PLATFORM.md).

| Data | Status | Deletion/export |
|------|--------|-----------------|
| `UserPreference` (budget, currency default `PHP`, country default `PH`, goals, categories, priority floats, mode flags, screen/colors, `personal_profile_id`) | IMPLEMENTED | Account-level deletion/export NOT FOUND |
| Favorite brands / marketplaces, wishlist, owned products, accessories | IMPLEMENTED | Account-level NOT FOUND |
| `UserSettings` (theme, language default `en`, `ai_mode_preference`, privacy/community dicts) | IMPLEMENTED (service) | NOT FOUND |
| `NotificationPreference` (`email_enabled` default False, `push_enabled` False, deal/price alerts, `newsletter` default False) | IMPLEMENTED at bootstrap | NOT FOUND |
| Saved products / comparisons / searches / recommendation history / recently viewed | IMPLEMENTED | Per-item delete for saved products only (`DELETE .../saved-products/{id}`); full account purge NOT FOUND — [`app/api/v1/endpoints/user.py`](../../app/api/v1/endpoints/user.py) |

### 3.5 Auth audit / security events

`SecurityEvent` via `AuditLogger` — IMPLEMENTED (in-process ring buffer and/or `user_platform.audit_events`). May include **normalized email** in metadata on some rate-limit / login-failure paths. Evidence: [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md); [`app/auth/service.py`](../../app/auth/service.py).

### 3.6 Merchant identity (separate bounded context)

Separate from consumer User Platform: `MerchantAccount` / `MerchantUser` with email, display_name, etc. Evidence: [`app/domain/entities/merchant.py`](../../app/domain/entities/merchant.py). Merchant org `terms_accepted_at` exists for merchant orgs — **not** consumer registration consent.

---

## 4. Guest / non-account data

| Topic | Status | Evidence / notes |
|-------|--------|------------------|
| Durable guest account table | NOT FOUND | |
| Anonymous API access | IMPLEMENTED | Shopping assistant / some watchlist-alert paths allow unauthenticated use; `personalization_mode: "anonymous"` — [`app/services/user_platform_service.py`](../../app/services/user_platform_service.py) |
| Guest ID cookie / anonymous session cookie | NOT FOUND | |
| localStorage / sessionStorage guest continuity | NOT FOUND | [`app/static/demo.html`](../../app/static/demo.html) has no `localStorage`/`sessionStorage`/`document.cookie` usage found |
| Search / comparison / recommendation history for guests (server durable) | NOT IMPLEMENTED as guest account store | Authenticated saved-items are account-linked |
| Sprint 16 Personal Agent fixture profiles (including anonymous demo persona) | FIXTURE / MOCK ONLY | [`app/intelligence/personal/fixtures.py`](../../app/intelligence/personal/fixtures.py); [`app/launch/fixtures.py`](../../app/launch/fixtures.py) |
| Request IP in HTTP structured logs | PARTIAL / IMPLEMENTED in middleware | `request.client.host` — [`app/core/middleware/request_logging.py`](../../app/core/middleware/request_logging.py) |
| User-Agent / IP on sessions for guests | NOT APPLICABLE / NOT FOUND | Sessions are for registered users |
| Guest continuity across devices/browsers | NOT IMPLEMENTED / NOT FOUND | No durable guest identity found; no roadmap sprint owns guest continuity as of this HEAD |
| Attribution for guests | PARTIAL / FIXTURE | Affiliate click body may include optional `user_id` / `session_id` / `country` supplied by client — [`app/domain/entities/affiliate.py`](../../app/domain/entities/affiliate.py) |

---

## 5. Search / product / offer data

| Data category | Classification | Status | Evidence |
|---------------|----------------|--------|----------|
| User search query / SA filters (budget, use cases, profile_id) | USER-PROVIDED | IMPLEMENTED (request input) | Shopping Assistant / DealScore search APIs |
| Marketplace listings (Shopee/Lazada-style connectors) | FIXTURE / MOCK ONLY | FIXTURE / MOCK ONLY | [`app/intelligence/marketplace/`](../../app/intelligence/marketplace/) |
| Sprint 18 sync/offers (`fixture` / `imported` / `live` modes) | FIXTURE / IMPORTED / SIMULATED LIVE | IMPLEMENTED for those modes; **real live HTTP merchants NOT IMPLEMENTED** | [`docs/MARKETPLACE_DATA.md`](../MARKETPLACE_DATA.md); `MockLiveMarketplaceConnector` |
| CSV/JSON imports | IMPORTED | IMPLEMENTED (in-memory import pipeline) | [`docs/DATA_IMPORTS.md`](../DATA_IMPORTS.md) |
| Deal attributes (shipping, warranty, official store, returns) | FIXTURE / DERIVED heuristics | FIXTURE / MOCK ONLY + DERIVED | [`app/intelligence/dealscore/enrichment.py`](../../app/intelligence/dealscore/enrichment.py) |
| Prices, availability, seller rating inputs to DealScore | FIXTURE / DERIVED (from mock/imported offers) | IMPLEMENTED as scoring inputs on available data | [`app/intelligence/dealscore/engine.py`](../../app/intelligence/dealscore/engine.py) |
| Reviews / review summaries | FIXTURE / MOCK / AI-assisted narrative paths | PARTIAL / FIXTURE paths | Review modules + AI adapters (live HTTP off by default) |
| Price history | FIXTURE / MOCK ONLY | FIXTURE / MOCK ONLY | [`app/intelligence/price_history/mock_fixture.py`](../../app/intelligence/price_history/mock_fixture.py) |
| Live merchant coverage (PH/US/SG/UK/CA) | PLANNED | NOT IMPLEMENTED; EXT-01…05 `not_started` | [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md) |
| Canonical DealScore values as durable DB rows | DERIVED (compute-on-read) | NOT IMPLEMENTED as durable score store | Recomputed per request; optional short launch cache |

**Do not claim live merchant coverage in public materials** unless/until EXT certification evidence exists.

---

## 6. PiqScore / DealScore

| Item | Fact | Status |
|------|------|--------|
| Public name | **PiqScore** | Policy IMPLEMENTED — [`docs/roadmap/PIQSAVI_PUBLIC_BRAND_POLICY.md`](../roadmap/PIQSAVI_PUBLIC_BRAND_POLICY.md) |
| Internal / API machine fields | **DealScore** / `deal_score` | IMPLEMENTED |
| Ownership | Sprint 5; `WeightedDealScoreEngine` | IMPLEMENTED — [`app/intelligence/dealscore/engine.py`](../../app/intelligence/dealscore/engine.py) |
| Meaning (architecture) | Objective offer evaluation | Locked — [`docs/architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md) |
| Inputs | Total cost vs peers, seller rating, shipping, availability, official store, warranty months, return days | IMPLEMENTED |
| Deterministic | Yes; engine docs state no LLMs / no live APIs inside scoring | IMPLEMENTED |
| AI changes canonical score? | No | IMPLEMENTED (AI downstream) |
| Personalization changes canonical DealScore? | No | IMPLEMENTED — PersonalDealScore composes separately ([`docs/PERSONAL_DEALSCORE.md`](../PERSONAL_DEALSCORE.md)) |
| Affiliate compensation affects score? | Forbidden by architecture lock | IMPLEMENTED as policy + post-rank attachment |
| Merchant commission affects organic ranking? | Forbidden | IMPLEMENTED as policy |
| Missing/unknown fields | Scoring uses available attributes; enrichment may use mock/heuristic deal attributes | PARTIAL / FIXTURE inputs |
| Historical data used in canonical DealScore? | Price-history fragments forbidden in recommendation explanations; DealScore uses current offer attributes | See recommendation engine guards; durable live history NOT IMPLEMENTED |
| Score persistence | Compute-on-read | NOT IMPLEMENTED as durable score table |
| Recompute | Each evaluate/search call | IMPLEMENTED |
| API | `GET /api/v1/dealscore/search` | IMPLEMENTED |

**PersonalDealScore / Personalized PiqScore (separate, non-canonical):** blends catalog DealScore with preference/budget/brand/ownership/community signals. Does **not** mutate `WeightedDealScoreEngine`. Evidence: [`app/intelligence/personal/scoring_engine.py`](../../app/intelligence/personal/scoring_engine.py).

---

## 7. Recommendation

Architecture meaning: **Recommendation = what the customer should do** (distinct from objective PiqScore). Evidence: [`docs/architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md); counsel intake package [`docs/roadmap/evidence/SPRINT_26_COUNSEL_INTAKE_PACKAGE_DRAFT.md`](../roadmap/evidence/SPRINT_26_COUNSEL_INTAKE_PACKAGE_DRAFT.md).

### 7.1 Organic Buy / Wait / Consider / Avoid (Sprint 6) — IMPLEMENTED

| Item | Fact |
|------|------|
| Engine | `RuleBasedRecommendationEngine` — [`app/intelligence/recommendation/engine.py`](../../app/intelligence/recommendation/engine.py) |
| API | `GET /api/v1/recommendations/search` |
| Inputs | DealScore ranking result (ranks, costs, warnings, market average) |
| Output | `PurchaseDecision` + headline/summary/reasoning/tradeoffs/warnings/confidence/alternatives |
| Can decision differ from “buy the highest PiqScore”? | Yes — top listing may still yield WAIT/CONSIDER/AVOID based on thresholds/tradeoffs/confidence |
| AI role | None in this engine |
| Personalization role | None in Sprint 6 engine |
| Affiliate role | None (must not influence) |
| Explanation vs decision | Both produced; structured reasons; must not invent price history |

### 7.2 Shopping Assistant ranking — IMPLEMENTED (mock catalog)

Primary sort uses intent `match_score`, then data_status, then catalog `deal_score`, etc. Can differ from highest catalog DealScore. Affiliate links attached **after** selection. Evidence: [`app/services/shopping_assistant_service.py`](../../app/services/shopping_assistant_service.py); [`app/intelligence/shopping_assistant/recommendation.py`](../../app/intelligence/shopping_assistant/recommendation.py).

### 7.3 Personal recommendations / Buying Advisor — FIXTURE / MOCK ONLY profiles

Rank/verdict using PersonalDealScore and fixture profiles. Output labeled mock. Evidence: [`docs/BUYING_ADVISOR.md`](../BUYING_ADVISOR.md); [`app/intelligence/personal/recommendation_engine.py`](../../app/intelligence/personal/recommendation_engine.py).

---

## 8. Personalization

Architecture rule: personalization may influence the personally recommended Piq **without rewriting** canonical objective DealScore. Evidence: [`docs/architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md).

| Signal | Status | Persistence | Deletion/export |
|--------|--------|-------------|-----------------|
| Account `UserPreference` (budget, brands via favorites, categories, priorities, country/currency, modes) | IMPLEMENTED | Memory or `operational_entities` | Account-level NOT FOUND (Sprint 28 PLANNED) |
| Favorite brands/marketplaces, wishlist, owned, accessories | IMPLEMENTED | same | NOT FOUND (account-level) |
| Sprint 16 Personal Agent fixture profiles | FIXTURE / MOCK ONLY | Process-local | N/A fixture |
| PreferenceEngine dimensions | IMPLEMENTED (ephemeral compute) | Not a durable preference store itself | N/A |
| Past searches / clicks / purchases as behavioral learning | NOT IMPLEMENTED (called out as limitation in Personal Agent docs) | — | — |
| Recommendation feedback loops | PARTIAL / limited saved recommendation history entities | Account-linked if used | NOT FOUND (account purge) |
| Profile vectors / ML embeddings | NOT FOUND | — | — |
| Inferred preferences beyond explicit prefs | UNKNOWN / NOT FOUND as separate inference store | — | — |

Anonymous callers: `personalization_mode: "anonymous"` — no persisted guest preference profile. Evidence: [`app/services/user_platform_service.py`](../../app/services/user_platform_service.py).

---

## 9. AI / LLM processing

| Topic | Status | Evidence |
|-------|--------|----------|
| Provider adapters present | IMPLEMENTED (code) | OpenAI / Anthropic Claude / Gemini + Deterministic under [`app/infrastructure/ai/`](../../app/infrastructure/ai/) |
| Live external HTTP by default | NOT IMPLEMENTED / disabled | `DisabledTransport`; flags `AI_*_LIVE_HTTP` default false — [`docs/AI_PROVIDER_SETUP.md`](../AI_PROVIDER_SETUP.md); [`app/core/config.py`](../../app/core/config.py) |
| AI used for canonical DealScore? | No | Architecture lock §10 |
| AI used for organic Recommendation decision engine? | No | Sprint 6 deterministic |
| AI used for explanation / review narrative / shopping assistant narrative | IMPLEMENTED as architecture (with deterministic fallback when AI off) | [`docs/AI_SHOPPING_ASSISTANT_V1.md`](../AI_SHOPPING_ASSISTANT_V1.md); [`docs/SHOPPING_ASSISTANT_SAFETY.md`](../SHOPPING_ASSISTANT_SAFETY.md) |
| Data that adapters are designed to send (when transport enabled) | Product/review evidence payloads; shopping structured evidence; secrets stripped in builders | Provider base modules under [`app/infrastructure/ai/`](../../app/infrastructure/ai/) |
| User account PII intentionally sent | NOT FOUND as required fields in scoring; shopping context may include personalization mode / profile-linked signals when authenticated — exact production payload set UNKNOWN until live path enabled and reviewed | Counsel/provider review recommended before enabling live HTTP |
| Conversation persistence | PARTIAL — in-memory TTL (default 1800s); prompts/keys not intended for durable store | [`app/intelligence/shopping_assistant/memory.py`](../../app/intelligence/shopping_assistant/memory.py); config `AI_SHOPPING_CONVERSATION_TTL_SECONDS` |
| Durable AI prompt/response log store | NOT FOUND / NOT IMPLEMENTED | |
| Human-review workflow for AI outputs | NOT FOUND | |
| Provider retention / training use of customer data | UNKNOWN — COUNSEL / PROVIDER REVIEW REQUIRED | Not inferable from repo |

**Production AI claim boundary:** Public tagline “Your AI Personal Shopper” is brand policy ([`docs/roadmap/PIQSAVI_PUBLIC_BRAND_POLICY.md`](../roadmap/PIQSAVI_PUBLIC_BRAND_POLICY.md)). Live provider execution is **not** the default runtime path at this HEAD.

---

## 10. Affiliate / redirect / attribution

Architecture invariant: **Affiliate monetization must never increase organic PiqScore / DealScore / Recommendation ranking.** Attachment is post-selection. Evidence: [`docs/architecture/ARCHITECTURE_LOCK.md`](../architecture/ARCHITECTURE_LOCK.md); [`docs/AFFILIATE_LINK_SERVICE.md`](../AFFILIATE_LINK_SERVICE.md).

| Capability | Status | Stored / notes |
|------------|--------|----------------|
| Demo affiliate link generation | FIXTURE / MOCK ONLY (IMPLEMENTED demo templates) | `DEMO_*` tokens — [`app/affiliate/fixtures.py`](../../app/affiliate/fixtures.py) |
| Click tracking API `POST /api/v1/affiliate/click` | IMPLEMENTED (store) | `AffiliateClick` fields include `click_id`, optional `user_id`/`session_id`, `merchant_id`, `product_id`, `timestamp`, `device`, `country`, `campaign_id`, `source`, `referrer`, conversion/revenue/commission fields, `simulated` — [`app/domain/entities/affiliate.py`](../../app/domain/entities/affiliate.py) |
| Attribution engine | FIXTURE / MOCK ONLY (simulated) | [`app/affiliate/attribution/engine.py`](../../app/affiliate/attribution/engine.py); [`docs/AFFILIATE_ATTRIBUTION.md`](../AFFILIATE_ATTRIBUTION.md) |
| Real network APIs / postbacks / payouts | NOT IMPLEMENTED | [`docs/AFFILIATE_REVENUE_ENGINE.md`](../AFFILIATE_REVENUE_ENGINE.md) |
| First-party redirect endpoint (`/go`, `/r`) | NOT FOUND | |
| HTTP Set-Cookie for affiliate | NOT FOUND | Merchant `cookie_days` is registry metadata only (fixtures 7–30), **not** used to set browser cookies |
| Tracking params on generated URLs | IMPLEMENTED in demo builder | e.g. `campaign_id`, `sub_id`, `click_id` |
| User/account linkage | OPTIONAL client-supplied `user_id` on click body | May be personally identifying if populated |
| Guest linkage | OPTIONAL `session_id` in click body | Not a durable guest cookie system |
| Conversion / commission / revenue fields | FIXTURE / simulated | Labeled/simulated paths |
| Used in DealScore / organic ranking? | Must not; engines must not read affiliate tables | Architecture IMPLEMENTED as policy |
| Exposed to merchants | Merchant analytics may read affiliate aggregates as demo/simulated | [`docs/MERCHANT_ANALYTICS.md`](../MERCHANT_ANALYTICS.md) — demo-labeled |
| Real affiliate IDs (EXT-07) | PLANNED / `not_started` | [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md) |
| Disclosure copy | FIXTURE / MOCK ONLY placeholder | [`docs/AFFILIATE_DISCLOSURE.md`](../AFFILIATE_DISCLOSURE.md) — explicitly not legal advice |
| Retention of clicks | NO RETENTION POLICY FOUND | `cookie_days` ≠ purge job |

---

## 11. Email / communications

| Channel | Status | Evidence |
|---------|--------|----------|
| Identity email architecture (reset/verify message objects) | PARTIAL | [`app/auth/service.py`](../../app/auth/service.py) + `NullEmailSender` |
| Real transactional delivery | NOT IMPLEMENTED | |
| Resend provider selection / account | EXT-08 `applied` (ops); **app integration NOT IMPLEMENTED** | [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md); no `RESEND` in [`app/core/config.py`](../../app/core/config.py) / `.env.example` found |
| SPF/DKIM/DMARC | EXT-09 `applied` = DNS **plan** only; DNS **not** applied/verified | Same register |
| Sprint 27 complete reset/verify + delivery | PLANNED | [`docs/roadmap/sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](../roadmap/sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md) — Status: Planned |
| Notification email | FIXTURE / MOCK ONLY | `MockEmailNotificationProvider`; recipients like `{user_id}@example.invalid` — [`app/notifications/email/provider.py`](../../app/notifications/email/provider.py) |
| Marketing / newsletter send | NOT IMPLEMENTED as real send | Preference flag `newsletter` default False exists |
| Push / SMS | NOT IMPLEMENTED | [`docs/NOTIFICATIONS.md`](../NOTIFICATIONS.md) |
| Support inbox | IMPLEMENTED (ops receiving) | `support@piqsavi.com` EXT-17 `provisioned` |
| Privacy inbox | IMPLEMENTED (ops receiving) | `privacy@piqsavi.com` EXT-18 `provisioned` |
| Unsubscribe product flow | NOT FOUND for marketing | Preference fields exist; no ESP unsubscribe pipeline |
| Open/click email event tracking | NOT FOUND | |

**Do not describe Sprint 27 behavior as implemented.**

---

## 12. Cookies / local storage / tracking

| Item | Status | Exact names |
|------|--------|-------------|
| Auth session cookies | NOT FOUND | Auth is Bearer header — [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md) |
| Other first-party cookies | NOT FOUND in `app/static/demo.html` | — |
| `localStorage` / `sessionStorage` keys | NOT FOUND | — |
| Google Analytics / GTM | NOT FOUND | EXT-15 `not_started` |
| Meta / TikTok / advertising pixels | NOT FOUND | — |
| Affiliate cookies | NOT FOUND (HTTP) | Merchant `cookie_days` metadata only |
| Fingerprinting | NOT FOUND | — |
| Consent manager / cookie banner | NOT FOUND / PLANNED | EXT-22 `not_started`; Sprint 28/39 PLANNED |
| Permissions-Policy (geolocation disabled etc.) | IMPLEMENTED as security header config path | `.env.example` / security headers middleware — not a tracking cookie |

**Cookie list for counsel drafting from current code: empty (none found).** Future cookies would require a new audit after introduction.

---

## 13. Logs / observability

| Mechanism | Status | May contain |
|-----------|--------|-------------|
| Structured HTTP request logs | PARTIAL / IMPLEMENTED when enabled | method, path, status, duration_ms, request_id, **client IP host** — [`app/core/middleware/request_logging.py`](../../app/core/middleware/request_logging.py) |
| Auth/affiliate/merchant event logs | PARTIAL | action path + status + request_id |
| Auth audit store | IMPLEMENTED / PARTIAL durability | event types; **email** possible in metadata on some paths |
| Redaction of secret-looking keys | IMPLEMENTED (policy/helpers) | password/token/api_key/authorization/cookie patterns — [`app/launch/redaction.py`](../../app/launch/redaction.py); [`docs/SECURITY.md`](../SECURITY.md) |
| Rate-limit keys | IMPLEMENTED | IP-based keys — [`app/core/middleware/rate_limiting.py`](../../app/core/middleware/rate_limiting.py) |
| AI prompts/responses in structured logs | NOT FOUND as deliberate logger fields | |
| Search query text in structured logs | NOT FOUND as deliberate logger fields (path may include querystring if callers put it there — UNKNOWN depending on client URL design) | Flag for counsel/ops review of access logs |
| Error-tracking vendor (Sentry etc.) | NOT FOUND / EXT-16 `not_started` | |
| Product analytics provider | NOT FOUND / EXT-15 `not_started` | |

**Flag (fact, not legal conclusion):** IP addresses and occasionally emails may appear in operational/audit logs without a coded privacy retention/purge policy.

---

## 14. Storage / infrastructure

| Store | Technology | Data categories | Persistence | Deletion method | Backup | Encryption at rest | Encryption in transit | Region/location |
|-------|------------|-----------------|-------------|-----------------|--------|--------------------|----------------------|-----------------|
| App DB | PostgreSQL (+ SQLAlchemy/Alembic) | Users, sessions, profiles, saved items, affiliate demo records, merchant ops, marketplace sync ops, etc. | IMPLEMENTED (Sprint 23 adapters) | Per-entity deletes where APIs exist; **account purge NOT FOUND** | PARTIAL — [`docs/BACKUP_RESTORE.md`](../BACKUP_RESTORE.md) (pg_dump/demo; not enterprise DR claim) | UNKNOWN at app layer (cloud disk encryption UNKNOWN unless infra proves) | TLS to public endpoints PLANNED/PARTIAL (staging ACM may be empty/HTTP bootstrap noted in TF vars) | Staging TF default `us-east-1` evidenced — [`infra/terraform/environments/staging/variables.tf`](../../infra/terraform/environments/staging/variables.tf); [`docs/SPRINT_25B4C_STAGING_PROVISIONING_REPORT.md`](../SPRINT_25B4C_STAGING_PROVISIONING_REPORT.md). Production applied region: UNKNOWN if not applied. |
| In-memory adapters | Process memory | Same domain shapes in dev/demo | IMPLEMENTED for non-prod defaults | Process restart | N/A | N/A | N/A | Process host |
| Shopping conversations / some KG/reviews/personal fixtures | Process-local | AI conversations, fixtures | NOT durable by design (yet) — [`docs/PERSISTENCE.md`](../PERSISTENCE.md) | TTL / process end | N/A | N/A | N/A | Process host |
| Secrets | AWS Secrets Manager / SSM (staging/prod path) | App secrets, DB creds | PLANNED/PARTIAL ops | Ops rotation UNKNOWN | UNKNOWN | UNKNOWN (provider feature) | UNKNOWN | Staging region evidence `us-east-1`; production UNKNOWN |
| Object storage | NOT FOUND as primary consumer PII store | — | — | — | — | — | — | — |
| Browser storage | NOT FOUND | — | — | — | — | — | — | Client device |
| Logs | App structured logs / CloudWatch path planned | Ops telemetry | PARTIAL | NO RETENTION POLICY FOUND for PII in app | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN / staging AWS |

**AWS production account resources:** EXT-13 partial TF only; not fully applied. Evidence: [`docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md`](../roadmap/EXTERNAL_DEPENDENCY_REGISTER.md).

---

## 15. Third parties

Neutral label: **THIRD-PARTY SERVICE / ROLE TO BE CONFIRMED BY COUNSEL.** This table does **not** assert legal “processor” or “subprocessor” status.

| Service | Purpose (repo-evidenced) | Data potentially shared | Posture | Contract/status evidence | International-transfer relevance |
|---------|--------------------------|-------------------------|---------|--------------------------|----------------------------------|
| AWS | Hosting (Compose+RDS path), Secrets Manager, SSM, deploy | App DB contents, secrets, logs if CloudWatch used | Staging path evidenced; production EXT-13 partial | Infra under [`infra/terraform/`](../../infra/terraform/); EXT-13 | KNOWN intent us-east-1 for staging default; production applied region UNKNOWN |
| Resend | Chosen transactional email provider | Email addresses + message content **when Sprint 27 integrates** | Account EXT-08 `applied`; **not integrated in app** | EXT-08/09 notes | UNKNOWN until integration + provider terms reviewed |
| Google Workspace / Gmail | Receive support/privacy mail | Inbound message contents to aliases | EXT-17/18 `provisioned` | Register notes | UNKNOWN (Google terms) |
| Cloudflare | Domain registrar for `piqsavi.com` | Domain registration data | EXT-10 `approved`; public DNS/TLS EXT-11/12 `not_started` | Register notes | UNKNOWN |
| OpenAI / Anthropic / Gemini | Optional AI explanation/review | Product/review/shopping evidence payloads **if live HTTP enabled** | Adapters present; live HTTP off by default | [`docs/AI_PROVIDER_SETUP.md`](../AI_PROVIDER_SETUP.md); EXT-25 Unknown | UNKNOWN — COUNSEL / PROVIDER REVIEW REQUIRED |
| GitHub | Source / CI deploy OIDC path | Source code, CI metadata (not end-user PII by default) | Used for engineering | Sprint 25b.2 docs | UNKNOWN |
| Analytics provider | Product analytics | PLANNED | EXT-15 `not_started` | — | UNKNOWN |
| Error-tracking provider | Ops errors | PLANNED | EXT-16 `not_started` | — | UNKNOWN |
| Cookie-consent solution | Consent UX | PLANNED | EXT-22 `not_started` | — | UNKNOWN |
| FX provider | FX rates | PLANNED | EXT-23 `not_started` | — | UNKNOWN |
| Merchant/affiliate platforms (Shopee, Lazada, TikTok Shop, Amazon, Temu shortlist, etc.) | Product data / affiliate | PLANNED; EXT-01…05 `not_started` | No live certified feeds | Merchant counsel worksheet | UNKNOWN |
| Payment providers / App Store / Play | Payments / native apps | `n_a_beta` | Out of beta scope | EXT-26–28 | N/A for beta |
| Legal counsel (Pauline Anne Sambuang) | Review engagement | Engagement materials | EXT-19 `applied` | Schedule 2026-08-19 10:00 PH time; firm affiliation **not** shown in retained evidence | N/A |

---

## 16. Retention

| Data class | Classification | Evidence |
|------------|----------------|----------|
| Accounts / profiles / saved items | NO RETENTION POLICY FOUND | Sprint 28 PLANNED — [`docs/roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md); gap inventory notes missing retention |
| Sessions | EXPIRY ONLY | Default 1h / remember-me 30d — [`app/auth/service.py`](../../app/auth/service.py) |
| Password-reset tokens | EXPIRY ONLY | 1 hour |
| Email-verification tokens | EXPIRY ONLY | 1 day |
| Shopping assistant conversations | EXPIRY ONLY | Default 1800s TTL |
| Launch/performance cache | EXPIRY ONLY | Short TTL (e.g. ~30s default class) — operational, not privacy policy |
| Affiliate clicks / attributions | NO RETENTION POLICY FOUND | `cookie_days` is not a purge job |
| Auth audit events | NO RETENTION POLICY FOUND | Ring buffer / ops store |
| AI provider-side retention | UNKNOWN | Provider terms outside repo |
| Backups | UNKNOWN / PARTIAL ops docs | [`docs/BACKUP_RESTORE.md`](../BACKUP_RESTORE.md) — no coded PII retention period |
| Deleted accounts | NOT APPLICABLE yet | Deletion not implemented |
| Exports | NOT APPLICABLE yet | Export not implemented |

**Never invent days/months/years beyond the technical TTLs above.**

---

## 17. Deletion

| Capability | Status | Evidence |
|------------|--------|----------|
| Consumer delete-account endpoint | NOT FOUND / NOT IMPLEMENTED | Staging proof notes absence — roadmap evidence Sprint 26 |
| Soft delete / anonymization pipeline | NOT FOUND | |
| Hard delete cascading across stores | NOT FOUND | `UserRepository.delete` NOT FOUND |
| Deletion request workflow (ticket-only) | UNKNOWN as ops process; product API NOT FOUND | Privacy inbox exists (EXT-18) for contact |
| Token/session revocation on account delete | NOT IMPLEMENTED (no account delete); logout revoke IMPLEMENTED | |
| Affiliate data handling on account delete | NOT FOUND | |
| Recommendation/history purge on account delete | NOT FOUND | |
| Backup deletion of user data | NOT FOUND / UNKNOWN | |
| Audit/log retention after delete | NOT FOUND | |
| Sprint 28 deletion + propagation checklist | PLANNED | [`docs/roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md`](../roadmap/sprints/SPRINT_28_PRIVACY_LEGAL_CONSENT_DELETION.md) |
| Closest existing delete | `DELETE /api/v1/user/saved-products/{saved_id}` | Per-item only |

---

## 18. Export

| Capability | Status | Evidence |
|------------|--------|----------|
| User data export / DSAR download API | NOT FOUND / NOT IMPLEMENTED | Sprint 28 PLANNED |
| Format / auth / scope | N/A until implemented | |
| Related non-user export | Launch **config** export endpoints exist | [`app/api/v1/endpoints/launch.py`](../../app/api/v1/endpoints/launch.py) — not account PII portability |

---

## 19. User request mechanisms

| Mechanism | Current product/process fact | Status |
|-----------|------------------------------|--------|
| Access request (self-serve) | `GET /api/v1/auth/me` + profile/preferences APIs for authenticated user | PARTIAL (account holder API access; not a formal DSAR package) |
| Correction | Profile/preferences update APIs | PARTIAL |
| Deletion | No product endpoint; privacy contact mailbox provisioned | PLANNED (product) / PARTIAL (contact) |
| Export | No product endpoint | PLANNED |
| Objection / consent withdrawal | No registration consent records; notification prefs exist (`email_enabled`, `newsletter` defaults False) | PARTIAL prefs / NOT IMPLEMENTED consent framework |
| Support escalation | `support@piqsavi.com` monitored | IMPLEMENTED (ops) |
| Privacy contact | `privacy@piqsavi.com`; escalation path to counsel relationship (EXT-19) noted in register | IMPLEMENTED (ops contact) |

This section states product/process facts only — not legal entitlements.

---

## 20. Market / location

| Input | Status | Evidence |
|-------|--------|----------|
| Explicit user preference `country` / `currency` | IMPLEMENTED | Defaults `PH` / `PHP` — [`app/domain/entities/user_platform.py`](../../app/domain/entities/user_platform.py) |
| Shipping destination engine | PLANNED (MarketContext) | Sprint 37 Planned — [`docs/roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md`](../roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md) |
| Browser locale → market | NOT FOUND as market authority | `UserSettings.language` default `en` exists |
| IP/geolocation → market | NOT FOUND | Permissions-Policy disables geolocation in header config path |
| Account country | IMPLEMENTED as preference field | Same as explicit setting |
| Merchant market / allowed_countries on affiliate fixtures | FIXTURE / MOCK ONLY | Affiliate merchant fixtures |
| Named supported markets PH/US/SG/UK/CA | PLANNED; not certified | EXT-01…05 `not_started` |

**Do not claim automatic geolocation.**

---

## 21. Children / age

| Item | Status |
|------|--------|
| Minimum age policy in code/UI | NOT FOUND / NO REPOSITORY POLICY FOUND |
| Age gate | NOT IMPLEMENTED |
| Date of birth field | NOT FOUND |
| Parental consent flow | NOT FOUND |
| Roadmap mention | PLANNED — Sprint 28 “Minimum age policy” |

**Flag for counsel:** adopt and publish an age rule; none is implemented in the product today.

---

## 22. Security facts (repository-backed only)

| Control | Status | Evidence |
|---------|--------|----------|
| Password hashing PBKDF2-HMAC-SHA256 (260k iterations default, per-password salt, `hmac.compare_digest`) | IMPLEMENTED | [`app/auth/password.py`](../../app/auth/password.py); [`docs/SECURITY_MODEL.md`](../SECURITY_MODEL.md) |
| Password policy (min 8, upper+lower+digit) | IMPLEMENTED | AuthService validation |
| Session token hashing (SHA-256); raw token not stored | IMPLEMENTED | [`docs/SESSION_MANAGEMENT.md`](../SESSION_MANAGEMENT.md) |
| Bearer auth (not cookie session) | IMPLEMENTED | SECURITY_MODEL |
| CSRF token issued | PARTIAL (prep only; no cookie CSRF middleware) | SECURITY_MODEL |
| In-process auth rate limiting | IMPLEMENTED (not distributed WAF) | SECURITY_MODEL |
| Security headers middleware (`X-Content-Type-Options`, CSP, HSTS setdefault path) | IMPLEMENTED | [`app/core/middleware/security_headers.py`](../../app/core/middleware/security_headers.py) |
| Production fail-closed validation (secrets/backends; demo reset tokens forbidden in production) | IMPLEMENTED | [`app/core/validation.py`](../../app/core/validation.py) |
| Secrets handling via AWS Secrets Manager (staging/prod path) | PARTIAL / ops | Deploy assemble scripts; EXT-14 `not_started` for production secrets populated |
| MFA / OAuth | NOT IMPLEMENTED (extension points only) | SECURITY_MODEL |
| Audit logging | PARTIAL (demo-scale durability) | SECURITY_MODEL |
| Consumer/merchant identity isolation | IMPLEMENTED as separate bounded contexts | Architecture lock |
| HTTPS/TLS public hostname | NOT IMPLEMENTED for public piqsavi.com (EXT-11/12 `not_started`); staging TLS may be deferred/HTTP bootstrap per TF comments | Register + TF vars |

**Do not claim generic “secure” or “industry standard.”** Document specific controls only.

---

## 23. Current vs future matrix

| Topic | CURRENT IMPLEMENTATION | PUBLIC-BETA TARGET (roadmap) | LATER ROADMAP | UNKNOWN / COUNSEL DECISION |
|-------|------------------------|------------------------------|---------------|----------------------------|
| Public brand PiqSavi / PiqScore naming | Brand policy locked; many machine fields still DealBrain/DealScore | Consumer surfaces become PiqSavi (Sprint 29+) | — | Exact legal entity name on policies |
| Register/login/session | Yes (Bearer) | Hardened + email verify/reset (Sprint 27) | OAuth/MFA later | Session cookie transport? |
| Transactional email | Null/mock only | Resend delivery + DNS auth (27; EXT-08/09) | — | Provider DPA / retention wording |
| Live merchant offers | No (fixture/import/sim) | Certified markets after EXT-01…05 + sprints 32–36 | More markets | Which merchants/disclosures |
| PiqScore / Recommendation / affiliate neutrality | Engines + locks exist on mock data | Same semantics on live data | — | Automated-decision / AI disclosure wording |
| AI live HTTP | Off by default | Optional with deterministic fallback; disclose | Quota EXT-25 | Training/retention disclosures |
| Affiliate monetization | Demo links/clicks | Real IDs EXT-07 after partners | Revenue ops | Advertising/affiliate disclosure text |
| Privacy Policy / ToS publication | Not published (EXT-20/21 `not_started`) | Sprint 28 drafts + counsel; publish by launch control | — | All policy substance |
| Consent / age / cookies | Prefs flags only; no age/cookies | Sprint 28 + EXT-22 | Analytics Sprint 39 | Consent taxonomy; age floor |
| Account deletion / export / retention | Not implemented | Sprint 28 APIs + policy | — | Retention periods; deletion exceptions |
| Support/privacy contacts | Mailboxes provisioned | Published in policies/UI | — | Formal DPO appointment? |
| Analytics / pixels | None found | Consent-gated optional (39) | — | What is “essential” |
| Production public site | Not launched | Sprint 41/45 cutover | Stabilization 46 | Operator disclosures |
| Payments / native apps | Out of beta | — | post-beta EXT-26–28 | — |

---

## 24. Unknowns

Material unknowns that counsel should treat as open facts (not invented here):

1. **Legal operator / contracting entity** name, address, and jurisdiction for PiqSavi (not evidenced as a formal entity block in application code).
2. **Firm affiliation** of engaged counsel beyond the individual name recorded in EXT-19 notes (explicitly not invented in register).
3. **Production AWS region / residency** actually applied (staging default evidenced `us-east-1`; production applied state UNKNOWN).
4. **Encryption-at-rest / backup encryption** guarantees as operated (not fully specified as app-level claims).
5. **AI provider contractual retention, training, and subprocessors** if/when live HTTP is enabled.
6. **Resend contractual retention** and international transfers once integrated.
7. **Google Workspace / Cloudflare / AWS** roles and transfer mechanisms for privacy notices (counsel confirmation).
8. **Whether any non-repo systems** (manual spreadsheets, inbox archives, device backups) store additional user data.
9. **Ops process** for privacy/support ticket handling beyond mailbox reachability.
10. **Access-log querystring contents** in deployed reverse proxies/ALB (outside app middleware guarantees).
11. **Whether demo/staging databases contain real personal data** from testers beyond fixture emails.
12. **International transfer legal mechanism** (none selected in repo).
13. **Minimum age** (none coded).
14. **Retention periods** for accounts, logs, backups, affiliate records (none as privacy policy).
15. **Merchant/affiliate program permissions** for scraping, caching, scoring, AI reuse, attribution (EXT-01…05 not started; merchant counsel worksheet separate).

---

## 25. Counsel questions

Questions only — not answers:

1. What legal entity / operator should be named in Terms of Service and Privacy Policy?
2. Which third-party services must be disclosed now vs only when integrated (AWS, Resend, Google Workspace, Cloudflare, AI providers, future analytics)?
3. Which retention periods should be adopted where the repository has **NO RETENTION POLICY FOUND**?
4. Which technical TTLs (sessions, reset tokens, conversation TTL) should be described as privacy retention vs security expiry?
5. Given **no cookies found** today, what cookie/tracking disclosure is required now vs placeholder for future analytics (EXT-15/22)?
6. How should demo/simulated affiliate attribution and placeholder FTC disclosure be described until real programs exist?
7. What affiliate advertising disclosure is required for post-rank monetized redirects once EXT-07 is live?
8. What AI / automated-decision / recommendation disclosure is appropriate given deterministic scoring + optional LLM explanation + personalization layers?
9. May PersonalDealScore / Personalized PiqScore be described differently from objective PiqScore in consumer notices?
10. What deletion exceptions (security logs, legal holds, backups, affiliate accounting) should exist once Sprint 28 deletion ships?
11. What minimum-age rule should be adopted, and is any age gate required before public beta?
12. Which international-transfer wording is required for staging in `us-east-1` and for any production region?
13. Should `privacy@piqsavi.com` / `support@piqsavi.com` be the sole published contacts, and is a formal DPO appointment required for intended markets?
14. What registration consent / policy-version acceptance records are required before self-serve public registration?
15. How should fixture/mock marketplace data be disclosed so consumers are not misled about live merchant coverage?
16. What consumer-protection disclosures are needed for Buy/Wait/Consider/Avoid style recommendations?
17. What must wait for written counsel approval (EXT-19 `approved`) before publication (EXT-20/21) or launch claims?
18. For merchant shortlist research (Shopee, Lazada, TikTok Shop, Amazon, Temu), which uses require affirmative contractual permission before any live ingestion?

---

## Document control

| Item | Value |
|------|-------|
| Created for | Counsel consultation input (EXT-19 applied; written approval not claimed) |
| Sprint statuses | Sprint 26 OPEN; Sprint 27 NOT STARTED — unchanged by this document |
| EXT statuses | Unchanged by this document |
| Code/schema/tests/infra modified | No (documentation file only) |
| Secrets included | No |
| Legal conclusions included | No |

**End of PiqSavi Data Processing & Product Behavior Specification (Counsel Draft Input).**
