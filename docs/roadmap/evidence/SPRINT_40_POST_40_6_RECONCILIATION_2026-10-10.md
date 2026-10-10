# Sprint 40 post-40.6 reconciliation — 2026-10-10

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Decision-path body `conversation_id` must not adopt the stored owner.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.6 are merged. This change is a reconciliation audit only. It does not assume a Sprint 40.7 implementation exists.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `483d30a91f70167656b51f976ffb2bb3521a0b7e`

**Post-merge evidence on that SHA:** CI #472 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38035626154`). Full pytest on that run: 4388 passed, 5 skipped. The pip-audit gate on that run reported 71 packages, 0 vulnerabilities, 0 exceptions. Build Image #168 succeeded (`https://github.com/markbilbao/dealbrain/actions/runs/38036114733`). Those runs are publication and test evidence for the merged tree. They are not a staging abuse exercise, a signed provenance attestation, or a security go/no-go.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical audit, not carried forward:** [`SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md`](SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md). That audit started at `0452c40610ac61cd9dce4af361718cb4fd2c02d7`, before Sprint 40.1 through Sprint 40.6. Its matrix classes stay in that file. This reconciliation re-reads the tree at `483d30a91f70167656b51f976ffb2bb3521a0b7e` and classifies R1–R21 again.

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
| IMPLEMENTED-NOT-PROVEN | 1 (R18) |
| PARTIAL | 19 (R1–R10, R12–R17, R19–R21) |
| MISSING | 1 (R11) |
| BLOCKED-DEPENDENCY | 0 |
| NOT-APPLICABLE | 0 |

## Requirement matrix

