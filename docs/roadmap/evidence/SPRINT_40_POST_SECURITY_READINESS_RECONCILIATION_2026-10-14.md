# Sprint 40 post-security-readiness reconciliation — 2026-10-14

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Add one deterministic SAST gate in CI over application code.

This slice is not named Sprint 40.8. A later implementation may take a number. This audit only selects the work.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.7 are merged. The durable failed-login lock is merged. Shopping-assistant submission idempotency is merged. The security-readiness package is merged. This change is a reconciliation audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `e4a8802e7edd87e234996e2f86be4ca2dee31c3e`

**Post-merge evidence on that SHA:** CI #495 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38522700330`). Full pytest on that run: 4484 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #176 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38523452539`). Those runs are publication and test evidence for the merged tree. They are not a penetration test, a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical inputs, not copied forward:** [`SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md`](SPRINT_40_POST_MESSAGE_IDEMPOTENCY_RECONCILIATION_2026-10-13.md) and [`SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md`](SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md). Those files keep the classes they recorded. The 2026-10-13 reconciliation still records R11 as MISSING. The package record still copies the prior PARTIAL set forward. This reconciliation re-reads the tree at `e4a8802e7edd87e234996e2f86be4ca2dee31c3e` and classifies R1–R21 again. The 2026-10-09 readiness audit stays historical.

**Gap inventory:** section I and the Sprint 30 security-finding map in [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md) are not rewritten. Additive notes below say which historical findings are still true.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate activation stays off. Live research stays off. No provider or public-market activation was changed. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. This audit does not reopen Sprint 38 or Sprint 39 engineering.

## How a row becomes PROVEN

Code on `main` is not enough. A row is PROVEN only when the current tree shows the control, a test fails closed for the abuse case, and the Sprint 40 acceptance bar for that control is met. A fresh staging or production run is recorded when it exists. Absence of that run keeps a complete, tested control at IMPLEMENTED-NOT-PROVEN. A control that is only partly present stays PARTIAL even when some of its tests pass. A requirement that is itself a written review is IMPLEMENTED-NOT-PROVEN when this reconciliation covers the named topics and Sprint 44 has not accepted the package. A review row stays PARTIAL when the named control is still missing in code, even if this document describes the gap.

This reconciliation did not execute the application on staging or production. Repository tests cited below were re-read. They are not staging proof.

No Included requirement is PROVEN. No Included requirement is NOT-APPLICABLE. No Included requirement is BLOCKED-DEPENDENCY. Formal SOC 2 and a full WAF/CDN program remain explicit non-goals. They are not Included rows.

## Counts

| Class | Rows |
|-------|------|
| PROVEN | 0 |
| IMPLEMENTED-NOT-PROVEN | 13 (R1, R2, R3, R4, R5, R7, R8, R9, R11, R14, R17, R18, R20) |
| PARTIAL | 8 (R6, R10, R12, R13, R15, R16, R19, R21) |
| MISSING | 0 |
| BLOCKED-DEPENDENCY | 0 |
| NOT-APPLICABLE | 0 |

## Requirement matrix

