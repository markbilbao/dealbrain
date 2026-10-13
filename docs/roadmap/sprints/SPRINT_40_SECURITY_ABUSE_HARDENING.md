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
