# Failed-login lock — 2026-10-13

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `551f70d0b00a7368056e20ec859e29939ce53bb2`

This record is not named Sprint 40.8. It does not rewrite the 2026-10-09 readiness audit, the post-40.6 reconciliation, or the post-40.7 reconciliation. Those files keep the classes they recorded. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed. No Shopify call was made. Routing stays 0.

## Policy

No approved failed-login threshold or lock duration was found in the repository. Searches for `locked_until`, `failed_login`, `lockout`, and a consecutive-failure duration found only the existing shared auth window: 20 attempts / 60 seconds.

The conservative beta default is therefore named and used:

- `FAILED_LOGIN_LOCK_THRESHOLD` = 20 consecutive failures
- `FAILED_LOGIN_LOCK_DURATION_SECONDS` = 900 (15 minutes)

The 15 minutes are measured from the attempt that reaches the threshold (`locked_until = now + 15 minutes`). They are not a bucket that starts on the first failure and can expire immediately after the threshold is crossed. There is no permanent exponential lockout in this slice.

## What was added

`AuthService.login` keeps the existing `RateLimiterHook(max_attempts=20, window_seconds=60)` on the opaque HMAC of the normalized email. The durable control is an additional layer, checked before that window and before password verification.

Before the password check:

- If `locked_until` is still in the future, login raises `UserPlatformRateLimitError("Too many login attempts. Try again later.")`. The password is not verified and no session is issued.
- If the lock store cannot be read, the same public error is raised. Staging and production do not fall back to memory.
- Otherwise the existing 20/60 check runs unchanged.

On an unknown email, an inactive account, or a bad password, one durable failure is recorded for that opaque identity. The public error remains `UserPlatformAuthError("Invalid email or password.")`, including on the attempt that reaches the threshold. The next attempt is blocked until `locked_until`.

When the threshold is reached, the row's `locked_until_ms` is set from that event. Later failures during the lock do not move the deadline. After `locked_until`, the next failure starts a new sequence at count 1. A successful login deletes the row and still resets the 20/60 window, then issues the session as before.

`User.is_active` is not the lock. An inactive account stays inactive. An active account stays active while locked.

## Persistence

Table `failed_login_locks`, Alembic revision `f6a7b8c9d0e1` (revises `e5f6a7b8c9d0`):

| Column | Meaning |
|--------|---------|
| `identity_key` | Opaque `login:<hmac-sha256>` of the normalized email. Primary key. |
| `failure_count` | Consecutive failures since the last success or expired lock. |
| `locked_until_ms` | Deadline of the current lock, or null when not locked. |
| `first_failure_ms` | Start of the current failure sequence. |
| `last_failure_ms` | Most recent failure in that sequence. |

The table has no email, password, bearer token, session token, or owner-cookie column. Staging and production use `SqlFailedLoginLockStore` on the same PostgreSQL selection as `SqlRateLimitStore`. `RATE_LIMIT_BACKEND=memory` remains forbidden there. Development and unit tests use `InMemoryFailedLoginLockStore`. The SQL module does not reference the memory store.

## Concurrency

An active or not-yet-locked row is updated with one conditional `UPDATE` that sets `failure_count = failure_count + 1`. The database applies that expression to the locked row, so concurrent failures do not lose increments. `locked_until_ms` is written only when it is null and the new count reaches the threshold. A row that is already locked keeps its deadline.

An expired lock is not incremented. A second conditional `UPDATE` matches `locked_until_ms <= now` and replaces the row with failure count 1. If two sessions race that reset, one matches; the other matches zero rows and then increments. The first row is inserted, and a primary-key conflict retries the update. Store errors raise `FailedLoginLockUnavailable` and never open an in-memory substitute.

## Enumeration safety

Unknown email, inactive account, and bad password return the same `Invalid email or password.` message. While the opaque identity is locked, or when the store cannot be evaluated, both known and unknown identities return `Too many login attempts. Try again later.` The response does not include the failure count, the lock deadline, or whether an account exists.

Audit events for this control use `detail` `login_locked` or `login_lock_unavailable` and metadata `control=failed_login_lock`. They do not store the raw email, password, or token. The pre-existing short-window audit, which can still record an email on `detail=login`, is unchanged.

## Directly affected requirements

| Row | Post-slice class | Why |
|-----|------------------|-----|
| R9 | IMPLEMENTED-NOT-PROVEN | Repeated failed logins against one normalized email stay restricted after the 60-second auth window expires. The lock is shared through PostgreSQL in staging and production, is temporary, and clears on successful login. Staging has not exercised it, so the row is not PROVEN. |
| R8 | PARTIAL | The shared 20/60 auth window and the shared HTTP limiter remain. Bot challenge and click-fraud scoring are still absent. Required staging evidence "Abuse controls exercised" is absent. |
| R16 | PARTIAL | Login locking is not a per-session rate-limit bucket and does not extend the Origin/CSRF policy. The origin MEDIUM stays IMPLEMENTED-NOT-PROVEN. |

R1, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. R11 stays MISSING. R12, R13, and R20 stay PARTIAL. Counts after this slice, counting only the R9 move: PROVEN 0, IMPLEMENTED-NOT-PROVEN 4 (R1, R9, R14, R18), PARTIAL 16, MISSING 1 (R11), BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0. No Included requirement is PROVEN.

The Sprint 40 HIGH "In-process rate limits only" stays IMPLEMENTED-NOT-PROVEN. This slice does not close it. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs stay IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence stays CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

## Out of scope

CAPTCHA, WAF/CDN bot protection, MFA, IP reputation, click-fraud scoring, device fingerprinting, SAST, container scanning, IaC security scanning, message idempotency, prompt-injection redesign, the security IR package, and guest-to-account snapshot rebind were not implemented.

## Local verification

This run is repository verification on the implementation branch. It is not a GitHub CI run and not staging proof. The starting `main` result remains CI #480 SUCCESS, Build Image #171 SUCCESS, full pytest 4416 passed and 5 skipped, pip-audit 71 packages, 0 vulnerabilities, 0 exceptions.

- Focused durable-login-lock tests: 15 passed.
- Existing auth, rate-limit, login/session, identity-lifecycle, migration, and post-40.7 reconciliation tests: 171 passed.
- Sprint 40 security tests and database persistence tests: 282 passed, 15 deselected (the new lock file, run separately above).
- Architecture-lock tests: 5 passed.
- Ruff baseline gate: check=91 (baseline 91), unformatted=82 (baseline 86). No new regressions.
- `secret_scan_25a`: OK.
- pip-audit: 71 packages, 0 vulnerabilities, 0 exceptions, scanner 2.10.1.
- Full pytest: 4428 passed, 8 skipped, 0 failed, 268 warnings, 312.57s. The local skip count is 8, the same shape as the prior local run. It is not the GitHub count of 5 skipped.

## Roadmap truths

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. Routing stays 0. Shopify stays disabled. Real Shopify calls stay 0. Affiliate activation stays off. No deploy was performed. No Shopify call was made.
