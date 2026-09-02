# Sprint 32 — Philippines Source Certification Inventory

**Document type:** Non-secret certification-evidence inventory  
**Sprint slice:** 32.1 complete; 32.2 complete; 32.3 complete; 32.4 hardening validated. Sprint 32 is **not complete**.  
**Date recorded:** 2026-09-02  
**Baseline:** `d890df24559325bb8d1289b6c2a01b590c9e50ab`  
**Market:** PH  
**Register row:** EXT-01 (Philippines market) remains `not_started`  
**Trusted production certification records:** **zero**

**Related:**

- [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md)
- [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)
- [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md)
- [`SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md)
- [`../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md`](../../runbooks/MERCHANT_PROVIDER_ONBOARDING.md)
- [`../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md`](../../architecture/ADR_SPRINT_31_CONNECTOR_UNIFICATION.md)

**This document does not certify any provider.** Fixtures, mocks, imported samples, and simulations cannot satisfy production certification.

---

## Architecture choice (32.1)

Sprint 32.1 adds a **sibling evidence record**, not new fields on `ResearchProviderCertification`.

| Record | Authority |
|--------|-----------|
| `ResearchProviderCertification` | Trusted operational authorization: exact provider + capability + market + source, plus `status`, `policy`, version, fixture protection |
| `ResearchProviderCertificationEvidence` | Non-secret basis that may later support a certification decision |

Evidence binds to the same exact identity key as certification. Completeness states are only `incomplete` or `recorded`. They are **not** a second certification lifecycle. `ProviderCertificationStatus` and `CapabilityPolicyState` remain the only authorization states.

Invariant:

> Evidence present + no trusted `certified` + `allowed` certification = **not eligible**.

Production catalogs remain empty after 32.1.

### 32.2 trusted decision path

`ResearchProviderCertificationDecisionService` is the only supported way to create a certification from evidence.

Flow: evidence → explicit trusted review → optional `ResearchProviderCertification`.

Evidence registration is not a decision. Providers cannot self-certify. Routing is not written. `recorded` means capture finished, not legal sufficiency. `certified + allowed` is never inferred.

Shopee, Lazada, TikTok Shop, Amazon, and Temu remain **uncertified**. 32.2 does not change merchant evidence states.

### 32.3 documentary merchant records

Exact PH snapshots for `product_discovery`, `offer_discovery`, and `current_pricing` live in `app/research/philippines_certification_evidence.py`. They cite official `main` counsel/application evidence only.

Those records are **incomplete** and are not loaded by `production_research_provider_certification_evidence_catalog()`. Counsel clearance to apply is cited; it does not make product-data evidence decision-ready. Merchant evidence states below are unchanged.

### 32.4 provider-identity binding

Production `certified` writes require an exact registered provider: same `provider_id`, capability, market, and source. Documentary IDs (`ph-shopee`, `ph-lazada`, `ph-tiktok-shop`, `ph-amazon`, `ph-temu`) are candidate identities only. They do not become production identities because evidence exists.

Catalog `register` / `replace` remain trusted infrastructure primitives. `ResearchProviderCertificationDecisionService` is the policy path. Incomplete documentary records have no promotion helper. Official `main` still has no submitted Shopee application; unmerged Sprint 26 / owner-observed dashboard progress remains outside this branch.

---

## Rules

- Unknown stays **UNKNOWN**.
- Counsel clearance to apply ≠ application submitted ≠ merchant approval ≠ API/data rights ≠ credentials ≠ production certification.
- Affiliate permission ≠ product-data permission.
- Shopee Affiliate Open API ≠ Shopee Seller/ISV Open Platform.
- Register EXT-01 is the Philippines **market** row. Counsel-form “EXT-01” is a Shopee **label** only.
- Family-local identifiers (Sprint 4 `marketplace_name`, Sprint 18 `connector_id`, affiliate `merchant_id`) are recorded where they exist. No production Sprint 31 `provider_id` exists.
- Destination-sensitive `shipping` and `taxes_import` remain Sprint 37. They are listed as contemplated and blocked, not certified.
- Commission / payout fields are not inventory authorization facts and must not affect certification or routing.

---

## Shared PH production state

| Field | State |
|-------|-------|
| Sprint 31 production provider registry | empty |
| Sprint 31 production certification catalog | empty |
| Sprint 31 production routing catalog | empty |
| Sprint 32 production evidence catalog | empty |
| EXT-01 / EXT-06 / EXT-07 | `not_started` |
| Public PH support claim | forbidden |

---

## Shopee

**Source identity:** `shopee`  
**Market:** PH  
**Sprint 31 production `provider_id`:** none  
**Family-local IDs:** Sprint 4 `shopee`; Sprint 18 stub `future-shopee-official`; affiliate demo `merchant-shopee-ph`

### Merchant-level facts

| Field | State |
|-------|-------|
| Technical implementation | Mock search (`ShopeeConnector`), mock collection (`MockShopeeCollector`), mock reviews (`MockShopeeReviewCollector`), official stub (`future-shopee-official`), demo affiliate placeholder. No live official adapter. |
| Provider descriptor (Sprint 31 production) | none |
| Counsel / legal review | Counsel-cleared to **apply** (signed record 2026-08-25). Not production authorization. |
| Application state | **not submitted** on official `main` |
| Merchant approval | **no** |
| Product-data / API rights | **UNKNOWN**. Affiliate Open API access is not established as granted. Seller/ISV Open Platform is a separate program and is not established as granted. |
| Credentials | **none**. AppID / Secret absent. |
| Display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Affiliate rights | **UNKNOWN** / not assumed from counsel clearance. Affiliate membership alone cannot satisfy Sprint 32 merchant-data certification. |
| Sandbox rights | **UNKNOWN** |
| Production rights | **none** |
| Certification evidence status | incomplete / none in production catalog |
| Trusted certification status | no record — **not certified** |
| Blocker | No official API access, no credentials, no established data/display/cache/AI rights, no production descriptor or certification |
| Owning sprint | 26 (application) / 32 (PH certification) |

Official `main` supports counsel/application preparation. Do not treat unmerged Sprint 26 branch notes or conversational observations as authoritative application-progress evidence.

### Contemplated capabilities

| Capability | Technical implementation | Sprint 31 descriptor | Certification evidence | Trusted certification | Blocker |
|------------|--------------------------|----------------------|------------------------|-----------------------|---------|
| `product_discovery` | mock search / collection only | none | incomplete | none | no official access or rights |
| `offer_discovery` | mock search / demo affiliate link templates | none | incomplete | none | no official access or rights |
| `current_pricing` | mock prices only; official docs may later expose min/max/discount fields. Those fields are **not** final effective cost, selected-variant price, or landed cost. | none | incomplete | none | no official access or rights |
| `availability` | not implemented as a live official path | none | incomplete | none | rights **UNKNOWN** |
| `promotion_evidence` | mock / not official | none | incomplete | none | rights **UNKNOWN** |
| `review_community_evidence` | mock reviews only | none | incomplete | none | rights **UNKNOWN** |
| `shipping` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |
| `taxes_import` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |

---

## Lazada

**Source identity:** `lazada`  
**Market:** PH  
**Sprint 31 production `provider_id`:** none  
**Family-local IDs:** Sprint 4 `lazada`; Sprint 18 stub `future-lazada-official`; affiliate demo `merchant-lazada-ph`

### Merchant-level facts

| Field | State |
|-------|-------|
| Technical implementation | Mock search, mock collection, mock reviews, official stub, demo affiliate placeholder. No live official adapter. |
| Provider descriptor (Sprint 31 production) | none |
| Counsel / legal review | Counsel-cleared to apply (2026-08-25) |
| Application state | **not submitted** |
| Merchant approval | **no** |
| Product-data / API rights | **UNKNOWN**. Affiliate portal ≠ Open Platform. |
| Credentials | **none** |
| Display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Affiliate rights | **UNKNOWN** |
| Sandbox rights | **UNKNOWN** |
| Production rights | **none** |
| Certification evidence status | incomplete / none in production catalog |
| Trusted certification status | no record — **not certified** |
| Blocker | No application, approval, credentials, rights, or trusted certification |
| Owning sprint | 26 / 32 |

### Contemplated capabilities

| Capability | Technical implementation | Sprint 31 descriptor | Certification evidence | Trusted certification | Blocker |
|------------|--------------------------|----------------------|------------------------|-----------------------|---------|
| `product_discovery` | mock only | none | incomplete | none | no official access or rights |
| `offer_discovery` | mock / demo affiliate templates | none | incomplete | none | no official access or rights |
| `current_pricing` | mock only | none | incomplete | none | no official access or rights |
| `availability` | not implemented as a live official path | none | incomplete | none | rights **UNKNOWN** |
| `review_community_evidence` | mock reviews only | none | incomplete | none | rights **UNKNOWN** |
| `shipping` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |
| `taxes_import` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |

---

## TikTok Shop

**Source identity:** `tiktok_shop`  
**Market:** PH contemplated; demo affiliate is **US**  
**Sprint 31 production `provider_id`:** none  
**Family-local IDs:** Sprint 18 stub `future-tiktok-shop-official`; affiliate demo `merchant-tiktok-shop-us` (`allowed_countries` US/GB/SG — not PH)

### Merchant-level facts

| Field | State |
|-------|-------|
| Technical implementation | Mock reviews only. No PH search/collection connector. Official stub only. |
| Provider descriptor (Sprint 31 production) | none |
| Counsel / legal review | Counsel-cleared to apply (2026-08-25) |
| Application state | **not submitted** |
| Merchant approval | **no** |
| Product-data / API rights | **UNKNOWN**. Creator affiliate ≠ Partner Center ≠ developer API. |
| Credentials | **none** |
| Display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Affiliate rights | **UNKNOWN**. No PH affiliate placeholder. |
| Sandbox rights | **UNKNOWN** |
| Production rights | **none** |
| Certification evidence status | incomplete / none in production catalog |
| Trusted certification status | no record — **not certified** |
| Blocker | No PH research provider, no application, no rights, no certification |
| Owning sprint | 26 / 32 |

### Contemplated capabilities

| Capability | Technical implementation | Sprint 31 descriptor | Certification evidence | Trusted certification | Blocker |
|------------|--------------------------|----------------------|------------------------|-----------------------|---------|
| `product_discovery` | none for PH | none | incomplete | none | no official PH path |
| `offer_discovery` | none for PH | none | incomplete | none | no official PH path |
| `current_pricing` | none for PH | none | incomplete | none | no official PH path |
| `review_community_evidence` | mock reviews only | none | incomplete | none | rights **UNKNOWN** |
| `shipping` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |
| `taxes_import` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |

---

## Amazon

**Source identity:** `amazon`  
**Market:** PH contemplated; demo affiliate is **US**  
**Sprint 31 production `provider_id`:** none  
**Family-local IDs:** Sprint 18 stub `future-amazon-official`; affiliate demo `merchant-amazon-us` (`allowed_countries` US/CA/GB)

### Merchant-level facts

| Field | State |
|-------|-------|
| Technical implementation | Mock reviews; official stub (SP-API / partner wording); US affiliate placeholder. No PH official adapter. |
| Provider descriptor (Sprint 31 production) | none |
| Counsel / legal review | Counsel-cleared to apply (2026-08-25) |
| Application state | **not submitted** |
| Merchant approval | **no** |
| Product-data / API rights | **UNKNOWN**. Associates ≠ Creators API ≠ PA-API. |
| Credentials | **none** |
| Display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Affiliate rights | **UNKNOWN** |
| Sandbox rights | **UNKNOWN** |
| Production rights | **none** |
| Certification evidence status | incomplete / none in production catalog |
| Trusted certification status | no record — **not certified** |
| Blocker | PH marketplace/API assignment **UNKNOWN**; no credentials; no rights; no certification |
| Owning sprint | 26 / 32 |

### Contemplated capabilities

| Capability | Technical implementation | Sprint 31 descriptor | Certification evidence | Trusted certification | Blocker |
|------------|--------------------------|----------------------|------------------------|-----------------------|---------|
| `product_discovery` | none official for PH | none | incomplete | none | no official PH path |
| `offer_discovery` | none official for PH | none | incomplete | none | no official PH path |
| `current_pricing` | none official for PH | none | incomplete | none | no official PH path |
| `review_community_evidence` | mock reviews only | none | incomplete | none | rights **UNKNOWN** |
| `shipping` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |
| `taxes_import` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |

---

## Temu

**Source identity:** `temu`  
**Market:** PH contemplated  
**Sprint 31 production `provider_id`:** none  
**Family-local IDs:** none

### Merchant-level facts

| Field | State |
|-------|-------|
| Technical implementation | **none** — no stub, mock, collector, or affiliate placeholder |
| Provider descriptor (Sprint 31 production) | none |
| Counsel / legal review | Counsel-cleared to apply (2026-08-25) |
| Application state | **not submitted** |
| Merchant approval | **no** |
| Product-data / API rights | **UNKNOWN**. Affiliate track ≠ partner/API. |
| Credentials | **none** |
| Display rights | **UNKNOWN** |
| Caching / storage rights | **UNKNOWN** |
| AI-transmission rights | **UNKNOWN** |
| Affiliate rights | **UNKNOWN** |
| Sandbox rights | **UNKNOWN** |
| Production rights | **none** |
| Certification evidence status | incomplete / none in production catalog |
| Trusted certification status | no record — **not certified** |
| Blocker | No technical path and no merchant evidence |
| Owning sprint | 26 / 32 |

### Contemplated capabilities

| Capability | Technical implementation | Sprint 31 descriptor | Certification evidence | Trusted certification | Blocker |
|------------|--------------------------|----------------------|------------------------|-----------------------|---------|
| `product_discovery` | none | none | incomplete | none | no implementation or rights |
| `offer_discovery` | none | none | incomplete | none | no implementation or rights |
| `current_pricing` | none | none | incomplete | none | no implementation or rights |
| `shipping` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |
| `taxes_import` | not a 32.1 runtime path | none | incomplete | none | Sprint 37; rights **UNKNOWN** |

---

## Other repository sources inspected (not Sprint 32 PH candidates)

These appear in stubs or demo affiliate fixtures. They are **not** counsel-cleared Sprint 26 PH merchants and are **not** added as certification candidates.

| Source | Why listed | PH certification status |
|--------|------------|-------------------------|
| eBay (`future-ebay-official`, `merchant-ebay-us`) | Sprint 18 stub + US affiliate placeholder | not a PH candidate from current evidence |
| AliExpress (`merchant-aliexpress-global`) | inactive global affiliate placeholder | not a PH candidate from current evidence |

No Zalora, Carousell, Shein, or other extra PH retailers are contemplated in repository contracts.

---

## Explicit non-claims

- No production `ResearchProviderCertification` is created by this inventory.
- No production evidence catalog rows are seeded.
- No merchant HTTP, credentials, scraping, or live research is authorized.
- Shopee remains uncertified and fail-closed.
- Sprint 32 is **not complete**.
