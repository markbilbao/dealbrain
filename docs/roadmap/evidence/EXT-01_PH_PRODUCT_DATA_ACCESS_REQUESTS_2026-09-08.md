# EXT-01 — Philippines product-data access requests (2026-09-08)

**Document type:** Sanitized Sprint 26 / EXT-01 evidence record (non-secret)  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Sprint definition:** [`../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md`](../sprints/SPRINT_26_STAGING_CURRENT_MAIN_PROOF.md)  
**Sprint 26 close record:** [`SPRINT_26_COMPLETION.md`](SPRINT_26_COMPLETION.md)  
**Evidence / action date:** 2026-09-08  
**Register lifecycle after this record:** EXT-01 `not_started` → **`applied`**  
**Evidence source:** Owner-supplied Gmail **Sent** screenshots (Philippines local timestamps)

This record retains confirmation that PiqSavi submitted real Philippines **product-data** access requests. It does **not** record provider approval, credentials, a product feed, API access, or Sprint 32 certification.

---

## 1. Why these qualify as product-data access requests

EXT-01’s Sprint 26 bootstrap meaning is a real PH **product-data** access application/request for at least one legitimate useful path (official merchant API, authorized product feed, authorized retailer integration, partner/data feed, permitted public data source, or another documented legitimate path).

Both emails:

- request an authorized programmatic product-data path (API, Open Platform, product feed, partnership integration, or another approved method);
- explicitly distinguish the request from affiliate monetization;
- state that the initial public beta is planned **without affiliate commissions**;
- ask about product fields needed for research / comparison (title, identifiers, price, seller, availability, product URL, and related catalog fields).

They are **not** affiliate-only applications. Affiliate dashboard access, Payment & Tax, Affiliate Open API documentation, and Lazada/Optimise affiliate approval remain separate and still do **not** by themselves satisfy EXT-01 `approved` / `provisioned`.

`applied` means: request submitted; awaiting external provider response/decision.

---

## 2. Lazada Philippines

| Field | Value |
|-------|-------|
| Provider contacted | Lazada Philippines |
| Sender | Mark Victor Bilbao `<mark@piqsavi.com>` |
| Recipient | `affiliate@lazada.com.ph` |
| Sent | 2026-09-08, 11:09 PM Philippines local time |
| Subject | PiqSavi PH AI Shopping Assistant — Request for Authorized Product Data / Product Feed Access |
| Mailed-by | `piqsavi.com` |
| Evidence path | [`external/EXT-01_LAZADA_PH_PRODUCT_DATA_REQUEST_2026-09-08.png`](external/EXT-01_LAZADA_PH_PRODUCT_DATA_REQUEST_2026-09-08.png) |

**What was requested.** An authorized product feed, API, Open Platform capability, or another approved data-access method suitable for an AI shopping / product-comparison service. The email states that priority is authorized product-data access rather than affiliate monetization, and that the initial beta is launching without affiliate commissions.

**Requested data points visible in the retained screenshot:**

- Product title and product/variant identifiers
- Current price and sale price
- Seller/store information
- Availability/stock status
- Product URL
- Product image
- Category and product specifications
- Promotion/voucher information where permitted

The owner-supplied email also asked about rights to display, normalize, compare, rank, use as recommendation evidence, cache under an approved freshness policy, and route users back to Lazada. Those usage-rights questions are part of the request. They are **not** granted by sending the email.

---

## 3. Shopee Philippines

| Field | Value |
|-------|-------|
| Provider contacted | Shopee Philippines |
| Sender | Mark Victor Bilbao `<mark@piqsavi.com>` |
| Recipient | `affiliate_ph@shopee.com` |
| Sent | 2026-09-08, 11:11 PM Philippines local time |
| Subject | PiqSavi PH AI Shopping Assistant — Request for Product Data / Open API Partnership |
| Mailed-by | `piqsavi.com` |
| Evidence path | [`external/EXT-01_SHOPEE_PH_PRODUCT_DATA_REQUEST_2026-09-08.png`](external/EXT-01_SHOPEE_PH_PRODUCT_DATA_REQUEST_2026-09-08.png) |

**What was requested.** A legitimate, authorized programmatic product-data path, including Shopee Open Platform, an approved API/product feed, a partnership integration, or another authorized method suitable for an AI shopping assistant researching Shopee products for Filipino shoppers. The email states that the current request is not primarily for affiliate monetization and that the initial public beta is planned without affiliate commissions.

**Requested data points visible in the retained screenshot:**

- Product title and product/variant identifiers
- Current price and sale price
- Shop/seller information
- Product availability
- Product URL

The owner-supplied email also asked about authorized product-data usage. Asking is not the same as receiving permission.

This request is **separate** from the historical Shopee affiliate-onboarding record at [`SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md`](SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md). That affiliate record still does **not** satisfy EXT-01 by itself.

---

## 4. What the screenshots show

Owner-supplied Gmail **Sent** screenshots (`in:sent`) with the message-details popover open.

Retained:

- PiqSavi business sender `mark@piqsavi.com`
- Public provider recipient addresses
- Date, subject, mailed-by `piqsavi.com`
- Visible request body distinguishing product-data access from affiliate monetization

Not retained / not transcribed from the screenshots:

- Unrelated inbox rows or other message subjects
- Credentials, tokens, account identifiers, API keys
- Personal email addresses other than the PiqSavi business sender
- Provider replies (none are claimed)

---

## 5. Register / Sprint effect

| Item | After this record |
|------|-------------------|
| EXT-01 lifecycle | **`applied`** |
| Application / request date | **2026-09-08** |
| Sprint 26 bootstrap action | Satisfied — real PH product-data access request evidence now exists |
| Sprint 26 close | Permitted on this evidence plus already-packaged technical staging proof |
| EXT-06 credentials | Unchanged — `not_started` |
| EXT-07 affiliate tracking | Unchanged — `n_a_beta` / deferred |
| Sprint 32 | Unchanged — **not complete**; pending certification |

---

## 6. Explicit non-claims

This record does **not** mean:

- Lazada approved PiqSavi
- Shopee approved PiqSavi
- BuyWhere approved or provisioned PiqSavi
- API Hub PH approved or provisioned PiqSavi
- PiqSavi has Shopee API credentials
- PiqSavi has Lazada API credentials
- PiqSavi has a Lazada product feed
- PiqSavi has a Shopee product feed
- Any provider has granted production use
- Any provider has granted all requested rights
- Any live PH merchant source has been technically connected
- Any live normalized PH offer has been certified
- Sprint 32 is complete
- Philippines shopping launch certification is complete

Do **not** use `approved`, `provisioned`, `certified`, `live`, `connected`, or equivalent language for EXT-01 from these emails.

Affiliate approval is still not product-data permission. The initial PH public beta remains without affiliate monetization. EXT-07 stays `n_a_beta`.
