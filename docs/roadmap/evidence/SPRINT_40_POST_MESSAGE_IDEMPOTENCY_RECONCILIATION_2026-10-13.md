# Sprint 40 post-message-idempotency reconciliation — 2026-10-13

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Write the Sprint 40 security-readiness package: a penetration-test readiness checklist, a security incident-response runbook, a vulnerability-response process, and a Sprint 44 security go/no-go draft.

This slice is not named Sprint 40.8. A later implementation may take a number. This audit only selects the work.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.7 are merged. The durable failed-login lock is merged. Shopping-assistant submission idempotency is merged. This change is a reconciliation audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `32b5a0292195588625e8e515badd5e176cbeb6e8`

**Post-merge evidence on that SHA:** CI #491 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38402419948`). Full pytest on that run: 4471 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #174 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38403333813`). Those runs are publication and test evidence for the merged tree. They are not a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical inputs, not copied forward:** [`SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md`](SPRINT_40_POST_FAILED_LOGIN_LOCK_RECONCILIATION_2026-10-13.md) and [`SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md`](SPRINT_40_MESSAGE_SUBMISSION_IDEMPOTENCY_2026-10-13.md). Those files keep the classes they recorded. This reconciliation re-reads the tree at `32b5a0292195588625e8e515badd5e176cbeb6e8` and classifies R1–R21 again. The 2026-10-09 readiness audit stays historical.

**Gap inventory:** section I and the Sprint 30 security-finding map in [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md) are not rewritten. Additive notes below say which historical findings are still true.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate activation stays off. No provider or public-market activation was changed. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. This audit does not reopen Sprint 38 or Sprint 39 engineering.

## How a row becomes PROVEN

Code on `main` is not enough. A row is PROVEN only when the current tree shows the control, a test fails closed for the abuse case, and the Sprint 40 acceptance bar for that control is met. A fresh staging or production run is recorded when it exists. Absence of that run keeps a complete, tested control at IMPLEMENTED-NOT-PROVEN. A control that is only partly present stays PARTIAL even when some of its tests pass. A requirement that is itself a written review is IMPLEMENTED-NOT-PROVEN when this reconciliation covers the named topics and Sprint 44 has not accepted the package.

This reconciliation did not execute the application on staging or production. Repository tests cited below were re-read. They are not staging proof.

No Included requirement is PROVEN. No Included requirement is NOT-APPLICABLE. No Included requirement is BLOCKED-DEPENDENCY. Formal SOC 2 and a full WAF/CDN program remain explicit non-goals. They are not Included rows.

## Counts

| Class | Rows |
|-------|------|
| PROVEN | 0 |
| IMPLEMENTED-NOT-PROVEN | 9 (R1, R3, R5, R7, R9, R14, R17, R18, R20) |
| PARTIAL | 11 (R2, R4, R6, R8, R10, R12, R13, R15, R16, R19, R21) |
| MISSING | 1 (R11) |
| BLOCKED-DEPENDENCY | 0 |
| NOT-APPLICABLE | 0 |

## Requirement matrix

