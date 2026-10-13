# Sprint 40 post-40.7 reconciliation — 2026-10-13

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Failed logins must stay limited after the shared auth window expires.

This slice is not named Sprint 40.8. A later implementation may take a number. This audit only selects the work.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.7 are merged. This change is a reconciliation audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `bbf7158dfa70c969e851f032702732f0e7e863ea`

**Post-merge evidence on that SHA:** CI #477 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38351455086`). Full pytest on that run: 4410 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #170 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38352197142`). Those runs are publication and test evidence for the merged tree. They are not a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical inputs, not copied forward:** [`SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md`](SPRINT_40_POST_40_6_RECONCILIATION_2026-10-10.md) and [`SPRINT_40_7_DECISION_PATH_OWNER_BINDING_2026-10-13.md`](SPRINT_40_7_DECISION_PATH_OWNER_BINDING_2026-10-13.md). Those files keep the classes they recorded. This reconciliation re-reads the tree at `bbf7158dfa70c969e851f032702732f0e7e863ea` and classifies R1–R21 again. The 2026-10-09 readiness audit stays historical.

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
| IMPLEMENTED-NOT-PROVEN | 3 (R1, R14, R18) |
| PARTIAL | 17 (R2–R10, R12, R13, R15–R17, R19–R21) |
| MISSING | 1 (R11) |
| BLOCKED-DEPENDENCY | 0 |
| NOT-APPLICABLE | 0 |

## Requirement matrix

