# Penetration-test readiness checklist

**Status:** READY TO TEST. No item in this checklist is TESTED / PASSED.

**Package date:** 2026-10-14

**Owner:** Sprint 40 security-readiness package

**This checklist does not claim that a penetration test has been executed.** No penetration test has been executed. Repository tests are not a penetration-test result. A passing unit test, a green CI run, or this document does not move a row to TESTED / PASSED.

Related process documents:

- Security incident response: [`../runbooks/SECURITY_INCIDENT_RESPONSE.md`](../runbooks/SECURITY_INCIDENT_RESPONSE.md)
- Vulnerability response: [`VULNERABILITY_RESPONSE.md`](VULNERABILITY_RESPONSE.md)
- Sprint 44 draft: [`../roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md`](../roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md)
- Current control note: [`../SECURITY.md`](../SECURITY.md)

Current roadmap links:

- [`../roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)
- [`../roadmap/sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md`](../roadmap/sprints/SPRINT_42_PRODUCTION_OPERATIONS_DR.md)
- [`../roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md`](../roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md)
- [`../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
- Latest pre-package reconciliation: [`../roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`](../roadmap/evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md)

Sprint 40 stays Planned. It is not ENGINEERING COMPLETE, not PRODUCTION PROVEN, and not LAUNCH READY. This checklist does not close a HIGH or MEDIUM finding. It does not approve Sprint 44. It does not approve launch.

## How to read a row

| Checklist status | Meaning |
|------------------|---------|
| READY TO TEST | The target and the expected control are identified. A tester may exercise them in an authorized environment. |
| TESTED / PASSED | An authorized test was executed, the expected control held, and evidence is stored outside this template. |

Every row below is READY TO TEST. Observed result is `NOT TESTED`. Severity if failed is `unassigned`. Evidence location is `none`. Retest status is `not started`.

Fill the evidence template at the end when a test is actually run. Do not edit a row to TESTED / PASSED inside this readiness file unless a later evidence record cites the test, the environment, and the result.

## Safe-test rules

Prefer a local or staging environment that the operator has authorized for security testing. Production testing requires explicit written authorization for the named window, the named surfaces, and the named accounts. Destructive production testing is out of scope for this checklist.

Additional rules:

- Do not call a real merchant or provider, including Shopify, Resend delivery beyond a single authorized mailbox, or a live model API, merely to mark a row covered.
- `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Routing stays 0. Do not enable Shopify to satisfy coverage.
- Live research stays off. Do not enable `AI_SHOPPING_LIVE_HTTP`, review live HTTP, or community live HTTP to test prompt isolation.
- Affiliate activation stays off. Do not turn on affiliate payout, click billing, or affiliate network tracking.
- Do not send bulk email. Identity mail tests use one authorized mailbox.
- Do not perform a denial-of-service or load attack. Rate-limit checks use a small number of requests inside an approved window. Capacity work belongs to Sprint 43.
- Stop when a test shows possible data disclosure, credential exposure, or an isolation failure. Preserve redacted evidence and follow [`../runbooks/SECURITY_INCIDENT_RESPONSE.md`](../runbooks/SECURITY_INCIDENT_RESPONSE.md).
- Store evidence with timestamps, the commit SHA, and the environment name. Do not copy passwords, bearer tokens, reset tokens, cookies, or API keys into tickets, chat, or this repository.
- Use test accounts created for the exercise. Do not use a real shopper account.

## Scope definition

Production Early Access HTML is limited to `/`, `/privacy`, `/terms`, account registration and login pages, and health probes. `unfinished_html_surfaces_enabled()` is false when `APP_ENV=production`, so `/search`, `/results/{decision_id}`, `/compare/{decision_id}`, and `/why-best-piq/{decision_id}` redirect to `/` in production. Development and staging may render those pages. A staging render is not production launch of public Results. Public Results stays disabled as a launch claim.

| ID | Surface | Live state on 2026-10-14 | Checklist status |
|----|---------|---------------------------|------------------|
| PT-SCOPE-01 | Public consumer pages: `/`, `/privacy`, `/terms` | Present. Legal pages are public documents. | READY TO TEST |
| PT-SCOPE-02 | `/search`, `/results/{id}`, `/compare/{id}`, `/why-best-piq/{id}` | Disabled in production by redirect to `/`. Renderable in development and staging. Private decision routes set `noindex`. `robots.txt` disallows `/results/`, `/compare/`, `/why-best-piq/`, and `/account`. | READY TO TEST |
| PT-SCOPE-03 | Authentication, registration, reset, verification, email change | Present. Pages: `/login`, `/register`, `/reset-password`, `/verify-email`, `/confirm-email-change`. API prefix: `/api/v1/auth/`. | READY TO TEST |
| PT-SCOPE-04 | Account and session lifecycle | Bearer sessions plus `piqsavi_decision_owner` cookie. `POST /api/v1/auth/logout` revokes the presented bearer. Public sign-out also calls `POST /account/clear-device`. | READY TO TEST |
| PT-SCOPE-05 | `POST /api/v1/shopping-assistant/query` | Present. Requires `Idempotency-Key`. Deterministic assistant path can run while model providers stay off. | READY TO TEST |
| PT-SCOPE-06 | Decision-owner cookie flows | Cookie is `HttpOnly`, `SameSite=Lax`, and `Secure` in staging and production. Unsafe cookie-authorized mutations require a trusted `Origin`. | READY TO TEST |
| PT-SCOPE-07 | Merchant and admin API | Routes exist under `/api/v1/merchants` and `/api/v1/admin`. Merchant authentication is demo bearer tokens. Production merchant identity is not implemented. `GET /api/v1/merchants/meta/demo` is a local demo listing. | READY TO TEST |
| PT-SCOPE-08 | Feedback and analytics submission | `POST /api/v1/feedback/reports` and `POST /api/v1/analytics/events`. Feedback does not send email. Analytics is consent-gated and rejects restricted fields. | READY TO TEST |
| PT-SCOPE-09 | Health and readiness | `/live`, `/ready`, `/health`, and the `/api/v1` copies. `/ready` may return 503. These probes are not a product analytics surface. | READY TO TEST |
| PT-SCOPE-10 | Server-fetch boundaries | `validate_server_fetch_url` accepts https and rejects numeric private, loopback, link-local, and metadata hosts. Shopify transport accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend posts only to its pinned URL with redirects off. | READY TO TEST |
| PT-SCOPE-11 | Marketplace and browser links | `validate_browser_destination` accepts http or https. Private hosts are allowed because the server does not fetch them. There is no merchant-host allowlist. | READY TO TEST |
| PT-SCOPE-12 | Transactional email links | Reset, verify, and email-change links use `PUBLIC_APP_BASE_URL`. Production email secret attach remains Sprint 41. `ALLOW_DEMO_RESET_TOKENS` must be false outside development. | READY TO TEST |
| PT-SCOPE-13 | Early Access interest list | `POST /api/v1/early-access`. This is not account registration. | READY TO TEST |
| PT-SCOPE-14 | Launch demo and OpenAPI docs | `/demo` and `/api/v1/launch/demo` are demo tooling. Production requires `DEMO_LAUNCHER_ENABLED` false. `/docs` and `/redoc` are off in production unless `OPENAPI_PUBLIC_DOCS` is set, and they are incompatible with the strict CSP. | READY TO TEST |
| PT-SCOPE-15 | Disabled or non-live providers | Shopify live calls are disabled. Live research is fail-closed. AI shopping, review, and community live HTTP default off. Affiliate payout and click billing stay off. MFA and OAuth are extension points and are not implemented. | READY TO TEST |

## Authentication and authorization

Expected controls come from the merged Sprint 40.1 and Sprint 40.7 behavior and from the session review in the 2026-10-13 reconciliation. Staging proof is still absent. A repository test is not TESTED / PASSED for this checklist.

| ID | Target | Prerequisites | Steps | Expected control | Observed result | Severity if failed | Evidence location | Retest status | Checklist status |
|----|--------|---------------|-------|------------------|-----------------|--------------------|-------------------|---------------|------------------|
| PT-AUTHZ-01 | Broken object-level authorization on decision snapshots | Two owners, A and B, in the authorized environment. B has a canonical snapshot. | 1. Authenticate as A. 2. Request B's decision id on results, compare, why, and destination reevaluation. | `get_for_owner` returns nothing for A. The response does not include B's decision body. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-02 | Conversation owner isolation | Two owners with separate assistant conversations. | 1. Continue A's conversation with B's cookie or bearer. 2. Repeat with only a body `conversation_id`. | Continuation uses the verified request owner. A foreign id does not adopt the stored owner. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-03 | Decision snapshot owner isolation | A canonical snapshot owned by A. | 1. Call answer, refinement, and research proposal as B, passing A's `conversation_id`. | Loads use `get_for_owner`. They do not call an ownerless `get` and do not adopt `context.owner` from the body. Missing owner access fails closed. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-04 | Foreign conversation ids | A known conversation id from another owner. | 1. Submit the foreign id with the caller's own credential. 2. Submit it with no credential. | The foreign row is not readable, continuable, or mutable. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-05 | Body `user_id`, `profile_id`, and `conversation_id` | A valid owner cookie or bearer. | 1. Send another user's ids in the JSON body. 2. Omit the caller's real credential. | Body fields are lookup or fingerprint values. Authority is the verified owner. The submission scope does not read body `user_id` or `profile_id`. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-06 | Guest versus account isolation | One guest cookie and one account bearer. | 1. Read the account's decision with the guest cookie. 2. Read the guest decision with the account bearer before any claim. | Each owner sees only rows bound to that verified owner. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-07 | Owner-cookie theft and reuse | A copied `piqsavi_decision_owner` value. | 1. Replay the copied cookie from another client until expiry. 2. Replay it after `POST /account/clear-device` on the original browser. | The cookie is HMAC-SHA256 and expires in seven days. There is no server-side guest revocation list, so a copied cookie works until expiry. Clear-device deletes the cookie on the browser that calls it. This residual is already recorded on R2. This package does not close it. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-08 | Logout and clear-device | An account that has both a bearer and an owner cookie. | 1. Call only `POST /api/v1/auth/logout`. 2. Repeat the public sign-out sequence, which also posts `/account/clear-device` with a trusted Origin. | Logout revokes the presented bearer and does not itself clear the owner cookie. Public sign-out also clears the device cookie. The internal demo logout does not clear it. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-09 | Session expiry and revocation | A bearer session. | 1. Use the bearer after `expires_at`. 2. Use it after logout. 3. Use it after password reset or email-change confirmation. | `validate_session` rejects a missing, revoked, or expired session and revokes an expired one. Reset and email-change confirmation call `revoke_all_for_user`. Default bearer TTL is 3600 seconds. Remember-me uses 2592000 seconds and the consumer stores that bearer in `localStorage`. The server stores the SHA-256 hash. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-10 | Password reset, verify, and email-change tokens | `ALLOW_DEMO_RESET_TOKENS` false. One authorized mailbox. | 1. Request each flow. 2. Confirm with a valid token once. 3. Replay the same token. 4. Submit an expired or altered token. | Raw tokens are absent from API responses outside development. A token is consumed on success. Reset confirmation revokes bearer sessions. Invalid, expired, and consumed tokens fail with the same invalid-token result. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-11 | Enumeration resistance | Unused and existing addresses. | 1. Login with an unknown email and with a wrong password. 2. Request password reset and email verification for an unknown address and a known address. 3. Register an address that already exists. | Login failures share `Invalid email or password.` Reset and verification requests return an accepted response that does not disclose membership. Registration currently returns `Email already registered` with the address. Record that registration difference. This package does not change it and does not mark it closed. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-AUTHZ-12 | Ownerless non-decision Ask | A cookieless client and no `decision_id`. | 1. Post one shopping-assistant query. 2. Try to continue that conversation and to attach a decision context. | Anonymous `create(owner=None)` may store a non-decision row. The next request cannot continue it. The row cannot hold a decision context. This is the Sprint 40.1 contract. | NOT TESTED | unassigned | none | not started | READY TO TEST |

## Request integrity

| ID | Target | Prerequisites | Steps | Expected control | Observed result | Severity if failed | Evidence location | Retest status | Checklist status |
|----|--------|---------------|-------|------------------|-----------------|--------------------|-------------------|---------------|------------------|
| PT-INT-01 | Origin enforcement | Decision-owner cookie, or a clear-device call. | 1. POST `/api/v1/shopping-assistant/query`, `/consumer/claim-decision`, `/api/v1/feedback/reports`, and `/api/v1/analytics/events` with the owner cookie and no `Origin`. 2. Repeat with `Origin: null`, a foreign origin, and a trusted origin from `PUBLIC_APP_BASE_URL` or `CORS_ORIGINS`. 3. POST `/account/clear-device` with a missing origin. | Missing or untrusted Origin fails closed with HTTP 403 `origin_rejected`. `Host` and `Referer` are not substitutes. Bearer-only routes and preference-cookie writers stay outside this check. SameSite=Lax is not the control. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-02 | Idempotency-Key replay | One logical Ask submission. | 1. Send `Idempotency-Key` and a payload. 2. Retry the same scoped key and the same payload. | The stored response is replayed. `service.query` and `emit_ask_product_events` do not run again. Staging and production use the SQL ledger. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-03 | Same key, different payload | The key from PT-INT-02. | 1. Change a mutation-relevant field, including body `user_id` or `profile_id`, and reuse the key. | HTTP 409 `Idempotency-Key does not match the original request.` The second payload does not execute. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-04 | Concurrent duplicate | Two clients sharing one scoped key. | 1. Submit the same new key at the same time. | One SQL primary-key winner executes. The other receives HTTP 409 `Request already in progress.` and does not execute. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-05 | Malformed or missing key | The public Ask route. | 1. Omit `Idempotency-Key`. 2. Send an empty or malformed key. | HTTP 400 before a claim. The server does not invent a key. The internal demo fetch omits the header and therefore cannot execute. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-06 | Request size and malformed input | Authorized test environment. | 1. Send invalid JSON, unknown fields, and an oversized body to Ask, feedback, analytics, and auth. 2. Record the status code and whether the body is logged. | Schema validation rejects malformed input. No application-wide body-size ceiling was found when this checklist was written. Observe the actual limit. Do not assume a WAF. The request log records method, path, status, duration, request id, and client host, and does not record the body. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-07 | Rate limits | Staging or a local SQL-backed configuration. Use few requests. | 1. Confirm the environment rejects `RATE_LIMIT_BACKEND=memory`. 2. Exercise one public bucket and one auth bucket with a small burst. 3. Send a forged `X-Forwarded-For` prefix. | Staging and production use `SqlRateLimitStore`. Public identity is the trusted client address appended by the ALB or Docker proxy, or an account HMAC for a verified bearer or account owner cookie. A forged forwarding prefix is not the key. A per-session bucket is still absent. That gap stays PARTIAL on R16. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INT-08 | Durable failed-login lock | One test account. | 1. Submit 20 consecutive bad passwords. 2. Wait past 60 seconds and try again during the lock. 3. Succeed after the lock expires, or wait 15 minutes on an unlocked sequence and confirm the count restarts. | The 20-attempt / 60-second window still applies. Twenty consecutive failures then set a 15-minute `locked_until` from the threshold event. Unlocked history is kept for 15 minutes. Unknown, inactive, and bad-password failures share one message. Store failure returns the public rate-limit text. | NOT TESTED | unassigned | none | not started | READY TO TEST |

## Injection and browser

| ID | Target | Prerequisites | Steps | Expected control | Observed result | Severity if failed | Evidence location | Retest status | Checklist status |
|----|--------|---------------|-------|------------------|-----------------|--------------------|-------------------|---------------|------------------|
| PT-INJ-01 | XSS | A page the test environment is allowed to render. | 1. Submit HTML and script-shaped text in fields that echo into HTML, including feedback where HTML is rejected. 2. Inspect the response and the CSP header. | `h()` and `attr()` use `html.escape`. Feedback rejects HTML. The default CSP is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SECURITY_CSP` can still override the default. Record the effective header. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-02 | CSP | `SECURITY_HEADERS_ENABLED` true. | 1. Fetch `/`, `/privacy`, `/terms`, and an enabled account page. 2. Confirm `script-src`, `style-src`, `object-src`, `frame-ancestors`, `base-uri`, and `form-action`. | Default policy is `default-src 'self'` with first-party script, style, image, font, and connect sources, `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`, and `form-action 'self'`. HSTS applies on staging and production. This control is not staging-proven. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-03 | SQL injection | API only. Do not open a production database shell for exploit attempts. | 1. Send quote and comment characters in ids and text fields. 2. Confirm the response is a validation or not-found error. | Request-path SQL found in review is ORM or a constant `SELECT 1` health probe. Untrusted text is not concatenated into SQL. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-04 | Open redirect | Account and consumer redirect parameters. | 1. Supply an absolute external URL in `next` and similar redirect fields. | Redirects use `_safe_next` local prefixes. An external URL is not the redirect target. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-05 | URL and SSRF trust boundaries | No live provider call. | 1. Review a server-fetch candidate aimed at loopback, link-local, and metadata addresses. 2. Confirm the Shopify transport allowlist and redirect refusal in code and configuration. 3. Do not send the request to Shopify or to a cloud metadata address from production. | Server fetches require https and reject those hosts. Browser links are a separate policy and may name a private host because the server does not fetch them. DNS rebinding is out of scope. No reachable SSRF is claimed. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-06 | Command injection | Source review plus any field that reaches a shell. | 1. Search the exercised paths for shell execution of request data. | Review found no `subprocess`, `os.system`, `eval`, or `exec` call under `app/`. Confirm a new path has not added one. Do not run host commands against production. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-07 | Browser merchant-link handling | A page that renders an outbound merchant URL. | 1. Inspect the href policy for javascript, data, and unexpected schemes. 2. Confirm the link is a browser destination. | Browser destinations accept http or https. The server does not fetch the merchant URL. There is no merchant-host allowlist. Affiliate activation stays off, so the link is not a paid click. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-INJ-08 | Prompt-injection boundaries | AI flags and live HTTP remain off. | 1. Submit shopper text containing the six warning markers. 2. Confirm the model transport stays disabled. 3. Do not enable a provider. | `contains_prompt_injection` matches `ignore previous`, `ignore all instructions`, `system prompt`, `reveal the prompt`, `api key`, and `override safety`. A match adds a warning. It does not isolate untrusted content from system instructions. Ranking still runs on the deterministic path. Merchant, review, and community text are not covered by that function. R10 and R19 stay PARTIAL. | NOT TESTED | unassigned | none | not started | READY TO TEST |

## Data and privacy

| ID | Target | Prerequisites | Steps | Expected control | Observed result | Severity if failed | Evidence location | Retest status | Checklist status |
|----|--------|---------------|-------|------------------|-----------------|--------------------|-------------------|---------------|------------------|
| PT-PRIV-01 | Credential redaction | Structured logging enabled. | 1. Trigger a failed login and a validation error. 2. Inspect the request log. | `redact_value` redacts secret-like keys. Passwords, API keys, and Authorization headers are not written to routine logs. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-02 | Session and cookie redaction | A request that sends the owner cookie and a bearer. | 1. Inspect the request log fields. | The request log does not record the owner cookie, a session id, or a bearer token. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-03 | Conversation-body logging | One Ask submission. | 1. Compare the question text with the request log. | The question and answer body are not request-log fields. The submission ledger stores the public response for replay. That ledger is not the request log and not product analytics. The raw idempotency key is stored as SHA-256. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-04 | Analytics restricted-field rejection | Analytics consent on and off. | 1. Post an event containing question, answer, email, session id, or conversation id. | `FORBIDDEN_ANALYTICS_FIELDS` rejects those fields. Consent off stores no product-analytics row for the client event. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-05 | Security-audit identity | A login failure and a login lock. | 1. Inspect `SecurityEvent` metadata. 2. Confirm product analytics does not receive the same email. | Authentication audit records may store the account email. That store is intentional audit identity. The durable-lock audit uses `login_locked` or `login_lock_unavailable` and does not store the raw email. Do not copy audit emails into product analytics. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-06 | Response leakage | Error responses from auth, Ask, and decision reads. | 1. Force a not-found, a validation error, and a server-side dependency failure. | Clients receive a stable error envelope. Provider stack traces, secret values, and another owner's decision body are absent. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-PRIV-07 | Error enumeration | Same accounts as PT-AUTHZ-11. | 1. Compare status codes and bodies for known and unknown addresses on login, reset, and verification. | Login, reset, and verification do not disclose whether the address exists. Registration does disclose an existing address. Record that separately. | NOT TESTED | unassigned | none | not started | READY TO TEST |

## Abuse

| ID | Target | Prerequisites | Steps | Expected control | Observed result | Severity if failed | Evidence location | Retest status | Checklist status |
|----|--------|---------------|-------|------------------|-----------------|--------------------|-------------------|---------------|------------------|
| PT-ABUSE-01 | Credential stuffing | One test email. Small volume. | 1. Repeat failed logins across the 60-second window and into the lock. | The shared per-email HMAC window and the durable 15-minute lock apply. This is a beta control. It is not a WAF. Staging has not exercised it. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-02 | Distributed limiter | Two application processes sharing one staging database, if the environment has them. | 1. Send a small number of limited requests through each process. | Counters live in PostgreSQL for staging and production. Memory is rejected there. Development may stay in-process. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-03 | Account lock | The account from PT-INT-08. | 1. Confirm a locked account cannot obtain a session. 2. Confirm a successful login after expiry clears the lock. | `FailedLoginLock` blocks session issuance while `locked_until` is in the future. Success clears the lock. Password reset stays on the short window only and does not itself issue a session. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-04 | Replay and idempotency | The keys from PT-INT-02. | 1. Retry after success. 2. Retry a payload conflict. 3. Observe an in-progress duplicate. | Replay returns the stored response once. Conflict and in-progress duplicates do not apply the mutation twice. A processing row becomes indeterminate after 15 minutes and is not re-executed. Completed and indeterminate rows are kept for 24 hours. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-05 | Bot-abuse review | No CAPTCHA vendor. | 1. Record whether a bot challenge exists on register, login, and Ask. | No CAPTCHA or bot challenge was found. Full WAF/CDN depth is a Sprint 40 non-goal. Record the absence. Do not mark the row passed. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-06 | Cost-amplification review | Providers remain disabled. | 1. Confirm AI flags and live research stay off. 2. Read the estimate cap wiring without enabling a provider. | `AI_MAX_ESTIMATED_COST_PER_REQUEST` compares a returned estimate on review, shopping, and community orchestrators. It is not a live-research budget. Live research remains fail-closed. Do not enable a provider to measure cost. | NOT TESTED | unassigned | none | not started | READY TO TEST |
| PT-ABUSE-07 | Affiliate and click-fraud controls | Affiliate activation stays off. | 1. Confirm no click payout or affiliate-network call is made while exercising outbound links. 2. Record whether a click-fraud score exists. | Affiliate routes can store clicks when the flag is on. Click-fraud scoring was not found. Affiliate activation stays off, so there is no click payout to score. Do not enable affiliate tracking for this test. | NOT TESTED | unassigned | none | not started | READY TO TEST |

## Evidence template

Copy this block for every executed test. Leave it unused until a test is run.

```
Test id:
Target:
Environment:
Commit SHA:
Tester role:
Started at:
Finished at:
Prerequisites:
Steps performed:
Expected control:
Observed result:
Severity if failed: unassigned | SEV-1 | SEV-2 | SEV-3 | SEV-4
Evidence location:
Secrets excluded: yes
Retest status: not started | retest scheduled | retest passed | retest failed
Checklist status: READY TO TEST | TESTED / PASSED
```

Severity labels in that template are for a future failed test. They do not relabel the existing Sprint 40 HIGH or MEDIUM findings. Those findings stay at the classes recorded in the latest reconciliation until staging proof, a fix, or a separate written risk acceptance says otherwise. This package records no risk acceptance.

Stop conditions, evidence handling, and secrets handling are the safe-test rules above. A failed test that shows disclosure or isolation failure moves to the security incident-response runbook before anyone continues the checklist.
