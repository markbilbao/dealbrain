# Engineering retention map (Sprint 28)

**Status:** Engineering runbook — **not** a legal retention schedule, **not** a published Privacy Policy, **not** counsel approval.
**Does not** authorize purge jobs that claim statutory completeness.
**Counsel-owned:** legal retention periods, statutory exceptions, backup-erasure windows, DSAR deadlines.

This file maps **repository-evidenced technical TTLs** so operators can tell the difference between a product timeout and an approved legal retention rule. There is **no** privacy retention scheduler and **no** legal purge job in the application.

## Technical TTLs (product/security, not legal retention)

| Store / process | Technical TTL / lifetime | Source | Legal retention |
|-----------------|--------------------------|--------|-----------------|
| Bearer session (default) | 1 hour | `AuthService` `session_ttl_seconds=3600` | Counsel-owned; not encoded |
| Bearer session (remember-me) | 30 days | `remember_me_ttl_seconds=2_592_000` | Counsel-owned; not encoded |
| Password-reset token | 1 hour | `PASSWORD_RESET_TTL` | Counsel-owned; not encoded |
| Email-verification token | 1 day | `EMAIL_VERIFICATION_TTL` | Counsel-owned; not encoded |
| Email-change token | 1 day | `EMAIL_CHANGE_TTL` | Counsel-owned; not encoded |
| Shopping-assistant conversation | Default 1800s (config range 60–86400) | `AI_SHOPPING_CONVERSATION_TTL_SECONDS`; `cleanup_expired` | Counsel-owned; not encoded |
| First-party HTTP cookies (`piqsavi_decision_owner`, `piqsavi_delivery`, `piqsavi_shopping_market`) | Session cookies (no `max_age`) | Cookie setters | Counsel-owned; not encoded |
| `sessionStorage` `piqsavi_ask_conversation` | Tab/session | Consumer JS | Counsel-owned; not encoded |
| `sessionStorage` / `localStorage` `piqsavi_access_token` | Tab or remember-me device storage | `account.js` | Counsel-owned; not encoded |
| `localStorage` `piqsavi_remember_me` | Until cleared | `account.js` | Counsel-owned; not encoded |
| Account profile / saved items / consent rows | No product TTL | Live account store | Counsel-owned; deleted with the account on `POST /api/v1/auth/account/delete` |
| `user_platform.audit_events` | No product TTL | Security audit log | Retained on account delete; counsel-owned legal hold |
| HTTP / application logs | Ops/log pipeline | Not purged by account delete | Counsel-owned |
| Database backups / snapshots | Infra backup policy (Sprint 42) | Not claimed erased by account delete | Counsel-owned |
| Early Access waitlist | Separate relationship | Not deleted with User accounts | Counsel-owned |

## What account deletion does **not** encode

See [`ACCOUNT_DELETION_PROPAGATION.md`](ACCOUNT_DELETION_PROPAGATION.md). Shopping-assistant conversations are TTL-bound and are **not** listed by `user_id` on the delete path. Alert-rule rows in the alerts bounded context are **not** cascaded. Those remain documented engineering limitations, not silent erasure claims.

## Purge jobs

**Not found.** Do not treat session/token expiry as an approved privacy retention purge. Do not implement a legal retention cron from this document.

## Operator use

Use this map when answering “how long does this live in the product today?” Counsel still answers “how long must/may we keep it?” Sprint 44/45 remain the publication/approval gates.
