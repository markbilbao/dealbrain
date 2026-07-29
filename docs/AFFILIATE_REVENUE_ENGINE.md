# Affiliate Revenue Engine (Sprint 20)

**Status:** Sprint 20  
**Package:** `app/affiliate/`  
**Domain entities:** `app/domain/entities/affiliate.py`  
**Repository ports:** `app/domain/interfaces/affiliate_repository.py`  
**In-memory store:** `InMemoryAffiliateRepository` in `app/affiliate/memory.py`  
**Services:** `AffiliateMerchantService`, `AffiliateLinkService`, `AffiliateTrackingService`, `AffiliateReportingService`, `AffiliateDisclosureService`

## Overview

The Affiliate Revenue Engine lets DealBrain generate **demo** affiliate revenue
signals while preserving DealScore integrity.

**Hard rule:** Affiliate data is applied **only after** a recommendation has
already been selected. DealScore and ranking engines never receive commission,
payout, or tracking inputs.

```
Shopping Assistant / Recommendation
      │  rank by DealScore / match (NO commission)
      ▼
  top recommendation selected
      │
      ▼
  AffiliateLinkService.generate_for_recommendation()   ← post-rank only
      │
      ▼
  AffiliateTrackingService.track_click()
      │
      ▼
  AttributionEngine  →  AffiliateReportingService
```

## Architecture

```
API (/api/v1/affiliate/{link,click,report,merchant,disclosure})
      │
      ▼
  Application services (app/services/affiliate_*.py)
      │
      ├─ AffiliateMerchantService     merchant registry CRUD / activate / commission
      ├─ AffiliateLinkService         template + tracking params + deep links
      ├─ AffiliateTrackingService     clicks + conversion status + attribution
      ├─ AffiliateReportingService    clicks / CTR / revenue rollups
      └─ AffiliateDisclosureService   FTC / regional / merchant disclosure hooks
      │
      ▼
  Pure engines (app/affiliate/)
      ├─ linking/builder.py           AffiliateLinkBuilder
      ├─ attribution/engine.py        AttributionEngine
      ├─ disclosure/texts.py          select_disclosures()
      └─ reporting/aggregator.py      aggregate_revenue_report()
      │
      ▼
  InMemoryAffiliateRepository (demo store — no DB, no real networks)
```

## Merchant registry

Placeholder merchants only (Amazon, Shopee, Lazada, TikTok Shop, eBay, AliExpress).

Fields: `merchant_id`, `merchant_name`, `marketplace`, `country`,
`affiliate_network`, `tracking_template`, `commission_type`,
`commission_value`, `cookie_days`, `status`, `priority`, `created_at`,
`updated_at`, plus health / country restrictions.

**No real credentials.** Tracking templates use obvious `DEMO_*` tokens.

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST/GET | `/api/v1/affiliate/link` | Generate / list affiliate links |
| POST/GET | `/api/v1/affiliate/click` | Track / list clicks |
| POST | `/api/v1/affiliate/click/attribute` | Run attribution (simulated) |
| GET | `/api/v1/affiliate/report` | Revenue dashboard report |
| GET/POST/PATCH | `/api/v1/affiliate/merchant` | Merchant management |
| GET/POST | `/api/v1/affiliate/disclosure` | Disclosure text |

## Shopping Assistant integration

`ShoppingAssistantService` accepts an optional `affiliate_link_service`.
After the response (and top recommendation) is fully built, `_attach_affiliate_links`
decorates `processing["affiliate"]`. Ranking order and DealScore values are unchanged.

## Attribution models

`last_click`, `first_click`, `direct`, `organic`, `internal_recommendation`,
`external_campaign` (future campaign hook).

## Limitations

- **No real affiliate APIs**
- **No real commissions**
- **No real conversions** / network postbacks
- **No billing**
- **No payouts**
- **No merchant portal**
- **Demo / in-memory data only**
- Disclosure text is a **placeholder**, not legal advice
- Commission never influences DealScore or recommendation ranking