| ID | Requirement | Class | Current code evidence | Current test evidence | Staging evidence | Production evidence | Sprint 40 engineering still required | Dependency owner | Exact next action |
|----|-------------|-------|------------------------|-----------------------|------------------|---------------------|--------------------------------------|------------------|-------------------|
| R1 | AuthN/AuthZ/object-level review | IMPLEMENTED-NOT-PROVEN | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot reads use `get_for_owner`. Non-decision `ShoppingAssistantService.query` continues a conversation only through `_owned_conversation_context` and loads an account only through `_authorized_account_user_id`. Answer, refinement, and research proposal load a body `conversation_id` only with `get_for_owner`. They do not call `ConversationRepository.get` and do not adopt `context.owner`. A missing snapshot owner raises `DecisionSnapshotOwnershipError`. The submission ledger scopes replay with `submission_authority_scope` and does not authorize a conversation from the key or from body `user_id`. | `tests/unit/test_sprint40_7_decision_path_owner_binding.py`, `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_shopping_submission_idempotency.py` | None on this SHA | None | No new object-level slice. Remaining proof is a staging exercise. | None | Do not treat repository tests as staging proof. Do not reopen Sprint 40.1 or Sprint 40.7. |
| R2 | Session security review | PARTIAL | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. `validate_session` rejects a missing, revoked, or expired session and revokes an expired one. Default bearer TTL is 3600 seconds. Remember-me uses 2592000 seconds and the consumer stores that bearer in `localStorage`. Password reset and email change call `revoke_all_for_user`. Guest `principal_id` and `session_id` are `uuid4`. The owner cookie is HMAC-SHA256, lasts seven days, and is `HttpOnly` plus `SameSite=lax`, with `Secure` in staging and production. `parse_owner_cookie` checks the MAC and expiry. There is no server-side guest revocation list, so a copied cookie works until expiry. `POST /api/v1/auth/logout` revokes the bearer and does not clear the owner cookie. Public account sign-out then calls `POST /account/clear-device`, which deletes the cookie. The internal demo logout does not. `ensure_guest_owner_cookie` reuses a valid cookie. That is continuation of a server-minted cookie, not a client-chosen session id. These residuals are separate from the canonical-snapshot rebind conflict on R15. | `tests/unit/test_user_platform_security.py`, `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | Sprint 27 and Sprint 29 session notes were not re-run on this SHA | None. Production secret attach remains Sprint 41 | Guest revocation and making API logout clear the owner cookie are residual session work. They are not the selected slice. The public sign-out path already clears the device. | Sprint 41 for production email and session secrets only | Do not treat the snapshot-rebind conflict as this session defect. Do not reopen Sprint 27. |
| R3 | Headers/CSP/CORS/CSRF policy completion | IMPLEMENTED-NOT-PROVEN | `DEFAULT_SECURITY_CSP` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` also sets `nosniff`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS on staging and production. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes a missing or untrusted `Origin` on unsafe decision-owner-cookie requests, including `POST /api/v1/shopping-assistant/query` when the owner cookie is present, and always on `POST /account/clear-device`. Trusted origins come from `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS`. SameSite=Lax remains and is not the control. `CsrfTokenService.validate` is still not called by any route. Tokens are issued onto the bearer session and are not a second required control for the covered cookie mutations. Origin enforcement is the beta control for that covered set. Preference-cookie writers stay outside that set. They are not decision-owner authorization. FastAPI `/docs` and `/redoc` stay incompatible with the strict CSP outside production. `/openapi.json` remains usable. | `tests/unit/test_sprint40_6_csp.py`, `tests/unit/test_sprint40_4_cookie_origin.py` | None on this SHA | None | No new header or CSRF-token slice. Remaining proof is a staging exercise of the default CSP and the origin policy. | None | Do not add CSRF tokens on top of the origin policy for the covered routes. Do not call the row PROVEN. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | PARTIAL | `validate_server_fetch_url` accepts https only and rejects numeric private, loopback, link-local, and metadata hosts. `validate_browser_destination` accepts http or https and allows private hosts because the server does not fetch them. Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend posts only to the pinned URL with `follow_redirects=False`. Live Shopify stays fail-closed. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Request-path SQL found is ORM or a constant `SELECT 1` probe. Account and consumer redirects use `_safe_next` local prefixes. Browser merchant links are checked as browser destinations and are not restricted to a merchant-host allowlist. DNS rebinding stays out of scope. The SSRF half is implemented. The allowlist half is the remaining implementation gap and needs a product host list. | `tests/unit/test_sprint40_5_url_trust.py` | None on this SHA | None | No new SSRF slice. The merchant-host allowlist is not selected. | Sprint 38 and Sprint 41 keep live fetch and production network controls | Do not reopen SSRF because staging proof is absent. Do not record a reachable SSRF. |
| R5 | Log redaction; body logging policy; PII handling | IMPLEMENTED-NOT-PROVEN | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body, the owner cookie, a session id, or a bearer token. `redact_value` redacts secret-like keys before structured logs. Product analytics reject question, query, answer, message, email, session id, and conversation id. Security-audit `AuditLogger` records can still store the account email on registration rate-limit, login rate-limit, login failure, and password-reset events. That store is `SecurityEvent` metadata, not the request log and not `product.analytics_events`. The durable-lock audit uses `detail` `login_locked` or `login_lock_unavailable` and does not store the raw email. Sprint 40 asks for body omission, redaction, and PII handling, and R18 names conversation bodies and session identifiers. It does not prohibit an account email inside the security-audit record of an authentication event. That email is intentional audit identity, not an unresolved Sprint 40 violation. | `tests/unit/test_sprint39_1_consent_analytics_feedback.py` `test_server_identity_is_opaque_and_ask_text_is_absent`, durable-lock audit tests | None on this SHA for a log sample | None | No new redaction slice. Remaining proof is a staging log sample. | Sprint 28 owns account export and deletion. Sprint 39 owns product-analytics privacy | Do not copy audit emails into product analytics. Do not strip security-audit identity in the selected slice. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | Secrets: `scripts/secret_scan_25a.py` runs in CI and scans infra, env examples, scripts, and workflows. It does not scan `app/`. Dependency: `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1 against the frozen `uv.lock` closure with an empty exception list. CI #491 reported 71 packages, 0 vulnerabilities, 0 exceptions. SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`. Ruff is a lint gate, not SAST. Container: the CI image job builds and smoke-imports. `build-image.yml` publishes a digest. Neither scans the image for vulnerabilities. Terraform: `terraform fmt` and `terraform validate` run. That is syntax validation, not IaC security scanning. No tfsec or Checkov config was found. The three missing classes are separate. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #491 is a clean secret scan and pip-audit run. It is not a SAST, container-scan, or IaC-security result | None | Yes, later, one class at a time. Not this slice. | None for adding a gate. Sprint 41 does not own CI scanners | Do not install SAST, container scanning, and IaC security scanning as one change. |
| R7 | Supply-chain provenance checks; immutable image authority verification | IMPLEMENTED-NOT-PROVEN | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, writes a release manifest, and states that the digest is deployment authority. Deploy and rollback workflows reject mutable-tag authority and pull by digest. `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum. The gap inventory already records GHCR digest authority as `implemented_verified` under Sprint 25b.1 / 40. No cosign, SLSA, or signed attestation was found. Sprint 41 owns production image pull, digest promotion, and IAM. Its included requirements do not name image signing. Sprint 44 and Sprint 45 require the immutable image digest on the launch record (EC-22). They do not name a signature. Signed provenance is not a Sprint 40 engineering blocker. It is later release-control work that no current sprint owns as an implementation gate. | `tests/unit/test_sprint25b1_image_publication.py` | Build Image #174 succeeded for this SHA. That is publication. It is not a production pull and not a signed attestation | None. Production pull remains Sprint 41 | No. The immutable tag, digest, and manifest checks are present. Signed provenance is outside this sprint's closure bar. | Sprint 41 for production image pull | Do not treat Build Image #174 as Sprint 40 closure. Do not add cosign in the selected slice. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | PARTIAL | Staging and production must use `SqlRateLimitStore`. `RATE_LIMIT_BACKEND=memory` is rejected there. There is no silent fallback to memory. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified bearer session or account owner cookie. Auth failures use a separate shared `auth` scope keyed by an HMAC of the normalized email, 20 attempts per 60 seconds. The durable login lock adds a 20-failure, 15-minute hold on that same opaque identity. No CAPTCHA, bot challenge, or click-fraud score was found. Affiliate routes use the affiliate bucket only. Affiliate activation stays off, so there is no click payout to score. Full WAF/CDN remains a non-goal. Credential stuffing has a beta control. Bot challenge and click-fraud scoring do not, and the sprint's "appropriate to beta" clause does not require them while affiliate activation stays off and the shared limiter plus the login lock are in place. Required staging evidence "Abuse controls exercised" is absent, which keeps the row from being PROVEN even for the controls that exist. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_failed_login_lock.py` | None on this SHA | None | No bot-challenge or click-fraud slice. The in-process HIGH stays IMPLEMENTED-NOT-PROVEN. | Sprint 43 owns cache and capacity depth. Sprint 40 still owns the beta abuse decision | Do not add a WAF, CAPTCHA, or click-fraud score in this audit. Do not invent a requirement the contract does not set. |
| R9 | Account lockout or equivalent | IMPLEMENTED-NOT-PROVEN | `AuthService.login` still applies the 20-attempt / 60-second limiter, then `FailedLoginLock`. Twenty consecutive failures set `locked_until` from that threshold event for 900 seconds. Unlocked history is kept for 900 seconds. A stale unlocked sequence and an expired lock restart at 1. An active lock is not extended. Success calls `clear` and then `reset`. Staging and production use `SqlFailedLoginLockStore`. Memory is forbidden there. Store errors raise `FailedLoginLockUnavailable` and the public text matches the rate-limit error. Unknown, inactive, and bad-password failures share `Invalid email or password.` The stored key is `login:<hmac-sha256>`. Password reset stays on the short window only. That separate throttle does not issue a session. | `tests/unit/test_sprint40_failed_login_lock.py`, `tests/unit/test_user_platform_auth_service.py` | None on this SHA | None | No new lockout slice. Remaining proof is a staging exercise. | None | Do not call this row PROVEN. Do not treat CI #491 as an abuse exercise. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings and runs on the cleaned shopper query. A match adds a warning. Deterministic ranking still runs. Merchant text, reviews, community text, and tool results are not passed through that function. `build_shopping_prompts` and `build_community_prompts` put catalog, review, and community text in the user JSON and say in the system string not to follow instructions in that text. `build_analysis_prompt` puts review text in the user JSON and does not say that. None of the builders uses a separate untrusted channel. Default transports are `DisabledTransport`. `AI_SHOPPING_ENABLED`, `AI_REVIEW_ENABLED`, and `AI_COMMUNITY_ENABLED` default false. No model-chosen tool loop was found. Shopify catalog tool names in `live_start_claim` are a fixed contract and do not perform HTTP while `SHOPIFY_LIVE_CALL_PERMITTED` is false. Public-web research content is not fetched into a prompt on the default path. | `tests/unit/test_shopping_assistant_service.py` `test_prompt_injection_resistance`, `tests/unit/test_shopping_assistant_intent.py` `test_prompt_injection_detection` | None | None | Yes, later, as launch hardening before an AI flag or live research is enabled. Not this slice. The model path is off, so this is not a current public-beta model exploit. | Sprint 13 owns assistant fallback. Sprint 38 owns live research and stays fail-closed | Do not enable a provider to test isolation. Do not rewrite all three builders in one change. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | MISSING | No pen-test checklist, security incident-response runbook, vulnerability-response process, or security go/no-go draft suitable for Sprint 44 was found. `docs/SECURITY.md` is the Sprint 22 control note. `docs/SECURITY_MODEL.md` is the Sprint 17 model. Sprint 42 operational paging is not this package. The merged login lock and the submission ledger do not add these documents. | None | None | None | Yes. This documentation package is the selected slice. | Sprint 42 owns operational probes, alerts, paging, and incident operations. Sprint 40 still owns this package and the security go/no-go draft. Sprint 44 consumes the draft. | Write only that package. Do not move it to Sprint 42. Do not mix a scanner or a runtime change into it. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH and the four Sprint 40 MEDIUMs are reconciled below. Each implemented control is IMPLEMENTED-NOT-PROVEN or CLOSED BY IMPLEMENTATION for the dependency class. None is closed by staging proof. No written risk acceptance exists. Sprint 41 and Sprint 42 HIGHs remain open and are not Sprint 40 engineering. This audit does not assign a new HIGH or MEDIUM. | Tests cited on the findings do not close them. Staging proof is absent | None that exercises abuse controls or the new policies | None | Yes, as a closure gate. Not one code change | Sprint 41 and Sprint 42 for the HIGHs they own | Do not mark Sprint 40 closed. Do not risk-accept an open finding in this audit. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Decision contexts cannot be stored without an owner. `ConversationContext.__post_init__` raises when `decision_context` is set and `owner` is `None`. Decision reads require a verified owner. A cookieless `POST /api/v1/shopping-assistant/query` with no `decision_id` still calls `create(owner=verified_owner)`, and `verified_owner` is `None` when the request has no owner. The stored row has no decision context. `get_for_owner` returns nothing for a null stored owner. `live_start_claim` refuses an ownerless conversation. The endpoint does not mint a guest cookie. This is the merged Sprint 40.1 anonymous contract. It is not a reachable path for a sensitive decision context. Closing the literal "every conversation" sentence would change that contract. | `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row` and the Sprint 40.7 ownerless decision-path negatives | Sprint 29 guest-claim notes were not re-run | None | No. Changing anonymous create is a product and security decision. It is not the selected slice. | None | Do not select ownerless `create` only because the repository permits `owner=None`. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | IMPLEMENTED-NOT-PROVEN | Body `conversation_id`, `user_id`, `profile_id`, `decision_id`, and `context_version` are lookup values. Authority is the verified owner. The submission fingerprint includes normalized body `user_id` and `profile_id` so a changed body conflicts. `submission_authority_scope` does not read those fields. Affiliate link decoration can still copy a body `user_id` into link generation. Affiliate activation stays off, and that copy does not read another owner's conversation, profile, decision, or history. | `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_sprint40_7_decision_path_owner_binding.py`, `test_fingerprint_includes_body_identity_without_making_it_the_scope` | None | None | No new authorization slice. Remaining proof is staging. | None | Do not treat the fingerprint fields as authorization. Do not treat the affiliate user id copy as an authorization bug. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256 with a seven-day expiry. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie. Public sign-out revokes the bearer and then clears the owner cookie. `claim_guest_conversation` rebinds and rotates to the account owner only when no canonical UUID snapshot exists. When one exists, it returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. The function comment says replacing the cookie would hide the decision. Sprint 40 acceptance says the transition preserves the active decision while rotating ownership credentials. Snapshot immutability says the opposite for a canonical UUID snapshot. That conflict is a product definition. It is not an implementation bug selected for change. | `tests/unit/test_sprint29_guest_claim.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | Sprint 29 staging logout notes were not re-run | None | No, until a product decision. This audit does not change snapshot immutability. | None. Snapshot immutability is already implemented | Decide whether canonical snapshots stay immutable, or whether guest-to-account transition must rotate credentials and still show the decision. Do not implement either choice here. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement is the beta control for decision-owner-cookie mutations, including the shopping-assistant POST when the owner cookie is present, and for `POST /account/clear-device`. A cookieless Idempotency-Key POST is not an owner-cookie mutation, so the origin policy does not apply, and the ledger still requires a valid key. Bearer-only requests stay unchanged. CSRF-token non-enforcement is not an independent gap for that covered set. HTTP rate-limit identity is the trusted client IP, or an account HMAC when a bearer session or account owner cookie is verified. A guest session id is not a rate-limit key. Guest and anonymous traffic share the IP bucket. The included sentence also names a per-session bucket. That bucket is still absent. One guest cookie reused from many addresses is not limited as a session. That is why this row stays PARTIAL. The IP bucket already caps one address, and the account bucket covers a verified account. A new cookie per request is not what a per-session key stops. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests. No per-session bucket test exists because that key is absent | None | None | Per-session limiting remains named and unimplemented. It is not the selected slice. The origin policy stays IMPLEMENTED-NOT-PROVEN as a finding, and it does not by itself complete this row. | None | Do not add CSRF tokens to satisfy this row. Do not treat the IP bucket as a per-session limit. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | IMPLEMENTED-NOT-PROVEN | `POST /api/v1/shopping-assistant/query` requires `Idempotency-Key`. A missing or malformed key is HTTP 400 and does not claim a row. The public consumer creates one `crypto.randomUUID()` key before the first fetch, reuses it for a network failure, HTTP 503, HTTP 429, or HTTP 409 `Request already in progress.`, and creates a new key after a terminal response, including when the question text is unchanged. The same scoped key and canonical fingerprint replay the stored response. Replay does not call `service.query` and does not call `emit_ask_product_events`. A changed mutation-relevant payload, including body `user_id` or `profile_id`, is HTTP 409. Those fields are in the fingerprint and are not read by `submission_authority_scope`. Scope is the verified account, the verified guest, or an HMAC of the trusted client host for anonymous Ask. Concurrent SQL inserts have one primary-key winner. Staging and production use `SqlShoppingSubmissionStore`. `RATE_LIMIT_BACKEND=memory` is rejected there. Store errors are HTTP 503 and do not execute the query. An in-progress duplicate does not execute. A processing row is sealed indeterminate after 15 minutes and is not re-executed. Completed and indeterminate rows expire after 24 hours. Research confirmation still derives `research-auth:<sha256>` and ignores the client confirmation token. The internal demo fetch omits the header and therefore cannot execute. That is fail-closed, not a second apply. | `tests/unit/test_shopping_submission_idempotency.py`, `tests/unit/test_research_authorization_handoff.py` `test_idempotency_key_is_server_derived` | None on this SHA. The ledger has not been exercised on staging | None | No new message-idempotency slice. Remaining proof is a staging exercise. | Sprint 38 owns research-execution consumption of the server key. That key is unchanged | Do not call this row PROVEN. Do not reopen Sprint 38. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, a session id, or a bearer credential. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. The submission ledger stores the public response so a replay can be returned without calling `service.query`. That store is not the request log and not product analytics. The raw key is stored only as SHA-256. Ask analytics still omit the question and answer text, and a replay does not emit them again. | `test_server_identity_is_opaque_and_ask_text_is_absent`, `test_http_replay_skips_query_analytics_and_a_second_turn` | None on this SHA for a log or analytics sample | None | No. Remaining proof is a staging sample. | Sprint 39 owns the analytics forbid-list | Do not put conversation text into `product.analytics_events`. Do not call this row PROVEN. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are the same facts as R3 and R4. The six markers and the user-prompt embedding are the same facts as R10. Assistant, review, community, answer, refinement, and research processing set `secrets_included` and `prompts_included` false. Shopping and community prompt builders drop keys whose names contain `api_key`, `secret`, `token`, or `prompt`. Review prompts do not use that filter. `AI_MAX_ESTIMATED_COST_PER_REQUEST` is wired on the review, shopping, and community orchestrators and compares a returned estimate. It is not a live-research budget. Live research remains fail-closed. Current public-beta model risk is absent. Launch hardening before enabling AI or live research is still incomplete. | `test_no_secrets_in_response_processing`, `test_prompt_injection_resistance`, `tests/unit/test_sprint40_6_csp.py` | None | None | No slice that enables live research or a provider. The written review is R10 and is later. | Sprint 38 owns live research execution and stays fail-closed | Do not enable live research to test cost controls. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | IMPLEMENTED-NOT-PROVEN | This matrix is the coverage review. Each named topic is classified on its own row: identity and owner binding on R1, R13, and R14; SSRF and link safety on R4; CSP and headers on R3; secrets on R6; rate limiting on R8 and R16; credential stuffing on R8 and R9; bot abuse and click fraud on R8; prompt injection and tool abuse on R10 and R19; PII and redaction on R5 and R18; vulnerability response on R11; private SEO and session isolation on R2, R15, and the `noindex` / `robots.txt` rules. Open findings do not keep this row PARTIAL. The review exists. Sprint 44 has not accepted it, so it is not PROVEN. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py`, and the tests cited on the rows above | No fresh staging crawl was run | None | No as a separate implementation slice. The missing process document is R11. | Sprint 29 owns the SEO implementation | Do not reopen Sprint 29. Do not enable affiliate tracking. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same open findings as R12. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | None | Yes, as the same closure gate | Sprint 41 and Sprint 42 for findings they own | Do not start Sprint 45. |

