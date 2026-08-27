# Sprint 26 Merchant Application Counsel Clearance

**Document type:** Sanitized engineering / external-dependency evidence  
**Purpose:** Record counsel application-clearance facts needed to prepare owner merchant/program applications  
**Date recorded:** 2026-08-27  
**Counsel-review / signed-record date:** 2026-08-25  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Related:** [`SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md`](SPRINT_26_MERCHANT_APPLICATION_PREPARATION.md) · [`SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md) · [`SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md`](SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md)

**Rule:** This record is application clearance only. It does **not** advance register EXT-01…EXT-05 (Philippines / United States / Singapore / United Kingdom / Canada market rows) from `not_started` to `applied`.

---

## Identifier Namespace Warning

The signed counsel form uses EXT-01 through EXT-05 as merchant-row labels for Shopee, Lazada, TikTok Shop, Amazon, and Temu. The authoritative PiqSavi External Dependency Register already uses EXT-01 through EXT-05 for market bootstrap rows PH, US, SG, UK, and CA. These identifiers are not equivalent and must not be mapped automatically.

Repository operational documentation refers to merchant application work by merchant/program name. The counsel-form EXT labels are retained only when describing the signed legal record.

Do **not** treat the following as engineering truth:

- `EXT-01 = Shopee`
- `EXT-02 = Lazada`
- `EXT-03 = TikTok Shop`
- `EXT-04 = Amazon`
- `EXT-05 = Temu`

Those equalities are **not** register meanings. Register EXT-01 remains the Philippines market row; EXT-02 the United States; EXT-03 Singapore; EXT-04 the United Kingdom; EXT-05 Canada.

---

## Evidence handling

Signed counsel authorization was received and is retained **outside the repository**. Sanitized engineering evidence is recorded here.

The signed record itself states that repository evidence should retain only:

- merchant / program
- market
- counsel-review date
- application-clearance status
- material operational conditions
- later, actual merchant application submission evidence

**Not stored in Git:** the signed PDF, signature image, privileged legal reasoning, confidential lawyer communications, optional counsel registry identifiers, or other unnecessary counsel identifiers.

Counsel identity is recorded only because the existing EXT-19 convention already names the engaged counsel.

---

## Historical counsel-form row labels (signed record only)

Quoted here solely so the signed PDF can be traced. Each label is **not** a register identifier.

| Merchant / program | How the signed counsel form labels that row | Authoritative register meaning of the same EXT token |
|--------------------|---------------------------------------------|-----------------------------------------------------|
| Shopee | The signed counsel form labels the Shopee row as “EXT-01.” | This is a counsel-form label only and does **not** redefine External Dependency Register EXT-01 (Philippines market). |
| Lazada | The signed counsel form labels the Lazada row as “EXT-02.” | This is a counsel-form label only and does **not** redefine External Dependency Register EXT-02 (United States market). |
| TikTok Shop | The signed counsel form labels the TikTok Shop row as “EXT-03.” | This is a counsel-form label only and does **not** redefine External Dependency Register EXT-03 (Singapore market). |
| Amazon | The signed counsel form labels the Amazon row as “EXT-04.” | This is a counsel-form label only and does **not** redefine External Dependency Register EXT-04 (United Kingdom market). |
| Temu | The signed counsel form labels the Temu row as “EXT-05.” | This is a counsel-form label only and does **not** redefine External Dependency Register EXT-05 (Canada market). |

Counsel clearance of a merchant/program does **not** select that merchant as the provider for any register market row. Intended market(s) per merchant/program remain **OWNER INPUT REQUIRED**. Owner must still choose intended market(s) and submit a real application before any register market row may move to `applied`.

---

## Sanitized counsel-clearance facts

| Field | Value |
|-------|-------|
| Public brand | PiqSavi |
| Internal codename | DealBrain |
| Counsel | Pauline Anne Sambuang |
| Discussion date (on the signed record) | 2026-08-19 |
| Signed-record date | 2026-08-25 |
| Signed record received | Yes — retained outside Git |
| Record title | Merchant Program Legal Review & Application Authorization Record |
| Scope | Sprint 26 application clearance for Shopee, Lazada, TikTok Shop, Amazon, and Temu merchant/program applications |
| Consolidated conditions / exceptions | **N/A** |
| Hold items | **None** — no merchant/program row on the signed form was marked on hold |

### Merchant application-clearance status

| Merchant / program | Application-clearance status | Application submitted? | Merchant approved PiqSavi? |
|--------------------|------------------------------|------------------------|----------------------------|
| Shopee | Counsel-cleared to proceed with application | **No** | **No** |
| Lazada | Counsel-cleared to proceed with application | **No** | **No** |
| TikTok Shop | Counsel-cleared to proceed with application | **No** | **No** |
| Amazon | Counsel-cleared to proceed with application | **No** | **No** |
| Temu | Counsel-cleared to proceed with application | **No** | **No** |

---

## Distinction preserved by the signed record

The signed record states that a “May proceed to apply” / counsel-cleared entry is evidence of counsel review and **application clearance only**.

It is **not** evidence that the merchant:

- approved PiqSavi
- issued credentials
- granted product-data / API rights
- authorized production use

Engineering must keep these states separate:

`counsel clearance to apply` ≠ `merchant approval` ≠ `credentials` ≠ `product-data/API permission` ≠ `production authorization`

---

## Register effect

| Register row | Lifecycle status after this record | What changed |
|--------------|------------------------------------|--------------|
| EXT-01…EXT-05 (PH / US / SG / UK / CA market rows) | remain `not_started` | Legal gate to **submit** Shopee, Lazada, TikTok Shop, Amazon, and Temu merchant/program applications is satisfied. No application date. No `applied` status. No merchant-to-market assignment. |
| EXT-06 | `not_started` | Unchanged — credentials still not issued |
| EXT-07 | `not_started` | Unchanged — tracking IDs still not issued |
| EXT-19 | remains `applied` (not `approved`) | Merchant-program **application** clearance is recorded separately; consumer ToS/Privacy written approval is still required before EXT-19 `approved` |

---

## Explicit non-claims

- No merchant application was submitted from this evidence task.
- No merchant approved PiqSavi.
- No affiliate permission, catalog/product-data permission, or other display/data right is inferred.
- No credentials, tracking IDs, or production authorization exist because of this record.
- No merchant was mapped to a market.
- No `ResearchProviderCertification` is created.
- No public “Shopee supported” / “Lazada live” / equivalent claim is authorized.
- Sprint 32 is **not** started.
- Sprint 26 remains **open** until real application-submission evidence exists for remaining bootstrap rows.
