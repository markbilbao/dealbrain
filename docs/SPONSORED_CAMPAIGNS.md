# Sponsored Campaigns (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/campaigns/`  
**Domain entities:** `MerchantCampaign`, `MerchantCampaignPlacement`, `MerchantCampaignBudget`, `CampaignPlacementType`, `MerchantCampaignStatus` in `app/domain/entities/merchant.py`  
**Service:** `MerchantCampaignService`  
**Label constant:** `SPONSORED_LABEL` = “Sponsored — not an organic recommendation”

## Overview

Sponsored campaigns are a **draft framework** for labeled merchant placements
(sponsored products, featured offers, collections, banners). Budget fields are
metadata only.

**Hard rules:**
- Sponsored content rendered separately from organic recommendations
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
- `organic_ranking_independent=True` on every campaign and placement
- No real billing, payment collection, or auction that alters organic rank

```
MANAGER+ creates campaign draft
      │
      ▼
  MerchantCampaignService.create_campaign()
      │  sponsored_label = SPONSORED_LABEL
      │  organic_ranking_independent = True
      │  budget.billing = not_implemented
      ▼
  placements (product_ids / offer_ids)
      │
      ▼
  Render path (future UI): sponsored rail ≠ organic list
```

## Architecture

```
API (/api/v1/merchants/{id}/campaigns)
      │
      ▼
  MerchantCampaignService
      │
      ├─ create / update / list
      ├─ pause / resume
      └─ (no charge / no invoice / no rank write)
      │
      ├─ require_membership + CAMPAIGN_MANAGE
      └─ audit: CAMPAIGN_CREATED / UPDATED / PAUSED / RESUMED / CANCELLED
      │
      ▼
  InMemoryMerchantRepository
```

## Placement types

| Type | Value | Notes |
|------|-------|-------|
| Sponsored product | `sponsored_product` | Product ids + sponsored label |
| Featured offer | `featured_offer` | Offer ids + sponsored label |
| Sponsored collection | `sponsored_collection` | Grouped product set |
| Banner placement | `banner_placement` | Banner slot metadata |

Every placement serializes `sponsored_label` and
`organic_ranking_independent: true`.

## Campaign status

| Status | Meaning |
|--------|---------|
| `draft` | Editable draft |
| `pending_review` | Awaiting internal review |
| `scheduled` | Future window |
| `active` | Metadata-active (still no organic rank change) |
| `paused` | Merchant or admin paused |
| `cancelled` | Cancelled |
| `completed` | Window ended |
| `rejected` | Internal rejection |

```
draft ──► pending_review ──► scheduled ──► active ──► completed
                │                 │           │
                └─ rejected       └───────────┴─ pause / cancel
```

## Budget — no billing

`MerchantCampaignBudget` stores `currency`, optional `daily_budget` /
`total_budget`, and notes:

> Budget metadata only — no real billing or payment collection.

Serialization includes `"billing": "not_implemented"`. There is no charge
API, invoice object, payment method, or spend ledger.

## Separation from organic ranking

| Organic recommendations | Sponsored campaigns |
|-------------------------|---------------------|
| DealScore / match ranking | Labeled placements only |
| Unaffected by campaign status | `organic_ranking_independent=True` |
| No sponsored label required | Always `SPONSORED_LABEL` |

Activating a campaign never injects boost factors into DealScore. Affiliate
attribution models may reference `external_campaign` as a future hook
(Sprint 20), but that does not reorder organic results.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/merchants/{id}/campaigns` | List campaign drafts |
| POST | `/api/v1/merchants/{id}/campaigns` | Create draft |
| PUT | `/api/v1/merchants/{id}/campaigns/{campaign_id}` | Update |
| POST | `/api/v1/merchants/{id}/campaigns/{campaign_id}/pause` | Pause |
| POST | `/api/v1/merchants/{id}/campaigns/{campaign_id}/resume` | Resume |

Requires `campaign_manage`.

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
- No ad auction, bid landscape, or real-time spend control
- Sponsored content rendered separately from organic recommendations
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