## What moved, and what did not

R17 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The merged ledger matches the engineering requirement checked below. Staging has not exercised it, so the row is not PROVEN.

R3 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. Origin enforcement is the documented beta control for the covered cookie-authorized mutations. CSRF-token non-enforcement is not a second required control for that set. Staging proof is still absent.

R5 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. Routine logs omit bodies and session identifiers. Security-audit email is intentional authentication identity, not a Sprint 40 redaction violation.

R7 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. Immutable tag, digest, and release-manifest checks exist. Signed provenance is not a Sprint 40 engineering blocker.

R20 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The coverage review is this matrix. Open findings on other rows do not keep the review itself partial.

R1, R9, R14, and R18 stay IMPLEMENTED-NOT-PROVEN. R2, R4, R6, R8, R10, R12, R13, R15, R16, R19, and R21 stay PARTIAL. R11 stays MISSING and is the selected slice. No row is PROVEN.

## R17 message idempotency

| Check | Result |
|-------|--------|
| `POST /api/v1/shopping-assistant/query` requires a valid `Idempotency-Key` | Yes. `parse_submission_key` rejects a missing or malformed header before a claim. The server does not invent a key. |
| One logical browser submit gets one fresh key | Yes. `newSubmissionKey` uses `crypto.randomUUID`, or `crypto.getRandomValues` when that function is absent. The key is not derived from the question, `decision_id`, `conversation_id`, `proposal_id`, a timestamp, or `user_id`. |
| Browser retries reuse the same key | Yes. `postAskSubmission` retries a network failure, HTTP 503, HTTP 429, and HTTP 409 `Request already in progress.` with the same key. The submit control is disabled while one request is active. That disablement is not the control. |
| Intentional later submits get a new key | Yes. A terminal success, payload conflict, indeterminate outcome, or other terminal HTTP error clears `pendingAskSubmission`. The next submit, including identical question text, calls `newSubmissionKey`. |
| Same scoped key and same canonical payload replay the stored response | Yes. `apply_shopping_submission` returns `replay` and does not call `execute`. |
| Replay does not call `service.query` | Yes. `execute` is the only caller of `service.query`, and replay does not enter it. |
| Replay does not call `emit_ask_product_events` | Yes. The endpoint emits only when `applied.fresh` is true. |
| Same key and a changed mutation-relevant payload return conflict | Yes. HTTP 409 `Idempotency-Key does not match the original request.` |
| `user_id` and `profile_id` are in the fingerprint and do not choose replay authority | Yes. `request_fingerprint` includes the normalized values. `submission_authority_scope` does not read them. A changed value conflicts. A blank value matches an omitted value. |
| Replay scope derives only from verified server authority | Yes for an account (`ask-acct`) and a guest (`ask-guest`). Anonymous Ask, which the merged contract still allows, uses `ask-anon` over the trusted client host. The host is server-derived. Body identity is not the scope. |
| Concurrent workers have one atomic SQL winner | Yes. The primary key is `(scope, key_hash)`. The first insert wins. A conflicting insert loads the committed row and does not execute. |
| Staging and production use the durable SQL store | Yes. Unset backend means PostgreSQL. `RATE_LIMIT_BACKEND=memory` raises `RateLimitConfigurationError`. |
| No silent memory fallback there | Yes. SQL errors raise `ShoppingSubmissionUnavailable`. The handler returns HTTP 503 and does not call `service.query` when the claim cannot be evaluated. |
| In-progress duplicates do not execute | Yes. The loser receives HTTP 409 `Request already in progress.` |
| Processing claims are not unsafe leases | Yes. Cleanup does not delete a `processing` row. The 15-minute horizon does not authorize a second execution. |
| A stale processing claim becomes indeterminate | Yes. `seal_stale_processing` sets `indeterminate` and does not call `execute`. |
| Completed and indeterminate rows use the 24-hour engineering retention | Yes. `SUBMISSION_RETENTION_SECONDS` is 86400. `docs/privacy/ENGINEERING_RETENTION.md` records that bounded default. After it elapses, a very late retry can execute because the row is gone. |
| Research-authorization idempotency remains intact | Yes. `derive_authorization_idempotency_key` still returns `research-auth:<sha256>` and ignores the client confirmation token. |

