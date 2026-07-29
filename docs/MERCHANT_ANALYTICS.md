# Merchant Analytics (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/analytics/`  
**Domain entities:** `MerchantAnalyticsSummary`, `MerchantProductPerformance`, `MerchantAffiliatePerformance`, `RankingExplanation` in `app/domain/entities/merchant.py`  
**Service:** `MerchantAnalyticsService`  
**Label constant:** `DEMO_ANALYTICS_LABEL` = “Demo analytics — simulated, not live sales reporting”

## Overview

Merchant analytics expose **demo / simulated** performance rollups for an
organization: views, affiliate clicks, watchlist activity, and safe ranking
explanations. Affiliate performance is read-only and optionally linked via
`affiliate_merchant_id`.

**Hard rule:** Analytics are observational. They never write DealScore or
reorder recommendations. Ranking explanations are informational only —
merchants cannot alter organic ranking. Merchant tools never directly
manipulate organic DealScore or recommendation ranking.

```
ANALYST+ requests dashboard
      │
      ▼
  MerchantAnalyticsService.get_analytics(org_id)
      │  simulated=True, DEMO_ANALYTICS_LABEL
      ├─ product performance rows
      ├─ affiliate summary (read-only)
      └─ active promo / campaign counts
      │
      ▼
  ranking-explanation → RankingExplanation (no write API)
```

## Architecture

```
API
  /merchants/{id}/analytics
  /merchants/{id}/products/{product_id}/performance
  /merchants/{id}/products/{product_id}/ranking-explanation
  /merchants/{id}/audit-log
      │
      ▼
  MerchantAnalyticsService
      │
      ├─ require_membership + ANALYTICS_ACCESS (audit: AUDIT_LOG_ACCESS)
      ├─ demo aggregates from in-memory / fixture signals
      └─ optional AffiliateReportingService read (no mutation)
      │
      ▼
  Response labeled simulated / demo
```

## Dashboard metrics

| Metric | Notes |
|--------|-------|
| `product_views` / `offer_views` | Demo counters |
| `affiliate_clicks` | From affiliate demo data when linked |
| `click_through_rate` | Derived demo ratio |
| `attributed_conversions` | Simulated / demo affiliate statuses |
| `estimated_commission` | Demo estimate — not a payable amount |
| `watchlist_additions` / `alert_activity` | Engagement signals |
| `comparison_appearances` / `recommendation_appearances` | Visibility counters |
| `active_promotions` / `active_campaigns` | Lifecycle counts |
| `simulated` | Always true for demo store |

## Affiliate performance (read-only)

`MerchantAffiliatePerformance` summarizes clicks, attributed conversions, and
estimated revenue when an org links `affiliate_merchant_id` to the Sprint 20
affiliate registry.

| Property | Value |
|----------|-------|
| `read_only` | `True` |
| `simulated` | Demo-labeled |
| Mutations | None — no commission edits, no payout triggers |

Affiliate data still never feeds DealScore (Sprint 20 hard rule preserved).

## Ranking explanations

`RankingExplanation` returns safe factors (`factor`, `contribution`, `detail`)
such as data freshness, price competitiveness, or seller quality **as
informational strings**.

| Guarantee | Detail |
|-----------|--------|
| `organic_ranking_independent` | `True` |
| Note | “Explanations are informational only — merchants cannot alter organic ranking.” |
| No proprietary leak | Avoids private model weights / competitor secrets |

There is no endpoint to “boost,” “pin,” or override organic rank from analytics.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/merchants/{id}/analytics` | Org dashboard |
| GET | `/api/v1/merchants/{id}/products/{product_id}/performance` | Per-product row |
| GET | `/api/v1/merchants/{id}/products/{product_id}/ranking-explanation` | Safe explanation |
| GET | `/api/v1/merchants/{id}/audit-log` | Audit events (separate permission) |

Requires `analytics_access` (audit log requires `audit_log_access`).

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
- Demo analytics — not live sales reporting unless backed by affiliate demo data
- Affiliate views are read-only; no payout or invoice generation
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
