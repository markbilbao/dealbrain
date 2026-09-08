# Email outage runbook (identity transactional mail)

**Sprint:** 27.1 foundation + 27.2 email-change + 27.3 cutover readiness + 27.4 consumer confirmation UX  
**Provider:** Resend  
**Port:** `EmailSender` / `ResendEmailSender`  
**EXT-08:** `applied` (account-establishment screenshot; staging delivery evidenced 2026-09-08)  
**EXT-09:** `approved` / **VERIFIED** (public DNS + owner-observed Resend domain **Verified**, 2026-09-08). Operator steps: [`EXT_09_RESEND_DNS.md`](EXT_09_RESEND_DNS.md)  
**Staging inbox E2E:** verify / reset / email-change **passed** 2026-09-08 — [`../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../roadmap/evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md)

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
4. If DNS/sender auth is the cause: follow [`EXT_09_RESEND_DNS.md`](EXT_09_RESEND_DNS.md).
   EXT-09 sender-domain evidence is **Verified** as of 2026-09-08 (public DNS
   plus Resend dashboard). Do not claim production sender cutover. Staging
   `PUBLIC_APP_BASE_URL=https://staging.piqsavi.com` is the trusted link
   origin. HTTPS for that host was independently confirmed on 2026-09-08;
   that is TLS evidence for staging, not a substitute for DKIM/SPF records.
5. Contingency: disable public self-serve reset/verify/email-change
   (invite-only) rather than turning on demo tokens in staging/production.

## Recovery

- Restore a valid Resend key in Secrets Manager and redeploy/restart.
- EXT-09 Resend **Verified** and staging inbox receive of reset, verify, and
  email-change mail are evidenced on 2026-09-08. Sprint 27 still does not
  close until the designed `identity_email_status().ready` gate is updated
  in a separate code PR, that digest is deployed to staging, and `/health`
  reports `identity_email_ready=true`.

## What this does not cover

- Sprint 19 `EmailNotificationProvider` (still mock)
- Production email live / production `RESEND_API_KEY` attach (Sprint 41)
- Distributed abuse controls (Sprint 40)
