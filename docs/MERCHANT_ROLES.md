# Merchant Roles & Permissions (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/security/`  
**Domain entities:** `MerchantRole`, `MerchantPermission`, `ROLE_PERMISSIONS` in `app/domain/entities/merchant.py`  
**Enforcement:** `app/merchant/security/permissions.py`  
**Services:** `MerchantMembershipService`, `MerchantAuthService`

## Overview

Merchant Platform uses least-privilege roles scoped to an organization.
`INTERNAL_ADMIN` is a DealBrain staff role (not an org membership) with full
access for review workflows.

**Hard rule:** Permission checks never grant the ability to write DealScore,
reorder organic recommendations, or relabel merchant data as live/verified.
Merchant tools never directly manipulate organic DealScore or recommendation
ranking.

```
Bearer demo-token
      │
      ▼
  MerchantAuthService.resolve_actor(org_id?)
      │
      ├─ MerchantAccount (is_internal_admin?)
      └─ MerchantMembership (role) when org-scoped
      │
      ▼
  MerchantActor.has_permission(permission)
      │
      ▼
  require_permission / require_membership / require_internal_admin
```

## Architecture

```
API route
      │
      ▼
  _actor(auth, Authorization, organization_id)
      │
      ▼
  Service method
      │
      ├─ require_membership(actor, org_id)
      ├─ require_permission(actor, MerchantPermission.*)
      └─ require_internal_admin(actor)   ← admin routes only
      │
      ▼
  ROLE_PERMISSIONS[MerchantRole] → frozenset[MerchantPermission]
```

## Roles

| Role | Scope | Intent |
|------|-------|--------|
| `OWNER` | Organization | Full org control including all permissions |
| `ADMIN` | Organization | Manage org, users, catalog, campaigns, analytics, audit |
| `MANAGER` | Organization | Catalog, promotions, campaigns, analytics (no user/org admin) |
| `ANALYST` | Organization | Analytics + audit log read |
| `EDITOR` | Organization | Product / offer / promotion edits |
| `VIEWER` | Organization | Analytics access only |
| `INTERNAL_ADMIN` | Platform | Staff review: verification, approve/reject, suspend |

## Permissions

| Permission | Meaning |
|------------|---------|
| `organization_manage` | Update profile, archive org |
| `user_manage` | Invite, change role, remove members |
| `product_submit` | Create / update / submit / withdraw products |
| `offer_submit` | Create / update / deactivate offers |
| `promotion_manage` | Create / update / pause promotions |
| `analytics_access` | Dashboards, product performance, ranking explanations |
| `campaign_manage` | Sponsored campaign drafts / pause / resume |
| `verification_review` | Update verification status (internal) |
| `audit_log_access` | Read org audit log |
| `admin_review` | Approve / reject submissions, suspend / activate orgs |

## Role → permission matrix

| Permission | OWNER | ADMIN | MANAGER | ANALYST | EDITOR | VIEWER | INTERNAL_ADMIN |
|------------|:-----:|:-----:|:-------:|:-------:|:------:|:------:|:--------------:|
| `organization_manage` | ✓ | ✓ | | | | | ✓ |
| `user_manage` | ✓ | ✓ | | | | | ✓ |
| `product_submit` | ✓ | ✓ | ✓ | | ✓ | | ✓ |
| `offer_submit` | ✓ | ✓ | ✓ | | ✓ | | ✓ |
| `promotion_manage` | ✓ | ✓ | ✓ | | ✓ | | ✓ |
| `analytics_access` | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ |
| `campaign_manage` | ✓ | ✓ | ✓ | | | | ✓ |
| `verification_review` | ✓ | | | | | | ✓ |
| `audit_log_access` | ✓ | ✓ | | ✓ | | | ✓ |
| `admin_review` | ✓ | | | | | | ✓ |

`OWNER` and `INTERNAL_ADMIN` receive `frozenset(MerchantPermission)` (all
permissions). Org `OWNER` still cannot act as another tenant without
membership; `INTERNAL_ADMIN` bypasses org membership via
`require_membership(..., allow_internal_admin=True)`.

## Membership lifecycle

```
OWNER/ADMIN invite(email, role)
      │
      ▼
  MerchantInvitation (PENDING)
      │  accept via POST /invitations/{id}/accept
      ▼
  MerchantMembership (active) + ROLE_PERMISSIONS
      │
      ├─ change_role → ROLE_CHANGED audit
      └─ remove_member → MEMBERSHIP_REMOVED audit
```

Invitations are in-app only. **No external email sending** — invitees use
demo accounts / tokens from fixtures or meta endpoint.

## Isolation

| Check | Error |
|-------|-------|
| Actor org ≠ requested org | `MerchantIsolationError` (HTTP 403) |
| Missing permission | `MerchantAuthorizationError` (HTTP 401) |
| Non-admin on `/api/v1/admin/...` | `MerchantAuthorizationError` |

Actors resolve membership only for the `organization_id` on the request path.
Cross-tenant reads/writes are rejected before service business logic runs.

## API

| Method | Path | Permission |
|--------|------|------------|
| GET | `/api/v1/merchants/{id}/members` | membership |
| POST | `/api/v1/merchants/{id}/invitations` | `user_manage` |
| PUT | `/api/v1/merchants/{id}/members/{member_id}` | `user_manage` |
| DELETE | `/api/v1/merchants/{id}/members/{member_id}` | `user_manage` |
| POST | `/api/v1/merchants/invitations/{id}/accept` | authenticated invitee |

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
- Roles never unlock organic ranking or DealScore writes
- Merchant-submitted data uses MERCHANT_SUBMITTED provenance regardless of role