| ID | Requirement | Class | Current code evidence | Current test evidence | Staging evidence | Production evidence | Sprint 40 engineering still required | Dependency owner | Exact next action |
|----|-------------|-------|------------------------|-----------------------|------------------|---------------------|--------------------------------------|------------------|-------------------|
| R1 | AuthN/AuthZ/object-level review | PARTIAL | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot repository reads use `get_for_owner`. Non-decision `ShoppingAssistantService.query` continues a conversation only through `_owned_conversation_context` → `get_for_owner`, and loads profiles only through `_authorized_account_user_id`. Decision answer and session refinement still call `ConversationRepository.get(conversation_id)` and then set `bound_owner = context.owner` before `snapshots.get_for_owner`. The services are `AnswerFromEvidenceService` and `RefineSessionRecommendationService`. A body `conversation_id` therefore selects the owner used to read a UUID snapshot. `ProposeResearchService._resolve_packet` uses `get_for_owner` when a request owner is present, and uses `get` plus the stored owner when the request owner is missing. | `tests/unit/test_sprint40_assistant_body_identity.py` rejects a foreign non-decision `conversation_id`, body `user_id`, and unbound `profile_id`. `test_decision_bound_foreign_owner_still_fails_closed` rejects owner B reading owner A's snapshot when B's own conversation is not bound to that snapshot. `tests/unit/test_phase_29_4a_answer_from_evidence.py` `test_bound_conversation_answers_from_snapshot` answers from a snapshot when the body supplies only `conversation_id` and no request owner. | None on this SHA | None | Yes. The decision-path read is the selected slice. | None | Implement the selected slice. Do not treat the non-decision tests as coverage of answer-from-evidence or refinement. |
| R2 | Session security review | PARTIAL | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. Expiry and revocation are checked in `AuthService.validate_session`. Password reset and email change call `revoke_all_for_user`. Guest `principal_id` and `session_id` are `uuid4`. The owner cookie is HMAC-SHA256, expires in seven days, and is `HttpOnly` plus `SameSite=lax`, with `Secure` in staging and production. There is no server-side guest revocation list. `POST /api/v1/auth/logout` revokes the bearer session and does not clear the owner cookie. `docs/SECURITY_MODEL.md` still describes Sprint 17 demo session limits. | `tests/unit/test_user_platform_security.py`, `tests/unit/test_user_platform_auth_service.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | Sprint 27 and Sprint 29 session notes are historical and were not re-run on this SHA | None. Production secret attach remains Sprint 41 | No new session-crypto slice. Guest revocation and logout cookie clearing stay with R15. | Sprint 41 for production email and session secrets only | Leave Sprint 27 closed. Reconcile `docs/SECURITY_MODEL.md` in a later doc pass. Do not reopen Sprint 27. |
| R3 | Headers/CSP/CORS/CSRF policy completion | PARTIAL | `DEFAULT_SECURITY_CSP` in `app/core/config.py` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` also sets `nosniff`, `X-Frame-Options`, Referrer-Policy, Permissions-Policy, and HSTS on staging and production. `SECURITY_CSP` can still replace the default. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes missing or untrusted `Origin` on `COOKIE_AUTHORIZED_MUTATION_PATHS` when the owner cookie is present, and always on `POST /account/clear-device`. Trusted origins come from `PUBLIC_APP_BASE_URL` and `CORS_ORIGINS`. `SameSite=lax` remains. `CsrfTokenService.validate` is still not called by any route. Preference routes in `PREFERENCE_COOKIE_MUTATION_PATHS` are outside the origin policy. FastAPI `/docs` and `/redoc` stay enabled outside production and are incompatible with the strict CSP. `/openapi.json` remains usable. That incompatibility does not reopen the CSP finding. | `tests/unit/test_sprint40_6_csp.py`, `tests/unit/test_sprint40_4_cookie_origin.py`, `tests/unit/test_sprint22_api.py`, `tests/unit/test_sprint29_owner_cookie_auth.py` | None on this SHA. The origin policy and the strict CSP have not been exercised on staging. | None | No for the default CSP or the Sprint 40.4 origin set. Later work can lock `SECURITY_CSP` and cover preference-cookie mutations. Not this slice. | None | Keep the CSP and origin MEDIUMs at IMPLEMENTED-NOT-PROVEN. Do not remove `SameSite=lax`. Do not require interactive docs to satisfy the CSP. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | PARTIAL | `app/security/url_trust.py` separates `validate_server_fetch_url` (https only; numeric private, loopback, link-local, and metadata hosts rejected) from `validate_browser_destination` (http or https; private hosts allowed because the server does not fetch them). Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend `_default_http_post` accepts only the pinned Resend URL and sets `follow_redirects=False`. Live Shopify stays fail-closed (`SHOPIFY_LIVE_CALL_PERMITTED` is false). Browser merchant links are not restricted to a merchant-host allowlist. DNS rebinding is documented as out of scope. `_safe_next` keeps account and consumer redirects on local prefixes. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. Request-path SQL found is ORM or constant `SELECT 1`. No current repository evidence proves a reachable SSRF. | `tests/unit/test_sprint40_5_url_trust.py`. No dedicated open-redirect test was found. | None on this SHA | None | No new SSRF slice. A merchant-host allowlist for browser links is a product choice and is not selected. | Sprint 38 and Sprint 41 keep live fetch and production network controls. They do not own this validation gap. | Do not open routing or call Shopify. Do not record a historical SSRF exploit. Staging proof of the server-fetch policy is still absent. |
| R5 | Log redaction; body logging policy; PII handling | PARTIAL | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body or the owner cookie. `app/launch/redaction.py` redacts secret-like keys. Auth audit metadata can still record email. Product analytics forbids question, query, answer, message, session id, and conversation id. Account export and deletion remain Sprint 28. | `tests/unit/test_sprint21_analytics_admin.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` `test_server_identity_is_opaque_and_ask_text_is_absent` | None on this SHA for a log sample | None | No new redaction slice. R18 covers conversation bodies and session ids in routine logs and analytics. | Sprint 28 owns account export and deletion. Sprint 39 owns product-analytics privacy. | Do not copy audit emails into product analytics. A staging log sample is operational evidence, not this slice. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | Secrets: `scripts/secret_scan_25a.py` runs in `.github/workflows/ci.yml` and scans infra, env examples, scripts, and workflows. It does not scan `app/`. Dependency: `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1 against the frozen `uv.lock` closure. `tests/security/baselines/pip-audit.baseline.json` has an empty exception list. CI #472 reported 71 packages, 0 vulnerabilities, 0 exceptions. SAST: no CodeQL, Bandit, or Semgrep workflow scans `app/`. Ruff is a lint gate, not SAST. Container: the CI image job builds and smoke-imports. `build-image.yml` publishes a digest. Neither scans the image. Terraform: `terraform fmt` and `terraform validate` run. That is syntax validation, not IaC security scanning. No tfsec or Checkov config was found. The requirement is the five capability classes, not the product names Dependabot, CodeQL, and Trivy. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #472 is a clean pip-audit and secret-scan run on this SHA. It is not a SAST, container-scan, or IaC-security result. | None | Yes, later. The smallest missing class is SAST: static security analysis of `app/` with an explicit baseline. Not this slice. | None for adding the gate. Sprint 41 does not own CI scanners. | After the selected slice, add one SAST gate. Do not install Dependabot, CodeQL, and Trivy as one change. Do not weaken the secret scan or pip-audit. |
| R7 | Supply-chain provenance checks; immutable image authority verification | PARTIAL | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, and states that mutable tags are not deployment authority. No cosign, SLSA, or signed provenance attestation was found. | `tests/unit/test_sprint25b1_image_publication.py` rejects a tampered manifest checksum and locks the immutable tag. | Build Image #168 succeeded for this SHA. That shows the publish workflow completed. It is not a signed provenance attestation. | None. Production pull and IAM review remain Sprint 41. | No. Digest publication already exists. Signed provenance is a later decision, not this slice. | Sprint 41 for production image pull | Do not treat Build Image #168 as Sprint 40 closure. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | PARTIAL | Staging and production must use `SqlRateLimitStore` on PostgreSQL. `RATE_LIMIT_BACKEND=memory` is rejected there. Development defaults to the in-process store. There is no silent fallback from PostgreSQL to memory. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified account. Auth windows are a separate scope keyed by normalized email or account id. Client IP walks `X-Forwarded-For` only when the socket peer is in `TRUSTED_PROXY_CIDRS`. No bot challenge, no click-fraud score, and no credential-stuffing control beyond those windows were found. Affiliate routes use the affiliate bucket only. Distributed counters are not complete abuse protection. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_3_trusted_proxy_client_ip.py` | None on this SHA. Required staging evidence is "Abuse controls exercised". That evidence is absent. | None | Yes, later, for bot, click-fraud, and stuffing controls beyond the shared windows. Not this slice. The in-process HIGH is IMPLEMENTED-NOT-PROVEN, not closed. | Sprint 43 owns cache and capacity depth. Sprint 40 still owns the beta abuse decision. The absence of Redis does not move this row. | Do not mark the HIGH closed. Do not add a WAF in this audit. |
| R9 | Account lockout or equivalent | PARTIAL | No `locked_until` or failed-login lock field was found. The current equivalent is the shared per-email auth window and the per-IP or per-account HTTP window. Login success resets the auth window. The windows are shared in staging and production. They are not a durable lockout. | Login rate-limit tests in `tests/unit/test_user_platform_auth_service.py` and the Sprint 40.3 shared-store tests | None | None | Yes, later. A lockout that only lives in process memory would not meet this row. Not this slice. | None | Do not call the shared windows a completed lockout. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | `contains_prompt_injection` matches six substrings and is called on the cleaned user query in `ShoppingAssistantService.query`. A match adds a warning. Deterministic ranking still runs. Merchant text, reviews, and tool results are not passed through that function. When AI flags are on, shopping, review, and community prompt builders can place catalog, review, and evidence text in the user prompt. Default AI transports stay disabled. This is not a completed sanitation review. | `tests/unit/test_shopping_assistant_service.py` `test_prompt_injection_resistance`, `tests/unit/test_shopping_assistant_intent.py` `test_prompt_injection_detection` | None | None | Yes, later, as a written review of the actual prompt sinks. Not this slice. | Sprint 13 owns assistant fallback. Sprint 40 owns the review. | Leave the six-marker list unchanged in the selected slice. Do not enable a provider to test it. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | MISSING | No pen-test checklist, security incident-response runbook, vulnerability-response process, or security go/no-go draft suitable for Sprint 44 was found. `docs/SECURITY.md` is the Sprint 22 control note. `docs/SECURITY_MODEL.md` is the Sprint 17 model. Sprint 42 operational paging is not this package. | None | None | None | Yes. This documentation package remains Sprint 40 work. It is not the selected slice. | Sprint 42 owns operational probes, alerts, paging, and incident operations. Sprint 40 still owns this package and the security go/no-go draft. | Write the package after the selected slice. Do not move it to Sprint 42. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH and the four Sprint 40 MEDIUMs are reconciled in the findings section. No written risk acceptance exists. Sprint 41 and Sprint 42 HIGHs remain open and are not Sprint 40 engineering. The decision-path read is an Included-requirement gap. This audit does not assign it a new HIGH or MEDIUM. | Tests cited on the individual findings do not close them. Staging proof is absent. | None that exercises abuse controls or the new policies | None | Yes, as a closure gate. Not one code change. | Sprint 41 and Sprint 42 for the HIGHs they own | Do not mark Sprint 40 closed. Do not risk-accept an open finding in this audit. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | Non-decision continuation requires `get_for_owner`. A new non-decision context uses `create(owner=verified_owner)`. An anonymous caller still gets `create(owner=None)`. That anonymous contract is what Sprint 40.1 merged and tested. Decision rows store an owner, but answer and refinement can read them from a body `conversation_id` without the caller presenting that owner. Repository `append_turn` can still materialize an ownerless row if a caller passes a missing id. The service non-decision path does not do that with a client id. | `test_foreign_conversation_id_cannot_read_or_append_prior_turns`, `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row`, `test_verified_owner_continues_own_non_decision_conversation` | Sprint 29 guest-claim staging notes are historical and were not re-run. | None | Yes, for the decision-path read, which is the selected slice. Binding anonymous queries to a new guest owner conflicts with the merged Sprint 40.1 anonymous contract and is not selected. | None | Close the decision-path read. Do not change anonymous `create(owner=None)` in this audit. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | PARTIAL | On the non-decision path, body `conversation_id`, `user_id`, and `profile_id` are lookup hints. Authority is the verified owner. History is written only for `_authorized_account_user_id`. A body profile personalizes only when it is already bound to that account. This is the Sprint 40.1 defect, and it is fixed in code and tests. It is not PROVEN. The decision path is not in the same state. `AnswerFromEvidenceService._resolve_packet` and `RefineSessionRecommendationService._resolve_packet` load `get(conversation_id)`, replace `bound_owner` with `context.owner`, and can replace `decision_id` from `context.decision_context` before `get_for_owner`. `ProposeResearchService._resolve_packet` does the same when the request owner is missing. Writes still go through `get_for_owner` with the request owner, so this residual is a read of the foreign snapshot, not a foreign turn append. Affiliate link generation still receives `shopping_query.user_id`. Affiliate activation stays off. That hint is not the selected slice. | Non-decision negatives in `tests/unit/test_sprint40_assistant_body_identity.py`. `test_bound_conversation_answers_from_snapshot` currently succeeds with no request owner. No test rejects a foreign bound `conversation_id` on answer or refinement. | None | None | Yes. This residual is the selected slice. | None | See the slice section. Do not weaken Sprint 40.1. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256. Expiry is seven days and is checked in `parse_owner_cookie`. Staging and production refuse placeholder secrets. `ensure_guest_owner_cookie` reuses a valid cookie, so it does not rotate. A copied cookie works until expiry because there is no revocation list. UI sign-out calls logout and then `POST /account/clear-device`. Logout itself does not clear the owner cookie. `claim_guest_conversation` rebinds and `set_owner_cookie` rotates to the account owner only when no canonical UUID snapshot exists. When one exists, the function returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. The code comment says replacing the cookie would hide the decision. | `tests/unit/test_sprint29_owner_cookie_auth.py`, `tests/unit/test_sprint29_guest_claim.py`, `tests/unit/test_sprint27_4_auth_aware_header.py` | Sprint 29 staging logout and `clear-device` notes were not re-run on this SHA. | None | No, until a product decision. This audit does not change snapshot immutability. | None. Snapshot immutability is already implemented. | Decide whether canonical snapshots stay immutable, or whether guest-to-account transition must rotate credentials and still show the decision. Do not implement either choice here. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement is the Sprint 40.4 control for the decision-owner cookie paths and `POST /account/clear-device`. Missing Origin is fail-closed. Bearer-only requests are unchanged. Preference-cookie mutations are not covered. The CSRF token is still not enforced. HTTP rate-limit identity is the trusted client IP, or an account HMAC when the bearer session or account owner cookie is verified. A guest session id is not a rate-limit key. Guest traffic uses the IP bucket. Auth email windows are separate and shared in staging and production. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests. No per-session bucket test exists because that key is absent. | None. Staging has not exercised the origin policy or the shared limiter. | None | Per-session limiting is later. Not this slice. The origin MEDIUM stays IMPLEMENTED-NOT-PROVEN. | None | Do not treat the shared IP and account buckets as per-session limits. Do not call the origin policy PROVEN. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | PARTIAL | Research confirmation derives `research-auth:<sha256>` from the owner binding, conversation, decision, proposal, and scope. The client confirmation token is ignored as execution identity. Repeat confirmation reuses the key. Ordinary non-decision `append_turn` has no idempotency key. A repeated assistant query appends another turn. | `tests/unit/test_research_authorization_handoff.py` `test_idempotency_key_is_server_derived` and `test_repeat_confirmation_reuses_same_authorization`. Sprint 38 execution tests cover the research key. No message-replay test. | None | None | Yes, later, for ordinary assistant message submission only. | Sprint 38 owns research-execution consumption. That server key is already present. | Do not reopen Sprint 38. Add message idempotency only after the selected slice. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, or a session id. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. Recommendation history stores the query only for `_authorized_account_user_id`. That store is the account's own history, not `product.analytics_events` and not the request log. The Sprint 40.1 body-`user_id` history write is gone. | `test_server_identity_is_opaque_and_ask_text_is_absent` and the Sprint 40.1 history tests | None on this SHA for a log or analytics sample | None | No. Remaining proof is a staging sample, not more application code. | Sprint 39 owns the analytics forbid-list. | Do not put conversation text into `product.analytics_events`. Do not call this row PROVEN. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are the same facts as R3 and R4. The six injection markers are the same facts as R10. Assistant processing sets `secrets_included` and `prompts_included` false. Provider prompts can include merchant and review text when the corresponding AI flag is enabled. Default transports do not make those calls. `AI_MAX_ESTIMATED_COST_PER_REQUEST` exists on the review path. Live research remains fail-closed, so confirmation does not spend a provider call today. Fail-closed research is not a cost limit that would hold if live research were opened. | `test_no_secrets_in_response_processing`, `test_prompt_injection_resistance`, `tests/unit/test_sprint40_6_csp.py` | None | None | No slice that enables live research or a provider. The written review is R10 and is later. | Sprint 38 owns live research execution and stays fail-closed. | Do not enable live research to test cost controls. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | PARTIAL | This matrix is the coverage review. Private decision routes set `noindex`, and `robots.txt` disallows `/results/`, `/compare/`, `/why-best-piq/`, and `/account`. Affiliate click storage exists. Click-fraud detection does not. Tool-abuse controls beyond the injection warning were not found. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py` | No fresh staging crawl was run. | None | No as a separate row. The open parts are the rows above, especially R1, R6, R8, R11, and R14. | Sprint 29 owns the SEO implementation. | Do not reopen Sprint 29. Do not enable affiliate tracking. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same open findings as R12. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | None | Yes, as the same closure gate | Sprint 41 and Sprint 42 for findings they own | Do not start Sprint 45. |

