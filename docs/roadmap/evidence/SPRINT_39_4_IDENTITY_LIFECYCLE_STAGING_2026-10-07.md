# Sprint 39.4 — identity lifecycle staging evidence — 2026-10-07

Sanitized record of one controlled staging session after Deploy Staging #43. This note does not store an email address, password, access token, session id, analytics subject, account id, or raw cookie.

Sprint 39 stays **IN PROGRESS**. It is not ENGINEERING COMPLETE, not COMPLETE / CLOSED, not PRODUCTION PROVEN, and not LAUNCH READY. This note does not deploy and does not call Shopify. Sprint 38 is unchanged. Sprint 40 and Sprint 41 are not started.

**Sprint definition:** [`../sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md`](../sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md)

**Closure audit:** [`SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md`](SPRINT_39_CLOSURE_READINESS_AUDIT_2026-10-02.md)

## Deploy

| Fact | Value |
|------|-------|
| Merged pull request | #181 |
| Application SHA | `d0f117b426010f629ec32b7d3f96f39dc6b865f7` |
| CI | #441 SUCCESS |
| Build Image | #156 SUCCESS |
| Deploy Staging | #43 |
| Run id | `37567160567` |
| Release | `rel-20261007T024027Z-d0f117b42601` |
| Deploy status | SUCCESS |
| Host evidence | `staging_ok` |

Deploy Staging #41 and Deploy Staging #42 facts stay in [`SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md`](SPRINT_39_2_STAGING_ANALYTICS_TEMPLATE.md). This note does not replace them.

## Initial identity-lifecycle dashboard

| Count | Value |
|-------|-------|
| `registration_completed` | 0 |
| `registration_verified` | 0 |
| `login_success` | 0 |
| `login_failure` | 0 |
| `account_deleted` | 0 |
| `authentication_transition` | 0 |
| `partial` | false |

## Explicit analytics opt-in

| Fact | Value |
|------|-------|
| choice | `analytics_allowed` |
| `analytics_allowed` | true |
| `advertising_allowed` | false |
| explicit | true |

## Registration

One controlled staging account was created successfully. Its address, credentials, and identifiers are not recorded here.

| Count | After registration |
|-------|--------------------|
| `registration_completed` | 1 |
| `registration_verified` | 0 |
| `login_success` | 0 |
| `login_failure` | 0 |
| `account_deleted` | 0 |
| `authentication_transition` | 0 |

## Login

One successful login was performed. One failed login was performed.

| Fact | Value |
|------|-------|
| Failed login HTTP status | 401 |
| Public detail | Invalid email or password. |
| `login_success` | 1 |
| `login_failure` | 1 |
| `registration_completed` | 1 |
| `registration_verified` | 0 |
| `account_deleted` | 0 |
| `authentication_transition` | 0 |
| `partial` | false |

The failed-login body is the generic public detail. It does not identify which check failed.

## Deletion

The same controlled account was then deleted successfully.

| Fact | Value |
|------|-------|
| status | `deleted` |
| `sessions_revoked` | 2 |
| `sessions_deleted` | 2 |
| `account_deleted` | 1 |

## Final dashboard

| Count | Value |
|-------|-------|
| `registration_completed` | 1 |
| `login_success` | 1 |
| `login_failure` | 1 |
| `account_deleted` | 1 |
| `registration_verified` | 0 |
| `authentication_transition` | 0 |
| `partial` | false |

## `registration_verified` was not exercised

`registration_verified` is implemented. It emits only after `POST /api/v1/auth/verify-email/confirm` marks the account verified.

This controlled run did not prove that transition. `ALLOW_DEMO_RESET_TOKENS` is development only. Staging and production must be false, and those environments do not return a demo verification token. The controlled account used a non-deliverable example.invalid address, so no real verification message was received. No verification token was fabricated.

Classification: **B — IMPLEMENTED, CLOSURE EVIDENCE BLOCKED ON A REAL TRANSACTIONAL EMAIL / VERIFICATION FLOW**. Not Class A. Not left Class C only because this run could not receive mail.

## `authentication_transition` was not exercised

`authentication_transition` is implemented at `POST /consumer/claim-decision`. It emits only when `claimed` is true.

That endpoint requires a valid authenticated account session, a valid server-signed guest owner cookie, and an existing conversation owned by that exact guest owner. `ensure_guest_owner_cookie()` is used by the consumer document flow. The public staging root remains Early Access. The unfinished Results / Compare / Why flow is not publicly active. The generic shopping-assistant API may create a conversation id. It does not provide authority to invent the matching signed guest owner cookie. No guest owner cookie was fabricated.

Classification: **B — IMPLEMENTED, STAGING VALIDATION BLOCKED ON THE REAL GUEST→ACCOUNT CONTINUITY FLOW**. Not Class A. Not left Class C.

## What this session does not claim

- Staging proof for `registration_verified`
- Staging proof for `authentication_transition`
- A non-zero core shopper funnel
- Sprint 39 engineering completion or closure
- Production proof or launch readiness
- A Shopify call, a new deploy, or a change to Sprint 38
