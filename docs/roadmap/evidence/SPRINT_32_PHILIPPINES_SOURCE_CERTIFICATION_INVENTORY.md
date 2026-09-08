# Sprint 32 — Philippines Source Certification Inventory

**Document type:** Non-secret certification-evidence inventory  
**Sprint slice:** 32.1–32.5 foundation complete. Sprint 32 is **not complete** (blocked on external certification).  
**Date recorded:** 2026-09-02  
**Baseline:** `d890df24559325bb8d1289b6c2a01b590c9e50ab`  
**Market:** PH  
**Register row:** EXT-01 (Philippines **product-data** access) is `applied` (2026-09-08 request evidence). This inventory snapshot originally recorded `not_started`. `applied` ≠ approved / provisioned / certified.
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

Catalog `register` / `replace` remain trusted infrastructure primitives. `ResearchProviderCertificationDecisionService` is the policy path. Incomplete documentary records have no promotion helper. Official `main` now retains the 2026-09-08 Shopee/Lazada PH **product-data request** evidence (EXT-01 `applied`). That is not a Shopee Open Platform application completion, not approval, and not certification. Affiliate-dashboard observations still do not certify.

### 32.5 reconciliation

Sprint 31 is formally owner-closed. Sprint 32 remains in progress and blocked on external certification. Authoritative slice status lives in [`../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md`](../sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md).

Owner-observed Shopee affiliate facts (affiliate dashboard access, Payment & Tax pending, Affiliate Open API docs, `productOfferV2`, feeds, GraphQL auth, documented 8000/hour, absent AppID/Secret) are **not** Sprint 32 certification evidence. The 2026-09-08 product-data request emails are now on the Sprint 26 evidence path as EXT-01 `applied` only. They do **not** certify Shopee.

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
| EXT-01 / EXT-06 | EXT-01 `applied` (2026-09-08 PH product-data requests; not approved); EXT-06 `not_started`; EXT-07 `n_a_beta` for September |
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
| Application state | Product-data access **request submitted** 2026-09-08 (EXT-01 `applied`). Provider decision pending. Not approved. Seller/ISV Open Platform still not submitted. |
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

Official `main` now also retains the 2026-09-08 Shopee PH product-data request evidence ([`EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md`](EXT-01_PH_PRODUCT_DATA_ACCESS_REQUESTS_2026-09-08.md)). That request does **not** certify Shopee. Do not treat affiliate-dashboard observations as certification evidence.

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
| Application state | Product-data access **request submitted** 2026-09-08 (EXT-01 `applied`). Provider decision pending. Not approved. |
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
| Blocker | Request submitted; no approval, credentials, rights, or trusted certification |
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

## 2026-09-06 owner lock — certification recording and launch scope

This addendum does **not** certify any provider and does not change the merchant-level facts above. Shopee, Lazada, TikTok Shop, Amazon, and Temu remain **uncertified**.

### Effective-cost field evidence (required at certification)

When a later trusted review creates a PH production certification, each source must record the components below **without treating `CapabilityPolicyState` as technical availability**. Preserve Sprint 31: technical ability ≠ contractual permission. Do not invent a second authorization system.

For each component, record three distinct facts:

| Layer | Meaning | How to record |
|-------|---------|---------------|
| A. Technical / source availability | Does the authorized data path actually expose enough data for this component? | Factual/technical evidence about the provider response/path. Reuse existing connector/certification evidence where possible. If `ConnectorCapability` is operation-level rather than field-level, record field exposure in the certification evidence/report. **Not** a policy state. |
| B. Contractual / policy authorization | May PiqSavi ingest/use/display/transform/compare this field for this provider/market? | Existing Sprint 31 `CapabilityPolicyState` only: `allowed` / `restricted` / `prohibited` / `unknown`. |
| C. Offer / shopper applicability | Where relevant, does evidence establish applicability to the evaluated offer under the known shopper context? | Offer-level evidence. Required before a discount/voucher may reduce scored effective cost. |

| Component | Technical exposure (A) | Policy (B) | Applicability note (C) |
|-----------|------------------------|------------|------------------------|
| Current listing price | Exposed / not exposed / unknown | `allowed` / `restricted` / `prohibited` / `unknown` | Distinct from final effective cost |
| Seller discount | Exposed / not exposed / unknown | same Sprint 31 states | May reduce scored cost only when applicable to this offer/shopper |
| Platform discount | Exposed / not exposed / unknown | same Sprint 31 states | Same applicability rule |
| Voucher/promotion information | Exposed / not exposed / unknown | same Sprint 31 states | Presence ≠ applicability |
| Voucher eligibility/applicability information | Exposed / not exposed / unknown | same Sprint 31 states | Required before a voucher may reduce scored effective cost |
| Destination-dependent shipping | Exposed / not exposed / unknown | same Sprint 31 states | Sprint 37 owns honesty; 32 records whether the path can supply it |
| Free-shipping status | Exposed / not exposed / unknown | same Sprint 31 states | Unknown shipping is not FREE |
| Unavoidable checkout/other costs | Exposed / not exposed / unknown | same Sprint 31 states | Taxes/duties/import/checkout when the path exposes them |
| Timestamp/freshness | Exposed / not exposed / unknown | same Sprint 31 states | Required for current-data claims |

Preserved distinctions: field present ≠ permitted to use; permitted to use ≠ field actually available; voucher available ≠ voucher applicable to this shopper/offer. All required conditions must be satisfied before a component can influence scored effective purchase cost.

Provider approval and affiliate approval do not imply technical exposure or policy permission. Do not require a merchant to expose fields it does not provide; record the limitation honestly.

Affiliate permission remains independent from product-data permission. Commission / payout fields remain non-authorization facts.

### Launch-scope notes (do not rewrite historical rows)

- Philippines is the September supported-market target (2026-09-07).
- Shopee Philippines and Lazada Philippines were historical 2026-09-06 **initial affiliate-monetization targets**. Affiliate monetization is **not** a September launch requirement. Affiliate approval is not product-data permission and does not certify a live research source.
- Official brand stores, direct retailers, electronics retailers, authorized reseller sites, and other marketplaces remain **eligible** for routing when a legitimate data path exists. Eligibility is not a requirement to query every integrated merchant on every request.
- Affiliate status must never exclude or privilege an otherwise relevant legitimate source.
- **TikTok Shop PH is not launch-critical** for September 2026. Keep the contemplated TikTok inventory rows. Do not include Singapore/paused campaign as PH launch evidence. Do not destructively remove architecture. Do not claim TikTok was searched unless it was actually queried. Do not give TikTok pre-launch engineering priority over higher-value launch work.
- Search inclusion depends on a legitimate data path, not affiliate status. Scraping is not a workaround. Public language remains **Best Piq among the offers PiqSavi evaluated**.

### 2026-09-07 owner lock addendum (do not rewrite historical rows)

Affiliate monetization is deferred for September public beta. Shopee and Lazada are no longer September affiliate launch dependencies. Product-data certification remains required. Ordinary outbound merchant links are valid launch behavior. Do not delete historical affiliate/network evidence in this inventory. Do not represent affiliate approval as product-data permission. Do not scrape merchants because monetization was removed.

## Explicit non-claims

- No production `ResearchProviderCertification` is created by this inventory.
- No production evidence catalog rows are seeded.
- No merchant HTTP, credentials, scraping, or live research is authorized.
- Shopee remains uncertified and fail-closed.
- Lazada remains uncertified and fail-closed.
- TikTok Shop remains uncertified and is not September-launch-critical.
- Sprint 32 is **not complete**.