The internal demo fetch in `app/static/demo/demo.js` does not send `Idempotency-Key`. The server rejects that request before a claim. It cannot apply the query twice. The public consumer in `app/static/consumer/js/consumer.js` is the browser that implements the key lifecycle.

R17 is IMPLEMENTED-NOT-PROVEN. It is not PROVEN. CI #491 is not a staging exercise of a retried submission.

## Authorization and ownerless conversations

Sprint 40.7 is still in force. Answer-from-evidence, session refinement, and research proposal do not adopt `context.owner` from a body `conversation_id`. Body `conversation_id`, `user_id`, `profile_id`, `decision_id`, and stored conversation ownership are lookup values.

Public `POST /api/v1/shopping-assistant/query` resolves the owner only from `authorized_owner_from_request`. A request with no owner and no `decision_id` creates an ownerless non-decision conversation. The next request cannot continue that row. The row cannot hold a decision context. UUID snapshot access without a verified owner fails closed.

This is not a reachable public path for creating, continuing, reading, or mutating a sensitive decision context. Changing it requires a product decision. It is not selected.

## R2 session residuals, distinct from snapshot rebind

The canonical-snapshot conflict is R15. It is not a session-crypto defect.

What remains on R2:

- A copied guest or account owner cookie cannot be revoked server-side. Expiry is seven days.
- `POST /api/v1/auth/logout` revokes only the bearer session. The public sign-out sequence also posts `/account/clear-device`, so a shopper who uses Sign out does not leave the owner cookie behind. A client that calls only the logout API, including the internal demo, does leave it.
- Remember-me is an implemented 30-day bearer TTL stored in `localStorage`. The server stores the SHA-256 hash. That is not a missing control.

