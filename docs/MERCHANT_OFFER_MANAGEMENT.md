# Merchant Offer Management (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/`  
**Domain entities:** `MerchantOfferSubmission`, `SubmissionStatus`, `MerchantSourceMode` in `app/domain/entities/merchant.py`  
**Repository ports:** `MerchantSubmissionRepository` in `app/domain/interfaces/merchant_repository.py`  
**Service:** `MerchantOfferService`

## Overview

Merchants create and maintain offer submissions (price, shipping, availability)
tied to a product submission or matched catalog product. Offers are always
merchant-submitted — never labeled as live scraped marketplace data.

**Hard rule:** Merchant-submitted data uses MERCHANT_SUBMITTED provenance.
Offer CRUD does not write DealScore, does not mark offers as “live,” and does
not reorder organic recommendations. Merchant tools never directly manipulate
organic DealScore or recommendation ranking.

```
EDITOR+ creates / updates offer
      │
      ▼
  MerchantOfferService
      │  source_mode = MERCHANT_SUBMITTED
      │  source_label = MERCHANT_SOURCE_LABEL
      ▼
  InMemoryMerchantRepository
      │
      └─ deactivate → is_active=False / archived status
```

## Architecture

```
API (/api/v1/merchants/{id}/offers)
      │
      ▼
  MerchantOfferService (app/services/merchant_offer_service.py)
      │
      ├─ create_offer
      ├─ update_offer
      ├─ list_offers / get
      └─ deactivate_offer
      │
      ├─ require_membership + OFFER_SUBMIT
      ├─ validation (price, currency, URLs)
      └─ audit: OFFER_SUBMITTED / OFFER_UPDATED / OFFER_DEACTIVATED
      │
      ▼
  InMemoryMerchantRepository (demo store)
```

## Offer model

| Field | Notes |
|-------|-------|
| `price` / `sale_price` | Numeric; `total_price = (sale_price or price) + shipping_cost` |
| `currency` | ISO-style string (demo validation) |
| `shipping_cost` | Defaults to `0.0` |
| `inventory_quantity` | Optional stock signal |
| `availability` | e.g. `in_stock` |
| `marketplace_url` | Safe `http`/`https` only |
| `product_submission_id` | Link to merchant product draft |
| `matched_product_id` | Optional catalog product id |
| `source_mode` | Always `merchant_submitted` |
| `is_active` | Soft deactivate without hard delete |

## Provenance — no live labeling

| Allowed | Forbidden in Sprint 21 |
|---------|------------------------|
| `source_mode=merchant_submitted` | Labeling as live / verified / scraped |
| `source_label` merchant-submitted disclaimer | Implying independent price verification |
| Demo fixture offers | Production marketplace postbacks |

Offers may reference a matched product for association, but association does
**not** upgrade provenance. Sponsored placements that include offer ids still
render with sponsored labeling and remain separate from organic lists.

## Lifecycle

```
create (draft/submitted) ──► update while pending
      │
      ├─ admin review may approve/reject related product context
      └─ deactivate → inactive / archived
```

Offer statuses reuse `SubmissionStatus` where applicable. Deactivate is the
supported retirement path (DELETE on the API maps to deactivate, not hard
erase).

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/merchants/{id}/offers` | List offers |
| POST | `/api/v1/merchants/{id}/offers` | Create offer |
| PUT | `/api/v1/merchants/{id}/offers/{offer_id}` | Update offer |
| DELETE | `/api/v1/merchants/{id}/offers/{offer_id}` | Deactivate / archive |

Requires `offer_submit` within the organization (or `INTERNAL_ADMIN`).

## Hard rules

- Merchant-submitted data uses MERCHANT_SUBMITTED provenance
- No live labeling of merchant offers
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
- Sponsored content rendered separately from organic recommendations (when an offer is used in a campaign placement)

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
- No automatic sync to external marketplace seller APIs
- No live inventory or price verification feeds
