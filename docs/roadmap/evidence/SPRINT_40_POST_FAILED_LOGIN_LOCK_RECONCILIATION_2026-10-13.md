# Sprint 40 post-failed-login-lock reconciliation — 2026-10-13

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Ordinary shopping-assistant message submission must not apply twice when the same client request is retried.

This slice is not named Sprint 40.8. A later implementation may take a number. This audit only selects the work.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.7 are merged. The durable failed-login lock is merged. This change is a reconciliation audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `bfdac461250d67f8e144df0811e707410b685437`

**Post-merge evidence on that SHA:** CI #484 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38379493008`). Full pytest on that run: 4445 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #172 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38380524821`). Those runs are publication and test evidence for the merged tree. They are not a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical inputs, not copied forward:** [`SPRINT_40_POST_40_7_RECONCILIATION_2026-10-13.md`](SPRINT_40_POST_40_7_RECONCILIATION_2026-10-13.md) and [`SPRINT_40_FAILED_LOGIN_LOCK_2026-10-13.md`](SPRINT_40_FAILED_LOGIN_LOCK_2026-10-13.md). Those files keep the classes they recorded. This reconciliation re-reads the tree at `bfdac461250d67f8e144df0811e707410b685437` and classifies R1–R21 again. The 2026-10-09 readiness audit stays historical.

**Gap inventory:** section I and the Sprint 30 security-finding map in [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md) are not rewritten. Additive notes below say which historical findings are still true.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate activation stays off. No provider or public-market activation was changed. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. This audit does not reopen Sprint 38 or Sprint 39 engineering.

## How a row becomes PROVEN

Code on `main` is not enough. A row is PROVEN only when the current tree shows the control, a test fails closed for the abuse case, and the Sprint 40 acceptance bar for that control is met. A fresh staging or production run is recorded when it exists. Absence of that run keeps a complete, tested control at IMPLEMENTED-NOT-PROVEN. A control that is only partly present stays PARTIAL even when some of its tests pass.

This reconciliation did not execute the application on staging or production. Repository tests cited below were re-read. They are not staging proof.

No Included requirement is PROVEN. No Included requirement is NOT-APPLICABLE. No Included requirement is BLOCKED-DEPENDENCY. Formal SOC 2 and a full WAF/CDN program remain explicit non-goals. They are not Included rows.

## Counts

| Class | Rows |
|-------|------|
| PROVEN | 0 |
| IMPLEMENTED-NOT-PROVEN | 4 (R1, R9, R14, R18) |
| PARTIAL | 16 (R2–R8, R10, R12, R13, R15–R17, R19–R21) |
| MISSING | 1 (R11) |
| BLOCKED-DEPENDENCY | 0 |
| NOT-APPLICABLE | 0 |

## Requirement matrix

