# Sprint 40 security readiness audit — 2026-10-09

**Audit verdict:** One bounded Sprint 40 engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Non-decision assistant body-identity authorization.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Not started. This change is the readiness audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `0452c40610ac61cd9dce4af361718cb4fd2c02d7`

**Post-merge evidence on that SHA:** CI #453 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/37861395472`). Build Image #161 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/37861975417`). Those runs are publication and test evidence for the merged tree. They are not a security-scanner clean bill and they are not an abuse-control exercise.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Gap inventory authority for historical findings:** section I and the Sprint 30 security-finding map in [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md). Those rows are not rewritten. This audit says which of them are still true on this `main`.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate tracking was not enabled. No provider or public-market activation was changed. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. This audit does not reopen Sprint 38 or Sprint 39 engineering. No repository evidence in this pass showed a new Sprint 38 or Sprint 39 gap.

## How a row becomes PROVEN

Code on `main` is not enough. A row is PROVEN only when the current tree shows the control, a test fails closed for the abuse case, and the Sprint 40 acceptance bar for that control is met. Staging or production evidence is recorded when it exists. Absence of a fresh staging run keeps a tested control at IMPLEMENTED-NOT-PROVEN or PARTIAL. This audit did not execute the application.

No Included requirement is PROVEN. No Included requirement is NOT-APPLICABLE. No Included requirement is wholly BLOCKED-DEPENDENCY. Formal SOC 2 and a full WAF/CDN program are explicit non-goals. They are not Included rows.

## Requirement matrix

