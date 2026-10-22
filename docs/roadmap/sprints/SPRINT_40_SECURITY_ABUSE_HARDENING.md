# Sprint 40 — Security & Abuse Hardening

**Status:** Planned
**Primary owner / domain:** Security engineering
**Master roadmap:** [`../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md`](../GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md)
**Beta blocker classification:** Yes

## Objective

Close launch-blocking security findings and establish abuse protections appropriate for public traffic.

## Included requirements

- AuthN/AuthZ/object-level review
- Session security review
- Headers/CSP/CORS/CSRF policy completion
- Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection
- Log redaction; body logging policy; PII handling
- Secret/dependency/SAST/container/Terraform scanning in CI
- Supply-chain provenance checks; immutable image authority verification
- Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta
- Account lockout or equivalent
- AI prompt-injection + merchant-content sanitation review
- Pen-test readiness package; security IR runbook; vulnerability-response process
- Close all HIGH and launch-blocking MEDIUM findings
- Bind every conversation and decision context to a verified guest session or authenticated principal.
- Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id`.
- Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding.
- Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits.
- Add idempotency and replay protection for message submission and research confirmation.
- Redact conversation bodies and session identifiers from routine logs and analytics.
- Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification.
- Explicit coverage of: identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation
- Close HIGH and launch-blocking MEDIUM issues before Sprint 45

## Explicit non-goals

- Full WAF/CDN depth program (post-beta OK)
- Formal SOC2 certification

## External dependencies

- None

## Implementation deliverables

- Scanning workflows
- Rate-limit/lockout hardening
- CSP/SSRF fixes
- IR templates

## Documentation deliverables

- SECURITY.md updates
- Vuln response
- Pen-test readiness checklist

## Required tests

- Security regression tests
- Scanner gates in CI

## Required staging evidence

- Scanners clean on candidate
- Abuse controls exercised

## Required production evidence

- Prod IAM review continues in 41

## Acceptance criteria

- No open HIGH
- Launch-blocking MEDIUM closed or time-boxed risk-accepted in writing
- CI scanning required on main
- Security package ready for 44 approval
- Foreign or expired decision contexts cannot be read, advanced, refined, researched, or rebound.
- Guest→authenticated transition preserves the active decision while rotating ownership credentials.
- Logout and shared-device reuse cannot expose a previous user’s context.
- No open HIGH or launch-blocking MEDIUM Conversational Continuity finding remains.

## Predecessor sprints

27, 28, 29

## Parallelizable work

39, 41 prep

## Go / no-go gate

Security go/no-go draft ready

## Rollback or contingency

Keep registration invite-only if abuse controls fail

## Change control

- Does not silently redistribute Architecture Lock ownership for Sprints 1–25.
- Completion requires listed evidence maturity, not code presence alone.
- Connector/market sprints require real provider evidence when claiming supported markets.

## Current reading (2026-10-09)

This section does not rewrite the Planned status or the Included requirements above. The readiness audit is [`../evidence/SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md`](../evidence/SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md). It starts from `0452c40610ac61cd9dce4af361718cb4fd2c02d7`. CI #453 and Build Image #161 succeeded on that SHA. No Included requirement is PROVEN. Engineering has not started. No runtime code changed.

**Audit verdict:** One bounded engineering slice is selected and is not implemented here.

**Selected next engineering slice:** Non-decision assistant body-identity authorization. Stop using request-body `conversation_id`, `profile_id`, and `user_id` as authority on the shopping-assistant query path that has no `decision_id`.

The open Sprint 40 HIGH remains in-process rate limits only. It is not the first slice. CSRF not enforced, CSP `'unsafe-inline'`, missing Dependabot/CodeQL/Trivy/pip-audit, and incomplete URL validation remain the existing MEDIUMs. This reading does not relabel them launch-blocking and does not risk-accept them. Production isolation, production OIDC/SSM, and paging stay with Sprint 41 and Sprint 42.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

## Implementation record (2026-10-09)

This section does not rewrite the Planned status, the Included requirements, or the readiness audit above. Sprint 40.1 implements the selected slice: non-decision assistant body-identity authorization. It is implemented and not PROVEN. Evidence: [`../evidence/SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md`](../evidence/SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md). Starting `main` for the slice is `09757717971ad01077cefbaf806caddf10b8624d`.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The open Sprint 40 HIGH remains in-process rate limits only. CSRF not enforced, CSP `'unsafe-inline'`, missing Dependabot/CodeQL/Trivy/pip-audit, and incomplete URL validation remain the existing MEDIUMs. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

## Implementation record — Sprint 40.2 (2026-10-09)

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1 record above. Sprint 40.2 adds a pip-audit 2.10.1 CI gate on the frozen `uv.lock` closure and locks the one pre-existing Mako advisory to the fixed release. It is implemented and not PROVEN. Evidence: [`../evidence/SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md`](../evidence/SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md). Starting `main` for the slice is `ed666678691522238eb44c395a3bc5273f36fa4b`.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The open Sprint 40 HIGH remains in-process rate limits only. The Sprint 30 MEDIUM "No Dependabot/CodeQL/Trivy/pip-audit" is no longer an open absence because the pip-audit gate is required in CI. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. CSRF not enforced, CSP `'unsafe-inline'`, and incomplete URL validation remain the existing MEDIUMs. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

## Implementation record — Sprint 40.3 (2026-10-09)

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1 and Sprint 40.2 records above. Sprint 40.3 adds a PostgreSQL shared rate-limit counter for staging and production. Public buckets use the client address appended by a trusted ALB or Docker proxy, not the socket peer and not a forged `X-Forwarded-For` prefix. The Sprint 40 HIGH "In-process rate limits only" is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. Required staging evidence "Abuse controls exercised" is absent. Evidence: [`../evidence/SPRINT_40_3_DISTRIBUTED_RATE_LIMIT_2026-10-09.md`](../evidence/SPRINT_40_3_DISTRIBUTED_RATE_LIMIT_2026-10-09.md). Starting `main` for the slice is `81a4d6aef4e9b49bf3648245190588f87c51c152`.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. CSRF not enforced, CSP `'unsafe-inline'`, and incomplete URL validation / SSRF hardening remain the existing MEDIUMs. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

## Implementation record — Sprint 40.4 (2026-10-10)

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1, Sprint 40.2, and Sprint 40.3 records above. Sprint 40.4 enforces a server-configured Origin check on unsafe requests that use the decision-owner cookie as authority, and on `POST /account/clear-device`. SameSite=Lax remains in place and is not the control. Bearer-only routes are unchanged. The Sprint 40 MEDIUM previously recorded as CSRF not enforced is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. Staging has not exercised the origin policy. Evidence: [`../evidence/SPRINT_40_4_COOKIE_ORIGIN_POLICY_2026-10-10.md`](../evidence/SPRINT_40_4_COOKIE_ORIGIN_POLICY_2026-10-10.md). Starting `main` for the slice is `06a2c9da40c2bc49bf361569e887e64b1dccb8a6`.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. CSP `'unsafe-inline'` and incomplete URL validation / SSRF hardening remain the existing MEDIUMs. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

## Implementation record — Sprint 40.5 (2026-10-10)

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1, Sprint 40.2, Sprint 40.3, and Sprint 40.4 records above. Sprint 40.5 separates server-fetch URL checks from browser link and browser resource checks. The Shopify production transport accepts only `https://catalog.shopify.com/api/ucp/mcp` and does not follow redirects. The Sprint 40 MEDIUM "URL validation / SSRF hardening incomplete" is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. No reachable SSRF exploit is demonstrated. Staging has not exercised the policy. Evidence: [`../evidence/SPRINT_40_5_URL_TRUST_2026-10-10.md`](../evidence/SPRINT_40_5_URL_TRUST_2026-10-10.md). Starting `main` for the slice is `5dbc52295a38d056bca9347f7a69f605b3ad7414`. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.4 CSRF/Origin MEDIUM remains IMPLEMENTED-NOT-PROVEN. CSP `'unsafe-inline'` remains an open MEDIUM. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Implementation record — Sprint 40.6 (2026-10-10)

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1, Sprint 40.2, Sprint 40.3, Sprint 40.4, and Sprint 40.5 records above. Sprint 40.6 removes `'unsafe-inline'` and `'unsafe-eval'` from the default Content-Security-Policy and keeps the policy first-party. Privacy, Terms, and the internal demo page now load external stylesheets, and the demo script is an external file. The Sprint 40 MEDIUM CSP `'unsafe-inline'` is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. Staging has not exercised the policy. Evidence: [`../evidence/SPRINT_40_6_CSP_HARDENING_2026-10-10.md`](../evidence/SPRINT_40_6_CSP_HARDENING_2026-10-10.md). Starting `main` for the slice is `c0c341187515d480bb4318c26c085d44a16af14e`. Affiliate activation is unchanged. Ranking and commission are unchanged.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.4 CSRF/Origin MEDIUM remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.5 URL/SSRF MEDIUM remains IMPLEMENTED-NOT-PROVEN. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Reconciliation — post Sprint 40.6 (2026-10-10)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, or the Sprint 40.1 through Sprint 40.6 records above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md`](../evidence/SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md). Starting `main` is `483d30a91f70167656b51f976ffb2bb3521a0b7e`. CI #472 succeeded. Build Image #168 succeeded. Full pytest on CI #472 was 4388 passed, 5 skipped. pip-audit on that run was 71 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here.

**Selected next engineering slice:** Decision-path body `conversation_id` must not adopt the stored owner.

R18 is IMPLEMENTED-NOT-PROVEN. R11 stays MISSING. The other Included rows stay PARTIAL. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 1, PARTIAL 19, MISSING 1, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The non-decision half of R14 is implemented and tested. Answer-from-evidence and session refinement still read a UUID snapshot by adopting the stored owner from a body `conversation_id`. That residual is why R1, R13, and R14 stay PARTIAL. Guest-to-account rebind of a canonical UUID snapshot remains a product-definition conflict with snapshot immutability. This reconciliation does not change snapshot immutability.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. `terraform validate` is not IaC security scanning. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded. Staging evidence remains absent.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Implementation record — Sprint 40.7 (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.6 records, or the post-40.6 reconciliation above. Sprint 40.7 stops decision-path answer, refinement, and research proposal from adopting a stored conversation owner out of a body `conversation_id`. The verified request owner is the authority. Body `conversation_id`, `decision_id`, and `context_version` stay lookup values. The slice is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. Staging has not exercised the control. Evidence: [`../evidence/SPRINT_40_7_DECISION_PATH_OWNER_BINDING_2026-10-13.md`](../evidence/SPRINT_40_7_DECISION_PATH_OWNER_BINDING_2026-10-13.md). Starting `main` is `df051a2e122816928bb85edb75c5f27290c1aaaa`.

R1 is IMPLEMENTED-NOT-PROVEN. R14 is IMPLEMENTED-NOT-PROVEN. R13 stays PARTIAL because anonymous non-decision `create(owner=None)` and ownerless `append_turn` materialization remain, and this slice does not change that Sprint 40.1 contract. R18 stays IMPLEMENTED-NOT-PROVEN. No other reconciliation row was reclassified. No Included requirement is PROVEN.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence stays CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. R6 stays PARTIAL. R11 stays MISSING. They are not relabeled launch-blocking. No risk acceptance is recorded. Canonical snapshot immutability is unchanged. Guest-to-account rebind of a canonical snapshot remains a product-definition conflict.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Reconciliation — post Sprint 40.7 (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, or the post-40.6 reconciliation above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_40_7_RECONCILIATION_2026-10-13.md`](../evidence/SPRINT_40_POST_40_7_RECONCILIATION_2026-10-13.md). Starting `main` is `bbf7158dfa70c969e851f032702732f0e7e863ea`. CI #477 succeeded. Build Image #170 succeeded. Full pytest on CI #477 was 4410 passed, 5 skipped. pip-audit on that run was 71 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here. It is not named Sprint 40.8.

