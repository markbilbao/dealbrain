# Email outage runbook (identity transactional mail)

**Sprint:** 27.1 foundation + 27.2 email-change  
**Provider:** Resend  
**Port:** `EmailSender` / `ResendEmailSender`  
**EXT-08:** `applied` (account only)  
**EXT-09:** `applied` (DNS plan only — not verified)

This runbook is for identity password-reset, verification, and email-change
mail. It does not cover Sprint 19 notification digests.

## Symptoms

- Users do not receive reset, verification, or email-change mail
- Auth audit events show `email_delivery_failed`
- Production startup fails when Resend is missing; staging may still boot
  with `NullEmailSender` when `LAUNCH_STRICT_STARTUP` is false

## Fail-closed rules

- Production must not start with `NullEmailSender`
- Staging may remain operational with `NullEmailSender`, but health/config
  must report `identity_email_ready=false` — that is not email readiness
- API request routes stay enumeration-safe even when Resend fails
- Do not enable `ALLOW_DEMO_RESET_TOKENS` outside development
- Do not log `RESEND_API_KEY`, raw tokens, or passwords

## Immediate actions

1. Confirm `APP_ENV`, `TRANSACTIONAL_EMAIL_PROVIDER=resend`, and that
   `RESEND_API_KEY` is present from Secrets Manager (`resend_api_key`).
   Never print the key.
2. Confirm `TRANSACTIONAL_EMAIL_FROM` and `PUBLIC_APP_BASE_URL` match the
   intended PiqSavi sender and `https` public origin.
3. Check Resend dashboard delivery/failure status. Do not paste provider
   payloads containing credentials into tickets or logs.
4. If DNS/sender auth is the cause: EXT-09 is still plan-only until records
   are applied and Resend reports the domain verified. Do not claim
   production sender readiness.
5. Contingency: disable public self-serve reset/verify/email-change
   (invite-only) rather than turning on demo tokens in staging/production.

## Recovery

- Restore a valid Resend key in Secrets Manager and redeploy/restart.
- After EXT-09 DNS apply/verify, confirm a real inbox receive of reset,
  verify, and email-change mail before treating Sprint 27 as closable.

## What this does not cover

- Sprint 19 `EmailNotificationProvider` (still mock)
- Live staging inbox proof for email-change (27.2 code path exists; E2E not done)
- Distributed abuse controls (Sprint 40)