| ID | Requirement | Class | Current-tree reading | Tests re-read | Staging or production | What remains |
|----|-------------|-------|----------------------|---------------|-----------------------|--------------|
| R1 | AuthN/AuthZ/object-level review | IMPLEMENTED-NOT-PROVEN | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot reads use `get_for_owner`. Non-decision `ShoppingAssistantService.query` continues a conversation only through an owned context and loads an account only through the verified account. Answer, refinement, and research proposal load a body `conversation_id` only with `get_for_owner`. They do not adopt `context.owner`. A missing snapshot owner fails closed. The submission ledger scopes replay with `submission_authority_scope` and does not authorize a conversation from the key or from body `user_id`. | `tests/unit/test_sprint40_7_decision_path_owner_binding.py`, `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_shopping_submission_idempotency.py` | None on this SHA | No new object-level slice. Remaining proof is staging. |
| R2 | Session security review | IMPLEMENTED-NOT-PROVEN | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. `validate_session` rejects a missing, revoked, or expired session and revokes an expired one. Default bearer TTL is 3600 seconds. Remember-me uses 2592000 seconds and the consumer stores that bearer in `localStorage`. Password reset and email change call `revoke_all_for_user`. Guest `principal_id` and `session_id` are `uuid4`. The owner cookie is HMAC-SHA256, `HttpOnly`, and `SameSite=lax`, with `Secure` in staging and production. Guest TTL is seven days. `parse_owner_cookie` checks the MAC and expiry. Account cookies are not sufficient by themselves: `authorize_conversation_owner` loads the session by id and returns nothing when the session is missing, revoked, expired, or bound to another user. Public Sign out revokes the bearer and then `POST /account/clear-device` deletes the cookie. `POST /api/v1/auth/logout` alone does not delete the cookie. After that logout, an account cookie no longer authorizes. A guest cookie has no server-side revocation list and remains valid until expiry. That is the bounded guest-session design. It is not a separate executable Sprint 40 gap. | `tests/unit/test_sprint29_owner_cookie_auth.py`, `tests/unit/test_user_platform_auth_service.py` | None on this SHA | No guest-revocation slice. Remaining proof is a staging logout and shared-device exercise. |
| R3 | Headers/CSP/CORS/CSRF policy completion | IMPLEMENTED-NOT-PROVEN | `DEFAULT_SECURITY_CSP` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` also sets `nosniff`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS on staging and production. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes a missing or untrusted `Origin` on unsafe decision-owner-cookie requests, including `POST /api/v1/shopping-assistant/query` when the owner cookie is present, and always on `POST /account/clear-device`. Trusted origins come from `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS`. SameSite=Lax remains and is not the control. `CsrfTokenService.validate` is still not called by any route. Tokens are issued onto the bearer session. Origin enforcement is the beta CSRF control for the covered cookie mutations. Sprint 40 acceptance does not require a second token on those routes. Preference-cookie writers stay outside that set. | `tests/unit/test_sprint40_4_cookie_origin.py`, `tests/unit/test_sprint40_6_csp.py` | None on this SHA | No CSRF-token slice. Remaining proof is staging. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | IMPLEMENTED-NOT-PROVEN | `validate_server_fetch_url` accepts https only and rejects numeric private, loopback, link-local, and metadata hosts. `validate_browser_destination` accepts http or https. It allows private hosts because the server does not fetch them. Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend posts only to the pinned URL with `follow_redirects=False`. Live Shopify stays fail-closed. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Account and consumer redirects use local `_safe_next` prefixes. Browser merchant links are checked as browser destinations. No authoritative merchant-host list exists in the repository, and this audit does not invent one. Server-fetch allowlisting is the pinned provider endpoints plus the private-network rejection. That is the Sprint 40 allowlisting control. A browser navigation is not a server fetch. | `tests/unit/test_sprint40_5_url_trust.py`, `tests/unit/test_sprint40_6_csp.py` | None on this SHA | No merchant-domain list. Remaining proof is staging. DNS rebinding stays out of scope. |
| R5 | Log redaction; body logging policy; PII handling | IMPLEMENTED-NOT-PROVEN | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body, the owner cookie, a session id, or a bearer token. `redact_value` redacts secret-like keys before structured logs. Product analytics reject question, query, answer, message, email, session id, and conversation id. Security-audit records can still store the account email on registration rate-limit, login rate-limit, login failure, and password-reset events. That store is `SecurityEvent` metadata, not the request log and not `product.analytics_events`. Logout audit detail can name the session that was revoked. That is authentication identity for the security event. Sprint 40 does not prohibit it. | `tests/unit/test_validation_error_logging.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` | None on this SHA | No redaction slice. Remaining proof is a staging log sample. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | The Included sentence names five capability classes. All five are required for this row and for Sprint 40 ENGINEERING COMPLETE. Secrets: `scripts/secret_scan_25a.py` runs in CI and scans infra, env examples, scripts, and workflows. It does not scan `app/`. Dependency: `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1 against the frozen `uv.lock` closure with an empty exception list. CI #495 reported 71 packages, 0 vulnerabilities, 0 exceptions. SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`. Ruff is a lint gate, not SAST. Container: the CI image job builds and smoke-imports. `build-image.yml` publishes a digest. Neither scans the image for vulnerabilities. Terraform: `terraform fmt` and `terraform validate` run. That is syntax validation, not IaC security scanning. No tfsec or Checkov config was found. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #495 is a clean secret and pip-audit run. It is not a SAST, image-CVE, or IaC-security result. Build Image #176 is not a vulnerability scan. | SAST is the selected slice. Container scanning and IaC security scanning stay open and are not part of that slice. |
| R7 | Supply-chain provenance checks; immutable image authority verification | IMPLEMENTED-NOT-PROVEN | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, writes a release manifest, and states that the digest is deployment authority. Deploy and rollback workflows reject mutable-tag authority and pull by digest. `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum. No cosign, SLSA, or signed attestation was found. Sprint 40 acceptance does not name a signature. Sprint 41 owns production image pull and does not name image signing. Sprint 44 and Sprint 45 require the immutable image digest on the launch record. Signed provenance is not a Sprint 40 engineering blocker. The Dockerfile copies `ghcr.io/astral-sh/uv:latest` as a build tool. That tag is not the deployment authority. | `tests/unit/test_sprint25b1_image_publication.py` | Build Image #176 published a digest. It is not a signature. | No signed-provenance slice. Remaining proof is the production pull, which Sprint 41 owns. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | IMPLEMENTED-NOT-PROVEN | Staging and production must use `SqlRateLimitStore`. `RATE_LIMIT_BACKEND=memory` is rejected there. There is no silent fallback to memory. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified bearer session or account owner cookie. Auth failures use a separate shared `auth` scope keyed by an HMAC of the normalized email, 20 attempts per 60 seconds. The durable login lock adds a 20-failure, 15-minute hold on that same opaque identity. No CAPTCHA, bot challenge, or click-fraud score was found. Affiliate routes are demo-only and do not pay a commission. Canonical pages do not attach an affiliate action. Full WAF/CDN remains a non-goal. Credential stuffing has a beta control. The shared IP limit is the beta bot control. Click-fraud scoring is not required while there is no payable click. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_failed_login_lock.py` | None. Required staging evidence "Abuse controls exercised" is absent. | No bot-challenge or click-fraud slice. Remaining proof is the staging abuse exercise. |
| R9 | Account lockout or equivalent | IMPLEMENTED-NOT-PROVEN | `AuthService.login` still applies the 20-attempt / 60-second limiter, then `FailedLoginLock`. Twenty consecutive failures set `locked_until` from that threshold event for 900 seconds. Unlocked history is kept for 900 seconds. A stale unlocked sequence and an expired lock restart at 1. An active lock is not extended. Success calls `clear` and then `reset`. Staging and production use `SqlFailedLoginLockStore`. Memory is forbidden there. Store errors raise `FailedLoginLockUnavailable` and the public text matches the rate-limit error. Unknown, inactive, and bad-password failures share `Invalid email or password.` The stored key is an HMAC of the normalized email. | `tests/unit/test_sprint40_failed_login_lock.py`, `tests/unit/test_user_platform_auth_service.py` | None on this SHA | No new lockout slice. Remaining proof is a staging exercise. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings and runs on the cleaned shopper query. A match adds a warning. Deterministic ranking still runs. Merchant text, reviews, community text, and tool results are not passed through that function. `build_shopping_prompts` and `build_community_prompts` put catalog, review, and community text in the user JSON and say in the system string not to follow instructions in that text. `build_analysis_prompt` puts review text in the user JSON and does not say that. None of the builders uses a separate untrusted channel. Default transports are `DisabledTransport`. `AI_SHOPPING_ENABLED`, `AI_REVIEW_ENABLED`, and `AI_COMMUNITY_ENABLED` default false, and the matching live-HTTP flags default false. No model-chosen tool loop was found. Public-web research content is not fetched into a prompt while live research stays fail-closed. | `tests/unit/test_shopping_assistant_deterministic.py` | None | Structural isolation is still absent. It is required before AI or live research is enabled. It is not the selected slice. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | IMPLEMENTED-NOT-PROVEN | The merged package is `docs/security/PENETRATION_TEST_READINESS.md`, `docs/runbooks/SECURITY_INCIDENT_RESPONSE.md`, `docs/security/VULNERABILITY_RESPONSE.md`, and `docs/roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md`. The checklist says no penetration test has been executed and no item is TESTED / PASSED. The runbook does not configure paging and does not claim a restore drill. The vulnerability process does not grant a risk acceptance. The Sprint 44 draft says SECURITY GO: NOT DECIDED. Sprint 42 still owns paging, probes, alerts, and restore rehearsal. Sprint 44 still owns approval. The runbook's copied-cookie example describes the seven-day guest cookie. Account cookies are additionally checked against session revocation. That wording limit does not make the package absent. | `tests/unit/test_sprint40_security_readiness_package.py` | None. The package has not been rehearsed. | No new package. Proof is later use, review, or rehearsal. R11 is not PROVEN. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH "In-process rate limits only" is IMPLEMENTED-NOT-PROVEN. Required staging evidence "Abuse controls exercised" is absent, so the HIGH is not closed. No historical Sprint 40 MEDIUM is designated launch-blocking. The CSRF/Origin, CSP, and URL/SSRF MEDIUMs are IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION for the original no-scanner condition. None of those MEDIUMs is the closure blocker. No written risk acceptance exists. This audit does not assign a new HIGH or MEDIUM. | Tests cited on the findings do not close them. | None that exercises abuse controls | The gate stays open until the HIGH is closed by staging proof or by a later written risk acceptance. This audit does not grant that acceptance. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Decision contexts cannot be stored without an owner. `ConversationContext.__post_init__` raises when `decision_context` is set and `owner` is `None`. Decision reads require a verified owner. A cookieless non-decision Ask can still call `create(owner=None)`. The stored row has no decision context. `get_for_owner` does not return it. `live_start_claim` refuses an ownerless conversation. The security intent, which is to stop sensitive-context adoption, is met. The literal sentence is not, because the anonymous non-decision row has no owner. That row is the Sprint 40.1 contract. It has no public security consequence. | `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row` and the Sprint 40.7 ownerless decision-path negatives | Sprint 40.1 did not exercise this on staging | No slice. Changing it requires a product decision to mint a guest owner for anonymous Ask. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | IMPLEMENTED-NOT-PROVEN | Body `conversation_id`, `user_id`, `profile_id`, `decision_id`, and `context_version` are lookup values. Authority is the verified owner. The submission fingerprint includes normalized body `user_id` and `profile_id` so a changed body conflicts. `submission_authority_scope` does not read those fields. Affiliate link decoration can still copy a body `user_id` into link generation. Affiliate activation stays off, and that copy does not read another owner's conversation, profile, decision, or history. | `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_sprint40_7_decision_path_owner_binding.py` | None | No new authorization slice. Remaining proof is staging. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256 with a seven-day expiry. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie. Public sign-out revokes the bearer and then clears the owner cookie. `claim_guest_conversation` rebinds and rotates to the account owner only when no canonical UUID snapshot exists. When one exists, it returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. Sprint 40 acceptance says the transition preserves the active decision while rotating ownership credentials. Snapshot immutability says the opposite for a canonical UUID snapshot. That conflict is a product definition. | `tests/unit/test_sprint29_guest_claim.py` | Sprint 29 staging logout notes were not re-run | No, until a product decision. This audit does not change snapshot immutability. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement is the beta control for decision-owner-cookie mutations and for `POST /account/clear-device`. Bearer-only requests stay unchanged. HTTP rate-limit identity is the trusted client IP, or an account HMAC when a bearer session or account owner cookie is verified. A guest session id is not a rate-limit key. The Included sentence also names a per-session bucket. That bucket is still absent. The exact missing control is a shared PostgreSQL bucket keyed by the verified guest `session_id` on owner-cookie requests, beside the existing IP and account buckets, without reading body identity. A new cookie per request and anonymous Ask are already limited by the trusted IP. Those patterns are why this bucket is not the selected slice. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests | None | The per-session bucket stays unimplemented. It is not the selected slice. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | IMPLEMENTED-NOT-PROVEN | `POST /api/v1/shopping-assistant/query` requires `Idempotency-Key`. The public consumer creates one key before the first fetch, reuses it for a retryable failure, and creates a new key after a terminal response. The same scoped key and canonical fingerprint replay the stored response. Replay does not call `service.query` and does not call `emit_ask_product_events`. A changed mutation-relevant payload, including body `user_id` or `profile_id`, is HTTP 409. Those fields are in the fingerprint and are not read by `submission_authority_scope`. Scope is the verified account, the verified guest, or an HMAC of the trusted client host for anonymous Ask. Concurrent SQL inserts have one primary-key winner. A processing row is sealed indeterminate after 15 minutes and is not re-executed. Completed and indeterminate rows expire after 24 hours. Research confirmation still derives `research-auth:<sha256>` and ignores the client confirmation token. | `tests/unit/test_shopping_submission_idempotency.py`, `tests/unit/test_research_authorization_handoff.py` | None on this SHA | No new message-idempotency slice. Remaining proof is a staging exercise. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, a session id, or a bearer credential. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. The submission ledger stores the public response so a replay can be returned without calling `service.query`. That store is not the request log and not product analytics. The raw key is stored only as SHA-256. Ask analytics still omit the question and answer text, and a replay does not emit them again. | `test_server_identity_is_opaque_and_ask_text_is_absent`, `test_http_replay_skips_query_analytics_and_a_second_turn` | None on this SHA | No. Remaining proof is a staging sample. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are implemented, as on R3 and R4. The six markers and the user-prompt embedding are the same facts as R10. Assistant, review, community, answer, refinement, and research processing set `secrets_included` and `prompts_included` false. Shopping and community prompt builders drop keys whose names contain `api_key`, `secret`, `token`, or `prompt`. Review prompts do not use that filter. `AI_MAX_ESTIMATED_COST_PER_REQUEST` defaults to 0.05 and compares a returned estimate on the review, shopping, and community orchestrators. It is not a live-research budget. Live research remains fail-closed. | `tests/unit/test_sprint40_6_csp.py`, prompt-injection unit coverage | None | The same pre-activation isolation gap as R10. Not the selected slice. Do not enable live research to test the cost cap. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | IMPLEMENTED-NOT-PROVEN | This matrix is the coverage review. Each named topic is classified on its own row. The penetration-test checklist, vulnerability process, and Sprint 44 draft now exist and do not replace this review. Open findings do not keep this row PARTIAL. Sprint 44 has not accepted the package, so it is not PROVEN. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py`, and the tests cited on the rows above | No fresh staging crawl was run | No separate implementation slice. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same gate as R12. The finding that prevents closure is the HIGH "In-process rate limits only", which remains IMPLEMENTED-NOT-PROVEN because staging has not exercised the shared counters. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | Do not start Sprint 45. Do not risk-accept the HIGH in this audit. |

## What moved, and what did not

R2 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. Account owner cookies are checked against the bearer session. A revoked, expired, or mismatched session does not authorize. The guest cookie is a stateless HMAC credential until its seven-day expiry. That is an accepted bounded guest-session design, not a launch blocker, not the R15 snapshot conflict, and not a separate executable gap.

R4 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. Server fetches are allowlisted by pinned endpoints and by the private-network rejection. Browser merchant links are not server fetches. No authoritative merchant-host list exists, so this audit does not invent one. No unresolved implementation defect was found on this row.

R8 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The shared PostgreSQL limits, the per-email auth window, and the durable login lock are the beta controls for credential stuffing and for bot traffic. Click-fraud scoring is not required while affiliate activation stays off and no click is paid. A bot challenge is not required for this public beta. Full WAF/CDN stays a non-goal. Staging has not exercised the controls, so the row is not PROVEN.

R1, R3, R5, R7, R9, R11, R14, R17, R18, and R20 stay IMPLEMENTED-NOT-PROVEN. R11 is not PROVEN because the files exist. R6, R10, R12, R13, R15, R16, R19, and R21 stay PARTIAL. No row is PROVEN. No row is MISSING.

## R2 session residuals

The previous reconciliation said a copied owner cookie cannot be revoked server-side. That reading is true for a guest cookie and false for an account cookie.

`authorize_conversation_owner` returns a guest owner after the MAC and expiry checks. It returns an account owner only when `SessionRepository.get_by_id` finds a matching, unrevoked, unexpired session for the same user. Password reset and email-change confirmation call `revoke_all_for_user` before they report success. Public Sign out calls `POST /api/v1/auth/logout` and then `POST /account/clear-device`. The internal demo logout calls only the bearer logout. After that call, the account cookie no longer authorizes even if the browser still holds it.

What remains:

- A copied guest cookie works until the seven-day expiry. There is no guest revocation list.
- `ensure_guest_owner_cookie` reuses a valid guest cookie. That is continuation of the device session, not fixation. Forging the cookie requires the HMAC secret.
- API logout alone does not clear the cookie. Account authorization still fails after the session is revoked. The public Sign out path also clears the cookie.

Classification of that residual: an accepted bounded guest-session design. It is not a Sprint 40 launch blocker. It is not the guest-to-account snapshot conflict. It is not selected.

The acceptance sentence "Logout and shared-device reuse cannot expose a previous user's context" is met for an account by session revocation plus the public clear-device call. A guest cookie is the guest session. The next person on the same browser continues that guest until clear-device or expiry. That is the device-bound session, not a second user's account.

## R3 origin, unused CSRF tokens, and CSP

Origin enforcement is the intended beta control for decision-owner-cookie mutations and for clear-device. The shopping-assistant POST is in that set when the owner cookie is present. A missing Origin fails closed.

`CsrfTokenService` is still unused on routes. The sprint wording is a CSRF/origin policy. One fail-closed Origin design covers the cookie-authorized mutations Sprint 40.4 named. This reconciliation does not require a second token on those routes. The unused token machinery is defense-in-depth, not an open requirement.

CSP was re-read separately. `DEFAULT_SECURITY_CSP` still has no `'unsafe-inline'` and no `'unsafe-eval'`. `SECURITY_CSP` can still override the default. That override does not reopen the historical finding. Staging has not exercised the policy, so R3 stays IMPLEMENTED-NOT-PROVEN.

## R4 browser links and server fetches

These are different trust boundaries.

Server fetches:

- Shopify production transport accepts only `https://catalog.shopify.com/api/ucp/mcp`, passes `validate_server_fetch_url`, and refuses redirects. `SHOPIFY_LIVE_CALL_PERMITTED` is false. Real Shopify calls stay 0.
- Resend accepts only its pinned HTTPS URL, passes `validate_server_fetch_url`, and sets `follow_redirects=False`.
- Generic server-fetch policy rejects non-https URLs, embedded credentials, and non-global literal addresses. Hostnames are not resolved. DNS rebinding stays out of scope.

