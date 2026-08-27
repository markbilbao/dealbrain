# Sprint 26 Merchant Application Counsel Clearance — EXT-01 to EXT-05

**Document type:** Sanitized engineering / external-dependency evidence  
**Purpose:** Record counsel application-clearance facts needed to prepare owner merchant applications  
**Date recorded:** 2026-08-27  
**Counsel-review / signed-record date:** 2026-08-25  
**Register authority:** [`../EXTERNAL_DEPENDENCY_REGISTER.md`](../EXTERNAL_DEPENDENCY_REGISTER.md)  
**Related:** [`SPRINT_26_EXT01_05_APPLICATION_PREPARATION.md`](SPRINT_26_EXT01_05_APPLICATION_PREPARATION.md) · [`SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md`](SPRINT_26_EXTERNAL_BOOTSTRAP_CHECKLIST.md) · [`SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md`](SPRINT_26_MERCHANT_COUNSEL_DECISION_WORKSHEET_DRAFT.md)

**Rule:** This record is application clearance only. It does **not** advance register EXT-01…EXT-05 from `not_started` to `applied`.

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

## ID crosswalk (do not collapse)

The signed counsel form labeled merchant programs as EXT-01…EXT-05. The authoritative register uses the same EXT-01…EXT-05 IDs for **markets**. Those are different numbering schemes.

| Counsel-form merchant ID | Merchant / program reviewed | Register market ID (unchanged) | Register dependency |
|--------------------------|-----------------------------|--------------------------------|---------------------|
| Counsel-form EXT-01 | Shopee | Register EXT-01 | Philippines market merchant/API or affiliate access |
| Counsel-form EXT-02 | Lazada | Register EXT-02 | United States market merchant/API or affiliate access |
| Counsel-form EXT-03 | TikTok Shop | Register EXT-03 | Singapore market merchant/API or affiliate access |
| Counsel-form EXT-04 | Amazon | Register EXT-04 | United Kingdom market merchant/API or affiliate access |
| Counsel-form EXT-05 | Temu | Register EXT-05 | Canada market merchant/API or affiliate access |

Counsel clearance of a merchant program does **not** select that merchant as the provider for any register market row. Owner must still choose intended market(s) per merchant and submit a real application before any register row may move to `applied`.

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
| Scope | Sprint 26 merchant-program application clearance for the five programs below |
| Consolidated conditions / exceptions | **N/A** |
| Hold items | **None** — no EXT item marked on hold |

### Merchant application-clearance status

| Counsel-form ID | Merchant / program | Application-clearance status | Application submitted? | Merchant approved PiqSavi? |
|-----------------|--------------------|------------------------------|------------------------|----------------------------|
| EXT-01 | Shopee | Counsel-cleared to submit application | **No** | **No** |
| EXT-02 | Lazada | Counsel-cleared to submit application | **No** | **No** |
| EXT-03 | TikTok Shop | Counsel-cleared to submit application | **No** | **No** |
| EXT-04 | Amazon | Counsel-cleared to submit application | **No** | **No** |
| EXT-05 | Temu | Counsel-cleared to submit application | **No** | **No** |

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
| EXT-01…EXT-05 | remain `not_started` | Legal gate to **submit** an application for the five counsel-cleared merchant programs is satisfied. No application date. No `applied` status. |
| EXT-06 | `not_started` | Unchanged — credentials still not issued |
| EXT-07 | `not_started` | Unchanged — tracking IDs still not issued |
| EXT-19 | remains `applied` (not `approved`) | Merchant-program **application** clearance is recorded separately; consumer ToS/Privacy written approval is still required before EXT-19 `approved` |

---

## Explicit non-claims

- No merchant application was submitted from this evidence task.
- No merchant approved PiqSavi.
- No affiliate permission, catalog/product-data permission, or other display/data right is inferred.
- No credentials, tracking IDs, or production authorization exist because of this record.
- No `ResearchProviderCertification` is created.
- No public “Shopee supported” / “Lazada live” / equivalent claim is authorized.
- Sprint 32 is **not** started.
- Sprint 26 remains **open** until real application-submission evidence exists for remaining bootstrap rows.