## What moved, and what did not

Sprint 40.1 removed body `conversation_id`, `user_id`, and `profile_id` as authority on the non-decision assistant path. That part of R1, R13, and R14 is implemented and tested. It is not PROVEN, and it is not the whole row.

R1, R13, and R14 stay PARTIAL because answer-from-evidence and session refinement still authorize a UUID snapshot read from a body `conversation_id`. The 2026-10-09 audit said the decision path already matched R14. This reconciliation does not carry that sentence forward. `test_bound_conversation_answers_from_snapshot` is current repository evidence that a bound conversation id alone is enough.

R18 moves from PARTIAL to IMPLEMENTED-NOT-PROVEN. The body-`user_id` history write is gone, routine request logs omit conversation bodies and session ids, and the analytics forbid-list is tested. No staging sample exists, so the row is not PROVEN.

R5 stays PARTIAL because auth-audit email and the broader PII program are not closed by the logging middleware. No new redaction slice is selected.

R11 stays MISSING. The security package was not added by Sprint 40.1 through Sprint 40.6.

## Historical finding reconciliation

These notes are additive. They do not rewrite the Sprint 30 map or section I of the gap inventory.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. Shared counters do not add bot detection, click-fraud scoring, durable lockout, or a per-session bucket. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. `CsrfTokenService` is still unused on routes. Preference-cookie routes are outside the policy. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. `SECURITY_CSP` can still override the default. FastAPI `/docs` and `/redoc` are incompatible with the strict policy when they are enabled. `/openapi.json` remains usable. That incompatibility does not reopen the finding. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the dependency class. SAST, container scanning, and IaC security scanning STILL OPEN | pip-audit 2.10.1 is a required CI gate. CI #472 reported 71 packages, 0 vulnerabilities, and 0 exceptions. The historical sentence is no longer a total absence. Dependabot, CodeQL, and Trivy remain absent. Their absence is not, by itself, the Sprint 40 requirement. Secrets scanning remains present. `terraform validate` remains syntax validation. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. This audit does not claim a historical reachable SSRF. Staging has not exercised the policy. Browser links are not a merchant-host allowlist. The finding is not closed and not PROVEN. |

