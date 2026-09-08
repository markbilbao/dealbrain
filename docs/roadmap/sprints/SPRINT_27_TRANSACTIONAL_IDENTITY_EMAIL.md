# Sprint 27 — Transactional Identity & Email

**Status:** COMPLETE / CLOSED. 27.1–27.4 implementation is on `main`. 2026-09-08 owner/operator staging inbox E2E (verify, password reset, email-change) **passed**. Auth-aware header/logout E2E **passed**. EXT-09 is **PASS / VERIFIED** (public DNS + Resend domain **Verified**). PR #121 merged the identity-email readiness gate at `a5468ecf65be40bb36a053a97869cec97e3a529c`. Deploy Staging #32 succeeded on that digest. Live `https://staging.piqsavi.com/health` on 2026-09-08 reported `identity_email_adapter=resend` and `identity_email_ready=true`. Production secret attach remains Sprint 41. Sprint 27 completion does **not** mean production transactional email is live. Evidence: [`../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md).
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
| Email-change confirmation | **implemented** (27.2) — authenticated request + purpose-bound confirm; 2026-09-08 staging inbox E2E passed |
| EXT-08 Resend account | `applied` / **AMBER** — account-establishment screenshot unchanged; staging delivery now evidenced 2026-09-08 |
| EXT-09 sender-domain DNS auth | `approved` — **PASS / VERIFIED** 2026-09-08 (public DNS + Resend domain **Verified**) |
| Staging real-inbox E2E | **passed** 2026-09-08 (verify, reset, email-change) |
| Production email readiness / Secrets Manager cutover | **not claimed** (path recorded; attach remains Sprint 41) |
| Sprint 27 / P0-5 closure | **COMPLETE / CLOSED** — PR #121 merged; Deploy Staging #32; live `/health` `identity_email_adapter=resend` / `identity_email_ready=true` on 2026-09-08 |

27.1 implements the production email boundary and reset/verify confirm routes. 27.2 adds verified account email change. Neither slice by itself closed Sprint 27. EXT-09 sender-domain evidence is recorded as **Verified**. Production email attach remains Sprint 41.

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
| EXT-08 / EXT-09 / production readiness | EXT-09 **PASS / VERIFIED**; staging inbox E2E passed 2026-09-08; production attach remains Sprint 41 |

**Re-auth policy.** Email change is a sensitive action. The caller must present a valid bearer session **and** the current account password, matching Sprint 28.1 account deletion. The request body has no account selector.

**Token lifecycle.** Tokens are generated with `secrets.token_urlsafe`, stored as SHA-256 hashes only, bound to the authenticated user, the intended new email, and `purpose=email_change`. TTL is 24 hours. Confirmation requires the correct hash, purpose, user binding, destination-email binding, and an unconsumed unexpired record that is the newest unconsumed request for that user. Password-reset and ordinary verification tokens cannot confirm email change; email-change tokens cannot reset a password or satisfy ordinary verify-email confirmation.

**Verified-state semantics.** Successful confirmation sets `email_verified=True` for the new email. Prior verification state is not carried over.

**Session security.** Successful confirmation calls `SessionRepository.revoke_all_for_user` **before** the email mutation. The confirming session and every other session for that user are revoked. Other users' sessions are untouched. Revoke failure leaves email, verified state, and token unchanged and sends no notice. Consume failure after a successful save does not return success; prior sessions are already revoked. Repositories still commit independently — this is fail-closed ordering, not a new transaction framework.

**Old-email notice.** The notice is a secondary notification, not authorization. It is sent only after a first-time identity mutation, contains no confirmation token, and never rolls back a completed or in-progress identity change.

**External blockers (Sprint 27 sender-domain).** EXT-08 register status remains `applied` (account-establishment screenshot). EXT-09 is **`approved` / VERIFIED** (public DNS + owner-observed Resend domain **Verified**, 2026-09-08). Staging inbox E2E for verify/reset/email-change **passed** on 2026-09-08. Production email readiness is not claimed.

## 27.3 record (owner slice)

