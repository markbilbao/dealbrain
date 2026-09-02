# Shopee — Affiliate Onboarding Active / Open API Access Pending

**Document type:** Authoritative Sprint 26 merchant-specific evidence record (sanitized; non-secret)  
**Merchant / program:** Shopee  
**Sprint status:** **SPRINT 26 — SHOPEE EVIDENCE UPDATED / EXTERNAL ACCESS STILL PENDING**  
**Date recorded:** 2026-09-02  
**Baseline:** created from official `main` `ae316e6010edeca713148988580809212e72b22a` (PR #99 merge). This file was **not** merged from unmerged branch `ops/sprint-26-shopee-application-prep` (`5dcf9ba`).  
**Counsel gate:** Cleared to apply — signed record **2026-08-25** ([`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md))  
**Shared preparation:** [`SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)

**This file answers:** What Shopee access does PiqSavi actually have today? What has been submitted? What is still pending? What program/API exists? What rights have **not** been granted? What still blocks Sprint 32 certification?

**This file is not:** merchant legal approval, Affiliate Open API authorization, credentials, production certification, or a public “Shopee supported” claim.

**Sprint boundary:** Sprint 26 owns merchant/program applications, merchant responses, access evidence, credentials-status evidence, program/API-access evidence, and truthful submission/progress records. Sprint 32 owns Philippines production certification and remains **in progress / blocked on external certification**. This reconciliation does **not** close Sprint 26 or Sprint 32 and does **not** start Sprint 33.

---

## Identifier Namespace Warning

Operational work is identified as the **Shopee** merchant/program. Counsel-form row label “EXT-01” on the signed counsel PDF is historical only and does **not** redefine register EXT-01.

| Token | Authoritative meaning |
|-------|------------------------|
| Register EXT-01 | Philippines **market** row |
| Register EXT-02 | United States market |
| Register EXT-03 | Singapore market |
| Register EXT-04 | United Kingdom market |
| Register EXT-05 | Canada market |
| Counsel-form “EXT-01” | Shopee **merchant-row label** on the signed PDF only |

Do **not** use `EXT-01 = Shopee`.

---

## Evidence classification

| Class | Meaning |
|-------|---------|
| **Repository / counsel evidence** | Facts already supported by merged repository evidence (counsel clearance, register, preparation). |
| **Owner-verified operational observation** | Facts personally observed by the owner in the authenticated Shopee interface or official Shopee documentation during onboarding/research. These require repository reconciliation. They are **not** merchant legal conclusions. |
| **Not yet established** | Access, approval, or rights still unknown. Unknown stays **UNKNOWN**. |

Owner-verified operational observation ≠ merchant legal approval ≠ contractual-use evidence ≠ production certification.

Public documentation existence / technical capability evidence ≠ PiqSavi authorization / contractual-use evidence.

---

## Current truthful status

| Area | State | Classification |
|------|-------|----------------|
| Counsel-cleared to apply | **Yes** (2026-08-25; conditions N/A; no hold) | Repository / counsel |
| Affiliate dashboard access | **Yes** — owner can access the Shopee Affiliate environment | Owner-verified operational observation |
| Payment & Tax onboarding | **Submitted; review pending** | Owner-verified operational observation |
| Full affiliate account approval | **Not assumed** | Not yet established |
| Affiliate Open API program exists | **Yes** — documented GraphQL Affiliate Open API | Owner-verified operational observation (documentation existence) |
| `productOfferV2` documented | **Yes** — product-level offer discovery is documented | Documentation existence / technical capability |
| Item-feed APIs documented | **Yes** — `listItemFeeds` / `getItemFeedData` documented | Documentation existence / technical capability |
| Affiliate Open API access granted to PiqSavi | **No** | Owner-verified operational observation |
| AppID | **None** | Owner-verified operational observation |
| Secret | **None** — none stored; none claimed | Owner-verified operational observation |
| Affiliate Open API usable by PiqSavi | **No** | Owner-verified operational observation |
| Product-data permission | **UNKNOWN / not established** | Not yet established |
| Display / cache / AI / comparison / production-API rights | **UNKNOWN** | Not yet established |
| Seller / ISV Open Platform | **Held; not submitted** | Repository / counsel + owner-verified observation |
| Production provider | **None** | Repository / counsel |
| Production certification | **None** | Repository / counsel |
| Public support claim | **Forbidden** | Repository / counsel |

Do **not** collapse these into one “Shopee application submitted” or “Shopee approved” state.

---

# SHOPEE — AFFILIATE ONBOARDING ACTIVE / OPEN API ACCESS PENDING

---

## 1. Counsel clearance

**Classification:** Repository / counsel evidence

Shopee merchant/program **application** is counsel-cleared to proceed (signed record 2026-08-25; Pauline Anne Sambuang; conditions/exceptions N/A; no hold).

Counsel clearance to apply ≠ merchant approval ≠ affiliate permission ≠ product-data/API permission ≠ credentials ≠ production authorization.

The 2026-08-25 counsel snapshot recorded Shopee application submitted = **No**. This later operational record does **not** rewrite that historical counsel snapshot. It records subsequent owner-observed onboarding facts as separate fields below.

---

## 2. Affiliate dashboard / account access

**Classification:** Owner-verified operational observation

The owner has authenticated access to the **Shopee Affiliate dashboard**.

This establishes **only** that the owner can access the Shopee Affiliate environment.

It does **not** establish:

- Affiliate Open API approval
- production API rights
- product-data rights
- certification
- credentials
- full affiliate account approval
- that a generic “Shopee merchant API application” was submitted

Market coverage of the accessed affiliate account (whether it is Philippines-only, multi-market, or otherwise) is **not yet established**. Philippines remains the launch focus. Confirming that a given Shopee program/account covers the Philippines remains **OWNER INPUT REQUIRED** / **MERCHANT CONFIRMATION REQUIRED**. Dashboard access does not automatically assign register EXT-01.

---

## 3. Payment & Tax

**Classification:** Owner-verified operational observation

Shopee Affiliate **Payment & Tax** onboarding has been **submitted; review pending**.

Recorded wording:

> Payment & Tax onboarding submitted; review pending.

This is **not**:

- Affiliate Open API approved
- merchant API approved
- full affiliate account approved
- production data permission granted

No tax ID, bank details, address, or other payout KYC values are stored in this repository.

---

## 4. Shopee Affiliate Open API — program existence vs PiqSavi access

**Shopee Affiliate Open API ≠ Shopee Seller/ISV Open Platform.** Do not collapse these.

### 4.1 Documentation existence / technical capability

**Classification:** Owner-verified operational observation of official Shopee Affiliate Open API documentation

The program exists. Official documentation describes a **GraphQL** Affiliate Open API.

That is documentation-existence / technical-capability evidence only.

### 4.2 PiqSavi authorization / contractual-use evidence

**Classification:** Owner-verified operational observation + not yet established

| Field | State |
|-------|-------|
| Affiliate Open API access granted | **No** |
| AppID | **None** |
| Secret | **None** |
| Interface indication | Access is unavailable / requires an access request or contact with Shopee |
| PiqSavi authorization / contractual-use evidence | **Absent** |
| Live calls / tested access | **None** — this task made no API calls |

# SHOPEE AFFILIATE OPEN API IS NOT YET USABLE BY PIQSAVI

Public documentation ≠ PiqSavi access.

---

## 5. Documented `productOfferV2` capability

**Classification:** Documentation existence / technical capability evidence  
**Not:** PiqSavi authorization / contractual-use evidence

Owner-observed official documentation shows query `productOfferV2`.

Documented filtering/search inputs include concepts such as:

- `shopId`
- `itemId`
- `productCatId`
- `keyword`
- sort controls
- paging
- seller/offer filters

Documented output fields include concepts such as:

- item ID
- product name
- shop ID
- shop name
- shop type
- `priceMin`
- `priceMax`
- category IDs
- rating
- sales
- discount rate
- image URL
- product link
- affiliate offer link
- offer period
- commission fields

This indicates the Affiliate Open API can provide **product-level offer discovery**, not merely a curated affiliate banner/feed.

PiqSavi cannot call `productOfferV2` today.

### Price-field semantics (documented only)

Documented fields include `priceMin`, `priceMax`, and discount rate.

Do **not** interpret those as:

- final effective cost
- selected-variant exact price
- shipping-inclusive cost
- landed cost
- checkout amount

Record only documented field availability. Sprint 37+ economics/truthfulness rules remain separate.

### Commission fields (documented only)

The documented API exposes affiliate/commercial fields. Examples may include commission rate, seller commission, Shopee commission, and commission amount.

Record only that such fields exist in the documentation.

**Architecture rule:** Commission must **never** affect certification or buying recommendation. Commission may eventually support downstream affiliate attribution. It must not influence certification, routing, evaluated-set inclusion, PiqScore, Recommendation, or Best Piq for You.

---

## 6. Documented item feeds

**Classification:** Documentation existence / technical capability evidence  
**Not:** PiqSavi authorization / contractual-use evidence

Owner-observed documentation includes:

- `listItemFeeds`
- `getItemFeedData`

Documented concepts include:

- FULL snapshots
- DELTA snapshots
- `datafeedId`
- feed name / reference / description
- total count
- date
- NEW / UPDATE / DELETE semantics
- paging
- maximum page size around 500 records

The returned feed `columns` field was observed as a JSON string whose exact merchant schema is **not yet established**. Do not invent that schema.

Architectural potential only (not implemented in Sprint 26):

- query-time product discovery via `productOfferV2`
- background catalog synchronization via feeds

PiqSavi cannot call these APIs today. Sprint 26 does not implement them.

---

## 7. Documented authentication

**Classification:** Documentation existence / technical capability evidence  
**Not:** PiqSavi credentials or a tested auth path

Owner-observed official documentation describes authorization using an `Authorization` header with SHA256-based signing involving AppId, Timestamp, Payload, and Secret.

Exact documented concept observed:

`SHA256(Credential + Timestamp + Payload + Secret)`

or equivalent official format.

**Security rule:** never put a real secret in Git. Future implementation must keep AppID/Secret server-side. This record stores no credentials, no AppID, and no Secret. None have been issued to PiqSavi.

---

## 8. Documented rate limit

**Classification:** Documentation existence / technical capability evidence  
**Not:** a tested PiqSavi runtime limit

Owner-observed documentation indicates **8000 API calls/hour**.

Recorded wording:

> documented program limit observed in Shopee Affiliate Open API documentation

PiqSavi currently does not have API access to test it.

---

## 9. Rights state

**Classification:** Not yet established

Do not infer rights from affiliate membership, dashboard access, Payment & Tax submission, or public documentation.

| Right | State |
|-------|-------|
| Product-data rights | **UNKNOWN** |
| Public display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| Data-retention rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Product-comparison rights | **UNKNOWN** |
| Production API rights | **UNKNOWN** / **none granted** |
| Affiliate tracking / monetized-redirect rights | **UNKNOWN** — dashboard access is not treated as a production affiliate grant |
| Sandbox rights | **UNKNOWN** |

Unknown remains **UNKNOWN**.

---

## 10. Seller / ISV Open Platform — HOLD

**Classification:** Repository / counsel (prior public-source evaluation) + owner-verified operational observation

Primary Shopee path under evaluation remains **Shopee Affiliate Open API**, subject to merchant access and rights.

The Seller/ISV Open Platform at [https://open.shopee.com/](https://open.shopee.com/) is a **separate** seller/partner API program. Current state:

# HOLD SELLER / ISV OPEN PLATFORM

| Field | State |
|-------|-------|
| Evaluated | **Yes** |
| Submitted | **No** |
| Hold | **Yes** |
| Business-registration dependency | **Unresolved** |

Owner-observed: that application path requires business information such as company/business name, registration information, and registration documentation. PiqSavi does **not** currently have the finalized business registration needed to truthfully complete that route.

Do **not**:

- invent a company registration
- use another company
- submit false information
- treat another person’s/company’s credentials as PiqSavi

Prior public-source evaluation (still valid unless new evidence says otherwise): Open Platform is documented as seller/ISV shop APIs (shop-scoped `shop_id` + access token), not a public marketplace catalog-search API. Public ISV criteria include a registered business, a live product with existing ecommerce integrations, and a trial account. PiqSavi is not applying as a Shopee seller to manage its own shop. Live Terms/Privacy URLs are not yet available (EXT-20/EXT-21 `not_started`).

That hold remains valid.

---

## 11. Application-status distinction

Do not rewrite the old Sprint 26 state `not submitted` into a single `merchant application submitted`.

| Track | Submitted? | Status |
|-------|------------|--------|
| 1. Affiliate dashboard / account access | Access exists (not recorded here as a dated application ID) | Dashboard access **yes** |
| 2. Payment & Tax onboarding | **Yes** | Submitted / pending review |
| 3. Affiliate Open API access | **Not established as submitted** | Access **not granted**; interface indicates a request or Shopee contact is required |
| 4. Seller / ISV Open Platform | **No** | Held |
| 5. Production data rights | **No** | UNKNOWN / none granted |

No Affiliate Open API access-request ID, Seller/ISV application ID, or generic “Shopee merchant API application” ID is recorded.

---

## 12. Register / EXT effect

| Register row | Lifecycle status after this record | What changed |
|--------------|------------------------------------|--------------|
| EXT-01 (Philippines market) | remains `not_started` | Pointer only. Dashboard access, Payment & Tax pending, and Affiliate Open API documentation do **not** satisfy EXT-01 `applied` (market merchant/API or affiliate **access application** with market-row submission evidence). |
| EXT-02…EXT-05 | remain `not_started` | Unchanged. No other-market Shopee assignment is evidenced. |
| EXT-06 | remains `not_started` | Unchanged — credentials still not issued |
| EXT-07 | remains `not_started` | Unchanged — tracking IDs still not issued |
| EXT-19 | remains `applied` (not `approved`) | Unchanged — consumer ToS/Privacy written approval still required |

This record does **not** mark EXT-01, EXT-06, or EXT-07 complete, approved, or provisioned.

---

## 13. Sprint 32 effect

**None in this task.**

Sprint 32 documentary certification records (15 incomplete PH records) are **not** updated here. They still cite official `main` counsel/application-preparation evidence. A later **separate Sprint 32 evidence-refresh** may decide whether any documentary rows should move after this Sprint 26 record is accepted.

Sprint 32 remains **in progress / blocked on external certification**.

Production state remains: certifications = 0; production evidence = 0; providers = 0; routing policies = 0.

---

## 14. Sensitive data

This record does **not** store:

- account email
- password
- tax ID
- bank details
- home/business address
- phone
- OTP
- screenshots containing private information
- session cookies
- AppID / Secret

None of those values were issued as Affiliate Open API credentials in any case.

---

## 15. Explicit non-claims

- PiqSavi does **not** have Shopee Affiliate Open API access.
- PiqSavi does **not** have an AppID or Secret.
- Payment & Tax submitted/pending is **not** Affiliate Open API approval.
- Affiliate dashboard access is **not** production API rights, product-data rights, certification, or credentials.
- Public Affiliate Open API documentation is **not** PiqSavi authorization.
- Documented `productOfferV2` / feed APIs are **not** implemented and were **not** called.
- Documented 8000 calls/hour is **not** a tested PiqSavi runtime limit.
- `priceMin` / `priceMax` / discount rate are **not** final effective / landed / checkout cost.
- Commission fields must **not** affect certification, routing, PiqScore, or Recommendation.
- Seller/ISV Open Platform is **held** and **not submitted**.
- No `ResearchProviderCertification` is created.
- No production provider is activated.
- No public “Shopee supported / live / certified / integrated / API-ready” claim is authorized.
- Sprint 26 is **not** closed.
- Sprint 32 is **not** closed.
- Sprint 33 is **not** started.

---

## 16. Remaining Shopee blockers

1. Payment & Tax review still pending.
2. Affiliate Open API access not granted.
3. No AppID / Secret.
4. Affiliate Open API access request is not recorded as submitted.
5. Product-data, display, caching, retention, AI-transmission, comparison, and production-API rights remain UNKNOWN.
6. Seller/ISV Open Platform remains held (business-registration dependency unresolved).
7. No production provider, credentials, or Sprint 32 certification.

---

## 17. Recommended next owner action

**Request Affiliate Open API access** through the official Shopee Affiliate interface (or contact Shopee Affiliate support if the interface provides only a contact path).

Basis:

- Payment & Tax is already submitted and awaiting merchant review; that track does not require a new submission from this record.
- The owner-observed Affiliate Open API interface indicates access is unavailable and requires an access request or contact with Shopee.
- Sprint 32 remains blocked on a real product-data / API path. Documentation existence does not grant that path.

This repository task does **not** submit that request, contact Shopee, fill forms, or use owner data.

Do not implement connectors, generate signatures, call GraphQL, scrape Shopee, or create fake test credentials.

---

## 18. Prior unmerged Sprint 26 branch (audit note)

Unmerged branch `ops/sprint-26-shopee-application-prep` (`5dcf9ba`, 2026-08-28) contained an earlier preparation file of the same path. It was **not** merged into `main`.

Still useful and retained in condensed form here:

- counsel gate and namespace warning
- Affiliate Program ≠ Seller/ISV Open Platform
- Seller/ISV hold and public-source reasons
- PH affiliate public portal [https://affiliate.shopee.ph/](https://affiliate.shopee.ph/) as the previously identified official PH web route
- public-terms notes that affiliate approval is at Shopee’s discretion and is a limited license to display Affiliate Links, not a catalog API grant

Stale relative to owner-verified 2026-09-02 observations (not copied as current truth):

- single collapsed status `not submitted`
- “recommended to submit now” affiliate-first handoff
- no knowledge of Affiliate Open API / `productOfferV2` / feeds / documented 8000/hour
- “Sprint 32 is not started”
- no dashboard access, no Payment & Tax pending state

---

## 19. Evidence to capture after later real events

Copy a block only after a real event. Leave IDs blank until issued. Store screenshots outside Git if they contain personal data. Never commit passwords, AppID/Secret, tokens, bank, tax, or ID images.

```md
| Field | Value |
|-------|-------|
| Merchant / program | Shopee |
| Track | Payment & Tax / Affiliate Open API access / Seller-ISV / other (specify) |
| Counsel-form row label, if applicable | Historical “EXT-01” on the signed counsel form only — not a register ID |
| Authoritative external-dependency reference, if later assigned | Register market row(s) only after owner-selected market is evidenced (e.g. EXT-01 PH) |
| Date/time | (real only) |
| Official portal / program | |
| Submission / ticket / application ID | (blank until issued) |
| Status shown | submitted / pending / approved / rejected / on hold / access granted / access denied |
| Issued AppID? | yes / no — if yes, store secret outside Git |
| Issued Secret? | yes / no — never Git |
| Product-data / API rights? | yes / no / unknown |
| Affiliate rights? | yes / no / unknown |
| Next action | |
```

Affiliate dashboard access ≠ Payment & Tax approval ≠ Affiliate Open API access ≠ Seller/ISV approval ≠ production certification.