| ID | Requirement | Class | Current code evidence | Current test evidence | Staging evidence | Production evidence | Sprint 40 engineering still required | Dependency owner | Exact next action |
|----|-------------|-------|------------------------|-----------------------|------------------|---------------------|--------------------------------------|------------------|-------------------|
| R1 | AuthN/AuthZ/object-level review | IMPLEMENTED-NOT-PROVEN | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot repository reads use `get_for_owner`. Non-decision `ShoppingAssistantService.query` continues a conversation only through `_owned_conversation_context` → `get_for_owner`, and loads profiles only through `_authorized_account_user_id`. `AnswerFromEvidenceService`, `RefineSessionRecommendationService`, and `ProposeResearchService` load a body `conversation_id` only with `get_for_owner` when a verified request owner is present. They do not call `ConversationRepository.get` and do not set an owner from `context.owner`. UUID snapshot reads use `get_for_owner` with the verified request owner. A missing owner raises `DecisionSnapshotOwnershipError` with `snapshot access requires a verified owner`. Owner-bound overlays, pending proposals, and research authorizations are loaded only through that same owner match, or through `find_bound_for_owner`. The failed-login lock does not read or authorize a conversation. | `tests/unit/test_sprint40_7_decision_path_owner_binding.py` rejects an ownerless body id, a foreign owner, and stored-owner adoption on answer, refinement, and research proposal. `tests/unit/test_sprint40_assistant_body_identity.py` still rejects a foreign non-decision `conversation_id`, body `user_id`, and unbound `profile_id`. | None on this SHA | None | No new object-level slice. Remaining proof is a staging exercise. | None | Do not treat repository tests as staging proof. Do not reopen Sprint 40.1 or Sprint 40.7. |
| R2 | Session security review | PARTIAL | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. Expiry and revocation are checked in `AuthService.validate_session`. Password reset and email change call `revoke_all_for_user`. Guest `principal_id` and `session_id` are `uuid4`. The owner cookie is HMAC-SHA256, expires in seven days, and is `HttpOnly` plus `SameSite=lax`, with `Secure` in staging and production. There is no server-side guest revocation list. `POST /api/v1/auth/logout` revokes the bearer session and does not clear the owner cookie. `docs/SECURITY_MODEL.md` still describes Sprint 17 demo session limits. The login lock does not add session revocation. | `tests/unit/test_user_platform_security.py`, `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | Sprint 27 and Sprint 29 session notes are historical and were not re-run on this SHA | None. Production secret attach remains Sprint 41 | No new session-crypto slice. Guest revocation and logout cookie clearing stay with R15. | Sprint 41 for production email and session secrets only | Leave Sprint 27 closed. Reconcile `docs/SECURITY_MODEL.md` in a later doc pass. Do not reopen Sprint 27. |
| R3 | Headers/CSP/CORS/CSRF policy completion | PARTIAL | `DEFAULT_SECURITY_CSP` in `app/core/config.py` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` also sets `nosniff`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS on staging and production. `SECURITY_CSP` can still replace the default. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes missing or untrusted `Origin` on `COOKIE_AUTHORIZED_MUTATION_PATHS` when the owner cookie is present, and always on `POST /account/clear-device`. That set includes `POST /api/v1/shopping-assistant/query`. Trusted origins come from `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS`. `SameSite=lax` remains. `CsrfTokenService.validate` is still not called by any route. Preference routes in `PREFERENCE_COOKIE_MUTATION_PATHS` are outside the origin policy. FastAPI `/docs` and `/redoc` stay enabled outside production and are incompatible with the strict CSP. `/openapi.json` remains usable. That incompatibility does not reopen the CSP finding. | `tests/unit/test_sprint40_6_csp.py`, `tests/unit/test_sprint40_4_cookie_origin.py`, `tests/unit/test_sprint22_api.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | None on this SHA. The origin policy and the strict CSP have not been exercised on staging. | None | No for the default CSP or the Sprint 40.4 origin set. Later work can lock `SECURITY_CSP` and cover preference-cookie mutations. Not this slice. | None | Keep the CSP and origin MEDIUMs at IMPLEMENTED-NOT-PROVEN. Do not remove `SameSite=lax`. Do not require interactive docs to satisfy the CSP. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | PARTIAL | `app/security/url_trust.py` separates `validate_server_fetch_url` (https only; numeric private, loopback, link-local, and metadata hosts rejected) from `validate_browser_destination` (http or https; private hosts allowed because the server does not fetch them). Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend `_default_http_post` accepts only the pinned Resend URL and sets `follow_redirects=False`. Live Shopify stays fail-closed (`SHOPIFY_LIVE_CALL_PERMITTED` is false). Browser merchant links are not restricted to a merchant-host allowlist. DNS rebinding is documented as out of scope. `_safe_next` keeps account and consumer redirects on local prefixes. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Request-path SQL found is ORM or constant `SELECT 1`. No current repository evidence proves a reachable SSRF. | `tests/unit/test_sprint40_5_url_trust.py`. No dedicated open-redirect test was found. | None on this SHA | None | No new SSRF slice. A merchant-host allowlist for browser links is a product choice and is not selected. | Sprint 38 and Sprint 41 keep live fetch and production network controls. They do not own this validation gap. | Do not open routing or call Shopify. Do not record a historical SSRF exploit. Staging proof of the server-fetch policy is still absent. |
| R5 | Log redaction; body logging policy; PII handling | PARTIAL | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body or the owner cookie. `app/launch/redaction.py` redacts secret-like keys. Auth audit metadata can still record email on login failure, rate limit, registration, and password reset. The durable-lock audit uses `detail` `login_locked` or `login_lock_unavailable` and metadata `control=failed_login_lock`. It does not store the raw email. The pre-existing short-window audit can still record an email on `detail=login`. Product analytics forbids question, query, answer, message, session id, and conversation id. Account export and deletion remain Sprint 28. | `tests/unit/test_sprint21_analytics_admin.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` `test_server_identity_is_opaque_and_ask_text_is_absent`, durable-lock audit tests in `tests/unit/test_sprint40_failed_login_lock.py` | None on this SHA for a log sample | None | No new redaction slice. R18 covers conversation bodies and session ids in routine logs and analytics. | Sprint 28 owns account export and deletion. Sprint 39 owns product-analytics privacy. | Do not copy audit emails into product analytics. A staging log sample is operational evidence, not this slice. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | Secrets: `scripts/secret_scan_25a.py` runs in `.github/workflows/ci.yml` and scans infra, env examples, scripts, and workflows. It does not scan `app/`. Dependency: `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1 against the frozen `uv.lock` closure. `tests/security/baselines/pip-audit.baseline.json` has an empty exception list. CI #484 reported 71 packages, 0 vulnerabilities, 0 exceptions. SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`. Ruff is a lint gate, not SAST. Container: the CI image job builds and smoke-imports. `build-image.yml` publishes a digest. Neither scans the image. Terraform: `terraform fmt` and `terraform validate` run. That is syntax validation, not IaC security scanning. No tfsec or Checkov config was found. The requirement is the five capability classes, not the product names Dependabot, CodeQL, and Trivy. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #484 is a clean pip-audit and secret-scan run on this SHA. It is not a SAST, container-scan, or IaC-security result. | None | Yes, later, one class at a time. SAST is the smallest missing class if a scanner slice is chosen. Not this slice. | None for adding the gate. Sprint 41 does not own CI scanners. | Do not install SAST, container scanning, and IaC security scanning as one change. Do not weaken the secret scan or pip-audit. |
| R7 | Supply-chain provenance checks; immutable image authority verification | PARTIAL | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, and states that mutable tags are not deployment authority. No cosign, SLSA, or signed provenance attestation was found. | `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum and locks the immutable tag. | Build Image #172 succeeded for this SHA. That shows the publish workflow completed. It is not a signed provenance attestation. | None. Production pull and IAM review remain Sprint 41. | No. Digest publication already exists. Signed provenance is a later decision, not this slice. | Sprint 41 for production image pull | Do not treat Build Image #172 as Sprint 40 closure. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | PARTIAL | Staging and production must use `SqlRateLimitStore` on PostgreSQL. `RATE_LIMIT_BACKEND=memory` is rejected there. Development defaults to the in-process store. There is no silent fallback from PostgreSQL to memory. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified bearer session or account owner cookie. That authenticated-principal bucket is shared in staging and production. A guest session id is not a rate-limit key. Auth failures use a separate `auth` scope keyed by an HMAC of the normalized email, 20 attempts per 60 seconds, also on the shared store in staging and production. The durable login lock is an additional layer and is not a bot challenge or a click-fraud score. Client IP walks `X-Forwarded-For` only when the socket peer is in `TRUSTED_PROXY_CIDRS`. The per-email auth window plus the durable lock is a beta-level control for guessing one account. It is not a bot challenge and not click-fraud detection. Affiliate routes use the affiliate bucket only. Affiliate activation stays off. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_3_trusted_proxy_client_ip.py`, login rate-limit tests in `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_sprint40_failed_login_lock.py` | None on this SHA. Required staging evidence is "Abuse controls exercised". That evidence is absent. | None | No new distributed-counter slice. Bot detection and click-fraud scoring remain absent and are not this slice. The in-process HIGH is IMPLEMENTED-NOT-PROVEN, not closed. The login lock does not promote this row. | Sprint 43 owns cache and capacity depth. Sprint 40 still owns the beta abuse decision. The absence of Redis does not move this row. | Do not mark the HIGH closed. Do not add a WAF, CAPTCHA, or click-fraud score in this audit. |
| R9 | Account lockout or equivalent | IMPLEMENTED-NOT-PROVEN | `AuthService.login` still applies `RateLimiterHook(max_attempts=20, window_seconds=60)` on `opaque_subject_key("login", normalized email)`. Before that window, and before the account lookup, `FailedLoginLock.is_locked` denies the attempt when `locked_until` is in the future. Twenty consecutive failures set `locked_until` from that threshold event for 900 seconds. An unlocked sequence is kept while `last_failure_at` is inside 900 seconds. A stale unlocked sequence, and an expired lock, start again at count 1. An active lock is not extended: the SQL increment keeps an existing future `locked_until_ms`, and a locked attempt returns before `record_failure`. Success calls `clear` and then `reset` on the short-window key. Staging and production use `SqlFailedLoginLockStore` on PostgreSQL. `RATE_LIMIT_BACKEND=memory` stays forbidden there. Store errors raise `FailedLoginLockUnavailable` and the public response is the same rate-limit text. Unknown, inactive, and bad-password failures share `Invalid email or password.` The stored key is `login:<hmac-sha256>`. The table has no email column. Password reset still uses only the expiring auth window. That separate throttle does not issue a session and does not move this row back to PARTIAL. | `tests/unit/test_sprint40_failed_login_lock.py` covers the threshold, the 15-minute lock, retention, stale restart, expired-lock restart, non-extension, success clear, enumeration-safe text, and SQL concurrency. Short-window tests remain in `tests/unit/test_user_platform_auth_service.py`. | None on this SHA. The control has not been exercised on staging. | None | No new lockout slice. Remaining proof is a staging exercise. Repository tests are not that proof. | None | Do not call this row PROVEN. Do not treat CI #484 as an abuse exercise. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings and is called on the cleaned shopper query in `ShoppingAssistantService.query`. A match adds a warning. Deterministic ranking still runs. Merchant text, reviews, and tool results are not passed through that function. `build_shopping_prompts` and `build_community_prompts` put catalog, review, and community text in the user JSON and say in the system string not to follow instructions found in that text. `build_analysis_prompt` puts review text in the user JSON and does not say that. None of the three builders uses a separate untrusted channel. Default transports are `DisabledTransport`. `AI_SHOPPING_ENABLED`, `AI_REVIEW_ENABLED`, and `AI_COMMUNITY_ENABLED` default false. No model-chosen tool loop was found. Shopify catalog tool names in `live_start_claim` are a fixed contract and do not perform HTTP. | `tests/unit/test_shopping_assistant_service.py` `test_prompt_injection_resistance`, `tests/unit/test_shopping_assistant_intent.py` `test_prompt_injection_detection` | None | None | Yes, later, as one bounded isolation or review change. Not this slice. The model path is off, so this is incomplete launch hardening rather than a current model exploit. Three prompt builders must not be rewritten together. | Sprint 13 owns assistant fallback. Sprint 40 owns the review. Sprint 38 owns live research and stays fail-closed. | Leave the six-marker list unchanged in the selected slice. Do not enable a provider to test it. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | MISSING | No pen-test checklist, security incident-response runbook, vulnerability-response process, or security go/no-go draft suitable for Sprint 44 was found. `docs/SECURITY.md` is the Sprint 22 control note. `docs/SECURITY_MODEL.md` is the Sprint 17 model. Sprint 42 operational paging is not this package. The merged login lock does not add these documents. | None | None | None | Yes. This documentation package remains Sprint 40 work. It does not outrank the selected slice. A missing document does not stop a retried public message from applying twice. | Sprint 42 owns operational probes, alerts, paging, and incident operations. Sprint 40 still owns this package and the security go/no-go draft. | Write the package after the selected slice. Do not move it to Sprint 42. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH and the four Sprint 40 MEDIUMs are reconciled in the findings section. No written risk acceptance exists. Sprint 41 and Sprint 42 HIGHs remain open and are not Sprint 40 engineering. The durable login lock does not close the in-process-rate-limit HIGH. Message replay is an Included-requirement gap. This audit does not assign it a new HIGH or MEDIUM. | Tests cited on the individual findings do not close them. Staging proof is absent. | None that exercises abuse controls or the new policies | None | Yes, as a closure gate. Not one code change. | Sprint 41 and Sprint 42 for the HIGHs they own | Do not mark Sprint 40 closed. Do not risk-accept an open finding in this audit. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Decision contexts cannot be stored without an owner. `ConversationContext.__post_init__` raises when `decision_context` is set and `owner` is `None`. Decision reads, overlays, and pending proposals require a verified owner, as recorded on R1. A cookieless `POST /api/v1/shopping-assistant/query` with no `decision_id` still calls `create(owner=None)` and then `append_turn` on that new server id. That is the merged Sprint 40.1 anonymous contract. The endpoint does not call `ensure_guest_owner_cookie`. The stored row has no decision context. `get_for_owner` returns nothing when the stored owner is null, so the same caller cannot continue it and a different caller cannot read it. Repository `append_turn` can still materialize an ownerless row when the id is missing. The three service callers do not pass a client id into that branch: they create first, or they `get_for_owner` first. `live_start_claim` refuses an ownerless conversation. `advance_verified_research_context` requires a matching owner. | `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row`, `test_foreign_conversation_id_cannot_read_or_append_prior_turns`, and the Sprint 40.7 ownerless decision-path negatives. No test shows a public request binding a decision to an ownerless row. | Sprint 29 guest-claim staging notes are historical and were not re-run. | None | No. Closing the literal "every conversation" sentence would change the Sprint 40.1 anonymous contract. That is a product and security decision. It is not the selected slice. | None | Do not select ownerless `create` only because the repository permits `owner=None`. Do not change anonymous create in this audit. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | IMPLEMENTED-NOT-PROVEN | On the non-decision path, body `conversation_id`, `user_id`, and `profile_id` are lookup hints. Authority is the verified owner. History is written only for `_authorized_account_user_id`. A body profile personalizes only when it is already bound to that account. On the decision path, body `conversation_id`, `decision_id`, and `context_version` are lookup values under the verified request owner. Affiliate link decoration can still copy a body `user_id` into affiliate link generation on the non-decision path. Affiliate activation stays off, and that copy does not read or authorize another owner's conversation, profile, decision, or history. It is not an authorization path. | Non-decision negatives in `tests/unit/test_sprint40_assistant_body_identity.py`. Decision-path negatives in `tests/unit/test_sprint40_7_decision_path_owner_binding.py`. | None | None | No new authorization slice. Remaining proof is staging. | None | Do not weaken Sprint 40.1 or Sprint 40.7. Do not treat the affiliate user id copy as an authorization bug. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256. Expiry is seven days and is checked in `parse_owner_cookie`. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie, so it does not rotate. A copied cookie works until expiry because there is no revocation list. UI sign-out calls logout and then `POST /account/clear-device`. Logout itself does not clear the owner cookie. `claim_guest_conversation` rebinds and rotates to the account owner only when no canonical UUID snapshot exists. When one exists, the function returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. The function comment says replacing the cookie would hide the decision. | `tests/unit/test_sprint29_owner_cookie_auth.py`, `tests/unit/test_sprint29_guest_claim.py`, `tests/unit/test_sprint27_4_auth_aware_header.py` | Sprint 29 staging logout and `clear-device` notes were not re-run on this SHA. | None | No, until a product decision. This audit does not change snapshot immutability. | None. Snapshot immutability is already implemented. | Decide whether canonical snapshots stay immutable, or whether guest-to-account transition must rotate credentials and still show the decision. Do not implement either choice here. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement is the Sprint 40.4 control for the decision-owner cookie paths, including `POST /api/v1/shopping-assistant/query` when the owner cookie is present, and for `POST /account/clear-device`. Missing Origin is fail-closed. Bearer-only requests are unchanged. Preference-cookie mutations are not covered. The CSRF token is still not enforced. HTTP rate-limit identity is the trusted client IP, or an account HMAC when the bearer session or account owner cookie is verified. That account key is shared in staging and production. A guest session id is not a rate-limit key. Guest traffic uses the IP bucket. Auth email windows and the durable login lock are separate shared controls. The lock is not a per-session bucket. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests, durable-lock tests. No per-session bucket test exists because that key is absent. | None. Staging has not exercised the origin policy, the shared limiter, or the login lock. | None | Per-session limiting and CSRF-token enforcement are later. Not this slice. The origin MEDIUM stays IMPLEMENTED-NOT-PROVEN. The login lock does not promote this row. | None | Do not treat the shared IP and account buckets as per-session limits. Do not call the origin policy PROVEN. A same-origin retry is not fixed by the origin check. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | PARTIAL | Research confirmation derives `research-auth:<sha256>` from the owner binding, conversation, decision, proposal, and scope. The client confirmation token is ignored as execution identity. A repeated confirmation of the same proposal reuses that key. `prepare_confirmed_research` keys execution off that server authorization. Ordinary message submission has no idempotency field. `ShoppingAssistantQueryRequest` has no submission id. `POST /api/v1/shopping-assistant/query` calls `emit_ask_product_events` after every successful query. Non-decision `append_turn` has no idempotency key. An authorized account records recommendation history again. A repeated research-need question while a proposal is pending mints a new `proposal_id` and increments `proposal_version`. A repeated refinement request appends another refine turn and saves the overlay again. A repeated confirmation still appends a propose-research turn even though the authorization key is reused. `app/static/consumer/js/consumer.js` posts the ask form with no submission id and no in-flight lock. Live research stays fail-closed, so the retry does not spend a provider call. | `tests/unit/test_research_authorization_handoff.py` `test_idempotency_key_is_server_derived` and `test_repeat_confirmation_reuses_same_authorization`. Sprint 38 execution tests cover the research key. No ordinary message-replay test. | None | None | Yes. This is the selected slice. Ordinary message submission only. | Sprint 38 owns research-execution consumption. That server key is already present. | Implement the selected slice. Do not reopen Sprint 38. Do not treat identical question text as the replay identity. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, or a session id. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. Recommendation history stores the query only for `_authorized_account_user_id`. That store is the account's own history, not `product.analytics_events` and not the request log. The Sprint 40.1 body-`user_id` history write is gone. Sprint 40.7 and the login lock do not add conversation text or session ids to those sinks. Ask analytics still omit the question and answer text. | `test_server_identity_is_opaque_and_ask_text_is_absent` and the Sprint 40.1 history tests | None on this SHA for a log or analytics sample | None | No. Remaining proof is a staging sample, not more application code. | Sprint 39 owns the analytics forbid-list. | Do not put conversation text into `product.analytics_events`. Do not call this row PROVEN. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are the same facts as R3 and R4. The six injection markers and the user-prompt embedding are the same facts as R10. Assistant, review, community, answer, refinement, and research processing set `secrets_included` and `prompts_included` false. Shopping and community prompt builders drop keys whose names contain `api_key`, `secret`, `token`, or `prompt`. Review prompts do not use that filter. Provider prompts can include merchant and review text when the corresponding AI flag and transport are enabled. Default transports do not make those calls. `AI_MAX_ESTIMATED_COST_PER_REQUEST` is wired on the review, shopping, and community orchestrators and compares a returned estimate. It is not a live-research budget. Live research remains fail-closed, so confirmation does not spend a provider call today. Fail-closed research is not a cost limit that would hold if live research were opened. No model-driven tool invocation was found. | `test_no_secrets_in_response_processing`, `test_prompt_injection_resistance`, `tests/unit/test_sprint40_6_csp.py` | None | None | No slice that enables live research or a provider. The written review is R10 and is later. | Sprint 38 owns live research execution and stays fail-closed. | Do not enable live research to test cost controls. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | PARTIAL | This matrix is the coverage review. Private decision routes set `noindex`, and `robots.txt` disallows `/results/`, `/compare/`, `/why-best-piq/`, and `/account`. Affiliate click storage exists. Click-fraud detection does not. Tool-abuse controls beyond the injection warning were not found. Credential stuffing has the shared per-email window and the durable login lock. Bot challenge is still absent. Vulnerability response is still the missing R11 package. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py` | No fresh staging crawl was run. | None | No as a separate row. The open parts are the rows above, especially R6, R11, and R17. | Sprint 29 owns the SEO implementation. | Do not reopen Sprint 29. Do not enable affiliate tracking. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same open findings as R12. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | None | Yes, as the same closure gate | Sprint 41 and Sprint 42 for findings they own | Do not start Sprint 45. |

