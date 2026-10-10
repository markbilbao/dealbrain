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

This section does not rewrite the Planned status, the Included requirements, the readiness audit, or the Sprint 40.1, Sprint 40.2, Sprint 40.3, and Sprint 40.4 records above. Sprint 40.5 separates server-fetch URL checks from browser link and browser resource checks. The Shopify production transport accepts only `https://catalog.shopify.com/api/ucp/mcp` and does not follow redirects. The Sprint 40 MEDIUM "URL validation / SSRF hardening incomplete" is IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN. No reachable SSRF exploit is demonstrated. Staging has not exercised the policy. Evidence: [`../evidence/SPRINT_40_5_URL_TRUST_2026-10-10.md`](../evidence/SPRINT_40_5_URL_TRUST_2026-10-10.md). Starting `main` for the slice is `5dbc52295a38d056bca9347f7a69f605b3ad7414`.

Sprint 40 stays Planned. It is not COMPLETE / CLOSED and not ENGINEERING COMPLETE. No Included requirement is PROVEN. The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.4 CSRF/Origin MEDIUM remains IMPLEMENTED-NOT-PROVEN. CSP `'unsafe-inline'` remains an open MEDIUM. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. They are not relabeled launch-blocking. No risk acceptance is recorded.

Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE, with closure validation blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.