Browser navigation:

- Merchant, marketplace, and product URLs pass `validate_browser_destination`.
- Schemes other than http and https are rejected.
- The server does not fetch those URLs.
- No file in the repository is an authoritative list of merchant hosts.

The Included words "merchant URL allowlisting" are satisfied by the server-fetch pins and the private-network rejection. They do not require a browser-host allowlist for links the server does not fetch. Inventing a domain list would not be an implementation of an existing contract.

No command-injection call was found under `app/`. Redirects used by account and consumer pages stay on local prefixes. No reachable SSRF was demonstrated. R4 is IMPLEMENTED-NOT-PROVEN because staging has not exercised the policy.

## R6 capability classes

| Class | Required for ENGINEERING COMPLETE | Status | Evidence |
|-------|-----------------------------------|--------|----------|
| Secrets | Yes | Present, narrow | `ci.yml` runs `scripts/secret_scan_25a.py`. Scan globs omit `app/`. |
| Dependency | Yes | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. CI #495: 71 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Yes | Absent | No CodeQL, Bandit, or Semgrep gate over `app/`. No `codeql.yml`. Ruff is not SAST. |
| Container vulnerability scanning | Yes | Absent | Image build, smoke import, and digest publication do not scan the image. Build Image #176 is not a vulnerability scan. |
| Terraform / IaC security | Yes | Absent | `terraform fmt` and `terraform validate` are present. They are not security scanning. |

