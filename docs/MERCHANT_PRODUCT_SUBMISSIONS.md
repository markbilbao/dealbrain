# Merchant Product Submissions (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/matching/`  
**Domain entities:** `MerchantProductSubmission`, `MerchantMatchResult`, `SubmissionStatus`, `MerchantSourceMode` in `app/domain/entities/merchant.py`  
**Repository ports:** `MerchantSubmissionRepository` in `app/domain/interfaces/merchant_repository.py`  
**Service:** `MerchantProductService`  
**Matcher:** `MerchantProductMatcher` wrapping Sprint 18 `MarketplaceProductMatcher`

## Overview

Merchants draft and submit product records for internal review. Every
submission carries provenance `MERCHANT_SUBMITTED` and the label
“Merchant-submitted data — not independently verified live data”.

**Hard rule:** Merchant-submitted data uses MERCHANT_SUBMITTED provenance.
Submissions never become live/verified marketplace rows through this API alone.
Merchant tools never directly manipulate organic DealScore or recommendation
ranking.

```
EDITOR+ creates draft
      │
      ▼
  MerchantProductService.create_product()
      │  source_mode = MERCHANT_SUBMITTED
      ▼
  submit_product()
      │
      ├─ validate fields
      ├─ MerchantProductMatcher.match(...)
      └─ status → SUBMITTED (or match review if ambiguous)
      │
      ▼
  INTERNAL_ADMIN approve / reject / needs_changes
```

## Architecture

```
API (/api/v1/merchants/{id}/products)
      │
      ▼
  MerchantProductService
      │
      ├─ create / update / list / get
      ├─ submit  → matching + validation
      └─ withdraw
      │
      ▼
  MerchantProductMatcher (app/merchant/matching/)
      │  wraps MarketplaceProductMatcher
      │  ambiguous / conflict → review_required, no silent merge
      ▼
  InMemoryMerchantRepository.save_product_submission()
```

## Submission lifecycle

| Status | Meaning |
|--------|---------|
| `draft` | Editable merchant draft |
| `submitted` | Queued for internal review; matching already run |
| `under_review` | Admin actively reviewing |
| `approved` | Accepted (still MERCHANT_SUBMITTED provenance) |
| `rejected` | Rejected with notes |
| `needs_changes` | Returned to merchant for edits |
| `withdrawn` | Merchant withdrew before/during review |
| `archived` | Soft-retired |

```
draft ──submit──► submitted ──► under_review ──► approved
                      │               │
                      │               ├──────────► rejected
                      │               └──────────► needs_changes ──► (edit) ──► submitted
                      └─ withdraw ──► withdrawn
```

## Matching

On submit, `MerchantProductMatcher` matches brand / model / title / SKU /
UPC / EAN / GTIN / merchant product id against the demo catalog
(`DEMO_CATALOG` in fixtures).

| Outcome | Behavior |
|---------|----------|
| Clear match | `matched_product_id` set; confidence + reasons recorded |
| Ambiguous / conflict | `matched_product_id=None`, `review_required=True`; optional `MerchantMatchReview` |
| Unmatched | No merge; may still proceed as new listing pending admin |

**Hard rule:** Never silently merge low-confidence or ambiguous matches.
Admin approval of an ambiguous submission may accept it as a new listing
without forcing a catalog merge.

## Provenance

| Field | Value |
|-------|-------|
| `source_mode` | `merchant_submitted` (`MerchantSourceMode.MERCHANT_SUBMITTED`) |
| `source_label` | `Merchant-submitted data — not independently verified live data` |

Approved submissions keep this provenance. There is no path in Sprint 21 to
relabel merchant data as verified live marketplace data.

## Fields

Typical payload: `title`, `brand`, `model`, `category`, `description`,
`sku`, `upc`, `ean`, `gtin`, `merchant_product_id`, `image_urls`,
`identifiers`, `warranty`, `seller_info`, `raw_payload`.

Validation (`app/merchant/security/validation.py`) enforces length limits,
safe URL schemes (`http`/`https`), and identifier shape. Credential-like
query params in URLs are rejected.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/merchants/{id}/products` | List submissions |
| POST | `/api/v1/merchants/{id}/products` | Create draft |
| GET | `/api/v1/merchants/{id}/products/{submission_id}` | Get one |
| PUT | `/api/v1/merchants/{id}/products/{submission_id}` | Update pending |
| POST | `/api/v1/merchants/{id}/products/{submission_id}/submit` | Submit + match |
| POST | `/api/v1/merchants/{id}/products/{submission_id}/withdraw` | Withdraw |
| GET | `/api/v1/admin/merchant-submissions` | Admin list |
| POST | `/api/v1/admin/merchant-submissions/{id}/approve` | Approve |
| POST | `/api/v1/admin/merchant-submissions/{id}/reject` | Reject / needs_changes |

Requires `product_submit` (merchant) or `INTERNAL_ADMIN` (admin routes).

## Limitations

- **Demo merchants only**
- **In-memory persistence**
- **No production merchant verification documents**
- **No real sponsored billing**
- **No payment processing**
- **No merchant payouts**
- **No ranking manipulation**
- **No public merchant self-service launch**
- **No production database**
- **No subscription billing**
- **No external email sending**
- Matching uses demo catalog entries only
- Approved ≠ live/verified marketplace provenance
- Merchant-submitted data uses MERCHANT_SUBMITTED provenance
