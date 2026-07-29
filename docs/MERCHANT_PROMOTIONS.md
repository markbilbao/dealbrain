# Merchant Promotions (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/`  
**Domain entities:** `MerchantPromotion`, `PromotionType`, `PromotionStatus` in `app/domain/entities/merchant.py`  
**Repository ports:** merchant promotion persistence via `app/domain/interfaces/merchant_repository.py`  
**Service:** `MerchantPromotionService`

## Overview

Promotions let merchants describe sales, vouchers, coupons, bundles, and
related offers for their catalog. They are informational merchant metadata.

**Hard rule:** Promotions do **not** automatically increase DealScore.
`dealscore_independent=True` is always set. Merchant tools never directly
manipulate organic DealScore or recommendation ranking.

```
MANAGER/EDITOR creates promotion
      │
      ▼
  MerchantPromotionService.create_promotion()
      │  dealscore_independent = True
      │  no DealScore write path
      ▼
  schedule / active / pause / expire
      │
      ▼
  Analytics may count active_promotions (demo) — still no rank boost
```

## Architecture

```
API (/api/v1/merchants/{id}/promotions)
      │
      ▼
  MerchantPromotionService
      │
      ├─ create / update / list
      └─ pause
      │
      ├─ require_membership + PROMOTION_MANAGE
      └─ audit: PROMOTION_CREATED / UPDATED / PAUSED
      │
      ▼
  InMemoryMerchantRepository
```

## Promotion types

| Type | Value | Typical use |
|------|-------|-------------|
| Sale price | `sale_price` | Temporary sale amount |
| Voucher | `voucher` | Voucher-style discount description |
| Coupon code | `coupon_code` | Code string + terms |
| Free shipping | `free_shipping` | Shipping promo |
| Bundle offer | `bundle_offer` | Multi-item package |
| Limited time | `limited_time` | Urgency window |
| Seasonal | `seasonal` | Seasonal campaign messaging |
| Cashback | `cashback` | Cashback description (not real payout) |

## Promotion status

| Status | Meaning |
|--------|---------|
| `draft` | Not yet scheduled |
| `scheduled` | Future `starts_at` |
| `active` | Currently in effect (metadata) |
| `expired` | Past `ends_at` |
| `paused` | Merchant paused |
| `cancelled` | Cancelled |

```
draft ──► scheduled ──► active ──► expired
              │            │
              └────────────┴── pause ──► paused
                               cancel ──► cancelled
```

## DealScore independence

| Claim | Reality in Sprint 21 |
|-------|----------------------|
| “Promotion boosts DealScore” | **False** — `dealscore_independent=True` |
| “Active promo changes organic rank” | **False** — no ranking engine input |
| “Cashback pays merchants/users” | **False** — description only |

Promotions may appear in merchant analytics rollups (`active_promotions`) as
demo counters. Those counters are observational and do not feed recommendation
scoring.

Sponsored campaigns are a separate surface (`SPONSORED_CAMPAIGNS.md`). A
promotion is not a sponsored placement; sponsored content is still rendered
separately from organic recommendations.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/merchants/{id}/promotions` | List promotions |
| POST | `/api/v1/merchants/{id}/promotions` | Create promotion |
| PUT | `/api/v1/merchants/{id}/promotions/{promotion_id}` | Update |
| POST | `/api/v1/merchants/{id}/promotions/{promotion_id}/pause` | Pause |

Requires `promotion_manage`.

## Fields

`title`, `description`, `promotion_type`, `status`, `coupon_code`,
`sale_price`, `currency`, `terms`, `product_ids`, `offer_ids`, `starts_at`,
`ends_at`, `cashback_description`, `dealscore_independent`.

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
- Promotions never auto-boost DealScore
- Cashback / coupon fields are descriptive only — no redemption engine
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