No new HIGH is assigned. No MEDIUM is relabeled launch-blocking. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## R6 capability classes

| Class | Status | Evidence |
|-------|--------|----------|
| Secrets | Present, narrow | `ci.yml` runs `scripts/secret_scan_25a.py`. Scan globs omit `app/`. |
| Dependency | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. CI #472: 71 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Absent | No CodeQL, Bandit, or Semgrep gate over `app/`. |
| Container | Absent | Image build, smoke import, and digest publication do not scan the image. |
| Terraform / IaC security | Absent | `terraform fmt` and `terraform validate` are present. They are not security scanning. |

The smallest missing class, if a later scanner slice is chosen, is SAST. It is not the selected slice. The decision-path read is higher priority because it violates the Sprint 40 acceptance sentence that a foreign decision context cannot be read.

## Guest session and canonical rebinding

This is a product-definition conflict, not an implementation bug selected for change.

Sprint 40 acceptance says guest-to-authenticated transition preserves the active decision while rotating ownership credentials.

`claim_guest_conversation` does rotate the cookie when no canonical UUID snapshot exists. When a canonical UUID snapshot exists, it returns `reason=immutable_snapshot_owner`, preserves the guest cookie, and does not rebind. The function comment states that replacing the cookie would hide the decision.

This audit does not change snapshot immutability. A product decision is required before any rebind change: keep canonical snapshot ownership immutable, or rotate credentials while still showing that decision. R15 stays PARTIAL until that decision. It is not the selected slice.