## What moved, and what did not

The durable failed-login lock is confirmed on this tree. R9 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The behavior checked below matches the merged control. Staging has not exercised it, so the row is not PROVEN.

R8 stays PARTIAL. The shared 20/60 auth window and the shared HTTP limiter remain. Bot challenge and click-fraud scoring are still absent. Required staging evidence "Abuse controls exercised" is absent. The lock is not those controls.

R16 stays PARTIAL. The lock is not a per-session rate-limit bucket and does not enforce `CsrfTokenService`. The origin policy already covers the shopping-assistant POST when the owner cookie is present. That policy is IMPLEMENTED-NOT-PROVEN. A same-origin retry is still applied twice.

R1, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. The lock does not change owner binding or log contents. R13 stays PARTIAL. Anonymous `create(owner=None)` remains the Sprint 40.1 contract and does not expose a decision context. R11 stays MISSING. R17 stays PARTIAL and is the selected slice. No row is PROVEN.

## Durable failed-login lock

| Check | Result |
|-------|--------|
| Shared 20-attempt / 60-second auth limiter remains | Yes. `default_auth_rate_limiter` still builds `RateLimiterHook(max_attempts=20, window_seconds=60)`. `login` still calls `check` before the password and `reset` after success. |
| Durable state is an opaque HMAC of the normalized email | Yes. `_abuse_key("login", cleaned_email)` calls `opaque_subject_key`, which returns `login:<hmac-sha256>`. The email is not stored. `require_opaque_login_identity` rejects an email-shaped value. |
| Twenty consecutive failures establish a 15-minute lock from the threshold event | Yes. `FAILED_LOGIN_LOCK_THRESHOLD` is 20. `FAILED_LOGIN_LOCK_DURATION_SECONDS` is 900. The deadline is `now + 900` on the attempt that reaches the threshold. The public error on that attempt stays `Invalid email or password.` The next attempt is denied. |
| Unlocked failed-login history is retained for 15 minutes | Yes. `FAILED_LOGIN_FAILURE_RETENTION_SECONDS` is 900. An unlocked row matches the increment while `last_failure_ms` is after the cutoff. |
| A stale unlocked sequence restarts at one | Yes. The increment requires `last_failure_ms > cutoff`. The stale path replaces the row with `failure_count=1`. |
| Expired locks restart a fresh sequence | Yes. An expired `locked_until_ms` does not match the increment. `_reset_matching` replaces it with count 1. |
| Active locks are not extended by later attempts | Yes. A future `locked_until_ms` is preserved by the SQL `case`. `login` returns before `record_failure` while the lock is active, so the deadline is not rewritten. |
| Success clears durable failure state and resets the short-window limiter | Yes. `_clear_durable_login_failure` runs, then `_rate_limiter.reset`. A durable-store failure denies the login. The short-window `reset` still returns if its own store is unavailable. That difference does not remove the clear. |
| Staging and production use PostgreSQL with no memory fallback | Yes. `resolve_rate_limit_backend` rejects `memory` in those environments. `SqlFailedLoginLockStore` errors raise `FailedLoginLockUnavailable`. The SQL module does not construct the memory store. |
| Unknown, inactive, and bad-password responses stay enumeration-safe | Yes. All three record one failure and raise `UserPlatformAuthError("Invalid email or password.")`. A lock or a store failure raises `UserPlatformRateLimitError("Too many login attempts. Try again later.")` without an account lookup on the lock path. |
| Staging proof | Absent. CI #484 and the unit tests are not a staging abuse exercise. |