| ID | Requirement | Class | Current code evidence | Current test evidence | Staging evidence | Production evidence | Sprint 40 engineering still required | Dependency owner | Exact next action |
|----|-------------|-------|------------------------|-----------------------|------------------|---------------------|--------------------------------------|------------------|-------------------|
| R1 | AuthN/AuthZ/object-level review | IMPLEMENTED-NOT-PROVEN | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot repository reads use `get_for_owner`. Non-decision `ShoppingAssistantService.query` continues a conversation only through `_owned_conversation_context` → `get_for_owner`, and loads profiles only through `_authorized_account_user_id`. `AnswerFromEvidenceService`, `RefineSessionRecommendationService`, and `ProposeResearchService` load a body `conversation_id` only with `get_for_owner` when a verified request owner is present. They do not call `ConversationRepository.get` and do not set an owner from `context.owner`. UUID snapshot reads use `get_for_owner` with the verified request owner. A missing owner raises `DecisionSnapshotOwnershipError` with `snapshot access requires a verified owner`. Owner-bound overlays, pending proposals, and research authorizations are loaded only through that same owner match, or through `find_bound_for_owner`. | `tests/unit/test_sprint40_7_decision_path_owner_binding.py` rejects an ownerless body id, a foreign owner, and stored-owner adoption on answer, refinement, and research proposal. The verified owner still reads their own snapshot, overlay, and pending proposal. `tests/unit/test_sprint40_assistant_body_identity.py` still rejects a foreign non-decision `conversation_id`, body `user_id`, and unbound `profile_id`. | None on this SHA | None | No new object-level slice. Remaining proof is a staging exercise. | None | Do not treat repository tests as staging proof. Do not reopen Sprint 40.1 or Sprint 40.7. |
| R2 | Session security review | PARTIAL | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. Expiry and revocation are checked in `AuthService.validate_session`. Password reset and email change call `revoke_all_for_user`. Guest `principal_id` and `session_id` are `uuid4`. The owner cookie is HMAC-SHA256, expires in seven days, and is `HttpOnly` plus `SameSite=lax`, with `Secure` in staging and production. There is no server-side guest revocation list. `POST /api/v1/auth/logout` revokes the bearer session and does not clear the owner cookie. `docs/SECURITY_MODEL.md` still describes Sprint 17 demo session limits. | `tests/unit/test_user_platform_security.py`, `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | Sprint 27 and Sprint 29 session notes are historical and were not re-run on this SHA | None. Production secret attach remains Sprint 41 | No new session-crypto slice. Guest revocation and logout cookie clearing stay with R15. | Sprint 41 for production email and session secrets only | Leave Sprint 27 closed. Reconcile `docs/SECURITY_MODEL.md` in a later doc pass. Do not reopen Sprint 27. |
| R3 | Headers/CSP/CORS/CSRF policy completion | PARTIAL | `DEFAULT_SECURITY_CSP` in `app/core/config.py` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` also sets `nosniff`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS on staging and production. `SECURITY_CSP` can still replace the default. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes missing or untrusted `Origin` on `COOKIE_AUTHORIZED_MUTATION_PATHS` when the owner cookie is present, and always on `POST /account/clear-device`. Trusted origins come from `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS`. `SameSite=lax` remains. `CsrfTokenService.validate` is still not called by any route. Preference routes in `PREFERENCE_COOKIE_MUTATION_PATHS` are outside the origin policy. FastAPI `/docs` and `/redoc` stay enabled outside production and are incompatible with the strict CSP. `/openapi.json` remains usable. That incompatibility does not reopen the CSP finding. | `tests/unit/test_sprint40_6_csp.py`, `tests/unit/test_sprint40_4_cookie_origin.py`, `tests/unit/test_sprint22_api.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | None on this SHA. The origin policy and the strict CSP have not been exercised on staging. | None | No for the default CSP or the Sprint 40.4 origin set. Later work can lock `SECURITY_CSP` and cover preference-cookie mutations. Not this slice. | None | Keep the CSP and origin MEDIUMs at IMPLEMENTED-NOT-PROVEN. Do not remove `SameSite=lax`. Do not require interactive docs to satisfy the CSP. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | PARTIAL | `app/security/url_trust.py` separates `validate_server_fetch_url` (https only; numeric private, loopback, link-local, and metadata hosts rejected) from `validate_browser_destination` (http or https; private hosts allowed because the server does not fetch them). Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend `_default_http_post` accepts only the pinned Resend URL and sets `follow_redirects=False`. Live Shopify stays fail-closed (`SHOPIFY_LIVE_CALL_PERMITTED` is false). Browser merchant links are not restricted to a merchant-host allowlist. DNS rebinding is documented as out of scope. `_safe_next` keeps account and consumer redirects on local prefixes. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Request-path SQL found is ORM or constant `SELECT 1`. No current repository evidence proves a reachable SSRF. | `tests/unit/test_sprint40_5_url_trust.py`. No dedicated open-redirect test was found. | None on this SHA | None | No new SSRF slice. A merchant-host allowlist for browser links is a product choice and is not selected. | Sprint 38 and Sprint 41 keep live fetch and production network controls. They do not own this validation gap. | Do not open routing or call Shopify. Do not record a historical SSRF exploit. Staging proof of the server-fetch policy is still absent. |
| R5 | Log redaction; body logging policy; PII handling | PARTIAL | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body or the owner cookie. `app/launch/redaction.py` redacts secret-like keys. Auth audit metadata can still record email on login failure, rate limit, registration, and password reset. Product analytics forbids question, query, answer, message, session id, and conversation id. Account export and deletion remain Sprint 28. | `tests/unit/test_sprint21_analytics_admin.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` `test_server_identity_is_opaque_and_ask_text_is_absent` | None on this SHA for a log sample | None | No new redaction slice. R18 covers conversation bodies and session ids in routine logs and analytics. | Sprint 28 owns account export and deletion. Sprint 39 owns product-analytics privacy. | Do not copy audit emails into product analytics. A staging log sample is operational evidence, not this slice. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | Secrets: `scripts/secret_scan_25a.py` runs in `.github/workflows/ci.yml` and scans infra, env examples, scripts, and workflows. It does not scan `app/`. Dependency: `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1 against the frozen `uv.lock` closure. `tests/security/baselines/pip-audit.baseline.json` has an empty exception list. CI #477 reported 71 packages, 0 vulnerabilities, 0 exceptions. SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`. Ruff is a lint gate, not SAST. Container: the CI image job builds and smoke-imports. `build-image.yml` publishes a digest. Neither scans the image. Terraform: `terraform fmt` and `terraform validate` run. That is syntax validation, not IaC security scanning. No tfsec or Checkov config was found. The requirement is the five capability classes, not the product names Dependabot, CodeQL, and Trivy. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #477 is a clean pip-audit and secret-scan run on this SHA. It is not a SAST, container-scan, or IaC-security result. | None | Yes, later. The smallest missing class, if a scanner slice is chosen, is SAST: static security analysis of `app/` with an explicit baseline. Not this slice. | None for adding the gate. Sprint 41 does not own CI scanners. | Do not install SAST, container scanning, and IaC security scanning as one change. Do not weaken the secret scan or pip-audit. |
| R7 | Supply-chain provenance checks; immutable image authority verification | PARTIAL | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, and states that mutable tags are not deployment authority. No cosign, SLSA, or signed provenance attestation was found. | `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum and locks the immutable tag. | Build Image #170 succeeded for this SHA. That shows the publish workflow completed. It is not a signed provenance attestation. | None. Production pull and IAM review remain Sprint 41. | No. Digest publication already exists. Signed provenance is a later decision, not this slice. | Sprint 41 for production image pull | Do not treat Build Image #170 as Sprint 40 closure. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | PARTIAL | Staging and production must use `SqlRateLimitStore` on PostgreSQL. `RATE_LIMIT_BACKEND=memory` is rejected there. Development defaults to the in-process store. There is no silent fallback from PostgreSQL to memory. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified bearer session or account owner cookie. That authenticated-principal bucket is shared in staging and production. A guest session id is not a rate-limit key. Auth failures use a separate `auth` scope keyed by an HMAC of the normalized email or account id, 20 attempts per 60 seconds, also on the shared store in staging and production. Client IP walks `X-Forwarded-For` only when the socket peer is in `TRUSTED_PROXY_CIDRS`. The per-email auth window is a beta-level throttle for guessing one account: extra source IPs and extra processes do not multiply that budget. It is not a bot challenge, not click-fraud detection, and not account lockout. Affiliate routes use the affiliate bucket only. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_3_trusted_proxy_client_ip.py`, login rate-limit tests in `tests/unit/test_user_platform_auth_service.py` | None on this SHA. Required staging evidence is "Abuse controls exercised". That evidence is absent. | None | No new distributed-counter slice. Bot detection and click-fraud scoring remain absent and are not this slice. The in-process HIGH is IMPLEMENTED-NOT-PROVEN, not closed. | Sprint 43 owns cache and capacity depth. Sprint 40 still owns the beta abuse decision. The absence of Redis does not move this row. | Do not mark the HIGH closed. Do not add a WAF, CAPTCHA, or click-fraud score in this audit. |
| R9 | Account lockout or equivalent | PARTIAL | No `locked_until` or failed-login lock field was found. `SqlRateLimitStore._consume_once` deletes rows whose `expires_at_ms` is already past and then inserts a new row at `hits=1`. `AuthService.login` consumes the shared auth key before the password check and calls `reset` only after success. When every attempt fails, the 60-second expiry deletes the row. The next attempt starts over. The HTTP `login` bucket is 10 requests per 60 seconds per trusted client IP and is not reset on success. Distributing source IPs multiplies that HTTP bucket. It does not multiply the email auth counter. Neither window is a lock that remembers failures after it expires. | Login rate-limit tests in `tests/unit/test_user_platform_auth_service.py` and the Sprint 40.3 shared-store tests show the window and the success reset. They do not show a lock that survives expiry. | None | None | Yes. This is the selected slice. A lockout that only lives in process memory would not meet this row. | None | Implement the selected slice. Do not call the shared windows a completed lockout. Do not add CAPTCHA or a WAF. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings and is called on the cleaned user query in `ShoppingAssistantService.query`. A match adds a warning. Deterministic ranking still runs. Merchant text, reviews, and tool results are not passed through that function. `build_shopping_prompts`, review `build_analysis_prompt`, and `build_community_prompts` put catalog, review, and community text in the user JSON. The system string says not to follow instructions found in that text. That is a role split plus a warning, not a structural isolation boundary. Default transports are `DisabledTransport`. AI flags default off. No model-chosen tool loop was found. Shopify catalog tool names in `live_start_claim` are a fixed contract and do not perform HTTP. | `tests/unit/test_shopping_assistant_service.py` `test_prompt_injection_resistance`, `tests/unit/test_shopping_assistant_intent.py` `test_prompt_injection_detection` | None | None | Yes, later, as one bounded isolation or review change. Not this slice. Three prompt builders must not be rewritten together. | Sprint 13 owns assistant fallback. Sprint 40 owns the review. Sprint 38 owns live research and stays fail-closed. | Leave the six-marker list unchanged in the selected slice. Do not enable a provider to test it. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | MISSING | No pen-test checklist, security incident-response runbook, vulnerability-response process, or security go/no-go draft suitable for Sprint 44 was found. `docs/SECURITY.md` is the Sprint 22 control note. `docs/SECURITY_MODEL.md` is the Sprint 17 model. Sprint 42 operational paging is not this package. | None | None | None | Yes. This documentation package remains Sprint 40 work. It is not the selected slice. The public login gap outranks it. | Sprint 42 owns operational probes, alerts, paging, and incident operations. Sprint 40 still owns this package and the security go/no-go draft. | Write the package after the selected slice. Do not move it to Sprint 42. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH and the four Sprint 40 MEDIUMs are reconciled in the findings section. No written risk acceptance exists. Sprint 41 and Sprint 42 HIGHs remain open and are not Sprint 40 engineering. The expiring login budget is an Included-requirement gap. This audit does not assign it a new HIGH or MEDIUM. | Tests cited on the individual findings do not close them. Staging proof is absent. | None that exercises abuse controls or the new policies | None | Yes, as a closure gate. Not one code change. | Sprint 41 and Sprint 42 for the HIGHs they own | Do not mark Sprint 40 closed. Do not risk-accept an open finding in this audit. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Decision contexts cannot be stored without an owner. `ConversationContext.__post_init__` raises when `decision_context` is set and `owner` is `None`. Decision reads, overlays, and pending proposals require a verified owner, as recorded on R1. A cookieless `POST /api/v1/shopping-assistant/query` with no `decision_id` still calls `create(owner=None)` and then `append_turn` on that new server id. That is the merged Sprint 40.1 anonymous contract. The endpoint does not call `ensure_guest_owner_cookie`. The stored row has no decision context. `get_for_owner` returns nothing when the stored owner is null, so the same caller cannot continue it and a different caller cannot read it. Repository `append_turn` can still materialize an ownerless row when the id is missing. The three service callers do not pass a client id into that branch: they create first, or they `get_for_owner` first. `live_start_claim` refuses an ownerless conversation. `advance_verified_research_context` requires a matching owner. | `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row`, `test_foreign_conversation_id_cannot_read_or_append_prior_turns`, and the Sprint 40.7 ownerless decision-path negatives. No test shows a public request binding a decision to an ownerless row. | Sprint 29 guest-claim staging notes are historical and were not re-run. | None | No. Closing the literal "every conversation" sentence would change the Sprint 40.1 anonymous contract. That is a product and security decision. It is not the selected slice. | None | Do not select ownerless `create` only because the repository permits `owner=None`. Do not change anonymous create in this audit. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | IMPLEMENTED-NOT-PROVEN | On the non-decision path, body `conversation_id`, `user_id`, and `profile_id` are lookup hints. Authority is the verified owner. History is written only for `_authorized_account_user_id`. A body profile personalizes only when it is already bound to that account. On the decision path, body `conversation_id`, `decision_id`, and `context_version` are lookup values under the verified request owner. Affiliate link decoration can still copy a body `user_id` into an affiliate `sub_id` on the non-decision path. Affiliate activation stays off, and that copy does not read or authorize another owner's conversation, profile, decision, or history. It is not an authorization path. | Non-decision negatives in `tests/unit/test_sprint40_assistant_body_identity.py`. Decision-path negatives in `tests/unit/test_sprint40_7_decision_path_owner_binding.py`. `test_bound_conversation_answers_from_snapshot` is now the ownerless negative. `test_verified_owner_bound_conversation_answers_from_snapshot` is the positive case. | None | None | No new authorization slice. Remaining proof is staging. | None | Do not weaken Sprint 40.1 or Sprint 40.7. Do not treat the affiliate `sub_id` copy as an authorization bug. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256. Expiry is seven days and is checked in `parse_owner_cookie`. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie, so it does not rotate. A copied cookie works until expiry because there is no revocation list. UI sign-out calls logout and then `POST /account/clear-device`. Logout itself does not clear the owner cookie. `claim_guest_conversation` rebinds and rotates to the account owner only when no canonical UUID snapshot exists. When one exists, the function returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. The function comment says replacing the cookie would hide the decision. | `tests/unit/test_sprint29_owner_cookie_auth.py`, `tests/unit/test_sprint29_guest_claim.py`, `tests/unit/test_sprint27_4_auth_aware_header.py` | Sprint 29 staging logout and `clear-device` notes were not re-run on this SHA. | None | No, until a product decision. This audit does not change snapshot immutability. | None. Snapshot immutability is already implemented. | Decide whether canonical snapshots stay immutable, or whether guest-to-account transition must rotate credentials and still show the decision. Do not implement either choice here. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement is the Sprint 40.4 control for the decision-owner cookie paths and `POST /account/clear-device`. Missing Origin is fail-closed. Bearer-only requests are unchanged. Preference-cookie mutations are not covered. The CSRF token is still not enforced. HTTP rate-limit identity is the trusted client IP, or an account HMAC when the bearer session or account owner cookie is verified. That account key is shared in staging and production. A guest session id is not a rate-limit key. Guest traffic uses the IP bucket. Auth email windows are separate and shared in staging and production. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests. No per-session bucket test exists because that key is absent. | None. Staging has not exercised the origin policy or the shared limiter. | None | Per-session limiting is later. Not this slice. The origin MEDIUM stays IMPLEMENTED-NOT-PROVEN. | None | Do not treat the shared IP and account buckets as per-session limits. Do not call the origin policy PROVEN. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | PARTIAL | Research confirmation derives `research-auth:<sha256>` from the owner binding, conversation, decision, proposal, and scope. The client confirmation token is ignored as execution identity. A repeated confirmation of the same proposal reuses that key. `prepare_confirmed_research` keys execution off that server authorization. Ordinary non-decision `append_turn` has no idempotency key. A repeated assistant query appends another turn. An authorized account records recommendation history again. `emit_ask_product_events` records `ask_question_submitted` and, when applicable, an answered or insufficient-evidence event on every request. The query path does not write a feedback record. A repeated research-need question while a proposal is pending mints a new `proposal_id` and increments `proposal_version`. A repeated explicit confirmation does not mint a second authorization. Live research stays fail-closed, so the retry does not spend a provider call. | `tests/unit/test_research_authorization_handoff.py` `test_idempotency_key_is_server_derived` and `test_repeat_confirmation_reuses_same_authorization`. Sprint 38 execution tests cover the research key. No message-replay test. | None | None | Yes, later, for ordinary assistant message submission only. | Sprint 38 owns research-execution consumption. That server key is already present. | Do not reopen Sprint 38. Do not select message idempotency ahead of the login lock. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, or a session id. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. Recommendation history stores the query only for `_authorized_account_user_id`. That store is the account's own history, not `product.analytics_events` and not the request log. The Sprint 40.1 body-`user_id` history write is gone. Sprint 40.7 does not add conversation text or session ids to those sinks. | `test_server_identity_is_opaque_and_ask_text_is_absent` and the Sprint 40.1 history tests | None on this SHA for a log or analytics sample | None | No. Remaining proof is a staging sample, not more application code. | Sprint 39 owns the analytics forbid-list. | Do not put conversation text into `product.analytics_events`. Do not call this row PROVEN. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are the same facts as R3 and R4. The six injection markers and the user-prompt embedding are the same facts as R10. Assistant, review, community, answer, refinement, and research processing set `secrets_included` and `prompts_included` false. Provider prompts can include merchant and review text when the corresponding AI flag and transport are enabled. Default transports do not make those calls. `AI_MAX_ESTIMATED_COST_PER_REQUEST` exists on the review, shopping, and community provider wiring. Live research remains fail-closed, so confirmation does not spend a provider call today. Fail-closed research is not a cost limit that would hold if live research were opened. No model-driven tool invocation was found. | `test_no_secrets_in_response_processing`, `test_prompt_injection_resistance`, `tests/unit/test_sprint40_6_csp.py` | None | None | No slice that enables live research or a provider. The written review is R10 and is later. | Sprint 38 owns live research execution and stays fail-closed. | Do not enable live research to test cost controls. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | PARTIAL | This matrix is the coverage review. Private decision routes set `noindex`, and `robots.txt` disallows `/results/`, `/compare/`, `/why-best-piq/`, and `/account`. Affiliate click storage exists. Click-fraud detection does not. Tool-abuse controls beyond the injection warning were not found. Credential stuffing has the shared per-email window and does not have a lockout. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py` | No fresh staging crawl was run. | None | No as a separate row. The open parts are the rows above, especially R6, R9, and R11. | Sprint 29 owns the SEO implementation. | Do not reopen Sprint 29. Do not enable affiliate tracking. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same open findings as R12. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | None | Yes, as the same closure gate | Sprint 41 and Sprint 42 for findings they own | Do not start Sprint 45. |

## What moved, and what did not

Sprint 40.7 is confirmed on this tree. Answer-from-evidence, session refinement, and research proposal no longer adopt `context.owner` from a body `conversation_id`. Owner-bound overlays and pending proposals are not loaded from an unverified body id. Sprint 40.1 non-decision behavior is unchanged: a foreign body id is not continued, and a new non-decision conversation uses the verified owner when one exists.

R1 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The object-level defect named on 2026-10-10 is closed in code and tests. No staging exercise exists, so the row is not PROVEN.

R14 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN for the same reason. The affiliate `sub_id` copy of a body `user_id` remains, with affiliate activation off. It does not authorize a read.

R13 stays PARTIAL. The decision-path half is implemented. The remaining gap is the Sprint 40.1 anonymous non-decision contract, not a reachable decision-context defect. See the ownerless section. It is not the selected slice.

R18 stays IMPLEMENTED-NOT-PROVEN. Sprint 40.7 did not add conversation bodies or session ids to routine logs or product analytics. No staging sample exists.

R6, R8, R9, R10, R11, R15, R16, and R17 stay at the classes recorded above after a fresh read. R11 stays MISSING. No row is PROVEN.

## Sprint 40.7 recheck

| Check | Result |
|-------|--------|
| Answer-from-evidence adopts `context.owner` from a body `conversation_id` | No. `_resolve_packet` uses `get_for_owner` only when the request owner is present. The snapshot read uses that request owner. |
| Session refinement does it | No. Same rule in `RefineSessionRecommendationService._resolve_packet` and `_existing_overlay`. |
| Research proposal does it | No. `ProposeResearchService._resolve_packet` no longer has an unscoped branch. `_bound_context` returns nothing when the request owner is missing. |
| Owner-bound overlays and pending proposals load from an unverified body id | No. Both lookups require `get_for_owner` or `find_bound_for_owner`. |
| Sprint 40.1 non-decision behavior | Intact. `_owned_conversation_context` still refuses a foreign or ownerless id. |
| `self._conversations.get(` in the three decision services | Absent. The remaining unscoped `get` calls are inside repository methods and `live_start_claim`, which then refuse a null or mismatched owner. |

The Sprint 40.7 record's classes for these four rows match this tree: R1 IMPLEMENTED-NOT-PROVEN, R13 PARTIAL, R14 IMPLEMENTED-NOT-PROVEN, R18 IMPLEMENTED-NOT-PROVEN. This audit agrees with those four classes and does not treat the rest of that record as a reason to skip the other rows.

## Ownerless conversations

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
| Dependency | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. CI #477: 71 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Absent | No CodeQL, Bandit, or Semgrep gate over `app/`. |
| Container | Absent | Image build, smoke import, and digest publication do not scan the image. Build Image #170 is not a vulnerability scan. |
| Terraform / IaC security | Absent | `terraform fmt` and `terraform validate` are present. They are not security scanning. |

The smallest missing class, if a later scanner slice is chosen, is SAST. It is not the selected slice. One scanner class must not be bundled with the others.

## Login, credential stuffing, and lockout

These are separate controls.

| Control | Current state |
|---------|----------------|
| Distributed rate limiting | Present for staging and production on PostgreSQL. Authenticated principals use `acct:<hmac>` and share that counter across processes. Development stays in-process. Not staging-proven. |
| Brute-force / credential-stuffing throttle | Present as the shared `auth` scope, HMAC of the normalized email, 20 attempts per 60 seconds, plus the HTTP `login` bucket at 10 per 60 seconds per trusted IP. Extra IPs do not multiply the email budget. Extra processes do not multiply it in staging or production. Success resets the email key only. This is a beta-level throttle for one account. It is not a lockout. |
| Account lockout or equivalent | Absent. Window expiry deletes the counter. Failures are forgotten. No `locked_until`. |
| Bot challenge | Absent. Repository evidence does not show that CAPTCHA or a WAF is required. Full WAF/CDN remains a non-goal. |
| Click-fraud detection | Absent. Affiliate click storage is not detection. Affiliate activation stays off. |

The shared windows satisfy the beta-level single-account stuffing throttle. They do not satisfy R9. R8 stays PARTIAL because bot controls and click-fraud detection are still absent, and because staging has not exercised the limiter.

## Prompt injection, merchant content, and cost

The six-marker warning is detection. It runs on the shopper query only. A match adds `prompt_injection_resistance` and deterministic ranking continues.

Merchant catalog text, review text, and community evidence can enter the user prompt of `build_shopping_prompts`, `build_analysis_prompt`, and `build_community_prompts` when those AI flags and transports are enabled. Instructions sit in the system string, including a sentence that says not to follow instructions in the untrusted text. The untrusted payload is JSON in the same user message. That is not structural separation.

External responses mark `secrets_included` and `prompts_included` false. `AI_MAX_ESTIMATED_COST_PER_REQUEST` is wired and was not treated as a live cost proof. Live research and live Shopify stay fail-closed. This audit did not enable a provider.

Tool names on the Shopify anonymous catalog contract are fixed. They are not chosen by a model from shopper, merchant, or review text, and that contract does not perform HTTP.

## Message idempotency

Research confirmation already derives its execution identity on the server and ignores the client confirmation token. A second confirmation of the same proposal reuses the authorization. Sprint 38 research-execution consumption of that key stays as it is. This audit does not reopen Sprint 38.

A browser retry of an ordinary assistant query can:

- append another turn for the same verified owner
- record recommendation history again for an authorized account
- emit another `ask_question_submitted` analytics event, and another answered or insufficient-evidence event when that status applies

The query path does not write feedback. A retry of a research-need question can mint a new proposal id and version while one is pending. A retry of the confirmation does not create a second authorization and does not start live research.

That gap is R17. It is later than the login lock, because it does not disclose another owner's decision and does not guess a password.

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

Sprint 42 owns production probes, alerts, paging, and operational incident operations. It does not receive this package by default. The package is entirely missing. It does not outrank the login lock, because a document does not stop password guessing on the public login route. It remains Sprint 40 work after the selected slice.

## Historical finding reconciliation

These notes are additive. They do not rewrite the Sprint 30 map or section I of the gap inventory.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. Shared counters do not add bot detection, click-fraud scoring, durable lockout, or a per-session bucket. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. `CsrfTokenService` is still unused on routes. Preference-cookie routes are outside the policy. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. `SECURITY_CSP` can still override the default. FastAPI `/docs` and `/redoc` are incompatible with the strict policy when they are enabled. `/openapi.json` remains usable. That incompatibility does not reopen the finding. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the dependency class. SAST, container scanning, and IaC security scanning STILL OPEN | pip-audit 2.10.1 is a required CI gate. CI #477 reported 71 packages, 0 vulnerabilities, and 0 exceptions. The historical sentence is no longer a total absence. Dependabot, CodeQL, and Trivy remain absent. Their absence is not, by itself, the Sprint 40 requirement. Secrets scanning remains present. `terraform validate` remains syntax validation. A successful Docker build is not container vulnerability scanning. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. This audit does not claim a historical reachable SSRF. Staging has not exercised the policy. Browser links are not a merchant-host allowlist. The finding is not closed and not PROVEN. |

No new HIGH is assigned. No MEDIUM is relabeled launch-blocking. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## Duplicated requirements

- R12 and R21 are the same closure gate. R21 adds the Sprint 45 deadline.
- R3 and R16 both include the origin policy. R16 also requires per-session, per-IP, and authenticated-principal limits. Per-IP and account limits exist and are shared in staging and production. Per-session limits do not.
- R4 and R19 both include encoding and XSS. R19 adds external-model minimization and cost.
- R5 and R18 both include logs. R18 is the conversation-body and session-id sentence, and it stays IMPLEMENTED-NOT-PROVEN.
- R1 and R14 now share the implemented owner-binding rule. R13 still includes the anonymous non-decision contract.
- R8 and R9 are not the same control. R8's shared per-email window is the beta stuffing throttle. R9 is the missing lock. Bot challenge and click-fraud sit in R8 and R20 and are not lockout.
- R10 and the prompt-injection clauses of R19 and R20 are one review. That review is not written, and the six markers are not isolation.

## Sprint 41 work, not this slice

- Production VPC, database, secrets, IAM, OIDC, deploy, rollback, DNS, and TLS.
- Production IAM review.
- Production image pull. Build Image #170 does not start that review.
- The HIGHs for production isolation and production OIDC/SSM.

Sprint 41 stays UNSTARTED. This audit does not start it.

## Sprint 42 work, not this slice

- CloudWatch and security paging.
- Operational incident response, probes, alerts, and paging runbooks.

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R11 is missing. R9 is still PARTIAL on a repository-backed login path. R6, R8, R10, R13, R16, and R17 still have repository-backed gaps. R15 still needs a product decision. Staging proof is absent even for the controls that are implemented. Those facts are not all proof that belongs to staging, Sprint 41, Sprint 42, or Sprint 44.

The guest-rebind acceptance conflict is not selected. It still needs a product decision. Anonymous `create(owner=None)` is not selected. It does not expose a decision context, and changing it conflicts with the merged Sprint 40.1 contract.

**Slice:** Failed logins must stay limited after the shared auth window expires.

Current defect, from repository code:

- `app/infrastructure/database/rate_limit_store.py` deletes an expired counter and starts the next attempt at one hit.
- `app/auth/service.py` `login` keys failures by the normalized email HMAC, allows 20 attempts per 60 seconds on the `auth` scope, and resets that key only after success.
- `app/launch/rate_limit_backend.py` attaches that hook to the shared PostgreSQL store in staging and production. Development keeps a private in-memory hook.
- After a minute of failures, the account can be guessed again at the full budget, from any set of source IPs.
- The HTTP login bucket remains a per-IP limit. It is not the lock.

**Likely files for the later slice:**

- `app/auth/service.py`
- `app/auth/security.py`
- `app/launch/rate_limit_backend.py`
- `app/infrastructure/database/rate_limit_store.py`, only if the existing consume/reset API cannot remember failures past the window
- `tests/unit/test_user_platform_auth_service.py`
- `tests/unit/test_sprint40_3_distributed_rate_limit.py`

**Acceptance tests for the later slice:**

1. Failed logins for one email, continued after the 60-second auth window and from more than one process or source address, do not receive a fresh full budget solely because the window expired.
2. A successful login clears that email's failure memory.
3. Unknown-email and bad-password responses stay the same text. The control must not reveal whether the account exists.
4. Staging and production keep the shared store. A store failure still denies the attempt. There is no memory fallback.
5. Sprint 40.1 non-decision tests, Sprint 40.7 owner-binding tests, and research-confirmation idempotency stay as they are. Live research stays disabled. Canonical snapshot immutability stays unchanged.

**Out of scope for the slice:** SAST, container scanning, IaC security scanning, bot challenge, CAPTCHA, WAF, click-fraud detection, message idempotency, prompt isolation, the pen-test package, guest rebind, anonymous ownerless create, CSP, origin policy, per-session rate limits, affiliate activation, Shopify calls, routing, and any deploy.

## Why this slice outranks the other gaps

The public login route accepts a fresh 20-attempt email budget every time the shared counter expires. Source IP distribution does not reduce that email budget, and it also does not stop the budget from returning. That is indefinite online guessing of one account. The existing window is already the beta stuffing throttle, so this slice does not rebuild rate limiting. It adds the missing memory.

SAST is the smallest missing scanner class and is the right choice if the next slice is a scanner. It does not stop this login path. Container scanning and IaC security scanning are separate absences and are not bundled with it. A successful image build and `terraform validate` do not fill them.

The security package is entirely missing and stays Sprint 40 work. It does not change login behavior, so it waits.

Message retries duplicate the caller's own turns, history, and ask analytics. Research confirmation already reuses a server key. That integrity gap does not guess a password.

Prompt isolation is real and incomplete. The model path is off by default, live research is fail-closed, and covering shopping, review, and community prompts is not one bounded change.

The ownerless conversation path cannot carry a decision. Selecting it would decide the Sprint 40.1 anonymous contract. Guest-to-account rebind of a canonical snapshot is the same kind of undecided conflict.

Bot challenge and click-fraud detection are different controls. This repository does not show that a WAF or CAPTCHA is required. Affiliate activation stays off.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No reachable public path that creates, continues, reads, or mutates a sensitive decision context through an ownerless conversation.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No pen-test report or written risk acceptance.