Those residuals are real and bounded. They are not the selected slice. The public shared-device path already clears the cookie. Guest revocation matters after the cookie has already been copied. The strict CSP and HttpOnly cookie are the current barriers to that copy.

## R3 and R16 origin, CSRF, and rate-limit buckets

Origin enforcement is the intended beta control for decision-owner-cookie mutations and for clear-device. The shopping-assistant POST is in that set when the owner cookie is present. A missing Origin fails closed. An Idempotency-Key does not replace that check, and the origin check does not replace the key.

`CsrfTokenService` is still unused on routes. The sprint wording is a CSRF/origin policy. One fail-closed Origin design covers the cookie-authorized mutations Sprint 40.4 named. This reconciliation does not require a second token on those routes.

Preference-cookie writers (`/consumer/location`, `/consumer/shopping-market`, `/api/v1/privacy/tracking-preference`) stay outside that set. They are not owner-cookie authorization. They do not reopen the historical CSRF finding and they do not require a token implementation in the selected slice.

Rate-limit buckets that exist and are shared in staging and production:

- Trusted client IP for public and guest traffic.
- Account HMAC for a verified bearer session or account owner cookie.
- Per-email HMAC for the auth window, plus the durable login lock.

The per-session bucket does not exist. The included R16 sentence names it beside per-IP and authenticated-principal limits. That absence keeps R16 PARTIAL. It does not keep R3 partial, because R3 is the header and origin policy, and that policy is implemented.

