# Merchant Admin Review (Sprint 21)

**Status:** Sprint 21  
**Package:** `app/merchant/`  
**Domain entities:** `MerchantVerification`, `MerchantMatchReview`, `SubmissionStatus`, `MerchantOrgStatus` in `app/domain/entities/merchant.py`  
**Service:** `MerchantAdminService`  
**API:** `/api/v1/admin/...`  
**Auth:** `INTERNAL_ADMIN` via `require_internal_admin`

## Overview

Internal admin workflows let DealBrain staff review product submissions,
update verification status, and suspend or activate merchant organizations.
Verification stores **document references only** — never identity document
bytes.

**Hard rules:**
- Admin approval does not relabel data as live/verified marketplace provenance
- Merchant-submitted data uses MERCHANT_SUBMITTED provenance even after approve
- Ambiguous matches are not silently merged
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
- Sponsored content rendered separately from organic recommendations

```
INTERNAL_ADMIN (demo-token-internal-admin)
      │
      ▼
  MerchantAdminService
      │
      ├─ list / approve / reject submissions
      ├─ suspend / activate organizations
      └─ update verification status
      │
      ▼
  Audit events + optional review notes
```

## Architecture

```
API (/api/v1/admin/...)
      │
      ▼
  MerchantAuthService.resolve_actor()
      │
      ▼
  MerchantAdminService
      │  require_internal_admin(actor)
      │
      ├─ MerchantSubmissionRepository
      ├─ MerchantOrganizationRepository
      ├─ MerchantAuxiliaryRepository (verification / match reviews)
      └─ MerchantAuditRepository
      │
      ▼
  InMemoryMerchantRepository (demo store)
```

## Submission review

| Action | Effect |
|--------|--------|
| List | Filter by status across orgs |
| Approve | `status=approved`; provenance remains `MERCHANT_SUBMITTED` |
| Reject | `status=rejected` or `needs_changes` when requested |
| Ambiguous match | May approve as new listing without forcing `matched_product_id` |

```
submitted / under_review / needs_changes
      │
      ├─ approve ──► approved (+ notes)
      └─ reject  ──► rejected | needs_changes
```

## Organization controls

| Action | Org status |
|--------|------------|
| Suspend | `suspended` |
| Activate | `active` (from pending / inactive / suspended as allowed) |

Suspension does not delete data; it blocks normal merchant operations per
service checks. Archive remains an org-owner path on the merchant API.

## Verification

| Status | Meaning |
|--------|---------|
| `unverified` | Default |
| `pending_review` | Queued |
| `verified` | Staff-marked verified (demo) |
| `rejected` | Verification rejected |
| `expired` | Prior verification expired |

`MerchantVerification.document_references` are opaque future-architecture
refs. Responses include limitation text that documents are not stored.

## Match reviews

`MerchantMatchReview` records open ambiguity for a submission (`confidence`,
`candidate_ids`, `ambiguity`). Admins resolve via submission approve/reject
flows rather than silent auto-merge.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/admin/merchant-submissions` | List submissions |
| POST | `/api/v1/admin/merchant-submissions/{id}/approve` | Approve |
| POST | `/api/v1/admin/merchant-submissions/{id}/reject` | Reject / needs_changes |
| POST | `/api/v1/admin/merchants/{id}/suspend` | Suspend org |
| POST | `/api/v1/admin/merchants/{id}/activate` | Activate org |
| POST | `/api/v1/admin/merchants/{id}/verification` | Update verification status |

All routes require an internal admin actor.

## Audit actions

Typical events: `SUBMISSION_APPROVED`, `SUBMISSION_REJECTED`,
`ORGANIZATION_SUSPENDED`, `ORGANIZATION_ACTIVATED`, `VERIFICATION_UPDATED`,
`MATCH_REVIEW_CREATED`. Metadata is redacted via `redact_secrets`.

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
- Verification is status metadata only — no KYC vendor integration
- Approve never upgrades provenance away from MERCHANT_SUBMITTED
- Merchant tools never directly manipulate organic DealScore or recommendation ranking