| ID | Requirement | Class | Evidence | Tests | Staging | Production | Severity if a real gap exists | Sprint 40 engineering blocker | Dependency owner | Recommended action |
|----|-------------|-------|----------|-------|---------|------------|--------------------------------|-------------------------------|------------------|--------------------|
| R1 | AuthN/AuthZ/object-level review | PARTIAL | Decision and canonical snapshot reads use `get_for_owner` with the signed owner cookie. Account cookies are checked against `SessionRepository` in `app/consumer/owner_authorization.py`. The non-decision assistant path still loads and appends by body `conversation_id` and personalizes from body `user_id` / `profile_id`. | `tests/unit/test_phase_29_4a_answer_from_evidence.py` raises on a foreign decision owner. `tests/unit/test_sprint29_guest_claim.py` rejects a foreign guest claim. No test rejects a foreign body id on `POST /api/v1/shopping-assistant/query` without `decision_id`. | None on this SHA | None | Unscored. See the selected slice. This audit does not assign a new HIGH or MEDIUM. | Yes. The missing object-level check is the selected slice. | Sprint 40 | Implement the selected slice. Do not treat the decision-path tests as coverage of the legacy query path. |
| R2 | Session security review | PARTIAL | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. Expiry and revocation are checked in `AuthService.validate_session`. Password reset and email change call `revoke_all_for_user`. `docs/SECURITY_MODEL.md` still describes Sprint 17 demo limits, including in-memory sessions. SQL session persistence exists and that document was not reconciled. MFA and OAuth extension points remain inert. | `tests/unit/test_user_platform_security.py`, `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_user_platform_password.py` | Sprint 27 staging inbox and logout evidence is historical. It was not re-run on this SHA. | None. Production secret attach remains Sprint 41. | None newly scored. The Sprint 30 HIGH "demo-grade auth/email/reset" is not still an open absence: Sprint 27 is COMPLETE / CLOSED for staging transactional email, and `ALLOW_DEMO_RESET_TOKENS` must be false in staging and production. | No. A fresh session review can follow the selected slice. | Sprint 41 for production email secrets only | Leave Sprint 27 closed. Reconcile `docs/SECURITY_MODEL.md` in a later doc pass. Do not reopen Sprint 27 engineering from this audit. |
| R3 | Headers/CSP/CORS/CSRF policy completion | PARTIAL | `SecurityHeadersMiddleware` sets CSP, `X-Frame-Options`, `nosniff`, Referrer-Policy, Permissions-Policy, and HSTS on staging/production. Default CSP in `app/core/config.py` still contains `script-src 'self' 'unsafe-inline'` and `style-src 'self' 'unsafe-inline'`. Production validation rejects CORS `*`. `CsrfTokenService` issues a token and does not enforce it on any route. Owner cookie is `HttpOnly`, `SameSite=lax`, and `Secure` in staging/production. | `tests/unit/test_sprint22_api.py` asserts CSP presence. `tests/unit/test_user_platform_security.py` tests token compare only. `tests/unit/test_sprint29_owner_cookie_auth.py` tests cookie flags. | None on this SHA | None | Existing MEDIUM from the Sprint 30 map: CSRF not enforced. Existing MEDIUM: CSP `'unsafe-inline'`. Both conditions are still true. This audit does not relabel either as launch-blocking. No written risk acceptance exists. | Yes, later. Not the first slice. `SameSite=lax` is a partial browser mitigation, not policy completion. | None | Keep both MEDIUM findings open. Do not remove `'unsafe-inline'` in the first slice; inline script use was not inventoried here. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | PARTIAL | `app/consumer/html.py` `h()` uses `html.escape` with `quote=False`. `attr()` and account `_esc` quote attributes. SQL found in request paths is constant `SELECT 1` through SQLAlchemy `text()`. `app/marketplace/security.py` `validate_url` allows any http(s) host and does not reject private or link-local addresses. No merchant-host allowlist was found. `_safe_next` in `app/api/account.py` and `app/api/consumer.py` keeps paths under `/results/`, `/compare/`, `/why-best-piq/`, `/account`, and `/search`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Live Shopify transport stays fail-closed. | No open-redirect test was found. No SSRF negative test was found. Encoding is covered indirectly by page tests. | None on this SHA | None | Existing MEDIUM: URL validation / SSRF hardening incomplete. The condition is still true as incomplete validation. This audit did not demonstrate a reachable SSRF, SQLi, command injection, or XSS, and it does not create those findings. | Yes, later, for URL hardening. Not the first slice. | Sprint 38 and Sprint 41 keep live fetch and production network controls. They do not own this validation gap. | Do not open routing or call Shopify to exercise SSRF. Add private-network rejection only after the body-identity slice, with tests that do not perform live fetches. |
| R5 | Log redaction; body logging policy; PII handling | PARTIAL | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body. `app/launch/redaction.py` redacts secret-like keys and a few free-text tokens. Auth audit metadata still records email. Product analytics forbids question, query, answer, session id, and conversation id. | `tests/unit/test_sprint21_analytics_admin.py`, `tests/unit/test_sprint25b5g_migration_url_evidence.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` `test_server_identity_is_opaque_and_ask_text_is_absent` | None on this SHA for a log sample | None | None newly scored. Email in the auth audit is an existing design, not a new finding. | No for the logging middleware. R18 covers the remaining conversation-body gap. | Sprint 28 owns account export and deletion. Sprint 39 owns product-analytics privacy. | Do not copy audit emails into product analytics. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | `.github/workflows/ci.yml` runs `scripts/secret_scan_25a.py` and `terraform validate`. The secret scan reads infra, env examples, scripts, and workflows. It does not scan `app/`. No Dependabot, CodeQL, Trivy, pip-audit, Bandit, Semgrep, Checkov, or tfsec config was found. The image job builds and smoke-imports. It does not scan the image. | `tests/unit/test_sprint25a_infrastructure.py` covers the secret-scan contract. | CI #453 succeeded. That is not a dependency, SAST, or image-scan result. | None | Existing MEDIUM: no Dependabot/CodeQL/Trivy/pip-audit. The condition is still true. This audit does not relabel it launch-blocking. | Yes, later. A scanner gate is a separate slice. Turning one on without a baseline can fail `main` for existing advisories. | None for adding the gate. Sprint 41 does not own CI scanners. | After the body-identity slice, add one scanner in CI with an explicit baseline. Do not weaken the existing secret scan. |
| R7 | Supply-chain provenance checks; immutable image authority verification | PARTIAL | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, and states that mutable tags are not deployment authority. No cosign, SLSA, or signed provenance attestation was found. | `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum. | Build Image #161 succeeded for this SHA. That shows the publish workflow completed. It is not a signed provenance attestation. | None. Production pull and IAM review remain Sprint 41. | None. The historical gap inventory calls GHCR digest authority `implemented_verified`. Signed provenance is still absent, so the combined Sprint 40 bullet is not PROVEN. | No. Digest publication already exists. Signed provenance is a later decision, not this slice. | Sprint 41 for production image pull | Do not treat Build Image #161 as Sprint 40 closure. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | PARTIAL | `ConfigurableRateLimiter` is an in-process sliding window. `RateLimitMiddleware` keys by client IP or the first 8 characters of a bearer token. Auth `RateLimiterHook` is a second in-process window keyed by email. Affiliate routes fall in the affiliate bucket. No bot challenge, no credential-stuffing control beyond those windows, and no click-fraud score were found. No shared limiter store exists. | `tests/unit/test_sprint22_services.py`, `tests/unit/test_user_platform_security.py` | None on this SHA. Required staging evidence is "abuse controls exercised". That evidence is absent. | None | Existing HIGH: in-process rate limits only. The condition is still true. It stays an open Sprint 40 HIGH. It is not selected as the first slice. A distributed MVP needs a shared counter. A wrong first limiter can lock legitimate users out. Full WAF remains a non-goal. | Yes. It remains open after the selected slice. | Sprint 43 owns cache and capacity depth. Sprint 40 still owns the beta decision and MVP. The absence of Redis does not move the HIGH to Sprint 43. | Record the HIGH as open. Do not implement a distributed limiter in the first slice. |
| R9 | Account lockout or equivalent | PARTIAL | No `lockout`, `failed_login` counter, or `locked_until` field was found. The equivalent on this tree is the in-process login and per-email windows. Those reset on process restart and are not shared across instances. | Login rate-limit tests in `tests/unit/test_user_platform_auth_service.py` | None | None | None newly scored. The gap inventory already says brute-force protection is rate limit only, with no lockout. | Yes, later. Closing it inside one process would not close the R8 HIGH. | None | Do not add a lockout that only lives in process memory and then call the HIGH closed. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings: "ignore previous", "ignore all instructions", "system prompt", "reveal the prompt", "api key", "override safety". A match adds a warning and the deterministic answer still runs. Merchant text, reviews, and tool calls are not passed through that function. | `tests/unit/test_shopping_assistant_service.py` `test_prompt_injection_resistance` | None | None | None newly scored. The six-marker warning is not a completed review. | No for this slice. The markers are a baseline, not the authorization hole. | Sprint 13 owns assistant fallback. Sprint 40 owns the review. | Leave the marker list unchanged in the first slice. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | MISSING | No pen-test checklist, security incident-response runbook, or vulnerability-response process was found. `docs/SECURITY.md` is the Sprint 22 control note. `docs/SECURITY_MODEL.md` is the Sprint 17 model. | None | None | None | None newly scored. Absence is the gap. | No. This is a documentation deliverable. It does not block the body-identity slice. | Sprint 42 owns operational incident response, probes, alerts, and paging. Sprint 40 still owns the pen-test package and the vulnerability-response process. | Write those documents after the control slice. Do not treat a Sprint 42 paging runbook as this package. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 30 map still matches current code for the Sprint 40 HIGH and the Sprint 40 MEDIUMs named below. No risk-acceptance record exists. Findings owned by Sprint 41 and Sprint 42 cannot be closed here. | None that close the HIGH | None | None | See the findings section. | Yes, as a closure gate. Not one code change. | Sprint 41 and Sprint 42 for the HIGHs they own | Do not mark Sprint 40 closed. Do not risk-accept the in-process limiter in this audit. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Canonical decision routes call `authorized_owner_from_request`. `get_for_owner` returns nothing when the owner is missing or different. `InMemoryConversationRepository.create` accepts `owner=None`. `append_turn` loads with `get`, and if the id is new it stores a context with no owner. `_require_active_owner` rejects only an expired owner. A null owner passes. | Decision-owner tests cited under R1. `test_follow_up_conversation_context` continues a conversation with only the body id. | Sprint 29 guest-claim staging notes are historical and were not re-run. | None | Unscored. Same behavior as R14. | Yes. Same slice as R14. | None | Bind new non-decision conversations to the verified owner. Do not select an ownerless row from a client id. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | PARTIAL | `POST /api/v1/shopping-assistant/query` passes `body.model_dump()` through. With `decision_id`, `propose_research`, refinement, and evidence answers load through `get_for_owner`. Without `decision_id`, `ShoppingAssistantService.query` calls `self._conversations.get(conversation_id)` and later `append_turn` on that id. `_normalize_request` copies body `user_id` and `profile_id`. `_user_platform_context` loads that user's profile, display name, and overrides with no session check. `record_shopping_recommendation` writes the query and summary onto that `user_id`. `shopping_assistant_context` treats any found profile as authenticated. Decision-path body `conversation_id` is a lookup key under the cookie owner, which matches the requirement. The claim route also takes body ids and then calls `get_for_owner` for the guest cookie. | No negative test for the non-decision path. Foreign decision-owner tests do not cover it. | None | None | Unscored. The repository has no prior HIGH or MEDIUM for this path. This audit does not create one. The Included sentence is still false on the mounted non-decision route. | Yes. This is the selected slice. | None | See the slice section. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest `principal_id` and `session_id` are `uuid4`. The cookie is HMAC-SHA256 over the identity payload. Expiry is seven days and is checked in `parse_owner_cookie`. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie, so it does not rotate. There is no server-side guest revocation list, so a copied cookie works until expiry. UI sign-out calls `POST /api/v1/auth/logout` and then `POST /account/clear-device`. The logout route itself does not clear the owner cookie. `claim_guest_conversation` rebinds only when no canonical UUID snapshot exists. When one exists it returns `immutable_snapshot_owner` and keeps the guest cookie. | `tests/unit/test_sprint29_owner_cookie_auth.py` covers signature, expiry, and `Secure`. `tests/unit/test_sprint29_guest_claim.py` covers foreign claim, expired guest, and `clear-device`. `tests/unit/test_sprint27_4_auth_aware_header.py` asserts the UI calls both logout and `clear-device`. | Sprint 29 staging recorded logout 204 and `clear-device` deleting the cookie. Not re-run on this SHA. | None | None newly scored. The acceptance sentence that guest→authenticated transition rotates ownership credentials is not met for canonical snapshots. The code comment says that refusal is deliberate so an immutable snapshot is not hidden. | No for the first slice. The canonical refusal is a definition conflict, not the body-id hole. | None. Snapshot immutability is already implemented. | Do not change rebind behavior until a later reading reconciles the acceptance sentence with the immutable-snapshot rule. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Cookie transport has `SameSite=lax` and no Origin or CSRF check. Rate-limit identity is IP or a bearer prefix. It is not the session id and not the account principal. The per-email auth window is separate and in-process. | Cookie flag tests and rate-limit unit tests. No origin-rejection test. | None | None | Existing MEDIUM: CSRF not enforced. Still true. Not relabeled launch-blocking. | Yes, later. Not the first slice. | None | Add an origin check only after the body-identity slice, without disabling `SameSite=lax`. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | PARTIAL | Research confirmation derives `research-auth:<sha256>` from the owner binding, conversation, decision, proposal, and scope. The client confirmation token is ignored as execution identity. Repeat confirmation reuses the key. Non-decision `append_turn` has no idempotency key. A repeated message appends another turn. | `tests/unit/test_research_authorization_handoff.py` `test_idempotency_key_is_server_derived`. Sprint 38 execution tests cover the research key. No message-replay test. | None | None | None newly scored. Research confirmation already has the control. Message submission does not. | Yes, later, for message submission only. | Sprint 38 owns research execution consumption. It already has the server key. | Do not reopen Sprint 38. Add message idempotency in a later Sprint 40 slice. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | PARTIAL | Analytics `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. The request log does not record the body or the owner cookie. The non-decision assistant stores the raw query on recommendation history when a body `user_id` is present. Auth audit metadata can contain email. | `test_server_identity_is_opaque_and_ask_text_is_absent` asserts the ask event omits the question and the raw session id. | None on this SHA | None | None newly scored. The history write is part of R14, not a separate logging defect. | No beyond the selected slice, which stops writing that history from a body `user_id`. | Sprint 39 owns the analytics forbid-list. | Do not put conversation text into `product.analytics_events`. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the six injection markers are the same facts as R4 and R10. Assistant processing sets `secrets_included` and `prompts_included` false on the response object. This audit did not re-read every provider payload. No research cost cap or amplification guard was found on confirmation. Live research remains fail-closed, so confirmation does not spend a provider call today. | `test_no_secrets_in_response_processing`, `test_prompt_injection_resistance` | None | None | None. No cost-amplification incident is in the repository. Fail-closed research is not the same as a cost limit. | No | Sprint 38 owns live research execution and stays fail-closed. | Do not enable live research to test cost controls. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | PARTIAL | This matrix is the coverage review. Private decision routes set `noindex` and `robots.txt` disallows `/results/`, `/compare/`, `/why-best-piq/`, and `/account`. Affiliate click storage exists. Click-fraud detection does not. Tool-abuse controls beyond the injection warning were not found. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py` | Sprint 29 SEO tests are repository tests. No fresh staging crawl was run. | None | None newly scored for SEO. SEO isolation is implemented and tested. The rest of the list is not. | No as a separate row. The open parts are R1, R4, R6, R8, R11, and R14. | Sprint 29 owns the SEO implementation. | Do not reopen Sprint 29. Do not enable affiliate tracking. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same open findings as R12. Sprint 45 is the deadline, not a place to move the work. | None | None | None | Same as R12 | Yes, as the same closure gate | Sprint 41 and Sprint 42 for findings they own | Duplicate of R12. Do not start Sprint 45. |

## Open HIGH findings

These are the Sprint 30 map rows that are still true. This audit adds no new HIGH.

| Finding | Still true? | Owner | Sprint 40 engineering |
|---------|-------------|-------|------------------------|
| No production deploy/isolation path | Yes. Sprint 41 remains UNSTARTED. | Sprint 41 | No. Do not start Sprint 41. |
| Demo-grade auth/email/reset not production-safe | No longer an open absence. Sprint 27 is COMPLETE / CLOSED for staging transactional email and demo-reset refusal. Production email secret attach remains Sprint 41. | Sprint 27 closed the staging defect. Sprint 41 holds production secrets. | No. Do not reopen Sprint 27. |
| In-process rate limits only | Yes. `app/launch/rate_limit.py` states the limiter is not a distributed limiter. | Sprint 40 | Yes, later. Not the selected slice. |
| No CloudWatch/security paging | Yes. No paging implementation was found. | Sprint 42 | No. |
| Production OIDC/SSM interim vs staging hardening | Yes. Production IAM is not applied. | Sprint 41 | No. |

The acceptance line "No open HIGH" is therefore not met. Closing Sprint 40 cannot, by itself, clear the Sprint 41 and Sprint 42 HIGHs.

## Launch-blocking MEDIUM findings

The repository labels four Sprint 40 MEDIUMs. It does not separately mark any of them launch-blocking. No written, time-boxed risk acceptance exists. This audit does not promote them to launch-blocking and does not close them.

| Finding | Still true? | Notes |
|---------|-------------|-------|
| CSRF not enforced | Yes | Token issue and compare exist. No route enforces them. `SameSite=lax` reduces classic cross-site POST cookie sending. That is not enforcement. |
| CSP `'unsafe-inline'` | Yes | Default `security_csp` still contains it for scripts and styles. |
| No Dependabot/CodeQL/Trivy/pip-audit | Yes | CI has a deterministic secret scan and Terraform validate only. |
| URL validation / SSRF hardening incomplete | Yes | Scheme and host checks exist. Private-network and merchant allowlist controls do not. No reachable SSRF was demonstrated. Live fetch stays fail-closed. |
| No account deletion / GDPR path | No longer an absence | Sprint 28 has the deletion API and staging deletion evidence. Sprint 28 is not COMPLETE / CLOSED because external legal publication remains. That remainder is not Sprint 40 work. |

## Security items already satisfied

These are not Sprint 40 reopeners. They are also not PROVEN Included rows.

- Sprint 27 staging transactional email, demo-reset refusal, and the paired UI logout plus `clear-device` path.
- Sprint 28 account deletion and export engineering.
- Signed owner-cookie rejection of unsigned, tampered, forged, and expired values.
- Decision and snapshot reads that use `get_for_owner`.
- Foreign guest claim rejection.
- Research-confirmation idempotency keys derived on the server.
- Product-analytics refusal of question text and raw session ids on the ask event.
- Secret-key redaction and the existing CI secret scan.
- Immutable GHCR digest publication, exercised by Build Image #161, without signed provenance.
- Private-route `noindex` and robots disallow rules.
- No request-path command execution was found under `app/`.
- No dynamic SQL assembly was found on request paths. That is an absence of a sink, not a SQLi certification.
- Sprint 38 live research stays fail-closed. Routing stays 0. Real Shopify calls stay 0.

## Duplicated requirements

Implement each control once.

- R12 and R21 are the same closure gate. R21 adds the Sprint 45 deadline.
- R3 and R16 both require a CSRF/origin policy for cookies.
- R4 and R19 both cover output encoding, XSS, and prompt injection.
- R5 and R18 both cover log and analytics redaction. R18 adds conversation bodies and session ids.
- R1, R13, R14, and the identity clause of R20 are one authorization problem. R14 is the falsifiable sentence.
- R8, R9, and the rate-limit, credential-stuffing, bot, and click-fraud clauses of R20 are one abuse-control problem.
- R10 and the prompt-injection clauses of R19 and R20 are one review.

## Sprint 41 work, not Sprint 40 engineering

- Production VPC, database, secrets, IAM, OIDC, deploy, rollback, DNS, and TLS.
- The Sprint 40 production-evidence line "Prod IAM review continues in 41".
- Production email secret attach left open by Sprint 27.
- Production image pull. Build Image #161 does not start that review.
- The HIGHs for production isolation and production OIDC/SSM.

Sprint 41 stays UNSTARTED. This audit does not start it.

## Sprint 42 work, not this slice

- CloudWatch and security paging.
- Operational incident response, probes, alerts, and paging runbooks.

Sprint 40 still owns the pen-test readiness package and the vulnerability-response process. Those documents are missing. They are not a reason to start Sprint 42.

## Operational work, not this engineering slice

- Exercising abuse controls on a staging candidate.
- A scanner-clean result on a deployed candidate.
- A pen-test engagement.
- A written risk acceptance with an expiry.
- Production IAM review.

## Selected slice

**Choice:** A. One bounded Sprint 40 engineering slice.

B is not selected. The canonical rebind sentence conflicts with the implemented immutable-snapshot rule, and several Included bullets repeat each other. Neither conflict has to be rewritten before the body-identity requirement can be implemented. That requirement is already exact.

C is not selected. The slice does not need Sprint 41, a Shopify credential, routing, or a new store.

**Slice:** On the non-decision shopping-assistant query path, stop using request-body `conversation_id`, `profile_id`, and `user_id` as authority.

Current defect, from repository code only:

- `app/api/v1/endpoints/shopping_assistant.py` `query_shopping_assistant` passes the parsed body to `ShoppingAssistantService.query`.
- Without `decision_id`, `app/services/shopping_assistant_service.py` `query` reads `self._conversations.get(conversation_id)` and later `append_turn` on that id.
- `InMemoryConversationRepository.get` and the SQL `get` return the row with no owner check. `append_turn` can create an ownerless context.
- `_normalize_request` copies body `user_id` and `profile_id`.
- `UserPlatformService.shopping_assistant_context` loads that account and marks the context authenticated.
- `record_shopping_recommendation` stores the query text on that account.

The decision-bound branch already uses the cookie owner and `get_for_owner`. This slice must not weaken that branch.

**Likely files:**

- `app/services/shopping_assistant_service.py`
- `app/api/v1/endpoints/shopping_assistant.py`
- `app/services/user_platform_service.py`, only if history and profile reads must take the session user instead of a raw id
- `tests/unit/test_shopping_assistant_service.py`
- `tests/integration/test_shopping_assistant_flow.py`
- a new `tests/unit/test_sprint40_assistant_body_identity.py`

**Acceptance tests:**

1. A non-decision query that sends another conversation's `conversation_id` does not read that conversation's prior products or turns and does not append a turn to it.
2. A non-decision query that sends another account's `user_id` does not load that account's profile, display name, or overrides, and does not write recommendation history for that account.
3. A non-decision query that sends a `profile_id` does not apply personal-agent personalization unless that profile is already bound to the verified account principal.
4. The same verified guest or account owner can continue a non-decision conversation that is stored with that owner. A client id with no matching owner does not continue it.
5. Existing foreign decision-owner failures still fail closed, including `tests/unit/test_phase_29_4a_answer_from_evidence.py`.
6. `test_follow_up_conversation_context` must be updated. It currently continues with a body `conversation_id` and no owner. After the slice, that continuation is rejected unless the stored owner matches the caller.

**Out of scope for the slice:** CSP edits, scanner installation, a distributed limiter, account lockout, CSRF middleware, SSRF changes, rebind of canonical snapshots, Sprint 38 flags, Sprint 39 measurements, affiliate click behavior, and any deploy.

## What this audit did not find

- No new HIGH.
- No new MEDIUM, and no document that already marks a MEDIUM launch-blocking.
- No evidence that Sprint 38 engineering completeness or Sprint 39 Class C count changed.
- No pen-test report, scanner output, or risk register beyond the Sprint 30 map in the gap inventory.
- No reachable SSRF, SQLi, command injection, or XSS proof. Incomplete URL validation stays the existing MEDIUM. It is not a demonstrated exploit.