A per-session key would limit one guest cookie used from many addresses. It would not limit an attacker who mints a new cookie per request. The IP bucket already limits one address. Affiliate activation is off, and live model spend is off. The missing bucket is a named gap. It is not the current public-beta defect that outranks the missing security package.

## R6 capability classes

| Class | Status | Evidence |
|-------|--------|----------|
| Secrets | Present, narrow | `ci.yml` runs `scripts/secret_scan_25a.py`. Scan globs omit `app/`. |
| Dependency | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. CI #491: 71 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Absent | No CodeQL, Bandit, or Semgrep gate over `app/`. |
| Container | Absent | Image build, smoke import, and digest publication do not scan the image. Build Image #174 is not a vulnerability scan. |
| Terraform / IaC security | Absent | `terraform fmt` and `terraform validate` are present. They are not security scanning. |

If a later slice is a scanner, choose one class. SAST is the smallest missing class. It is not the selected slice.

## Prompt injection, merchant content, and cost

Paths into a model prompt or tool context:

- Shopper text enters `contains_prompt_injection` and the deterministic intent parser on every query. It enters `build_shopping_prompts` only when the shopping provider is available. That provider requires the AI flag, live HTTP, and an API key. Defaults are off, and the transport is `DisabledTransport`.
- Merchant catalog text and review text can enter the shopping user JSON on that same disabled path.
- Review text can enter `build_analysis_prompt` when review AI is enabled. The default is off.
- Community and review evidence can enter `build_community_prompts` when community AI is enabled. The default is off.
- Public-web and live Shopify research content are not fetched into a prompt while live research and `SHOPIFY_LIVE_CALL_PERMITTED` stay false.
- Provider output is marked `secrets_included` false and `prompts_included` false. It is not a second system prompt on the default path.

The six markers are `ignore previous`, `ignore all instructions`, `system prompt`, `reveal the prompt`, `api key`, and `override safety`. A match is a warning. It does not structurally separate untrusted content from system instructions.

Three current boundaries:

1. Currently reachable public-beta risk: none for a model following injected text. The model path is off.
2. Launch hardening needed before enabling AI or live research: separate untrusted content from system instructions, extend the review builder's refusal sentence, and do not treat the estimate cap as a live-research budget.
3. Later provider-specific work: vendor tool schemas and live provider output. `live_start_claim` tool names stay a fixed contract and do not perform HTTP today.