| Area | Status |
|------|--------|
| Staging demo-token example reconciled (`ALLOW_DEMO_RESET_TOKENS=false`) | implemented |
| Staging non-secret Resend configuration contract | implemented — example + compose + host env assembly |
| `RESEND_API_KEY` injection path | documented — AWS Secrets Manager `dealbrain/staging/resend_api_key` via `assemble-runtime-env.py`; no key in git |
| Trusted `PUBLIC_APP_BASE_URL` action links | preserved — request / forwarded Host unused |
| Resend failure isolation (timeout / non-2xx / transport / missing key / invalid From) | strengthened — generic `EmailDeliveryError`; no provider body, key, or token leak |
| PiqSavi consumer email branding | verified — no DealBrain in transactional copy |
| `identity_email_status().ready` | **implemented and live-staging-verified** — `external_evidence=verified` (merged EXT-09 + inbox E2E); `ready` is true only when adapter is Resend **and** runtime config is usable. Live `https://staging.piqsavi.com/health` after Deploy Staging #32 reported `identity_email_ready=true` |
| Operator EXT-09 DNS runbook | executed — public DNS resolvable; Resend reports **Verified** |
| Staging inbox E2E evidence | **passed** 2026-09-08 — [`../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md) |
| EXT-09 DNS verified | **YES** — public DNS + Resend domain **Verified** (2026-09-08) |
| Real inbox E2E | **YES** — verify, reset, and email-change on 2026-09-08 |
| Production secret attached | **NO** — Sprint 41 |
| Sprint 27 / P0-5 closure | **COMPLETE / CLOSED** |

27.3 prepares repository-controlled cutover so the owner can apply Cloudflare DNS and run real staging inbox proof. Staging inbox proof and EXT-09 Resend **Verified** now exist (2026-09-08). Live staging readiness health after PR #121 / Deploy Staging #32 is recorded in the final closure section. It does **not** claim production email live.

## 2026-09-08 reconciliation (pre-PR #121 historical evidence)

Full matrix and DNS notes: [`../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md`](../evidence/SPRINT_27_STAGING_EMAIL_EVIDENCE_2026-09-08.md). The table below is the **pre-PR #121** reconciliation. It correctly recorded live `/health` `identity_email_ready=false` on the earlier staging digest. Do not treat that observation as the current post-deploy state. **Final closure** after PR #121 / Deploy Staging #32 is recorded below.

| Decision | Value |
|----------|-------|
| Close Sprint 27 / P0-5? | **No** |
| Real inbox E2E (verify, reset, email-change) | **PASS** — owner/operator Gmail on live staging, no demo tokens |
| Auth-aware header / logout privacy | **PASS** — after PR #119 / Deploy Staging #31 |
| EXT-09 | **PASS / VERIFIED** — public DKIM/SPF/MX/DMARC plus Resend domain **Verified** |
| Production secret attach | **NOT SPRINT 27** — Sprint 41 |
| `identity_email_ready` | code gate now AND(runtime Resend config, verified Sprint 27 evidence). Live staging still reported `false` on 2026-09-08 on the previous digest. Remaining closure: deploy this digest and confirm live `/health` |

**Remaining closure action at the time of this 2026-09-08 reconciliation:** merge the readiness-gate implementation, deploy the immutable image to staging, and confirm live `https://staging.piqsavi.com/health` reports `identity_email_adapter=resend` and `identity_email_ready=true`. That action completed later the same day after PR #121 and Deploy Staging #32; see **Final closure** below. Production email is not live; production `RESEND_API_KEY` attach remains Sprint 41.

## 27.4 record (consumer UX slice)

| Area | Status |
|------|--------|
| Account "Change email" form | implemented — signed-in Account only; current password re-auth; existing `POST /api/v1/auth/email-change` |
| Displayed account email | unchanged until confirm succeeds |
| `GET /confirm-email-change` | implemented — explicit confirm button; no auto-success; token not rendered |
| Email-change success state | implemented — sign-in required; local bearer token cleared |
| Email verification final state | implemented — confirm control removed after success |
| Password-reset final state | implemented — reset form removed after success |
| Request-sent copy | implemented — enumeration-safe consumer language |
| Implementation evidence | tests + lint; live staging email-change inbox E2E passed 2026-09-08 |
| Live staging email-change inbox E2E | **passed** 2026-09-08 — owner/operator real Gmail confirm |
| Final Account/auth visual design | **not this slice** |
| Sprint 27 / P0-5 closure | **COMPLETE / CLOSED** — live staging `/health` verified after Deploy Staging #32 |

27.4 exposes the already-implemented email-change lifecycle in the Account UI and replaces engineering-stage confirmation leftovers with dedicated success/failure states. Live staging inbox delivery for email-change is now evidenced (2026-09-08). It does **not** mark production email readiness. Sprint 27 / P0-5 closure is recorded in **Final closure** below.

## 27.4 follow-up (auth-aware account header)

| Area | Status |
|------|--------|
| Shared account/auth header signed-out vs signed-in | implemented — `How it works` / `Support` always; signed-out shows `Sign in` / `Sign up`; signed-in shows `Account` / `Sign out` |
| Auth proof | implemented — stored bearer token is not sufficient; header uses existing `GET /api/v1/auth/me`; invalid token clears local/device auth and restores signed-out |
| Header Sign out | implemented — existing `POST /api/v1/auth/logout` + `clearLocalAuth()` / `/account/clear-device` + redirect `/` |
| Account Sessions Sign out | retained — same `signOutCurrentDevice` helper; default redirect remains `/login` |
| Initial markup | auth-dependent controls start `hidden` until `/auth/me` resolves (no Sign-in flash for a valid session) |
| Sprint 27 / P0-5 closure | **COMPLETE / CLOSED** — header E2E passed 2026-09-08; live `/health` `identity_email_ready=true` after Deploy Staging #32 |

This follow-up does **not** redesign Account Settings and does **not** change identity success states from 27.4. Staging auth-aware header/logout E2E **passed** on 2026-09-08 after PR #119. EXT-09 is **Verified**. The remaining readiness-gate digest was merged in PR #121 and verified live after Deploy Staging #32.

**Staging secret injection.** Deploy Staging never reads Resend from GitHub. The host assemble script reads optional Secrets Manager leaf `dealbrain/staging/resend_api_key` (same prefix as `app_secret_key` / `cors_origins`). If the leaf is missing or placeholder, assembled `TRANSACTIONAL_EMAIL_PROVIDER` stays `null` and `RESEND_API_KEY` is empty so current staging does not construct `ResendEmailSender` without a key. After the owner creates the secret, the next staging deploy selects Resend automatically.

**Readiness truth.** `identity_email_status()` distinguishes adapter, runtime configuration, and Sprint 27 external evidence. `external_evidence` is **verified** from the merged EXT-09 / inbox-E2E record; `/health` does not call Resend to re-prove it. `ready` is true only when the adapter is Resend, runtime config is usable (non-placeholder key, sender, valid `PUBLIC_APP_BASE_URL`), and that verified evidence gate is satisfied. A missing/placeholder key, `TRANSACTIONAL_EMAIL_PROVIDER=null`, unknown environment, or production without usable runtime Resend configuration keeps `ready=false`. Production email is **not** claimed live. Health still exposes only `identity_email_adapter` and `identity_email_ready`. Live staging `/health` after Deploy Staging #32 reported `identity_email_adapter=resend` and `identity_email_ready=true`. Local tests alone did not close Sprint 27 / P0-5.

## Final closure (Post-PR #121, 2026-09-08)

Sprint 27 / P0-5 is **COMPLETE / CLOSED**. All Sprint 27 acceptance evidence exists, including the final live staging health proof.

| Item | Value |
|------|-------|
| Git SHA | `a5468ecf65be40bb36a053a97869cec97e3a529c` (PR #121 merge commit) |
| Build Image run | `34230096725` |
| Release ID | `rel-20260908T130824Z-a5468ecf65be` |
| Immutable image digest | `sha256:0a0a3022ecb1f758a0f58aef821adf4dadf8b18834ed3971ee70dc45a2d72787` |
| Deploy Staging | #32 / run `34231964695` — SUCCESS |
| Date | 2026-09-08 |
| Live endpoint | `https://staging.piqsavi.com/health` |
| Observed | `environment=staging`, `status=up`, `identity_email_adapter=resend`, `identity_email_ready=true` |
| Authoritative deploy result | `final_status=staging_ok`, `localhost_live=true`, `localhost_ready=true`, `alb_target_healthy=true`, `smoke_ok=true` |

Sprint 27 proves: provider architecture and fail-closed behavior; sender-domain authentication; staging real-inbox E2E; staging runtime Resend configuration; merged readiness semantics; live staging readiness health.

Sprint 27 does **not** prove: production Resend live; production `RESEND_API_KEY` attached; production email end-to-end verified; production cutover complete. Those remain Sprint 41.

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

- Real inbox delivery of reset and verify emails — **passed** 2026-09-08
- E2E reset completes login — **passed** 2026-09-08
- Email-change inbox E2E — **passed** 2026-09-08 (additive to the original list)
- Sender-domain Resend **Verified** (EXT-09) — **passed** 2026-09-08

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
