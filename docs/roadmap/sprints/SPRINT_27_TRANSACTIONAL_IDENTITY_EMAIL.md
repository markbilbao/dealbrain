# Sprint 27 — Transactional Identity & Email

**Status:** In progress — 27.1 identity email adapter + reset/verify confirm implemented; 27.2 verified email-change lifecycle implemented. Sprint 27 is **not complete**. Staging inbox E2E, EXT-09 DNS verification, and production cutover remain open.
**Primary owner / domain:** Identity / user platform (Sprint 17 domain; adapter hardening)
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes — P0-5

## 27.1 record (owner slice)

| Area | Status |
|------|--------|
| `EmailSender` port + `NullEmailSender` test/dev sender | implemented |
| Resend adapter (`ResendEmailSender`) | implemented — no live Resend calls in tests |
| Production fail-closed (no `NullEmailSender`); staging Null allowed but not ready | implemented |
| Password-reset request (enumeration-safe) | implemented |
| Password-reset confirm + expiry + single-use | implemented |
| Email-verification request (enumeration-safe by email) | implemented |
| Email-verification confirm + expiry + single-use | implemented |
| Demo/inline tokens blocked in staging/production | implemented |
| PiqSavi sender/link identity (configurable) | implemented — uses `TRANSACTIONAL_EMAIL_FROM*` + `PUBLIC_APP_BASE_URL` |
| Session revoke-all after password reset | implemented (existing session store) |
| Email-change confirmation | **implemented** (27.2) — authenticated request + purpose-bound confirm; staging inbox E2E still required |
| EXT-08 Resend account | `applied` / **AMBER** — account establishment only; not provisioned |
| EXT-09 sender-domain DNS auth | `applied` / **AMBER** — DNS **plan** only; not verified |
| Staging real-inbox E2E | **not done** |
| Production email readiness / Secrets Manager cutover | **not claimed** (path recorded; attach remains Sprint 41) |
| Sprint 27 / P0-5 closure | **not closed** |

27.1 implements the production email boundary and reset/verify confirm routes. 27.2 adds verified account email change. Neither slice completes Sprint 27. Neither claims EXT-09 domain verification or production sender readiness.

## 27.2 record (owner slice)

| Area | Status |
|------|--------|
| Authenticated `POST /api/v1/auth/email-change` | implemented — session principal is the only account authority |
| Current-password re-auth (Sprint 28.1 pattern) | implemented — `Invalid credentials.` on mismatch |
| Purpose-bound `email_change` token (hash only, 24h, single-use) | implemented — operational store `user_platform.email_changes` |
| Confirmation to the proposed new email via `EmailSender` | implemented — PiqSavi template; `PUBLIC_APP_BASE_URL` links |
| Account email unchanged until valid confirm | implemented |
| Confirm atomically sets new email + `email_verified=True` | implemented — mailbox control proven by the new-address token |
| Session revoke-all after confirm | implemented (existing session store) |
| Newest-request-wins | implemented — later request invalidates prior unconsumed tokens |
| Occupied destination | request is enumeration-safe (accepted, no token); confirm fails closed |
| Old-email security notice | implemented after first-time identity mutation; secondary notification; no token; failure does not roll back |
| Client-supplied user/profile/account IDs | ignored — cannot retarget another account |
| EXT-08 / EXT-09 / staging inbox E2E / production readiness | **unchanged** — not claimed |

**Re-auth policy.** Email change is a sensitive action. The caller must present a valid bearer session **and** the current account password, matching Sprint 28.1 account deletion. The request body has no account selector.

**Token lifecycle.** Tokens are generated with `secrets.token_urlsafe`, stored as SHA-256 hashes only, bound to the authenticated user, the intended new email, and `purpose=email_change`. TTL is 24 hours. Confirmation requires the correct hash, purpose, user binding, destination-email binding, and an unconsumed unexpired record that is the newest unconsumed request for that user. Password-reset and ordinary verification tokens cannot confirm email change; email-change tokens cannot reset a password or satisfy ordinary verify-email confirmation.

**Verified-state semantics.** Successful confirmation sets `email_verified=True` for the new email. Prior verification state is not carried over.

**Session security.** Successful confirmation calls `SessionRepository.revoke_all_for_user` after the email mutation and before success is returned. The confirming session and every other session for that user are revoked. Other users' sessions are untouched. Revoke or consume failure does not return success; the token remains usable until consume succeeds so a retry can finish the security steps. Repositories still commit independently — this is fail-closed ordering, not a new transaction framework.

**Old-email notice.** The notice is a secondary notification, not authorization. It is sent only after a first-time identity mutation, contains no confirmation token, and never rolls back a completed or in-progress identity change.

**External blockers (still open).** EXT-08 is account-establishment only. EXT-09 is a DNS plan only. There is no real staging inbox E2E. Production email readiness is not claimed.

## Objective

Make self-serve authentication production-safe with real transactional email, complete password recovery, and email verification.

## Included requirements

- Select and integrate transactional email provider
- Sender-domain SPF/DKIM/DMARC verification
- Password-reset email + confirm route; token expiry and invalidation
- Email verification send + confirm
- Email-change verification
- Session rotation / revoke-all sessions
- Disable demo inline reset tokens in staging/production paths
- Failed-login messaging without account enumeration regressions

## Explicit non-goals

- OAuth/MFA
- Full privacy policy publication (28)
- Consumer UI polish (29)

## External dependencies

- EXT-08
- EXT-09

## Implementation deliverables

- Email sender adapter replacing NullEmailSender for staging/prod
- Confirm endpoints
- Config/secrets wiring

## Documentation deliverables

- AUTHENTICATION.md updates
- EMAIL_PROVIDER_ARCHITECTURE.md provider decision
- Runbook for email outages

## Required tests

- Unit/API tests for reset/verify confirm
- Enumeration-safe responses
- Token reuse rejected

## Required staging evidence

- Real inbox delivery of reset and verify emails
- E2E reset completes login

## Required production evidence

- Provider credentials in Secrets Manager (prep OK; full prod cutover in 41)

## Acceptance criteria

Launch acceptance explicitly covers:

- real transactional email
- sender authentication (SPF/DKIM/DMARC)
- account verification
- password reset
- secure token lifecycle (expiry, single-use invalidation, reuse rejected)
- email-change behavior where planned
- enumeration-safe errors
- session rotation/revocation
- staging E2E
- production cutover readiness (credentials/secrets path recorded; full prod attach remains Sprint 41)

Also:

- Staging user can reset password via email without demo tokens
- Verification flow completes
- Tokens expire and invalidate after use
- Production config cannot enable demo token leakage
- Guest→account continuity preserves the active decision where safely possible (co-owned with Sprint 29/40)

### Additive PiqSavi brand criteria (not marked complete)

Authority: [`../PIQSAVI_PUBLIC_BRAND_POLICY.md`](../PIQSAVI_PUBLIC_BRAND_POLICY.md)

- Consumer-visible email subjects/bodies use PiqSavi
- No unintended DealBrain branding in transactional emails
- Public email-link base uses approved `piqsavi.com` URL
- Password-reset URLs use PiqSavi public configuration
- Verification URLs use PiqSavi public configuration
- Sender identity is PiqSavi
- Sender-domain authentication is verified before public use
- Internal DealBrain technical identifiers remain unchanged

## Predecessor sprints

26

## Parallelizable work

28 drafting can start after identity API shapes freeze

## Go / no-go gate

Go if staging E2E email flows pass; else public self-serve auth blocked

## Rollback or contingency

Feature-flag email flows off; revert to invite-only

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.