Prompt isolation is not the selected slice. Selecting it later must stay inside the current repository and must not activate a provider.

## Guest session and canonical rebinding

This is a product-definition conflict, not an implementation bug selected for change.

Sprint 40 acceptance says guest-to-authenticated transition preserves the active decision while rotating ownership credentials.

`claim_guest_conversation` rotates the cookie when no canonical UUID snapshot exists. When a canonical UUID snapshot exists, it returns `reason=immutable_snapshot_owner`, preserves the guest cookie, and does not rebind.

This audit does not change snapshot immutability. R15 stays PARTIAL until a product decision. It is not the selected slice.

## Documentation package

Still absent, and still owned by Sprint 40:

- Penetration-test readiness checklist
- Security incident-response runbook
- Vulnerability-response process
- Security go/no-go draft suitable for Sprint 44

Sprint 42 owns production probes, alerts, paging, and operational incident operations. It does not receive this package. Sprint 44 consumes the security go/no-go. The package is the selected slice.

## Historical finding reconciliation

These notes are additive. They do not rewrite the Sprint 30 map or section I of the gap inventory. Historical wording is unchanged. The status column is the current reading.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. The durable login lock and the submission ledger use the same backend selection and do not close this HIGH. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. `CsrfTokenService` is still unused on routes. That unused token is not a second required control for the covered set. Preference-cookie routes are outside the policy. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. `SECURITY_CSP` can still override the default. FastAPI `/docs` and `/redoc` are incompatible with the strict policy when they are enabled. `/openapi.json` remains usable. That incompatibility does not reopen the finding. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the dependency class. SAST, container scanning, and IaC security scanning STILL OPEN | pip-audit 2.10.1 is a required CI gate. CI #491 reported 71 packages, 0 vulnerabilities, and 0 exceptions. The historical sentence is no longer a total absence. Dependabot, CodeQL, and Trivy remain absent. Their absence is not, by itself, the Sprint 40 requirement. Secrets scanning remains present. `terraform validate` remains syntax validation. A successful Docker build is not container vulnerability scanning. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. This audit does not claim a historical reachable SSRF. Staging has not exercised the policy. Browser links are not a merchant-host allowlist. The finding is not closed and not PROVEN. |

No new HIGH is assigned. No MEDIUM is relabeled launch-blocking. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## Duplicated requirements

- R12 and R21 are the same closure gate. R21 adds the Sprint 45 deadline. They stay PARTIAL because the HIGH and the launch-blocking-MEDIUM bar are not closed. They are not independent runtime features.
- R3 and R16 both include the origin policy. R3 is that policy and is IMPLEMENTED-NOT-PROVEN. R16 also requires a per-session bucket, which is absent, so R16 stays PARTIAL.
- R4 and R19 both include encoding and XSS. R4 stays PARTIAL because a merchant-host allowlist is absent. The SSRF half is not reopened. R19 adds external-model minimization and cost and stays PARTIAL.
- R5 and R18 both include logs. Both are IMPLEMENTED-NOT-PROVEN. Security-audit email is intentional audit identity.
- R1 and R14 share the implemented owner-binding rule. R13 still includes the anonymous non-decision contract.
- R8 and R9 are not the same control. R9 is the temporary login lock and is IMPLEMENTED-NOT-PROVEN. R8 still lacks a bot challenge and click-fraud scoring, and it lacks a staging abuse exercise.
- R10 and the prompt-injection clauses of R19 are one review. The six markers are a warning, not isolation. The model path is off.
- R17's research-confirmation half and its ordinary message-submission half are both implemented. The row is IMPLEMENTED-NOT-PROVEN.
- R20 is the coverage review itself. It is IMPLEMENTED-NOT-PROVEN. It does not stay PARTIAL because other rows are open.

## Sprint 41 work, not this slice

- Production VPC, database, secrets, IAM, OIDC, deploy, rollback, DNS, and TLS.
- Production IAM review.
- Production image pull. Build Image #174 does not start that review.
- The HIGHs for production isolation and production OIDC/SSM.
- CDN/WAF decision recorded. Full WAF/CDN remains a Sprint 40 non-goal.

Sprint 41 stays UNSTARTED. This audit does not start it. Signed image provenance is not in the Sprint 41 included requirements.

## Sprint 42 work, not this slice

- CloudWatch and security paging.
- Operational incident response, probes, alerts, and paging runbooks.

The Sprint 40 security incident-response runbook is not that operational package.

## Remaining candidate comparison