R9 therefore stays IMPLEMENTED-NOT-PROVEN. It is not promoted to PROVEN. R8 and R16 are not promoted.

## Authorization and ownerless conversations

Sprint 40.7 is still in force. Answer-from-evidence, session refinement, and research proposal do not adopt `context.owner` from a body `conversation_id`. Owner-bound overlays and pending proposals are not loaded from an unverified body id. Body `conversation_id`, `user_id`, `profile_id`, `decision_id`, and stored conversation ownership are lookup values. They are not authorization authority.

Anonymous `create(owner=None)` and the repository `append_turn` missing-id branch were re-read with their callers.

Public `POST /api/v1/shopping-assistant/query` resolves the owner only from `authorized_owner_from_request`. It does not mint a guest cookie. A request with no owner cookie and no `decision_id` creates an ownerless non-decision conversation and appends the caller's own query to that new id. The response can return the new id. The next request cannot continue that row, because `get_for_owner` treats a null stored owner as a miss.

That row cannot hold a decision context. The entity rejects `decision_context` without an owner. UUID snapshot access without a verified owner fails closed. Overlays and pending proposals are not loaded. `live_start_claim` returns `wrong_owner` when the conversation owner is null. Research advance requires a matching owner.

The `append_turn` missing-id branch still constructs an ownerless row with no decision context. Current service callers do not use it with a client-supplied missing id. Non-decision query creates the row first. Decision paths append only after `get_for_owner` succeeds, or they create with the verified owner.