The Included sentence is "Secret/dependency/SAST/container/Terraform scanning in CI". Acceptance says CI scanning is required on main. Two present classes do not complete a five-class requirement. `terraform validate` is not the Terraform class. A successful Docker build is not the container class. R6 stays PARTIAL.

If the next slice is a scanner, it is exactly one class. This reconciliation selects SAST. Container scanning and IaC security scanning are not bundled with it.

Repository constraints for the later slice:

- No CodeQL workflow exists. The slice must not depend on GitHub Advanced Security or a hosted code-scanning product.
- The existing dependency gate is a pinned local tool with a committed baseline. The SAST gate should follow that shape.
- Ruff stays the lint gate.
- Do not install a container scanner or an IaC policy scanner in the same change.
- The capability is the requirement. A brand is not.

## R8 compensating controls

| Threat named by the row | Current beta control | Required now |
|-------------------------|----------------------|--------------|
| Credential stuffing | Per-email 20/60-second shared limiter, plus the 20-failure / 15-minute durable lock, enumeration-safe errors, fail-closed PostgreSQL in staging and production | Yes. Implemented. Not staging-proven. |
| Bot traffic | Shared trusted-IP limit. Full WAF/CDN is an explicit non-goal. | The IP limit is the beta control. A CAPTCHA or bot challenge is not required. |
| Click fraud | Canonical pages do not attach an affiliate action. Affiliate API routes are marked demo-only and do not pay a commission. | Scoring is not required while activation stays off. It becomes a precondition of a later activation. It is not this slice. |

