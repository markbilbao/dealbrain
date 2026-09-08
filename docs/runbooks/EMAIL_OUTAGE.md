# Email outage runbook (identity transactional mail)

**Sprint:** 27.1 foundation + 27.2 email-change + 27.3 cutover readiness + 27.4 consumer confirmation UX  
**Provider:** Resend  
**Port:** `EmailSender` / `ResendEmailSender`  
**EXT-08:** `applied` (account-establishment screenshot; staging delivery evidenced 2026-09-08)  
**EXT-09:** `applied` (public DNS resolvable 2026-09-08; Resend **Verified** not independently established). Operator steps: [`EXT_09_RESEND_DNS.md`](EXT_09_RESEND_DNS.md)  
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
   EXT-09 stays open until Resend reports the domain verified and sanitized
   evidence is retained. Public DNS resolvability (2026-09-08) is not that
   proof. Do not claim production sender readiness. Staging
   `PUBLIC_APP_BASE_URL=https://staging.piqsavi.com` is the trusted link
   origin. HTTPS for that host was independently confirmed on 2026-09-08;
   that is TLS evidence for staging, not EXT-09 DKIM/SPF proof.
5. Contingency: disable public self-serve reset/verify/email-change
   (invite-only) rather than turning on demo tokens in staging/production.

## Recovery

- Restore a valid Resend key in Secrets Manager and redeploy/restart.
- After EXT-09 Resend **Verified** evidence is retained, update the designed
  `identity_email_status().ready` gate in a separate code PR before treating
  Sprint 27 as closable. Staging inbox receive of reset, verify, and
  email-change mail was already evidenced on 2026-09-08.

## What this does not cover

- Sprint 19 `EmailNotificationProvider` (still mock)
- Resend dashboard domain **Verified** (EXT-09 still open as of 2026-09-08)
- Distributed abuse controls (Sprint 40)
