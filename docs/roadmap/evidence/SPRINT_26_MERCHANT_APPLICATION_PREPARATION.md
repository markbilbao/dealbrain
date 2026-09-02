# Sprint 26 — Merchant Application Preparation

**Document type:** Owner execution checklist and evidence templates (preparation only)  
**Status:** Counsel-cleared to apply. Lazada, TikTok Shop, Amazon, and Temu remain **not submitted**. Shopee later operational evidence is recorded separately and is **not** a collapsed “Shopee merchant application submitted” claim.  
**Authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Counsel-clearance evidence:** [`SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md`](SPRINT_26_MERCHANT_APPLICATION_COUNSEL_CLEARANCE.md)  
**Bootstrap checklist:** [`SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md)  
**Shopee current evidence:** [`SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md) — affiliate onboarding active / Open API access pending; not a collapsed “application submitted” claim

**This task:** PREPARE ONLY. The owner will submit or separately authorize each merchant application. Do not treat this file as submission evidence.

Operational work is identified by merchant/program name (Shopee, Lazada, TikTok Shop, Amazon, Temu). Authoritative register EXT-01…EXT-05 remain **market** rows (PH / US / SG / UK / CA) and are not merchant IDs. See the Identifier Namespace Warning in the clearance record.

---

## Shared gates (all five merchants)

| Gate | Current state |
|------|----------------|
| Legal application gate | **Cleared** (signed counsel record 2026-08-25; conditions N/A; no hold) |
| Owner submission | **Required** — not done |
| Submission evidence | **Required** after owner submits — template in Section H |
| Merchant approval | Required later — **not** granted |
| Product-data / API permission | Must remain **separate** from affiliate approval |
| Credentials | Only after the provider issues them — **none** now |
| Tracking IDs | Only after affiliate approval where applicable — **none** now |
| Production integration | Not before permission **and** later Sprint 32–36 certification |
| Public support claim | Forbidden until technical + legal + certification evidence exists |

Known repository facts that may be reused (do not invent the rest):

| Field | Status |
|-------|--------|
| Public brand | **KNOWN** — PiqSavi |
| Domain | **KNOWN** — `piqsavi.com` (`https://piqsavi.com`) |
| Product description (draftable) | **KNOWN** — AI Personal Shopper; compare / score / recommend / explain / redirect after ranking |
| Support contact | **KNOWN** — `support@piqsavi.com` |
| Privacy contact | **KNOWN** — `privacy@piqsavi.com` |
| Live Terms URL | **NOT YET AVAILABLE** — EXT-21 `not_started` |
| Live Privacy URL | **NOT YET AVAILABLE** — EXT-20 `not_started` |
| Legal entity / applicant name | **OWNER INPUT REQUIRED** |
| Tax / bank / address / traffic / revenue / follower counts | **OWNER INPUT REQUIRED** — do not store secrets in Git |

---

## A. Shopee application