## Message idempotency

Research confirmation already derives its execution identity on the server and ignores the client confirmation token. Sprint 38 research-execution consumption of that key stays as it is. This audit does not reopen Sprint 38.

Ordinary assistant submission still has no idempotency key. `ShoppingAssistantService.query` appends a turn for each accepted non-decision query. A repeated body can append a duplicate turn for the same verified owner. That gap is R17. It is later than the decision-path read, because it does not disclose another owner's decision.

## Prompt injection, merchant content, and cost

The six-marker warning is not prompt-injection protection. It runs on the user query only.

Merchant, review, and community evidence can enter provider prompts in `build_shopping_prompts`, review `build_analysis_prompt`, and `build_community_prompts` when those AI flags and transports are enabled. The default transports are disabled. System prompt text tells the model to ignore instructions in untrusted content. That wording is not a sanitation control.

External responses mark `secrets_included` and `prompts_included` false. This audit did not find a cost-amplification incident. Live research and live Shopify stay fail-closed, so this audit did not activate them to measure cost.

## Documentation package

Still absent, and still owned by Sprint 40:

- Pen-test readiness checklist
- Security incident-response runbook
- Vulnerability-response process
- Security go/no-go draft suitable for Sprint 44

Sprint 42 owns production probes, alerts, paging, and operational incident operations. It does not receive this package by default.

