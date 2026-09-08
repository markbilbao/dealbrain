# Sprint 27.3 — Staging transactional-email E2E evidence template

**Document type:** Operator evidence harness  
**Sprint definition:** [`../sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md`](../sprints/SPRINT_27_TRANSACTIONAL_IDENTITY_EMAIL.md)  
**DNS runbook:** [`../../runbooks/EXT_09_RESEND_DNS.md`](../../runbooks/EXT_09_RESEND_DNS.md)  
**Status:** Historical harness. **Do not rewrite the blank tables below as if they were the original execution log.** Completed 2026-09-08 owner/operator + independent-check evidence lives at [`SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md).

The 2026-08/27.3 blank template is retained so later operators can re-run the same checks. It is not current closure status.

Use this after EXT-09 is verified in Resend and staging is running the 27.3+ digest with `dealbrain/staging/resend_api_key` attached.

## Forbidden evidence contents

Never store in this file, screenshots, tickets, or committed logs:

- API keys (`RESEND_API_KEY`, Secrets Manager values)
- raw session cookies / bearer tokens
- password-reset, verification, or email-change tokens
- passwords
- full provider response bodies that include credentials

Sanitize screenshots before committing. Action URLs in screenshots must have the `token=` query value redacted.

## Staging identity (fill at execution)

| Field | Value |
|-------|--------|
| Environment | staging |
| Deployed SHA | _fill after deploy_ |
| HTTP hostname used | _fill — approved consumer action host is `staging.piqsavi.com`; current ALB DNS is not that host_ |
| `PUBLIC_APP_BASE_URL` observed | _must be the trusted configured origin, not a request Host_ |
| `/health` `identity_email_adapter` | _fill_ |
| `/health` `identity_email_ready` | must remain `false` until this package is completed and accepted — do not flip from config alone |
| Resend domain verified | YES / NO — EXT-09 |
| Staging secret attached | YES / NO — `dealbrain/staging/resend_api_key` |

Approved staging PiqSavi action-link host: `https://staging.piqsavi.com`. That hostname is the configured trusted origin. It is **not** automatic proof that DNS or TLS currently resolve. If the operator must use the raw ALB hostname for HTTP probes, record that separately and still require email links to use `PUBLIC_APP_BASE_URL`.

## Test accounts (staging only)

Use owner-controlled real inboxes that can receive Resend mail. Do not use customer mailboxes.

| Role | Address (record locally; redact local-part if committing) |
|------|----------------------------------------------------------|
| Current staging account | |
| Proposed new email (email-change) | |

Passwords stay in the operator password manager. Do not paste them here.

---

## A. Password reset

| Step | Pass? | Notes (no secrets) |
|------|-------|--------------------|
| Request reset for the real staging test account | | Enumeration-safe accepted body; no `*_token_demo_only` |
| Email arrives in the real inbox | | Record Resend message id if shown in dashboard, not the raw token |
| Link host is the approved staging PiqSavi host from `PUBLIC_APP_BASE_URL` | | Must not be request Host / ALB Host / user URL |
| Reset completes | | |
| Old password fails | | |
| New password succeeds | | |
| Token reuse fails | | Same generic invalid/expired error |
| Old sessions revoked | | Prior bearer sessions rejected |

## B. Email verification

| Step | Pass? | Notes (no secrets) |
|------|-------|--------------------|
| Verification email arrives | | |
| Link completes verification | | Account `email_verified=true` |
| Token reuse fails | | |

## C. Email change

| Step | Pass? | Notes (no secrets) |
|------|-------|--------------------|
| Authenticated user re-enters current password | | Wrong password → `Invalid credentials.` |
| Confirmation reaches the proposed new inbox | | Old email unchanged at this point |
| Old email remains until confirmation | | |
| Confirmation changes email | | |
| New email becomes verified | | |
| Old sessions revoked | | Including the confirming session |
| Old email receives security notice | | Token-free “account email was changed” |
| Token reuse fails | | |

## Branding / sender checks

| Check | Pass? |
|-------|-------|
| Consumer subject/body uses PiqSavi | |
| No unintended DealBrain branding in the mail | |
| From display name is PiqSavi | |
| From address matches `TRANSACTIONAL_EMAIL_FROM` | |

## Explicit non-claims until every required row is evidenced

Historical template non-claims (kept for the blank harness):

- Completing this template file itself does not close Sprint 27
- Production secret is not attached (Sprint 41)
- EXT-09 is not verified by this template existing
- `/health` `identity_email_ready` must not be treated as true from configuration alone

Current (2026-09-08) status is recorded in [`SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md): inbox E2E passed; EXT-09 Resend **Verified** still required; Sprint 27 still open.