This is not a reachable public path for creating, continuing, reading, or mutating a sensitive decision context. It is two things at once:

1. A repository compatibility behavior for a missing id, not exercised by the public service callers with a client id.
2. A legitimate anonymous non-decision design from the merged Sprint 40.1 contract. The Included sentence "every conversation" conflicts with that contract.

Changing it requires a product and security decision: keep cookieless non-decision queries ownerless, or mint a guest principal for them. It is not selected. The repository default `owner=None` is not, by itself, a reason to select it.

## R6 capability classes

| Class | Status | Evidence |
|-------|--------|----------|
| Secrets | Present, narrow | `ci.yml` runs `scripts/secret_scan_25a.py`. Scan globs omit `app/`. |
| Dependency | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. CI #484: 71 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Absent | No CodeQL, Bandit, or Semgrep gate over `app/`. |
| Container | Absent | Image build, smoke import, and digest publication do not scan the image. Build Image #172 is not a vulnerability scan. |
| Terraform / IaC security | Absent | `terraform fmt` and `terraform validate` are present. They are not security scanning. |

The smallest missing class, if a later scanner slice is chosen, is SAST. It is not the selected slice. One scanner class must not be bundled with the others.

## Prompt injection, merchant content, and cost

The six-marker warning is detection. It runs on the shopper query only. A match adds `prompt_injection_resistance` and deterministic ranking continues. The markers are `ignore previous`, `ignore all instructions`, `system prompt`, `reveal the prompt`, `api key`, and `override safety`.