`AFFILIATE_ENABLED` defaults true for the Sprint 20 demo engine. That flag is not public affiliate activation. Public canonical pages still render an empty affiliate disclosure and do not attach an affiliate action.

R8 is IMPLEMENTED-NOT-PROVEN. The missing proof is the staging exercise already required for the HIGH, not a new control.

## Prompt injection, merchant content, and cost

Paths into a model prompt or tool context:

- Shopper text enters `contains_prompt_injection` and the deterministic intent parser on every query. It enters `build_shopping_prompts` only when the shopping provider is available. That provider requires the AI flag, live HTTP, and an API key. Defaults are off, and the transport is `DisabledTransport`.
- Merchant catalog text and review text can enter the shopping user JSON on that same disabled path.
- Review text can enter `build_analysis_prompt` when review AI is enabled. The default is off. That builder does not say to ignore instructions in the review text, and it does not strip secret-like keys.
- Community and review evidence can enter `build_community_prompts` when community AI is enabled. The default is off.
- Public-web and live Shopify research content are not fetched into a prompt while live research and `SHOPIFY_LIVE_CALL_PERMITTED` stay false.
- Provider output is marked `secrets_included` false and `prompts_included` false. It is not a second system prompt on the default path.

The six markers are `ignore previous`, `ignore all instructions`, `system prompt`, `reveal the prompt`, `api key`, and `override safety`. A match is a warning. It does not structurally separate untrusted content from system instructions. Merchant, review, and community text can become instruction-bearing user-prompt JSON on the disabled builders. No model-chosen tool call executes that text today.