## Duplicated requirements

- R12 and R21 are the same closure gate. R21 adds the Sprint 45 deadline.
- R3 and R16 both include the origin policy. R16 also requires per-session, per-IP, and authenticated-principal limits. Per-IP and account limits exist. Per-session limits do not.
- R4 and R19 both include encoding and XSS. R19 adds external-model minimization and cost.
- R5 and R18 both include logs. R18 is the conversation-body and session-id sentence, and it is the only row at IMPLEMENTED-NOT-PROVEN.
- R1, R13, and R14 share the decision-path read. R14 is the falsifiable sentence. The non-decision half of that sentence is already implemented.
- R8, R9, and the abuse clauses of R20 are one abuse-control problem. Shared counters close only the in-process HIGH's implementation, not the rest.
- R10 and the prompt-injection clauses of R19 and R20 are one review. That review is not written.

## Sprint 41 work, not this slice

- Production VPC, database, secrets, IAM, OIDC, deploy, rollback, DNS, and TLS.
- Production IAM review.
- Production image pull. Build Image #168 does not start that review.
- The HIGHs for production isolation and production OIDC/SSM.

Sprint 41 stays UNSTARTED. This audit does not start it.

## Sprint 42 work, not this slice

- CloudWatch and security paging.
- Operational incident response, probes, alerts, and paging runbooks.

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R11 is missing. R1, R13, and R14 are still PARTIAL on a repository-backed read. R6, R8, R9, R10, R16, and R17 still have repository-backed gaps. Staging proof is absent even for the controls that are implemented. Those facts are not all "proof that belongs to staging, Sprint 41, Sprint 42, or Sprint 44."