Shopper text, merchant catalog text, review text, and community evidence can enter the user prompt when the matching AI flag and transport are enabled. Instructions sit in the system string. The untrusted payload is JSON in the same user message. Shopping and community system strings say not to follow instructions in that text. The review system string does not. That is a role split plus, for two of the three builders, a warning. It is not structural separation.

External responses mark `secrets_included` and `prompts_included` false. `AI_MAX_ESTIMATED_COST_PER_REQUEST` defaults to 0.05 and is passed into the three orchestrators. It was not treated as a live cost proof. Live research and live Shopify stay fail-closed. This audit did not enable a provider. Current exploitability of a model-following injection is therefore absent on the default configuration. The launch-hardening review is still incomplete, so R10 and R19 stay PARTIAL.

Tool names on the Shopify anonymous catalog contract are fixed. They are not chosen by a model from shopper, merchant, or review text, and that contract does not perform HTTP. Provider and research content are not fetched into a prompt while live research is disabled.

## Message idempotency

Research confirmation already derives its execution identity on the server and ignores the client confirmation token. A second confirmation of the same proposal reuses the authorization. Sprint 38 research-execution consumption of that key stays as it is. This audit does not reopen Sprint 38. Live research stays disabled, so a repeated confirmation does not spend a provider call.

A retry of the same ordinary shopping-assistant request can still:

- append another conversation turn on the non-decision path, the answer path, the refinement path, and the proposal path
- write recommendation history again for an authorized account
- emit another `ask_question_submitted` analytics event, and another answered, insufficient-evidence, research, or refinement observation when that status applies
- mint a new `proposal_id` and increment `proposal_version` when a research-need question is submitted again while a proposal is pending
- save the session refinement overlay again and append another refine turn

`ShoppingAssistantQueryRequest` has no submission identity. The public consumer ask form in `app/static/consumer/js/consumer.js` does not send one and does not ignore a second submit while the first request is in flight. The demo page disables its button while a request runs. That client flag is not a server control.

Identical question text is not the replay identity. A shopper may ask the same sentence again on purpose. The defect is a retry of one submission, not a rule that two questions with the same words are one turn.

That gap is R17. It is the selected slice.

## Guest session and canonical rebinding

This is a product-definition conflict, not an implementation bug selected for change.

Sprint 40 acceptance says guest-to-authenticated transition preserves the active decision while rotating ownership credentials.

`claim_guest_conversation` does rotate the cookie when no canonical UUID snapshot exists. When a canonical UUID snapshot exists, it returns `reason=immutable_snapshot_owner`, preserves the guest cookie, and does not rebind. The function comment states that replacing the cookie would hide the decision.

This audit does not change snapshot immutability. A product decision is required before any rebind change: keep canonical snapshot ownership immutable, or rotate credentials while still showing that decision. R15 stays PARTIAL until that decision. It is not the selected slice.

## Documentation package

Still absent, and still owned by Sprint 40:

- Pen-test readiness checklist
- Security incident-response runbook
- Vulnerability-response process
- Security go/no-go draft suitable for Sprint 44

Sprint 42 owns production probes, alerts, paging, and operational incident operations. It does not receive this package by default. The package is entirely missing. It does not outrank ordinary message replay. A document does not stop the public shopping-assistant POST from applying a second time. It remains Sprint 40 work after the selected slice.

## Historical finding reconciliation

These notes are additive. They do not rewrite the Sprint 30 map or section I of the gap inventory. Historical wording is unchanged. The status column is the current reading.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. The durable login lock uses the same PostgreSQL selection and does not close this HIGH. Shared counters do not add bot detection, click-fraud scoring, or a per-session bucket. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. `CsrfTokenService` is still unused on routes. Preference-cookie routes are outside the policy. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. `SECURITY_CSP` can still override the default. FastAPI `/docs` and `/redoc` are incompatible with the strict policy when they are enabled. `/openapi.json` remains usable. That incompatibility does not reopen the finding. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the dependency class. SAST, container scanning, and IaC security scanning STILL OPEN | pip-audit 2.10.1 is a required CI gate. CI #484 reported 71 packages, 0 vulnerabilities, and 0 exceptions. The historical sentence is no longer a total absence. Dependabot, CodeQL, and Trivy remain absent. Their absence is not, by itself, the Sprint 40 requirement. Secrets scanning remains present. `terraform validate` remains syntax validation. A successful Docker build is not container vulnerability scanning. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. This audit does not claim a historical reachable SSRF. Staging has not exercised the policy. Browser links are not a merchant-host allowlist. The finding is not closed and not PROVEN. |

No new HIGH is assigned. No MEDIUM is relabeled launch-blocking. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## Duplicated requirements

- R12 and R21 are the same closure gate. R21 adds the Sprint 45 deadline.
- R3 and R16 both include the origin policy. R16 also requires per-session, per-IP, and authenticated-principal limits. Per-IP and account limits exist and are shared in staging and production. Per-session limits do not. The login lock does not fill that gap.
- R4 and R19 both include encoding and XSS. R19 adds external-model minimization and cost.
- R5 and R18 both include logs. R18 is the conversation-body and session-id sentence, and it stays IMPLEMENTED-NOT-PROVEN.
- R1 and R14 share the implemented owner-binding rule. R13 still includes the anonymous non-decision contract.
- R8 and R9 are not the same control. R9 is the temporary login lock and is IMPLEMENTED-NOT-PROVEN. R8 still includes bot challenge and click-fraud detection, which are absent.
- R10 and the prompt-injection clauses of R19 and R20 are one review. That review is not written, and the six markers are not isolation.
- R17's research-confirmation half is implemented. Its ordinary message-submission half is the selected slice.

## Sprint 41 work, not this slice

- Production VPC, database, secrets, IAM, OIDC, deploy, rollback, DNS, and TLS.
- Production IAM review.
- Production image pull. Build Image #172 does not start that review.
- The HIGHs for production isolation and production OIDC/SSM.

Sprint 41 stays UNSTARTED. This audit does not start it.

## Sprint 42 work, not this slice