Three current boundaries:

1. Currently reachable public-beta risk: none for a model following injected text. The model path is off. Deterministic ranking does not treat merchant text as instructions.
2. Engineering required before AI or live-research activation: one bounded change that separates untrusted catalog, review, and community text from system instructions, including the refusal sentence missing from `build_analysis_prompt`. Do not enable a provider to do it.
3. Provider-specific future work: vendor tool schemas and live provider output. `live_start_claim` tool names stay a fixed contract and do not perform HTTP today. The estimate cap is not a live-research budget.

Prompt isolation is not the selected slice. It does not change a request a shopper can make while the flags stay off.

## R11 package consistency

| Check | Result |
|-------|--------|
| Penetration-test readiness checklist exists | Yes. No test is claimed as executed or passed. |
| Security incident-response runbook exists | Yes. Paging is not configured. No restore drill is claimed. |
| Vulnerability-response process exists | Yes. No risk acceptance is granted. |
| Sprint 44 security go/no-go draft exists | Yes. DRAFT / NOT APPROVED. SECURITY GO: NOT DECIDED. |
| Sprint 42 boundary | Paging, probes, alerts, production incident operations, and restore rehearsal stay with Sprint 42. |
| Sprint 44 boundary | Final rehearsal and approval stay with Sprint 44. |

R11 is IMPLEMENTED-NOT-PROVEN. The files do not prove the package.

## R12 and R21

These are gates, not runtime features. They stay PARTIAL because one existing finding is not closed.

The finding that prevents closure is the HIGH "In-process rate limits only". The shared PostgreSQL counter is implemented. Staging evidence "Abuse controls exercised" is absent. The finding stays IMPLEMENTED-NOT-PROVEN. It is not closed and not PROVEN.

No existing MEDIUM is launch-blocking. This audit does not create a new severity and does not grant a risk acceptance. Other PARTIAL rows do not, by themselves, keep these gates partial.

Closing the gate is a staging exercise, or a later written risk acceptance. It is not the selected engineering slice.

## R13 ownerless non-decision rows

The literal requirement says every conversation and every decision context is bound to a verified guest or an authenticated principal. The security intent is that a sensitive context cannot be created or adopted without that owner.

Current behavior:

- An anonymous non-decision Ask can store `create(owner=None)`.
- That row cannot contain a decision context.
- A later request cannot continue it through `get_for_owner`.
- Decision-bound paths require a verified owner.
- `live_start_claim` refuses an ownerless conversation.

The exact gap is contractual: the anonymous non-decision row has no owner. It is not an exploitable decision-context path. Closing the literal sentence would change the Sprint 40.1 anonymous Ask contract. That needs a product decision. It is not selected.

## R15 guest rebind

This remains a product-definition conflict.

Sprint 40 acceptance says guest-to-authenticated transition preserves the active decision while rotating ownership credentials.

`claim_guest_conversation` rotates the cookie when no canonical UUID snapshot exists. When a canonical UUID snapshot exists, it returns `reason=immutable_snapshot_owner`, preserves the guest cookie, and does not rebind.

This audit does not change snapshot immutability. R15 stays PARTIAL until a product decision. It is not selected.