| Candidate | Current public-beta exploitability | Executable now | Product decision | Another sprint owns production proof | Launch blocker under the current roadmap |
|-----------|--------------------------------------|----------------|------------------|---------------------------------------|------------------------------------------|
| Security-readiness package (R11) | None. A missing document does not change a request. | Yes. Repository documents only. | No. | Sprint 44 accepts the go/no-go. Sprint 42 does not own the package. Staging does not prove a checklist. | Yes. Sprint 40 acceptance requires the package for Sprint 44, and the sprint go/no-go gate is that draft. |
| SAST | No demonstrated defect. The gap is undetected code risk. Secrets and pip-audit already gate CI. | Yes. One workflow class. | No. | No. The gate would be CI. | The scanning bullet names it. It is not a known exploitable hole. |
| Container vulnerability scanning | No demonstrated image CVE. A successful build is not a scan. | Yes. One workflow class. | No. | Sprint 41 owns production image pull. The scan itself can live in CI. | The scanning bullet names it. It is not a known exploitable hole. |
| IaC security scanning | Production Terraform is not applied. `terraform validate` is syntax only. | Yes. One workflow class. | No. | Sprint 41 owns the production apply. | The scanning bullet names it. It does not describe a current public request path. |
| Prompt/content isolation | Not currently reachable. AI flags and transports default off. Live Shopify and live research stay fail-closed. | Yes, as a bounded repository change that must not enable a provider. | No for a warning-channel split. Enabling a provider would be a different decision. | Sprint 38 owns live research proof and stays fail-closed. | Launch hardening before AI or live research is turned on. Not a current beta exploit. |
| Per-session abuse bucket | A reused guest cookie across many addresses is not session-limited. A new cookie per request is not stopped by that key either. The IP and account buckets exist. Affiliate payout and model spend are off. | Yes. | No. | Staging abuse exercise is still Sprint 40 evidence, not Sprint 41. | Named in R16. Not the dominant flood pattern, and not required beyond the contract's per-session sentence. |
| Session-security residual | Public Sign out clears the owner cookie. API logout alone does not. A copied cookie works until the seven-day expiry. No current unauthenticated read of another user's decision was found. | Yes for a revocation list or for logout clearing the cookie. | No for those two residuals. The snapshot rebind is a separate product decision and is not this candidate. | Production session secrets are Sprint 41. | The acceptance sentence is met by the public sign-out path. The residual is post-theft and API-only logout. |

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R11 is missing. R6 still lacks SAST, container vulnerability scanning, and IaC security scanning. R16 still lacks a per-session bucket. R10 and R19 still lack structural prompt isolation. R2 still lacks guest revocation. R4 still lacks a merchant-host allowlist. R15 still needs a product decision. R9, R17, and the other implemented rows are not staging-proven. Those facts are not all proof that belongs to staging, Sprint 41, Sprint 42, or Sprint 44. The security package is Sprint 40 implementation work.

The guest-rebind acceptance conflict is not selected. It still needs a product decision. Anonymous `create(owner=None)` is not selected. It does not expose a decision context. The login lock and the submission ledger are not selected again. They are already merged.

**Slice:** Write the Sprint 40 security-readiness package: a penetration-test readiness checklist, a security incident-response runbook, a vulnerability-response process, and a Sprint 44 security go/no-go draft.

The package describes the controls that are now in the tree. It does not implement a new runtime control. It does not record risk acceptance. It does not close a finding that still lacks staging proof.

**Likely files for the later slice:**

- `docs/SECURITY.md`, as an additive update
- a penetration-test readiness checklist under `docs/`
- a security incident-response runbook under `docs/runbooks/`
- a vulnerability-response process under `docs/`
- a Sprint 44 security go/no-go draft under `docs/roadmap/`

**Acceptance for the later slice:**

1. The checklist names the identity, owner-binding, origin, CSP, URL-trust, rate-limit, login-lock, and submission-idempotency controls a tester would exercise, and it states that repository tests are not staging proof.
2. The security incident-response runbook states how a suspected credential, session, or abuse incident is reported, contained, and recorded. It does not replace Sprint 42 paging.
3. The vulnerability-response process states how a dependency, application, or image finding is triaged and fixed. It does not install a scanner.
4. The Sprint 44 draft states the current Sprint 40 go/no-go position: Planned, not ENGINEERING COMPLETE, not PRODUCTION PROVEN, not LAUNCH READY, with the open HIGH and MEDIUM labels preserved.
5. No runtime code, scanner, provider, Shopify call, routing change, or deploy is included.

**Out of scope for the slice:** SAST, container scanning, IaC security scanning, bot challenge, CAPTCHA, WAF, click-fraud detection, prompt isolation, per-session rate limits, guest revocation, guest rebind, anonymous ownerless create, CSRF tokens, a merchant-host allowlist, signed provenance, affiliate activation, Shopify calls, routing, and any deploy.

## Why this slice outranks the other gaps

The public login lock and the shopping-assistant replay control are in the tree. A retried message no longer applies twice. A password guess no longer resumes when the 60-second window expires. The remaining candidates were compared against that tree.

R11 is the only Included row that is entirely absent. Sprint 40's documentation deliverables, implementation deliverable "IR templates", acceptance criterion "Security package ready for 44 approval", and go/no-go gate all name it. Sprint 42 paging does not supply it. The package can be written now, from the merged controls, without a product decision.

SAST is the right choice if the next slice is a scanner. It does not describe a known exploitable defect, and secrets plus pip-audit already gate CI. Container scanning and IaC security scanning are separate absences. A successful image build and `terraform validate` do not fill them. Installing all three would violate the one-class rule. None of them produces the Sprint 44 security input.

Prompt isolation is incomplete and is not reachable while AI transports and live research stay fail-closed. Covering it now would be launch hardening before a provider is enabled. This audit does not enable a provider.

The per-session bucket is a real R16 gap. It does not stop a flood that uses a new cookie per request, and the trusted-IP and account buckets already exist. Affiliate activation is off. It does not outrank the missing package.

The session residuals are real and are not the snapshot-rebind decision. Public Sign out already clears the owner cookie. Guest revocation matters after a cookie copy. That is a smaller current exposure than an absent security go/no-go package that Sprint 44 is specified to consume.

Signed provenance is not a Sprint 40 blocker. The immutable tag, digest, and manifest checks are present. Sprint 41 owns the production pull.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No reachable public path that creates, continues, reads, or mutates a sensitive decision context through an ownerless conversation.
- No evidence that the message ledger lets body `user_id` or `profile_id` choose replay authority.
- No evidence that a replay calls `service.query` or `emit_ask_product_events`.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No pen-test report or written risk acceptance.
- No Sprint 38 defect in research-confirmation idempotency. The authorization key is still server-derived.