- CloudWatch and security paging.
- Operational incident response, probes, alerts, and paging runbooks.

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R11 is missing. R6, R8, R10, R13, R16, and R17 still have repository-backed gaps. R15 still needs a product decision. R9 is implemented and is not staging-proven. Staging proof is absent even for the controls that are implemented. Those facts are not all proof that belongs to staging, Sprint 41, Sprint 42, or Sprint 44.

The guest-rebind acceptance conflict is not selected. It still needs a product decision. Anonymous `create(owner=None)` is not selected. It does not expose a decision context, and changing it conflicts with the merged Sprint 40.1 contract. The login lock is not selected again. It is already merged.

**Slice:** Ordinary shopping-assistant message submission must not apply twice when the same client request is retried.

Current defect, from repository code:

- `ShoppingAssistantQueryRequest` has no submission identity. `confirmation_token` is not that identity.
- `app/api/v1/endpoints/shopping_assistant.py` calls `emit_ask_product_events` after every successful `POST /api/v1/shopping-assistant/query`.
- `ShoppingAssistantService.query` calls `append_turn` and, for an authorized account, `_record_user_platform_history` on every non-decision query.
- `AnswerFromEvidenceService` appends a bound turn on every answer.
- `RefineSessionRecommendationService._persist_overlay` saves the overlay and appends a refine turn on every refinement.
- `compose_research_proposal` mints a new `proposal_id` and increments `proposal_version` when a research-need question arrives while a proposal is pending.
- `ProposeResearchService._persist_proposal` appends a turn on confirm and reconfirm as well. The research authorization key is still reused. That reuse stays.
- `app/static/consumer/js/consumer.js` submits the ask form without a submission id and without an in-flight guard.

**Likely files for the later slice:**

- `app/schemas/shopping_assistant.py`
- `app/api/v1/endpoints/shopping_assistant.py`
- `app/analytics/ask_events.py`
- `app/services/shopping_assistant_service.py`
- `app/services/answer_from_evidence.py`
- `app/services/refine_session_recommendation.py`
- `app/services/propose_research.py`, for message effects only
- `app/static/consumer/js/consumer.js`
- new unit tests for one retried submission

**Acceptance tests for the later slice:**

1. One shopping-assistant submission, retried with the same submission identity, appends one conversation turn.
2. That retry does not write recommendation history a second time for an authorized account.
3. That retry emits one `ask_question_submitted` event, and does not emit a second answered, insufficient-evidence, research, or refinement observation for the same submission.
4. That retry does not mint a second `proposal_id` or increment `proposal_version`, and does not write a second refinement transition.
5. A later submission with a different identity still applies, including when the question text matches the first submission. Identical text is not the replay identity.
6. The submission identity is not authorization. It cannot select another owner's conversation, profile, decision, or history.
7. Research confirmation keeps its server-derived `research-auth:` key. Sprint 38 is not reopened. Live research stays disabled. Canonical snapshot immutability stays unchanged. The failed-login lock stays as merged.

**Out of scope for the slice:** SAST, container scanning, IaC security scanning, bot challenge, CAPTCHA, WAF, click-fraud detection, prompt isolation, the pen-test package, guest rebind, anonymous ownerless create, CSP, origin policy, CSRF-token enforcement, per-session rate limits, another login-lock change, affiliate activation, Shopify calls, routing, and any deploy.

## Why this slice outranks the other gaps

The public shopping-assistant POST is on. A retry of one client submission appends another turn, can write the account's recommendation history again, emits another ask analytics event, and can replace a pending research proposal or record another refinement. The consumer ask form will send that second request. Research confirmation already refuses a second authorization for the same proposal, and live research does not run, so this slice does not reopen Sprint 38. It closes the ordinary message half of R17.

R11 is still missing and stays Sprint 40 work. It does not outrank this slice. A pen-test checklist, an incident-response runbook, a vulnerability-response process, and a Sprint 44 go/no-go draft do not stop the POST from applying twice. Sprint 42 paging does not remove the package, and it also does not fix the retry.

SAST is the smallest missing scanner class and is the right choice if the next slice is a scanner. It does not stop this POST. Container scanning and IaC security scanning are separate absences and are not bundled with it. A successful image build and `terraform validate` do not fill them. pip-audit already covers dependency scanning.

Prompt isolation is real and incomplete. Shopping, review, and community builders put untrusted text in the user JSON. The model path is off by default, transports are disabled, and live research is fail-closed, so a model is not currently following that text. Covering the three builders is not one bounded change, and it is launch hardening rather than a current exploit.

Bot challenge and click-fraud detection keep R8 PARTIAL. This repository does not show that a WAF or CAPTCHA is required. Full WAF/CDN remains a non-goal. Affiliate activation stays off, so click fraud has no payout to close here. The durable login lock already limits password guessing after the 60-second window. R8 and R16 stay PARTIAL for the controls the lock does not provide. The origin check already covers this POST when the owner cookie is present, and it still allows a same-origin retry.

The ownerless conversation path cannot carry a decision. Selecting it would decide the Sprint 40.1 anonymous contract. Guest-to-account rebind of a canonical snapshot is the same kind of undecided conflict. R9 is implemented and is waiting on staging, which is not an engineering slice.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No reachable public path that creates, continues, reads, or mutates a sensitive decision context through an ownerless conversation.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No pen-test report or written risk acceptance.
- No Sprint 38 defect in research-confirmation idempotency. The authorization key is still server-derived.