## R16 abuse the missing bucket would and would not stop

| Pattern | Trusted IP | Account HMAC | Per-session guest bucket |
|---------|------------|--------------|--------------------------|
| Many requests from one address, including a new cookie each time and anonymous Ask | Limited | Not used | Would not add a limit |
| One verified account from many addresses | Not the account key | Limited | Would not replace the account key |
| One copied guest cookie used from many addresses | Each address is limited; the cookie is not | Not used | Would limit the cookie |
| Owner-cookie mutation | Origin policy still applies | Used when the cookie is an account | Would apply only to a guest cookie |
| Same `Idempotency-Key` replay | Not a rate-limit control | Not a rate-limit control | Replay is already a stored response |

The cross-IP copied guest cookie is the only pattern a session bucket would newly limit. The cookie is `HttpOnly`. The default CSP has no `'unsafe-inline'`. Live model spend and live research are off, so the extra requests are deterministic Ask traffic that each source IP already limits. The Included sentence still names the bucket, so R16 stays PARTIAL. The bounded implementation, if a later slice chooses it, is the shared guest-`session_id` bucket described in the matrix. This audit does not add it. It would not materially address the flood that mints a new cookie or omits the cookie.

## Historical finding reconciliation

These notes are additive. They do not rewrite the Sprint 30 map or section I of the gap inventory. Historical wording is unchanged. The status column is the current reading.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. The durable login lock and the submission ledger use the same backend selection and do not close this HIGH. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. `CsrfTokenService` is still unused on routes. That unused token is not a second required control for the covered set. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the original no-scanner condition. SAST, container scanning, and IaC security scanning STILL OPEN as R6 capability gaps | The historical finding was the absence of a dependency scanner. pip-audit 2.10.1 is a required CI gate. CI #495 reported 71 packages, 0 vulnerabilities, and 0 exceptions. That original condition is closed by implementation. Dependabot, CodeQL, and Trivy remain absent. Their product names are not the Sprint 40 requirement. The remaining SAST, container, and IaC gaps are R6. They are not a rewrite of the historical finding into a broader absence. Secrets scanning remains present. `terraform validate` remains syntax validation. A successful Docker build is not container vulnerability scanning. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. Staging has not exercised the policy. Browser links are not a merchant-host allowlist, and that absence is not this finding. The finding is not closed and not PROVEN. |

No new HIGH is assigned. No MEDIUM is relabeled launch-blocking. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## Which PARTIAL rows are which kind of work

| Item | Kind | Engineering now |
|------|------|-----------------|
| Item R6 | Real implementation gap. Three of five required scanner classes are absent. | Yes. One class only. SAST is selected. |
| Item R10 | Real isolation gap on disabled prompt builders. Current public-beta model risk is absent. Required before AI or live-research activation. | Not selected. Do not enable a provider. |
| Item R12 | Staging proof of the HIGH. Not a runtime feature. | No. |
| Item R13 | Product/contract residue of anonymous non-decision `create(owner=None)`. No public security consequence. | No. |
| Item R15 | Product-definition conflict with canonical snapshot immutability. | No. |
| Item R16 | Named per-session bucket. Explicit in the Included sentence. It does not materially address the dominant flood. | Not selected. |
| Item R19 | Same pre-activation isolation and cost-budget gap as R10. Encoding and XSS are already implemented. | Not selected. |
| Item R21 | Same closure gate as R12. The blocking finding is the unclosed HIGH. | No. |

IMPLEMENTED-NOT-PROVEN rows that still need staging or production proof, and not more repository engineering, include R1, R2, R3, R4, R5, R7, R8, R9, R14, R17, and R18. R11 needs later use or rehearsal. R20 needs Sprint 44 acceptance. Those are not selected.

## Candidate comparison

