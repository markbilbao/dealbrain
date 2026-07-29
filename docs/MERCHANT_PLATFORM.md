# Merchant Platform (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/`  
**Domain entities:** `app/domain/entities/merchant.py`  
**Repository ports:** `app/domain/interfaces/merchant_repository.py`  
**In-memory store:** `InMemoryMerchantRepository` in `app/merchant/memory.py`  
**Services:** `MerchantAuthService`, `MerchantOrganizationService`, `MerchantMembershipService`, `MerchantProductService`, `MerchantOfferService`, `MerchantPromotionService`, `MerchantCampaignService`, `MerchantAnalyticsService`, `MerchantAdminService`  
**API:** `/api/v1/merchants`, `/api/v1/admin/...`

## Overview

Merchant Platform v1 is a **demo** merchant workspace for DealBrain. Seeded
organizations can manage profiles, invite members, submit products and offers,
create promotions and sponsored campaign drafts, and view demo analytics —
without ever influencing organic DealScore or recommendation ranking.

**Hard rule:** Merchant tools never directly manipulate organic DealScore or
recommendation ranking. Sponsored content is rendered separately from organic
recommendations. Merchant-submitted data uses `MERCHANT_SUBMITTED` provenance
and is never labeled as verified live marketplace data.

```
Merchant actor (Bearer demo-token)
      │
      ▼
  MerchantAuthService.resolve_actor()
      │  RBAC + org isolation
      ▼
  Application services (app/services/merchant_*.py)
      │
      ├─ org / membership / product / offer
      ├─ promotion / campaign / analytics
      └─ admin review (INTERNAL_ADMIN only)
      │
      ▼
  InMemoryMerchantRepository (demo store — no production DB)
```

## Architecture

```
API (/api/v1/merchants/{...}  +  /api/v1/admin/...)
      │
      ▼
  Application services (app/services/merchant_*.py)
      │
      ├─ MerchantAuthService              demo tokens → MerchantActor
      ├─ MerchantOrganizationService      org CRUD / archive
      ├─ MerchantMembershipService        invite / role / remove
      ├─ MerchantProductService           submissions + matching
      ├─ MerchantOfferService             offer CRUD / deactivate
      ├─ MerchantPromotionService         promo lifecycle
      ├─ MerchantCampaignService          sponsored drafts
      ├─ MerchantAnalyticsService         demo dashboards + ranking notes
      └─ MerchantAdminService             approve / suspend / verify
      │
      ▼
  Pure helpers (app/merchant/)
      ├─ matching/                       MerchantProductMatcher
      ├─ security/permissions.py         RBAC + isolation
      ├─ security/validation.py          input guards
      ├─ security/redaction.py           secret redaction + audit hook
      └─ fixtures.py                     demo orgs / tokens / catalog
      │
      ▼
  InMemoryMerchantRepository (demo store — no DB, no billing, no email)
```

## Hard rules

| Rule | Enforcement |
|------|-------------|
| Never manipulate organic DealScore / ranking | Services expose no DealScore write APIs; campaigns set `organic_ranking_independent=True` |
| Sponsored content separate from organic | Placements carry `SPONSORED_LABEL`; rendered outside organic recommendation lists |
| Merchant data provenance | `MerchantSourceMode.MERCHANT_SUBMITTED` + `MERCHANT_SOURCE_LABEL` on products/offers |
| Demo-only surface | Fixture tokens, in-memory store, explicit limitations on `/merchants/meta/demo` |

## Core concepts

| Concept | Entity / enum | Notes |
|---------|---------------|-------|
| Organization | `MerchantOrganization` | Tenant; statuses pending → active → suspended / archived |
| Membership | `MerchantMembership` | Account + role inside an org |
| Product submission | `MerchantProductSubmission` | Draft → review lifecycle; matching via Sprint 18 matcher |
| Offer submission | `MerchantOfferSubmission` | Price / availability under `MERCHANT_SUBMITTED` |
| Promotion | `MerchantPromotion` | Informational; `dealscore_independent=True` |
| Campaign | `MerchantCampaign` | Sponsored draft framework; no billing |
| Analytics | `MerchantAnalyticsSummary` | Demo-labeled; affiliate read-only |

## API surface (summary)

| Area | Base path | Purpose |
|------|-----------|---------|
| Demo meta | `GET /api/v1/merchants/meta/demo` | Demo accounts, tokens, limitations |
| Organizations | `/api/v1/merchants` | Create / list / get / update / archive |
| Members | `/api/v1/merchants/{id}/members` | List / invite / role / remove |
| Products | `/api/v1/merchants/{id}/products` | Submissions, submit, withdraw |
| Offers | `/api/v1/merchants/{id}/offers` | Offer CRUD / deactivate |
| Promotions | `/api/v1/merchants/{id}/promotions` | Promo CRUD / pause |
| Campaigns | `/api/v1/merchants/{id}/campaigns` | Sponsored drafts / pause / resume |
| Analytics | `/api/v1/merchants/{id}/analytics` | Demo dashboard + audit log |
| Admin | `/api/v1/admin/...` | Internal review workflows |

Auth: `Authorization: Bearer <demo-token>` (or raw demo token). Tokens are
opaque demo session keys from `app/merchant/fixtures.py` — not production
credentials.

## Documentation map

| Doc | Topic |
|-----|-------|
| [MERCHANT_ROLES.md](MERCHANT_ROLES.md) | Roles and permission matrix |
| [MERCHANT_PRODUCT_SUBMISSIONS.md](MERCHANT_PRODUCT_SUBMISSIONS.md) | Product lifecycle and matching |
| [MERCHANT_OFFER_MANAGEMENT.md](MERCHANT_OFFER_MANAGEMENT.md) | Offer CRUD and provenance |
| [MERCHANT_PROMOTIONS.md](MERCHANT_PROMOTIONS.md) | Promotion types; DealScore independence |
| [SPONSORED_CAMPAIGNS.md](SPONSORED_CAMPAIGNS.md) | Campaign framework and labeling |
| [MERCHANT_ANALYTICS.md](MERCHANT_ANALYTICS.md) | Demo analytics and ranking explanations |
| [MERCHANT_SECURITY.md](MERCHANT_SECURITY.md) | Auth, RBAC, isolation, audit, redaction |
| [MERCHANT_ADMIN_REVIEW.md](MERCHANT_ADMIN_REVIEW.md) | Internal admin workflows |

## Relationship to Affiliate Revenue Engine

Sprint 20 affiliate merchants remain a separate registry (`app/affiliate/`).
Merchant Platform orgs may optionally link via `affiliate_merchant_id` for
**read-only** affiliate performance views. Affiliate commission still never
feeds DealScore. Sprint 20 docs keep their own scope (including “No merchant
portal”); this platform is the Sprint 21 demo workspace layered on top.

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
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
- Sponsored content rendered separately from organic recommendations
- Merchant-submitted data uses MERCHANT_SUBMITTED provenance