**Selected next engineering slice:** Failed logins must stay limited after the shared auth window expires.

R1 is IMPLEMENTED-NOT-PROVEN. R14 is IMPLEMENTED-NOT-PROVEN. R18 stays IMPLEMENTED-NOT-PROVEN. R13 stays PARTIAL. Anonymous `create(owner=None)` remains the Sprint 40.1 contract and does not expose a decision context. R11 stays MISSING. The other Included rows stay PARTIAL. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 3, PARTIAL 17, MISSING 1, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The shared per-email auth window is a beta-level credential-stuffing throttle. It is not account lockout. Window expiry deletes the counter. That residual is the selected slice. SAST remains the smallest missing scanner class and is not selected. Guest-to-account rebind of a canonical UUID snapshot remains a product-definition conflict with snapshot immutability. This reconciliation does not change snapshot immutability.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded. Staging evidence remains absent.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Implementation record — failed-login lock (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, or the post-40.6 and post-40.7 reconciliations above. It is not named Sprint 40.8. Failed logins against one normalized email now stay limited after the 60-second shared auth window expires. The existing 20-attempt / 60-second limiter remains. The additional control is a temporary `locked_until` lock: 20 consecutive failures, then 15 minutes measured from the threshold event. No repository policy named a different threshold or duration. An unlocked failure sequence is remembered for 15 minutes (`FAILED_LOGIN_FAILURE_RETENTION_SECONDS` = 900); no approved failed-login retention duration was found. A sequence older than that horizon restarts at 1. Stale unlocked rows and expired locks are deleted during lock-store writes. Active locks are kept. The slice is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. Staging has not exercised the control. Evidence: [`../evidence/SPRINT_40_FAILED_LOGIN_LOCK_2026-10-13.md`](../evidence/SPRINT_40_FAILED_LOGIN_LOCK_2026-10-13.md). Starting `main` is `551f70d0b00a7368056e20ec859e29939ce53bb2`.

R9 is IMPLEMENTED-NOT-PROVEN. R8 stays PARTIAL because bot and click-fraud controls, and the staging exercise, remain. R16 stays PARTIAL. Login locking is not a per-session bucket and does not complete the Origin/CSRF policy. R11 stays MISSING. No Included requirement is PROVEN. The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN and is not closed by this lock.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Reconciliation — post failed-login lock (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the post-40.6 and post-40.7 reconciliations, or the failed-login lock record above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md`](../evidence/SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md). Starting `main` is `bfdac461250d67f8e144df0811e707410b685437`. CI #484 succeeded. Build Image #172 succeeded. Full pytest on CI #484 was 4445 passed, 5 skipped. pip-audit on that run was 71 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here. It is not named Sprint 40.8.

**Selected next engineering slice:** Ordinary shopping-assistant message submission must not apply twice when the same client request is retried.

R9 is IMPLEMENTED-NOT-PROVEN. The durable lock matches the merged policy and has no staging exercise, so it is not PROVEN. R8 stays PARTIAL. R16 stays PARTIAL. R1, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. R13 stays PARTIAL. Anonymous `create(owner=None)` remains the Sprint 40.1 contract and does not expose a decision context. R11 stays MISSING and does not outrank the message-replay slice. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 4, PARTIAL 16, MISSING 1, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN and is not closed by the login lock. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded. Canonical snapshot immutability is unchanged. Guest-to-account rebind of a canonical snapshot remains a product-definition conflict.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

## Implementation record — message submission idempotency (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the post-40.6 and post-40.7 reconciliations, or the failed-login lock and post-failed-login-lock records above. It is not named Sprint 40.8. `POST /api/v1/shopping-assistant/query` now requires an `Idempotency-Key`. One logical browser submission keeps that key across retries. A later intentional submit, including the same question text, uses a new key. The server scopes the key to a verified account, a verified guest, or an opaque anonymous host HMAC. The key is stored as a SHA-256 hash. A canonical fingerprint binds the key to one mutation-relevant payload. The same scoped key and fingerprint replay the stored response and skip `service.query` and `emit_ask_product_events`. A different fingerprint is HTTP 409. An in-flight duplicate does not execute. A crash after the mutation boundary is indeterminate and is not re-executed. Completed and indeterminate rows are kept for 24 hours. That period is a bounded beta default; `docs/privacy/ENGINEERING_RETENTION.md` had no approved shopping-submission lifetime. Staging and production use the shared SQL ledger and do not fall back to memory. Alembic revision `a7b8c9d0e1f2`. R17 is IMPLEMENTED-NOT-PROVEN. It is not PROVEN. Research-authorization idempotency is unchanged. Evidence: [`../evidence/SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md`](../evidence/SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md). Starting `main` is `591bcf751aae5e8f7cc14c1ffac17b81211b395a`.

R8, R10, R11, R15, R16, and R19 stay independent. R9, R1, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 5 (R1, R9, R14, R17, R18), PARTIAL 15, MISSING 1 (R11), BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0. The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN and is not closed by this control.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY. This record does not select a later engineering slice.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Reconciliation — post message idempotency (2026-10-13)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the post-40.6 and post-40.7 reconciliations, the failed-login lock record, the post-failed-login-lock reconciliation, or the message-submission record above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`](../evidence/SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md). Starting `main` is `32b5a0292195588625e8e515badd5e176cbeb6e8`. CI #491 succeeded. Build Image #174 succeeded. Full pytest on CI #491 was 4471 passed, 5 skipped. pip-audit on that run was 71 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here. It is not named Sprint 40.8.

**Selected next engineering slice:** Write the Sprint 40 security-readiness package: a penetration-test readiness checklist, a security incident-response runbook, a vulnerability-response process, and a Sprint 44 security go/no-go draft.

R17 is IMPLEMENTED-NOT-PROVEN. The merged ledger requires `Idempotency-Key`, replays one scoped payload without calling `service.query` or `emit_ask_product_events`, and keeps research-authorization idempotency. It is not PROVEN. Staging has not exercised it. R3, R5, R7, and R20 are IMPLEMENTED-NOT-PROVEN. Origin enforcement is the beta control for the covered cookie mutations. Security-audit email is intentional authentication identity. Signed provenance is not a Sprint 40 engineering blocker. The coverage review is this reconciliation and does not stay PARTIAL only because other rows are open. R1, R9, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. R11 stays MISSING and is the selected slice. R16 stays PARTIAL because a per-session rate-limit bucket is still absent. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 9 (R1, R3, R5, R7, R9, R14, R17, R18, R20), PARTIAL 11, MISSING 1 (R11), BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded. Canonical snapshot immutability is unchanged. Guest-to-account rebind of a canonical snapshot remains a product-definition conflict.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Implementation record — security-readiness package (2026-10-14)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, or the failed-login lock and message-idempotency records above. It is not named Sprint 40.8. The selected security-readiness package is now in the tree: a penetration-test readiness checklist, a security incident-response runbook, a vulnerability-response process, and a Sprint 44 security go/no-go draft. The package is preparation and process evidence. No penetration test has been executed. Production paging is not configured. No risk acceptance is created. No Sprint 44 approval is granted. Evidence: [`../evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md`](../evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md). Starting `main` is `e088cba9a87175e387038afb98a1754fe8cc885e`.

R11 was MISSING. R11 is IMPLEMENTED-NOT-PROVEN. R11 is not PROVEN. Proof still depends on use, review, or rehearsal where a later gate requires it. R1, R3, R5, R7, R9, R14, R17, R18, and R20 stay IMPLEMENTED-NOT-PROVEN. R2, R4, R6, R8, R10, R12, R13, R15, R16, R19, and R21 stay PARTIAL. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 10 (R1, R3, R5, R7, R9, R11, R14, R17, R18, R20), PARTIAL 11, MISSING 0, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. R6 stays PARTIAL. R10 and R19 stay PARTIAL. R16 stays PARTIAL because a per-session bucket is still absent. R15 stays a product-definition conflict. R12 and R21 stay closure gates. They are not relabeled launch-blocking. No risk acceptance is recorded. This record does not select a later engineering slice.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Reconciliation — post security-readiness package (2026-10-14)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the failed-login lock and message-idempotency records, or the security-readiness package record above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md`](../evidence/SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md). Starting `main` is `e4a8802e7edd87e234996e2f86be4ca2dee31c3e`. CI #495 succeeded. Build Image #176 succeeded. Full pytest on CI #495 was 4484 passed, 5 skipped. pip-audit on that run was 71 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here. It is not named Sprint 40.8.

**Selected next engineering slice:** Add one deterministic SAST gate in CI over application code.

R2, R4, and R8 are IMPLEMENTED-NOT-PROVEN. Account owner cookies are checked against session revocation. Browser merchant links are not a server-fetch allowlist, and no merchant-host list is invented. Credential stuffing, the shared IP limit, and affiliate activation staying off satisfy the beta abuse row. R11 stays IMPLEMENTED-NOT-PROVEN and is not PROVEN. R6 stays PARTIAL because SAST, container vulnerability scanning, and IaC security scanning are still absent. All five scanning classes are required for ENGINEERING COMPLETE. R10 and R19 stay PARTIAL as pre-activation prompt isolation. R13 and R15 stay product decisions. R16 stays PARTIAL because a per-session bucket is still absent and is not the selected slice. R12 and R21 stay closure gates because the HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 13 (R1, R2, R3, R4, R5, R7, R8, R9, R11, R14, R17, R18, R20), PARTIAL 8 (R6, R10, R12, R13, R15, R16, R19, R21), MISSING 0, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION. SAST, container scanning, and IaC security scanning remain open. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. They are not relabeled launch-blocking. No risk acceptance is recorded. Canonical snapshot immutability is unchanged. Guest-to-account rebind of a canonical snapshot remains a product-definition conflict.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Implementation record — SAST gate (2026-10-14)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the failed-login lock and message-idempotency records, or the security-readiness package record above. It is not named Sprint 40.8. The slice selected by the post-security-readiness reconciliation is now in the tree: one deterministic Bandit 1.9.4 gate over `app/**/*.py`. The first run scanned 649 application Python files and reported 35 findings. None was a HIGH vulnerability. The six MEDIUM results are reviewed string heuristics, not socket binds or request-path temporary files. Each current finding has one exact baseline exception. The SAST capability is IMPLEMENTED-NOT-PROVEN. It is not PROVEN. Evidence: [`../evidence/SPRINT_40_SAST_GATE_2026-10-14.md`](../evidence/SPRINT_40_SAST_GATE_2026-10-14.md). Starting `main` is `871e761685fe663c4d0ef4cf3b11094c32ed90b9`.

R6 stays PARTIAL. Container vulnerability scanning and IaC security scanning remain absent. R2, R4, and R8 stay IMPLEMENTED-NOT-PROVEN. R11 stays IMPLEMENTED-NOT-PROVEN and is not PROVEN. No Included requirement is PROVEN. The historical MEDIUM "No Dependabot/CodeQL/Trivy/pip-audit" stays CLOSED BY IMPLEMENTATION for the original no-dependency-scanner condition. This record does not select a later engineering slice.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Reconciliation — post SAST gate (2026-10-15)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the failed-login lock and message-idempotency records, the security-readiness package record, or the SAST gate record above. It records a fresh reconciliation of the current tree. Evidence: [`../evidence/SPRINT_40_POST_SAST_RECONCILIATION_2026-10-15.md`](../evidence/SPRINT_40_POST_SAST_RECONCILIATION_2026-10-15.md). Starting `main` is `80a4506485c7f4a6a566c495120723995dfc2c17`. CI #499 succeeded. Build Image #178 succeeded. Full pytest on CI #499 was 4511 passed, 5 skipped. The Bandit 1.9.4 gate scanned 649 files, reported 35 findings, and matched 35 exact exceptions. pip-audit on that run was 73 packages, 0 vulnerabilities, 0 exceptions. Runtime code is unchanged.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded next engineering slice is selected and is not implemented here. It is not named Sprint 40.8.

**Selected next engineering slice:** Add one deterministic container-vulnerability scan of the locally built runtime image, and fail publication before that image is pushed.

The SAST capability is IMPLEMENTED-NOT-PROVEN. It is not PROVEN. The 35 reviewed exceptions do not prevent that class. R6 stays PARTIAL because container vulnerability scanning and IaC security scanning remain absent. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. R10 and R19 stay PARTIAL as pre-activation prompt isolation. R13 stays PARTIAL because the literal binding sentence is unmet and no security consequence remains. R15 stays an owner decision. R16 stays PARTIAL because a per-session bucket is still absent and is defense-in-depth, not the selected slice. R12 and R21 stay closure gates because the HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. No Included requirement is PROVEN. Counts: PROVEN 0, IMPLEMENTED-NOT-PROVEN 13 (R1, R2, R3, R4, R5, R7, R8, R9, R11, R14, R17, R18, R20), PARTIAL 8 (R6, R10, R12, R13, R15, R16, R19, R21), MISSING 0, BLOCKED-DEPENDENCY 0, NOT-APPLICABLE 0.

The Sprint 40 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The CSRF/Origin, CSP `'unsafe-inline'`, and URL/SSRF MEDIUMs remain IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION for the original no-scanner condition. This reconciliation does not broaden that finding. They are not relabeled launch-blocking. No risk acceptance is recorded. Canonical snapshot immutability is unchanged. Guest-to-account rebind of a canonical snapshot remains a product-definition conflict and requires an owner decision.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Correction — secret-scan scope (2026-10-16)

This section does not rewrite the Planned status, the Included requirements, the earlier records, or the post-SAST reconciliation section above. It corrects that section's secret-scan status and its selected slice. Evidence remains [`../evidence/SPRINT_40_POST_SAST_RECONCILIATION_2026-10-15.md`](../evidence/SPRINT_40_POST_SAST_RECONCILIATION_2026-10-15.md). CI #501 is green on `3b7adfd7be1782bfebc6379e472c61e5fb8579dd`. Runtime code is unchanged. This correction is not named Sprint 40.8.

The first reading called secret scanning present and selected a container-vulnerability scan. That selection is withdrawn. `scripts/secret_scan_25a.py` scans `infra/**/*`, `.env*.example`, `scripts/**/*`, and `.github/workflows/**/*`. It does not scan `app/`. Bandit is not a secret scanner. `DEMO_PASSWORD` in `app/user/fixtures.py` matches the existing password-assignment rule. `INTERNAL_LAUNCH_ADMIN_TOKEN` in `app/launch/internal_auth.py` is a credential-shaped constant outside the gate. R6 stays PARTIAL. SAST stays IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning stay absent.

**Audit verdict:** B. Sprint 40 is not ENGINEERING COMPLETE. The corrected slice is not implemented here.

**Selected next engineering slice:** Extend the deterministic secret-scanning gate to application source with an explicit reviewed exact-exception mechanism for intentional safe demo constants.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Implementation record — application secret scan (2026-10-16)

This section does not rewrite the Planned status, the Included requirements, the 2026-10-09 readiness audit, the Sprint 40.1 through Sprint 40.7 records, the later reconciliations, the failed-login lock and message-idempotency records, the security-readiness package, the SAST gate record, or the secret-scan scope correction above. It is not named Sprint 40.8. The slice selected by that correction is now in the tree: `scripts/secret_scan_25a.py` scans `app/**/*.py` in addition to infra, env examples, scripts, and workflows. The application rule uses `ast.parse` and does not import application modules. After PR #206, the scan of current `main` read 649 application Python files and reported 8 findings. None was a production credential or private key. The removed launch-admin symbol has no exception. Each current finding has one exact baseline exception in `tests/security/baselines/secret-scan.baseline.json`. No application source was changed by this slice. The secret-scanning capability is IMPLEMENTED-NOT-PROVEN. It is not PROVEN. Evidence: [`../evidence/SPRINT_40_APPLICATION_SECRET_SCAN_2026-10-16.md`](../evidence/SPRINT_40_APPLICATION_SECRET_SCAN_2026-10-16.md). Starting `main` is `f7060de8ac1ef362bfb8df558762a148a6e1df59`.

R6 stays PARTIAL. SAST stays IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning remain absent. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. The historical MEDIUM "No Dependabot/CodeQL/Trivy/pip-audit" stays CLOSED BY IMPLEMENTATION for the original no-dependency-scanner condition. This record does not broaden that finding. This record does not select a later engineering slice.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Implementation record — container vulnerability gate (2026-10-17)

This section does not rewrite the Planned status, the Included requirements, the earlier records, or the application secret scan above. It is not named Sprint 40.8. Grype 0.120.1 scans the locally built runtime image. CI scans `dealbrain:ci-<gitsha>` after the image exists and the production smoke import succeeds, and it does not publish. Build Image builds the final `sha-<gitsha>` image locally, scans that same tag, and pushes it only after the gate succeeds. The release manifest still records the post-push registry digest. Evidence: [`../evidence/SPRINT_40_CONTAINER_VULNERABILITY_SCAN_2026-10-17.md`](../evidence/SPRINT_40_CONTAINER_VULNERABILITY_SCAN_2026-10-17.md). Starting `main` is `6ed3662d520d9e41a4bdc3df5ccc56b49c520300`.

The local scan of `dealbrain:ci-local` reported 1182 packages and 172 findings: 0 Critical, 55 High, 59 Medium, 11 Low, and 47 Negligible. The baseline has 0 exceptions. The 55 HIGH matches are Debian 13 packages with no fixed version listed. No image package was changed. The gate fails closed. Container vulnerability scanning is not a passing control, is not PROVEN, and is not complete. Secret scanning and SAST stay IMPLEMENTED-NOT-PROVEN. Dependency scanning stays implemented. IaC security scanning remains absent. R6 stays PARTIAL. The historical MEDIUM "No Dependabot/CodeQL/Trivy/pip-audit" stays CLOSED BY IMPLEMENTATION for the original no-dependency-scanner condition. This record does not broaden that finding. This record does not select IaC scanning.

## Base comparison — no HIGH-clearing candidate (2026-10-17)

This section does not rewrite the gate record above and does not select IaC scanning. Temporary full images were scanned with the same Grype 0.120.1 database. `python:3.12-slim-bookworm` reported 3 Critical and 79 High. `apt-get upgrade` did not change that result. `python:3.12-alpine` reported 0 Critical and 1 High (`CVE-2026-85091` on zlib, listed fix `1.3.2-r1`) and uses musl wheels. It is not selected. Removing uv and global pip from a temporary Debian 13 runtime left the 55 HIGH matches in place. The committed Dockerfile stays `python:3.12-slim`. No exception was added. Evidence: [`../evidence/SPRINT_40_CONTAINER_BASE_COMPARISON_2026-10-17.md`](../evidence/SPRINT_40_CONTAINER_BASE_COMPARISON_2026-10-17.md).

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged. Live research stays off. Real Shopify calls stay 0.

## Implementation record — IaC security scan (2026-10-20)

This section does not rewrite the Planned status, the Included requirements, the earlier records, or the container records above. It is not named Sprint 40.8. It is not a Sprint 40 reconciliation. Trivy 0.76.0 scans `infra/terraform` in the Terraform CI job. The installer checks the official Linux amd64 archive checksum `e24b1c51293c1b15e4ba8d45bbc7891ba053f90278ec2698f3562c993e145fe7`. The gate parses JSON and compares an explicit baseline. The baseline has 0 exceptions. Evidence: [`../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md`](../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md). Starting `main` is `078d768f2653dc0ac69f94063ea04ff57584fe15`.

The first scan reported 30 findings: 6 Critical, 9 High, 5 Medium, 10 Low, 0 Unknown. Two source defects were fixed without an apply: public subnets no longer auto-assign public instance addresses, and the ALB security group egress is TCP 8000 to the API security group. The rescan reported 24 findings: 4 Critical, 5 High, 5 Medium, 10 Low, 0 Unknown. Those 24 remain unbaselined because each one needs an owner or security decision, or a proposed not-applicable note that this slice does not commit. The gate exits 1. GitHub Actions run `39415287343` on draft PR #208 failed only in the Terraform job, on that gate. IaC security scanning is implemented and fail-closed. It is not a passing control, not PROVEN, and not IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning stays IMPLEMENTED-NOT-PROVEN. R6 stays PARTIAL. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. No Terraform apply was performed. No deploy was performed. No AWS resource was changed.

The Docker dependency stage still references `ghcr.io/astral-sh/uv:latest`. This slice does not change that floating build-tool reference. The later Sprint 40 reconciliation should evaluate it. This record does not select Sprint 41.

On 2026-10-22 `certifi` moved from 2026.7.22 to 2026.10.19, and the Dockerfile base is pinned to `python:3.12-alpine3.24@sha256:92abd2ba1bdfb48b1e2ac224b582dd1558d0d4bb11c903b126b5bf9c448fd656` (CPython 3.12.15, Alpine 3.24.3). The three CVE-2025-60876 exception PURLs now use `alpine-3.24.3`. Their rationale is unchanged. The IaC baseline stays empty. This is not a Sprint 40 reconciliation.

On 2026-10-22 the owner required the HTTP-forward listener and the all-protocol API egress rule to be removed, and approved five exact High exceptions only if a rescan showed no new Critical or High finding. The HTTP-forward listener is gone. API egress is TCP 443 to `0.0.0.0/0` and TCP 5432 to the RDS security group. The empty-baseline rescan removed both `AWS-0054` findings and both `api_all` findings, then reported a new Critical `AWS-0104` on `api_https` for staging and production. Those two findings were not baselined. The five approved High exceptions were not loaded. The baseline stays empty. Evidence: [`../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md`](../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md). No Terraform apply was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.

On 2026-10-22 the two Critical `api_https` findings were classified as a real architectural exposure, pending explicit acceptance. Preserving NAT for the PH-first beta is under consideration and is not acceptance. `not_applicable` and `false_positive` do not describe them. The gate still allows only those two rationales, so `accepted_risk` remains rejected. No exception was added. The smallest later policy change is one new `accepted_risk` rationale plus the two exact identities in the evidence file. No Terraform apply was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.

On 2026-10-22 the owner explicitly accepted the residual outbound HTTPS risk for the two `api_https` AWS-0104 findings only, for the current PH-first controlled public beta. The gate now allows `accepted_risk`. The baseline lists those two exact findings and no others. The five High findings and every Medium and Low finding stay unbaselined, so the IaC gate still fails closed. Outbound controls need another review before wider production exposure. Evidence: [`../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md`](../evidence/SPRINT_40_IAC_SECURITY_SCAN_2026-10-20.md). No Terraform apply was performed. No deploy was performed. No AWS resource was changed. This is not a Sprint 40 reconciliation.