The guest-rebind acceptance conflict is not selected. It still needs a product decision. Anonymous `create(owner=None)` is not selected for the same reason: Sprint 40.1 merged that contract, and the Included "every conversation" sentence now conflicts with it.

**Slice:** On decision-bound answer, session refinement, and research proposal, stop using a request-body `conversation_id` to adopt the stored conversation owner.

Current defect, from repository code and the existing test only:

- `AnswerFromEvidenceService._resolve_packet` and `RefineSessionRecommendationService._resolve_packet` call `get(conversation_id)` even when the request owner is missing or different.
- They set `bound_owner` to `context.owner` and may replace `decision_id` from `context.decision_context`.
- They then call `snapshots.get_for_owner` with that stored owner.
- `tests/unit/test_phase_29_4a_answer_from_evidence.py` `test_bound_conversation_answers_from_snapshot` expects an evidence answer when no request owner is passed.
- `ProposeResearchService._resolve_packet` has the same stored-owner adoption when the request owner is missing. When a request owner is present, it already uses `get_for_owner`.
- Turn append and refinement persistence already use `get_for_owner` with the request owner. The slice must not weaken that write check, and it must not weaken non-decision Sprint 40.1 behavior.

**Likely files:**

- `app/services/answer_from_evidence.py`
- `app/services/refine_session_recommendation.py`
- `app/services/propose_research.py`
- `tests/unit/test_phase_29_4a_answer_from_evidence.py`
- `tests/unit/test_sprint40_assistant_body_identity.py`
- the refinement and research-proposal tests that currently pass a body `conversation_id` without the verified owner

**Acceptance tests for the later slice:**

1. A caller with no owner, or with a different owner, who sends a victim's bound `conversation_id` does not receive that decision's evidence, refinement, or research proposal.
2. The verified owner of that conversation still receives the evidence answer. `test_bound_conversation_answers_from_snapshot` must pass that owner.
3. Existing foreign decision-owner failures still fail closed, including `test_decision_bound_foreign_owner_still_fails_closed` and `tests/unit/test_phase_29_4a_answer_from_evidence.py` `test_owner_mismatch_is_rejected`.
4. Non-decision Sprint 40.1 tests still pass, including foreign `conversation_id`, body `user_id`, and unbound `profile_id`.
5. Research-confirmation idempotency stays server-derived. Live research stays disabled. Canonical snapshot immutability stays unchanged.

**Out of scope for the slice:** SAST, container scanning, IaC security scanning, account lockout, message idempotency, the pen-test package, guest rebind, anonymous ownerless create, CSP, origin policy, rate limits, affiliate activation, Shopify calls, routing, and any deploy.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No Sprint 40.7 implementation on this tree.
- No pen-test report or written risk acceptance.