| Candidate | Repository evidence | Reachable beta risk | Requirement owner | Product decision | Size | Staging or production proof | Launch-blocking now |
|-----------|---------------------|---------------------|-------------------|------------------|------|-----------------------------|---------------------|
| SAST | No workflow scans `app/`. Secret scan globs omit `app/`. Ruff is lint. pip-audit already gates dependencies. | No demonstrated defect. Undetected application defects are the public request path. | Sprint 40 Included scanning sentence. Sprint 41 does not own CI SAST. | No. | One pinned CI gate and a baseline, on the pip-audit pattern. | The gate is CI. Staging cleanliness is later evidence, not a reason to skip the gate. | Yes for ENGINEERING COMPLETE. The five-class sentence is unmet. |
| Container vulnerability scanning | CI builds the image. Build Image #176 publishes a digest. Neither scans packages inside the image. The Dockerfile uses `python:3.12-slim` and `ghcr.io/astral-sh/uv:latest`. | No demonstrated image CVE. The image is not the production runtime. | Sprint 40 names the capability. Sprint 41 owns the production pull, not the scan. | No brand is required. Advisory databases change daily, so a gate needs a pinned database or a baseline to stay deterministic. | One CI or publish job. | Sprint 41 owns production deploy evidence. | Named, and not the current request path. Not bundled with SAST. |
| IaC security scanning | `terraform fmt` and `terraform validate` run for account, staging, and production. No policy scanner exists. Terraform is not applied. | No current public request. A bad plan matters before Sprint 41 apply. | Sprint 40 names the capability. Sprint 41 owns the apply. | No brand is required. `terraform validate` must not be reused as the scan. | One policy job. | Sprint 41 owns apply evidence. | Named, and lower current beta value than application SAST. Not bundled with SAST. |
| Prompt/content isolation | Six-marker warning on the shopper query. Shopping and community builders warn in the system string. Review builder does not. All three embed untrusted text in user JSON. Providers default off. | None while AI flags, live HTTP, live research, and Shopify stay off. | Sprint 40 review rows R10 and R19. Activation is a later decision. | No, for a channel split that does not enable a provider. Enabling a provider is a different decision. | One bounded builder change. Not an architecture redesign. | Sprint 38 owns live-research proof and stays fail-closed. | Launch hardening before activation. Not a current beta exploit. |
| Per-session rate limit | `client_rate_limit_identity` returns `ip:` or `acct:`. Guest `session_id` is not a key. | A copied guest cookie across many IPs is not session-limited. A new cookie per request is already IP-limited. Model spend is off. | Sprint 40 R16 names it. | No. | One shared bucket. | Staging abuse exercise is still Sprint 40 evidence. | Named. Not the dominant flood. Not selected. |
| Guest-cookie revocation | Guest cookies are stateless HMAC. Account cookies check `session.revoked`. Public Sign out clears the cookie. | A copied guest cookie works until expiry. An account cookie does not survive logout, password reset, or email change. | The acceptance sentence is met for accounts. The guest list is not an actionable extra requirement. | No for the account path. A guest revocation list would invent a server-side guest session the current design does not have. | A revocation store, if chosen later. | Production session secrets are Sprint 41. | Not selected. |
| Browser merchant-host allowlist | Browser links use `validate_browser_destination`. Server fetches are pinned. No merchant-host catalog exists. | The server does not fetch the link. | R4 does not require a browser allowlist. | A list would be an invented product decision. | Not estimated. It is not a defect. | Staging still has not exercised URL policy. | Not a gap. Not selected. |

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R6 still lacks SAST, container vulnerability scanning, and IaC security scanning, and all five classes are required for ENGINEERING COMPLETE. R16 still names a per-session bucket. R10 and R19 still lack structural prompt isolation on disabled builders. R13 and R15 still need product decisions. R12 and R21 still wait on staging proof of the HIGH. Those facts are not all proof, later-sprint work, or non-blocking defense-in-depth. The scanner gap is Sprint 40 implementation work.

The guest-rebind conflict is not selected. Anonymous `create(owner=None)` is not selected. The login lock, the submission ledger, and the security-readiness package are not selected again. They are already merged.

**Slice:** Add one deterministic SAST gate in CI over application code.

**Acceptance for the later slice:**

1. CI fails when the pinned analyzer reports a finding outside a committed baseline.
2. The analyzer reads application code under `app/`. The existing secret scan does not.
3. Ruff remains the lint gate and is not described as this gate.
4. The change does not add container vulnerability scanning or IaC security scanning.
5. The change does not require CodeQL, GitHub code scanning, or a hosted rules service. No CodeQL workflow exists, and none is required.
6. No runtime behavior, provider flag, Shopify call, routing change, or deploy is included.

**Out of scope for the slice:** container scanning, IaC security scanning, bot challenge, CAPTCHA, WAF, click-fraud detection, prompt isolation, per-session rate limits, guest revocation, guest rebind, anonymous ownerless create, CSRF tokens, a merchant-host allowlist, signed provenance, affiliate activation, Shopify calls, routing, and any deploy.

## Why this slice outranks the other gaps

The security-readiness package is in the tree. R11 is no longer missing. The remaining PARTIAL rows were compared against the current request path.

SAST is the missing scanner class whose subject is the code that already serves public Ask, auth, cookies, and idempotency. It can be a deterministic CI gate without a product decision and without a hosted scanner. Container scanning protects an image Sprint 41 has not deployed, and its advisory database is a poor fit for a deterministic gate unless it is pinned. IaC security scanning protects Terraform that Sprint 41 has not applied. `terraform validate` does not fill that class, and it is not selected as a substitute.

Prompt isolation is a real pre-activation gap and is not reachable. Selecting it would harden builders that `DisabledTransport` never calls. This audit does not enable a provider.

The per-session bucket is a real R16 sentence and a weak control for the floods that matter: a new cookie per request, and anonymous Ask. The trusted-IP and account buckets already exist.

Guest revocation and a browser merchant-host list are not actionable Sprint 40 requirements on this tree.

Signed provenance is not a Sprint 40 blocker. The immutable tag, digest, and manifest checks are present. Sprint 41 owns the production pull.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No reachable public path that creates, continues, reads, or mutates a sensitive decision context through an ownerless conversation.
- No evidence that the message ledger lets body `user_id` or `profile_id` choose replay authority.
- No evidence that a replay calls `service.query` or `emit_ask_product_events`.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No pen-test report, no paging configuration, no restore drill, and no written risk acceptance.
- No Sprint 44 approval. SECURITY GO remains NOT DECIDED.