Authoritative current Shopee evidence: [`SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md).

**Shopee Affiliate Open API ≠ Shopee Seller/ISV Open Platform.** Do not collapse dashboard access, Payment & Tax, Affiliate Open API access, Seller/ISV, or production data rights into one application state.

| Field | Value |
|-------|-------|
| Official program / application routes | **Shopee Affiliate Program** (dashboard access observed): previously identified PH web host [affiliate.shopee.ph](https://affiliate.shopee.ph/). **Shopee Affiliate Open API:** documented GraphQL program; PiqSavi access **not granted**. **Seller/ISV Open Platform:** [open.shopee.com](https://open.shopee.com/) — **separate; held**. |
| Intended market(s) | Philippines remains the launch focus. Dashboard access does **not** by itself prove PH market coverage or assign register EXT-01. Do not derive market scope from the signed counsel form’s row labels. |
| Affiliate dashboard access | **Yes** (owner-verified operational observation). Establishes dashboard/environment access only. |
| Payment & Tax | **Submitted; review pending.** Not Affiliate Open API approval and not full affiliate-account approval. |
| Affiliate Open API access | **Not granted.** AppID **none**. Secret **none**. Interface indicates access unavailable / requires access request or contact with Shopee. |
| Seller / ISV Open Platform | **Hold — not submitted.** Requires business-registration information PiqSavi cannot truthfully provide today. |
| Legal gate | **Cleared** to submit application |
| Owner submission required | **Still required** for Affiliate Open API access (not recorded as submitted). Do not treat Payment & Tax as that API-access application. |
| Submission evidence required | **Yes** — Section H, per distinct track |
| Merchant approval required later | **Yes** |
| Product-data / API permission | Remain separate — currently **unknown** / **not established**. Public Affiliate Open API documentation ≠ PiqSavi authorization. |
| Credentials | **None** — no AppID/Secret issued |
| Tracking IDs | Only after affiliate approval where applicable — **no** |
| Production integration | Not before permission / Sprint 32–36 certification |

Public eligibility notes (not a determination that PiqSavi qualifies): Affiliate Open API documentation describes product-level offer query `productOfferV2` and item-feed APIs; that is technical-capability evidence only. Seller/ISV Open Platform partner registration publicly requires business documents and a live product URL and remains held. **OWNER INPUT REQUIRED** for eligibility facts not already in the repo.

---

## B. Lazada application

| Field | Value |
|-------|-------|
| Official program / application route to be identified | **OWNER INPUT REQUIRED.** Public candidate routes: Lazada Affiliate Program market portals; Philippines official terms identify the affiliate platform at [adsense.lazada.com.ph](https://adsense.lazada.com.ph). Other markets use their own adsense host (example: Malaysia terms cite `adsense.lazada.com.my`). Product-data / partner API is a separate Open Platform at [open.lazada.com](https://open.lazada.com/). |
| Intended market(s) | **OWNER INPUT REQUIRED** per merchant/program. Do not derive market scope from the signed counsel form’s row labels. |
| Affiliate application required? | **Likely yes** if tracked Lazada links are intended — owner must confirm market portal. |
| Partner / API / product-data application required? | **Separate, if product data is required.** Open Platform developer registration ≠ affiliate approval. |
| Legal gate | **Cleared** to submit application |
| Owner submission required | **Yes** |
| Submission evidence required | **Yes** |
| Merchant approval required later | **Yes** |
| Product-data / API permission | Remain separate — currently **unknown** |
| Credentials | Only after provider issuance — **no** |
| Tracking IDs | Only after affiliate approval where applicable — **no** |
| Production integration | Not before permission / certification |

Public distinction: official PH affiliate T&Cs describe deeplink promotion via the Affiliate Platform. That is not Open Platform catalog access.

---

## C. TikTok Shop application

| Field | Value |
|-------|-------|
| Official program / application route to be identified | **OWNER INPUT REQUIRED.** Public candidate routes are **not** one program: (1) in-app / Creator Center TikTok Shop affiliate for creators; (2) TikTok Shop Partner Center for agencies / developers / service partners — regional hosts include [partner.tiktokshop.com](https://partner.tiktokshop.com/) and [partner.us.tiktokshop.com](https://partner.us.tiktokshop.com/). External-traffic / website comparison may require a different partner category than creator affiliate. Owner must identify the program that matches PiqSavi’s intended use before submit. |
| Intended market(s) | **OWNER INPUT REQUIRED** per merchant/program. Do not derive market scope from the signed counsel form’s row labels. |
| Affiliate application required? | **OWNER INPUT REQUIRED** — yes if monetized TikTok Shop traffic is intended; the correct affiliate vs partner program is not selected here. |
| Partner / API / product-data application required? | **Separate.** Partner Center / developer API access is not granted by creator-affiliate approval. |
| Legal gate | **Cleared** to submit application |
| Owner submission required | **Yes** |
| Submission evidence required | **Yes** |
| Merchant approval required later | **Yes** |
| Product-data / API permission | Remain separate — currently **unknown** |
| Credentials | Only after provider issuance — **no** |
| Tracking IDs | Only after affiliate approval where applicable — **no** |
| Production integration | Not before permission / certification |

Do not assume creator-affiliate, Partner Center, and product APIs are interchangeable.

---

## D. Amazon application

Keep these **separate**:

1. **Amazon Associates / affiliate participation** — official program home: [affiliate-program.amazon.com](https://affiliate-program.amazon.com/). Marketplace-specific Associates programs exist; owner must choose the marketplace(s).
2. **Product-data access** — historically Product Advertising API (PA-API); Amazon public docs now point new/existing catalog integrations to **Creators API** via Associates Central (`Tools` → Creators API), and describe PA-API 5 as deprecated in favor of Creators API. Associates account acceptance is a **prerequisite**, not the same as API permission. Public Creators API docs state sign-up is available only to associates who have referred qualified sales and received final program acceptance.

| Field | Value |
|-------|-------|
| Official program / application route to be identified | **OWNER INPUT REQUIRED** for marketplace. Candidate: Associates join at [affiliate-program.amazon.com](https://affiliate-program.amazon.com/); later, if catalog API is required, Creators API registration inside Associates Central (see [Creators API onboarding](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/onboarding)). |
| Intended market(s) | **OWNER INPUT REQUIRED** per merchant/program. Do not derive market scope from the signed counsel form’s row labels. |
| Affiliate application required? | **Yes, if Associates participation is intended** — first application is typically Associates, not PA-API. |
| Partner / API / product-data application required? | **Yes, separately, if catalog data is required.** Associates approval ≠ PA-API permission ≠ Creators API permission. |
| Legal gate | **Cleared** to submit application |
| Owner submission required | **Yes** |
| Submission evidence required | **Yes** — record Associates vs API as **distinct** application types |
| Merchant approval required later | **Yes** (per program) |
| Product-data / API permission | Remain separate — currently **unknown** |
| Credentials | Only after provider issuance — **no** |
| Tracking IDs | Only after Associates approval (Store ID / tracking IDs) — **no** |
| Production integration | Not before permission / certification |

Do **not** treat Associates approval as PA-API or Creators API permission.

---

## E. Temu application

Keep these **separate**:

1. **Affiliate / influencer / media-publisher participation** — official entry: [temu.com/affiliate_influencer_program.html](https://www.temu.com/affiliate_influencer_program.html). Public page distinguishes Affiliate, Influencer, and Affiliate Media Publisher (website/app with traffic; **business registration required** on the public copy).
2. **Any product-data / API / partner access** — not granted by affiliate enrollment. Partner/integrator surfaces (for example Temu Partner Platform) are a different relationship. Do not assume one grants the other.

| Field | Value |
|-------|-------|
| Official program / application route to be identified | **OWNER INPUT REQUIRED** which public track (Affiliate vs Influencer vs Media Publisher) matches PiqSavi. Candidate affiliate entry: URL above. Partner/API path remains **OWNER INPUT REQUIRED** if catalog data is needed. |
| Intended market(s) | **OWNER INPUT REQUIRED** per merchant/program. Do not derive market scope from the signed counsel form’s row labels. |
| Affiliate application required? | **Likely yes** if tracked Temu links are intended — owner selects the public track. |
| Partner / API / product-data application required? | **Separate, if product data is required.** Affiliate ≠ partner/API. |
| Legal gate | **Cleared** to submit application |
| Owner submission required | **Yes** |
| Submission evidence required | **Yes** |
| Merchant approval required later | **Yes** |
| Product-data / API permission | Remain separate — currently **unknown** |
| Credentials | Only after provider issuance — **no** |
| Tracking IDs | Only after affiliate approval where applicable — **no** |
| Production integration | Not before permission / certification |

---

## F. Permission matrix (Shopee, Lazada, TikTok Shop, Amazon, Temu)

Current state after counsel clearance:

- legal application gate: **cleared** (application only)
- merchant permission: **unknown / not yet granted**
- credentials: **not issued**
- production certification: **none**

Unknown stays unknown. Do not infer from counsel clearance.

| Permission | Shopee | Lazada | TikTok Shop | Amazon | Temu |
|------------|--------|--------|-------------|--------|------|
| Legal gate to apply | cleared | cleared | cleared | cleared | cleared |
| Affiliate permission | unknown | unknown | unknown | unknown | unknown |
| Catalog / product-data / API permission | unknown | unknown | unknown | unknown (Associates ≠ PA-API / Creators API) | unknown |
| Credentials | no | no | no | no | no |
| Price permission | unknown | unknown | unknown | unknown | unknown |
| Image / display permission | unknown | unknown | unknown | unknown | unknown |
| Review / rating permission | unknown | unknown | unknown | unknown | unknown |
| Availability permission | unknown | unknown | unknown | unknown | unknown |
| Shipping permission | unknown | unknown | unknown | unknown | unknown |
| Returns / warranty permission | unknown | unknown | unknown | unknown | unknown |
| Caching / storage permission | unknown | unknown | unknown | unknown | unknown |
| AI transmission permission | unknown | unknown | unknown | unknown | unknown |
| Deep-link permission | unknown | unknown | unknown | unknown | unknown |
| Attribution requirements | unknown | unknown | unknown | unknown | unknown |
| Market scope | unknown — owner must declare intended market(s) | unknown | unknown | unknown | unknown |
| Production use | **none** | **none** | **none** | **none** | **none** |

Fail closed until later provider terms + merchant response + Sprint 32–36 certification evidence exist.

---

## G. Owner input required

Do **not** invent these. Do **not** commit secrets. Fill outside Git or as non-secret references after the owner provides them.

### G.1 Shared (every application)

| Field | Why needed |
|-------|------------|
| Legal entity / applicant business name | Not finalized in repo (founder counsel notes still list structure as an open decision) |
| Company registration number | Not in repo |
| Tax number | Not in repo — do not store in Git |
| Bank / payout details | Provider payout setup — do not store in Git |
| Owner home / registered address | Provider KYC — do not store in Git |
| Submitting account identity (email / portal login reference, non-secret) | Evidence template field |
| Business contact | Application forms |
| Technical contact | Application forms |
| Intended market(s) per merchant/program | **OWNER INPUT REQUIRED.** Do not derive market scope from counsel-form numbering. A later submission may evidence one or more register **market** rows (PH / US / SG / UK / CA) only after the owner selects them. |
| Application type for this submit (affiliate / API / both / other) | Must not collapse affiliate vs product-data |
| Revenue / monthly traffic / follower counts / website analytics | Common portal fields — **not** in repo |
| Legal declarations / terms acceptance | Owner must accept; this task must not accept terms |
| Live consumer UI screenshots | Sprint 29 UI not a substitute; **NOT YET AVAILABLE** where portals require a live site |
| Live Terms of Service URL | EXT-21 `not_started` |
| Live Privacy Policy URL | EXT-20 `not_started` |

### G.2 Merchant-specific

| Merchant | Additional OWNER INPUT REQUIRED |
|----------|----------------------------------|
| Shopee | Affiliate dashboard access exists; Payment & Tax pending; whether/when to request Affiliate Open API access; Seller/ISV remains held; market coverage of the accessed affiliate account |
| Lazada | Market-specific adsense host; individual vs business track; whether Open Platform will be applied now or later |
| TikTok Shop | Program choice (creator affiliate vs Partner Center vs other); region/Partner Center host |
| Amazon | Associates marketplace (e.g. amazon.com vs others); whether catalog API (Creators API / remaining PA-API path) is in-scope for this submit |
| Temu | Track choice (Affiliate vs Influencer vs Media Publisher); whether any partner/API application is in-scope |

---

## H. Submission evidence template

Copy one block **after** the owner actually submits. Do **not** pre-fill submission IDs, dates, or statuses other than the defaults below.

```md
| Field | Value |
|-------|-------|
| Merchant / program | |
| Counsel-form row label, if applicable | Quote the signed form only if needed for traceability; do not treat as a register ID |
| Authoritative external-dependency reference, if later assigned | Register market row(s) such as EXT-01 PH / EXT-02 US / EXT-03 SG / EXT-04 UK / EXT-05 CA — only after owner selects the market(s). Leave blank until assigned. |
| Market | **OWNER INPUT REQUIRED** until selected |
| Application type | affiliate / product-data-API / partner / other (specify) |
| Date submitted | (real date only — never invent) |
| Submitting account / business identity reference | (non-secret) |
| Official portal / program URL or terms reference | |
| Application ID / ticket ID / submission ID | (leave blank until issued) |
| Screenshot / PDF evidence location | (sanitized; outside Git if sensitive) |
| Current status | submitted / pending / approved / rejected / on hold |
| Approval date if later approved | |
| Rejection / hold reason if later rejected | |
| Issued credentials? | yes / no |
| Product-data / API rights? | yes / no / unknown |
| Affiliate rights? | yes / no / unknown |
| Operational restrictions | |
| Next action | |
```

Do not force every merchant/program application into register EXT-01…EXT-05. Those IDs are market bootstrap rows, not merchant IDs.

Defaults until real submission evidence exists: date submitted blank; application ID blank; current status not `applied` in the register; issued credentials **no**; product-data/API rights **unknown**; affiliate rights **unknown**.

After evidence is retained, update **only** the affected **register market** row(s) to `applied`, and only those rows the owner actually selected.

---

## I. Sprint boundaries

| Work | Owner sprint |
|------|----------------|
| Submit applications; collect merchant responses; obtain program access, contractual evidence, credentials/tracking IDs where issued; preserve evidence | **Sprint 26** (this track) |
| Philippines merchant/source certification under the trusted Sprint 31 certification model | **Sprint 32** — authorized, **not started** |
| Other named-market certification | Sprints 33–36 |

Application approval alone must **not** create a `ResearchProviderCertification`.

---

## J. Next owner action

1. Choose the first merchant and intended market(s).
2. Supply Section G fields (outside Git for secrets).
3. Open the official portal for that program only.
4. Submit the application yourself (or authorize a later dedicated submission task).
5. Capture sanitized submission evidence using Section H.
6. Then, and only then, move the matching **register market** row from `not_started` to `applied`.
