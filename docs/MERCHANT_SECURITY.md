# Merchant Security (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/security/`  
**Domain entities:** `MerchantActor`, `MerchantAccount`, `MerchantAuditEvent` in `app/domain/entities/merchant.py`  
**Modules:** `permissions.py`, `validation.py`, `redaction.py`  
**Service:** `MerchantAuthService`

## Overview

Sprint 21 merchant security is demo-scale but structured: opaque demo bearer
tokens, RBAC, org isolation, input validation, audit events, and secret
redaction. It does not claim production identity verification or durable
compliance controls.

**Hard rule:** Security layers protect tenants and data hygiene; they never
grant ranking or DealScore mutation. Merchant tools never directly manipulate
organic DealScore or recommendation ranking. Merchant-submitted data uses
MERCHANT_SUBMITTED provenance.

```
Authorization: Bearer <demo-token>
      │
      ▼
  MerchantAuthService.require_token / resolve_actor
      │
      ├─ RateLimiterHook (in-process)
      ├─ MerchantAccount (+ is_internal_admin)
      └─ MerchantMembership for org routes
      │
      ▼
  permissions.require_*  +  validation.*  +  redact_secrets
      │
      ▼
  MerchantAuditHook → MerchantAuditEvent
```

## Architecture

```
API dependency injection
      │
      ▼
  MerchantAuthService
      │
      ├─ token → account (fixtures / memory)
      └─ actor (account + membership + org_id)
      │
      ▼
  app/merchant/security/
      ├─ permissions.py     RBAC + isolation
      ├─ validation.py      emails, URLs, lengths, ids
      └─ redaction.py       secret scrub + rate limit + audit hook
      │
      ▼
  Services write redacted audit metadata only
```

## Authentication

| Mechanism | Detail |
|-----------|--------|
| Header | `Authorization: Bearer <demo-token>` or raw demo token |
| Tokens | Deterministic demo keys in `app/merchant/fixtures.py` |
| Accounts | `MerchantAccount` with optional `demo_token` (omitted from public dict) |
| Production auth | **Not implemented** — no OAuth, MFA, or password login for merchants |

`GET /api/v1/merchants/meta/demo` lists demo accounts and tokens for local use.

## RBAC

See [MERCHANT_ROLES.md](MERCHANT_ROLES.md). Enforcement helpers:

| Helper | Behavior |
|--------|----------|
| `require_permission` | Raises `MerchantAuthorizationError` |
| `require_membership` | Org match or internal admin bypass |
| `require_internal_admin` | Staff-only admin routes |

## Isolation

Cross-organization access raises `MerchantIsolationError` (HTTP 403).
Membership must be active. Internal admins may cross tenants for review
workflows only; they still cannot write organic ranking.

## Validation

`app/merchant/security/validation.py` guards:

- Email format / length
- Safe identifiers
- URL schemes (`http` / `https` only); blocks credential query params
- Title / description / text max lengths
- Image URL count caps

Invalid input → `MerchantValidationError` (HTTP 400).

## Audit

`MerchantAuditHook` records `MerchantAuditEvent` rows (`MerchantAuditAction`
vocabulary: org, membership, product, offer, promotion, campaign, verification,
match review). Metadata passes through `redact_secrets` before persistence.

Audit log API: `GET /api/v1/merchants/{id}/audit-log` (`audit_log_access`).

## Redaction

`redact_secrets` recursively replaces values for keys matching password,
token, api_key, secret, authorization, credential, SSN, passport, tax_id,
bank_account, etc. with `***REDACTED***`.

`MerchantAccount.to_dict()` intentionally omits `demo_token`.

## Rate limiting

`RateLimiterHook` is an in-process sliding window (default 60 attempts / 60s).
Not a production WAF; resets on process restart.

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
- Demo tokens are not production credentials
- Verification document references are architecture-only — contents never stored
- Merchant-submitted data uses MERCHANT_SUBMITTED provenance
- Sponsored content rendered separately from organic recommendations
