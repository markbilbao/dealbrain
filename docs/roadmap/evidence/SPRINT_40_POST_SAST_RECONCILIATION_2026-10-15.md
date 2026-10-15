# Sprint 40 post-SAST reconciliation — 2026-10-15

**Audit verdict:** B. Sprint 40 is Not ENGINEERING COMPLETE. One bounded next engineering slice is selected. It is not implemented in this change.

**Selected next engineering slice:** Add one deterministic container-vulnerability scan of the locally built runtime image, and fail publication before that image is pushed.

This slice is not named Sprint 40.8. A later implementation may take a number. This audit only selects the work. It does not name a scanner brand.

**Sprint closure status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE.

**Engineering status:** Sprint 40.1 through Sprint 40.7 are merged. The durable failed-login lock is merged. Shopping-assistant submission idempotency is merged. The security-readiness package is merged. The Bandit SAST gate is merged. This change is a reconciliation audit only.

**Production proof:** No. Not PRODUCTION PROVEN.

**Launch:** No. Not LAUNCH READY.

**Starting `main`:** `80a4506485c7f4a6a566c495120723995dfc2c17`

**Verified post-merge evidence on that SHA:** CI #499 succeeded. Full pytest on that run: 4511 passed, 5 skipped. The Bandit 1.9.4 SAST gate scanned 649 files under `app/**/*.py`, reported 35 findings, and matched 35 exact baseline exceptions. There were no unbaselined findings. pip-audit reported 73 packages, 0 vulnerabilities, 0 exceptions. Build Image #178 succeeded. Those runs are publication and test evidence for the merged tree. They are not a penetration test, a staging abuse exercise, a container vulnerability scan, an IaC security scan, a signed provenance attestation, or a security go/no-go. CI is not staging or production proof. The SAST capability is not PROVEN from CI alone.

**Sprint definition:** [`../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md`](../sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md)

**Historical inputs, not copied forward:** [`SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md`](SPRINT_40_POST_SECURITY_READINESS_RECONCILIATION_2026-10-14.md) and [`SPRINT_40_SAST_GATE_2026-10-14.md`](SPRINT_40_SAST_GATE_2026-10-14.md). Those files keep the classes they recorded. The 2026-10-14 reconciliation still says SAST is absent and still selects the SAST gate. The SAST record does not select a later slice. This reconciliation re-reads the tree at `80a4506485c7f4a6a566c495120723995dfc2c17` and classifies R1–R21 again. The 2026-10-09 readiness audit stays historical.

**Gap inventory:** section I and the Sprint 30 security-finding map in [`../GAP_INVENTORY.md`](../GAP_INVENTORY.md) are not rewritten. Additive notes below say which historical findings are still true.

No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0. Affiliate activation stays off. Live research stays off. No provider or public-market activation was changed. Runtime code is unchanged.

Sprint 38 stays IN PROGRESS. Its engineering status stays ENGINEERING COMPLETE. Its closure validation stays blocked on Sprint 41. Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Sprint 39 Class C count remains 19. The Sprint 39 selected next engineering slice remains NONE. Sprint 41 stays UNSTARTED. This audit does not reopen Sprint 38 or Sprint 39 engineering.

## How a row becomes PROVEN

Code on `main` is not enough. A row is PROVEN only when the current tree shows the control, a test fails closed for the abuse case, and the Sprint 40 acceptance bar for that control is met. A fresh staging or production run is recorded when it exists. Absence of that run keeps a complete, tested control at IMPLEMENTED-NOT-PROVEN. A control that is only partly present stays PARTIAL even when some of its tests pass. A requirement that is itself a written review is IMPLEMENTED-NOT-PROVEN when this reconciliation covers the named topics and the named control is present. A review row stays PARTIAL when the named control is still missing in code. CI success does not prove a row.

This reconciliation did not execute the application on staging or production. Repository tests and the merged gate were re-read. They are not staging proof.

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

The class counts match the previous reconciliation. They were re-derived from this tree. The SAST merge changes the inside of R6. It does not move R6 out of PARTIAL, and it does not move any other row.

## Requirement matrix

| ID | Requirement | Class | Current-tree reading | Tests re-read | Staging or production | What remains |
|----|-------------|-------|----------------------|---------------|-----------------------|--------------|
| R1 | AuthN/AuthZ/object-level review | IMPLEMENTED-NOT-PROVEN | Account bearer sessions are checked in `AuthService.validate_session`. Decision and canonical snapshot reads use an owner. Non-decision `ShoppingAssistantService.query` continues a conversation only through `_owned_conversation_context`. A body `conversation_id` is a lookup hint. An ownerless row is not adopted. Answer, refinement, and research proposal receive the verified owner. `CanonicalDecisionSnapshot.owner` is a required `ConversationOwner`. | `tests/unit/test_sprint40_7_decision_path_owner_binding.py`, `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_shopping_submission_idempotency.py` | None on this SHA | No new object-level slice. Remaining proof is staging. |
| R2 | Session security review | IMPLEMENTED-NOT-PROVEN | Bearer tokens are `secrets.token_urlsafe(48)` and only the SHA-256 hash is stored. `validate_session` rejects a missing, revoked, or expired session. Guest ids are `uuid4`. The owner cookie is HMAC-SHA256, `HttpOnly`, and `SameSite=lax`, with `Secure` in staging and production. Account cookies are checked in `authorize_conversation_owner` against an active matching session. A guest cookie is returned after the MAC and expiry checks and has no server-side revocation list. Public Sign out revokes the bearer and then clears the cookie. | `tests/unit/test_sprint29_owner_cookie_auth.py`, `tests/unit/test_user_platform_auth_service.py` | None on this SHA | No guest-revocation slice. Remaining proof is a staging logout and shared-device exercise. |
| R3 | Headers/CSP/CORS/CSRF policy completion | IMPLEMENTED-NOT-PROVEN | `DEFAULT_SECURITY_CSP` is first-party and does not contain `'unsafe-inline'` or `'unsafe-eval'`. `SecurityHeadersMiddleware` sets the companion headers, including HSTS on staging and production. Production validation rejects CORS `*`. `OwnerCookieOriginMiddleware` fail-closes a missing or untrusted `Origin` on unsafe decision-owner-cookie requests and on `POST /account/clear-device`. `CsrfTokenService.validate` is still not called by any route. Origin enforcement is the beta CSRF control for the covered cookie mutations. | `tests/unit/test_sprint40_4_cookie_origin.py`, `tests/unit/test_sprint40_6_csp.py` | None on this SHA | No CSRF-token slice. Remaining proof is staging. |
| R4 | Output encoding; XSS; SQLi; SSRF; redirect validation; merchant URL allowlisting; command injection | IMPLEMENTED-NOT-PROVEN | `validate_server_fetch_url` accepts https only and rejects numeric private, loopback, link-local, and metadata hosts. `validate_browser_destination` accepts http or https and does not fetch the URL. Shopify `UrllibJsonTransport` accepts only `https://catalog.shopify.com/api/ucp/mcp` and refuses redirects. Resend posts only to its pinned URL with `follow_redirects=False`. `h()` and `attr()` use `html.escape`. No `subprocess`, `os.system`, `eval`, or `exec` call was found under `app/`. No merchant-host catalog exists, and this audit does not invent one. | `tests/unit/test_sprint40_5_url_trust.py`, `tests/unit/test_sprint40_6_csp.py` | None on this SHA | No merchant-domain list. Remaining proof is staging. DNS rebinding stays out of scope. |
| R5 | Log redaction; body logging policy; PII handling | IMPLEMENTED-NOT-PROVEN | `RequestLoggingMiddleware` logs method, path, status, duration, request id, and client host. It does not log the body, the owner cookie, a session id, or a bearer token. `redact_value` redacts secret-like keys before structured logs. Product analytics reject question, query, answer, message, email, session id, and conversation id. Security-audit records can store the account email on authentication events. That store is `SecurityEvent` metadata. | `tests/unit/test_validation_error_logging.py`, `tests/unit/test_sprint39_1_consent_analytics_feedback.py` | None on this SHA | No redaction slice. Remaining proof is a staging log sample. |
| R6 | Secret/dependency/SAST/container/Terraform scanning in CI | PARTIAL | The Included sentence names five capability classes. All five are required for this row and for Sprint 40 ENGINEERING COMPLETE. Secrets and pip-audit remain present. SAST is now present and is IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning are absent. `terraform validate` is not IaC security scanning. A successful Docker build is not container vulnerability scanning. | `tests/unit/test_sprint25a_infrastructure.py`, `tests/unit/test_sprint40_2_dependency_audit.py`, `tests/unit/test_sprint40_sast_baseline.py`, `tests/unit/test_sprint25b1_image_publication.py` | CI #499 is a clean secret, pip-audit, and SAST run. It is not an image-CVE or IaC-security result. Build Image #178 is not a vulnerability scan. | Container vulnerability scanning is the selected slice. IaC security scanning stays open and is not part of that slice. |
| R7 | Supply-chain provenance checks; immutable image authority verification | IMPLEMENTED-NOT-PROVEN | `build-image.yml` publishes `sha-<gitsha>`, checks a `sha256` digest, writes a release manifest, and states that the digest is deployment authority. Deploy and rollback workflows reject mutable-tag authority and pull by digest. No cosign, SLSA, or signed attestation was found. Sprint 40 acceptance does not name a signature. The Dockerfile copies `ghcr.io/astral-sh/uv:latest` and starts from `python:3.12-slim`. Those tags are not the deployment authority. | `tests/unit/test_sprint25b1_image_publication.py` | Build Image #178 published a digest. It is not a signature and not a vulnerability scan. | No signed-provenance slice. Remaining proof is the production pull, which Sprint 41 owns. |
| R8 | Distributed rate limiting decision+MVP; bot/credential-stuffing/click-fraud controls appropriate to beta | IMPLEMENTED-NOT-PROVEN | Staging and production must use `SqlRateLimitStore`. `RATE_LIMIT_BACKEND=memory` is rejected there. HTTP identity is `ip:<trusted client>` or `acct:<hmac>` for a verified bearer session or account owner cookie. Auth failures use a shared `auth` scope keyed by an HMAC of the normalized email, 20 attempts per 60 seconds. The durable login lock adds a 20-failure, 15-minute hold. No CAPTCHA or click-fraud score was found. Affiliate routes are demo-only and do not pay a commission. Full WAF/CDN remains a non-goal. | `tests/unit/test_sprint40_3_distributed_rate_limit.py`, `tests/unit/test_sprint40_failed_login_lock.py` | None. Required staging evidence "Abuse controls exercised" is absent. | No bot-challenge or click-fraud slice. Remaining proof is the staging abuse exercise. |
| R9 | Account lockout or equivalent | IMPLEMENTED-NOT-PROVEN | `AuthService.login` applies the 20-attempt / 60-second limiter, then `FailedLoginLock`. Twenty consecutive failures set `locked_until` for 900 seconds. Staging and production use `SqlFailedLoginLockStore`. Memory is forbidden there. Unknown, inactive, and bad-password failures share one error string. The stored key is an HMAC of the normalized email. | `tests/unit/test_sprint40_failed_login_lock.py`, `tests/unit/test_user_platform_auth_service.py` | None on this SHA | No new lockout slice. Remaining proof is a staging exercise. |
| R10 | AI prompt-injection + merchant-content sanitation review | PARTIAL | Three model prompt builders exist. Shopper, merchant, review, and community text enter a user JSON string beside the task. Shopping and community system strings say not to follow instructions in that text. The review system string does not. `contains_prompt_injection` warns on six shopper-query substrings and does not delimit data. No live AI HTTP transport exists. Defaults stay off. | `tests/unit/test_shopping_assistant_deterministic.py` | None | Structural isolation of the three builders is still absent. It is required before AI or live research is enabled. It is not the selected slice. |
| R11 | Pen-test readiness package; security IR runbook; vulnerability-response process | IMPLEMENTED-NOT-PROVEN | The merged package is `docs/security/PENETRATION_TEST_READINESS.md`, `docs/runbooks/SECURITY_INCIDENT_RESPONSE.md`, `docs/security/VULNERABILITY_RESPONSE.md`, and `docs/roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md`. No penetration test has been executed. Paging is not configured. No risk acceptance is granted. SECURITY GO: NOT DECIDED. R11 is not PROVEN. | `tests/unit/test_sprint40_security_readiness_package.py` | None. The package has not been rehearsed. | No new package. Proof is later use, review, or rehearsal. |
| R12 | Close all HIGH and launch-blocking MEDIUM findings | PARTIAL | The Sprint 40 HIGH "In-process rate limits only" is IMPLEMENTED-NOT-PROVEN. Required staging evidence "Abuse controls exercised" is absent, so the HIGH is not closed. No historical Sprint 40 MEDIUM is designated launch-blocking. The CSRF/Origin, CSP, and URL/SSRF MEDIUMs are IMPLEMENTED-NOT-PROVEN. The dependency-scanner absence is CLOSED BY IMPLEMENTATION for the original no-scanner condition. The SAST gate does not rewrite that finding. No written risk acceptance exists. | Tests cited on the findings do not close them. | None that exercises abuse controls | The gate stays open until the HIGH is closed by staging proof or by a later written risk acceptance. This audit does not grant that acceptance. |
| R13 | Bind every conversation and decision context to a verified guest session or authenticated principal | PARTIAL | A decision snapshot cannot be constructed without an owner. A decision-bound conversation cannot be stored with `owner=None`. `get_for_owner` returns nothing for an ownerless row. Body `conversation_id` does not adopt that row. The anonymous non-decision `create(owner=None)` row still has no principal. That row has no security consequence. The literal sentence is unmet. | `test_ownerless_and_unknown_client_ids_do_not_adopt_the_row` and the Sprint 40.7 ownerless decision-path negatives | Sprint 40.1 did not exercise this on staging | No slice. Closing the literal sentence requires a product decision to mint a guest owner for anonymous Ask. |
| R14 | Do not authorize access using request-body `conversation_id`, `profile_id`, or `user_id` | IMPLEMENTED-NOT-PROVEN | Body `conversation_id`, `user_id`, `profile_id`, `decision_id`, and `context_version` are lookup values. Authority is the verified owner. The submission fingerprint includes normalized body `user_id` and `profile_id` so a changed body conflicts. `submission_authority_scope` does not read those fields. | `tests/unit/test_sprint40_assistant_body_identity.py`, `tests/unit/test_sprint40_7_decision_path_owner_binding.py` | None | No new authorization slice. Remaining proof is staging. |
| R15 | Review guest-token entropy, rotation, fixation, replay, expiry, deletion, logout, shared-device isolation, and guest→authenticated rebinding | PARTIAL | Guest ids are `uuid4`. The cookie is HMAC-SHA256 with a seven-day expiry. `claim_guest_conversation` rebinds only when no canonical UUID snapshot exists. When one exists, it returns `immutable_snapshot_owner`, keeps the guest cookie, and does not rebind. Sprint 40 acceptance says the transition preserves the active decision while rotating ownership credentials. Snapshot immutability says the opposite for a canonical UUID snapshot. | `tests/unit/test_sprint29_guest_claim.py` | Sprint 29 staging logout notes were not re-run | No, until an owner decision. This audit does not change snapshot immutability and does not implement a rebind policy. |
| R16 | Apply CSRF/origin policy for cookie transport and per-session, per-IP, and authenticated-principal rate limits | PARTIAL | Origin enforcement covers decision-owner-cookie mutations and `POST /account/clear-device`. HTTP rate-limit identity is the trusted client IP, or an account HMAC when a bearer session or account owner cookie is verified. A guest `session_id` is not a rate-limit key. The Included sentence names a per-session bucket beside the per-IP and authenticated-principal buckets. That bucket is still absent. | `tests/unit/test_sprint40_4_cookie_origin.py`, Sprint 40.3 rate-limit tests | None | The per-session bucket stays unimplemented. It is defense-in-depth for the current beta and is not the selected slice. |
| R17 | Add idempotency and replay protection for message submission and research confirmation | IMPLEMENTED-NOT-PROVEN | `POST /api/v1/shopping-assistant/query` requires `Idempotency-Key`. The same scoped key and canonical fingerprint replay the stored response. Replay does not call `service.query` and does not call `emit_ask_product_events`. A changed mutation-relevant payload is HTTP 409. Scope is the verified account, the verified guest, or an HMAC of the trusted client host for anonymous Ask. Research confirmation still derives `research-auth:<sha256>` and ignores the client confirmation token. | `tests/unit/test_shopping_submission_idempotency.py`, `tests/unit/test_research_authorization_handoff.py` | None on this SHA | No new message-idempotency slice. Remaining proof is a staging exercise. |
| R18 | Redact conversation bodies and session identifiers from routine logs and analytics | IMPLEMENTED-NOT-PROVEN | The request log does not record the body, the owner cookie, a session id, or a bearer credential. `FORBIDDEN_ANALYTICS_FIELDS` includes question, query, answer, message, session id, guest session id, and conversation id. The submission ledger stores the public response for replay. That store is not the request log and not product analytics. The raw key is stored only as SHA-256. | `test_server_identity_is_opaque_and_ask_text_is_absent`, `test_http_replay_skips_query_analytics_and_a_second_turn` | None on this SHA | No. Remaining proof is a staging sample. |
| R19 | Review output encoding, XSS, user/merchant/review prompt injection, external-model data minimization, and research cost amplification | PARTIAL | Encoding and the strict default CSP are implemented, as on R3 and R4. The prompt builders are the same three as R10. Assistant, review, community, answer, refinement, and research processing set `secrets_included` and `prompts_included` false. Shopping and community builders drop secret-like keys. The review request schema is fixed fields, so it has no caller-controlled key to strip. `AI_MAX_ESTIMATED_COST_PER_REQUEST` defaults to 0.05 and compares a returned estimate. It is not a live-research budget. `LIVE_RESEARCH_EXECUTION_OPERATIONAL` is false. | `tests/unit/test_sprint40_6_csp.py`, prompt-injection unit coverage | None | The same pre-activation isolation gap as R10. Not the selected slice. Do not enable live research to test the cost cap. |
| R20 | Explicit coverage of identity/AuthZ; owner-bound decisions; SSRF; redirect/link safety; CSP/security headers; secrets; rate limiting; credential stuffing; bot abuse; affiliate/click fraud; prompt injection / tool abuse; PII/logging/redaction; vulnerability response; private SEO/session isolation | IMPLEMENTED-NOT-PROVEN | This matrix is the coverage review. Each named topic is classified on its own row. The penetration-test checklist, vulnerability process, and Sprint 44 draft exist and do not replace this review. Open findings do not keep this row PARTIAL. Sprint 44 has not accepted the package, so it is not PROVEN. | `tests/unit/test_sprint28_1_index_privacy.py`, `tests/unit/test_sprint29_seo_foundation.py`, and the tests cited on the rows above | No fresh staging crawl was run | No separate implementation slice. |
| R21 | Close HIGH and launch-blocking MEDIUM issues before Sprint 45 | PARTIAL | Same gate as R12. The finding that prevents closure is the HIGH "In-process rate limits only", which remains IMPLEMENTED-NOT-PROVEN because staging has not exercised the shared counters. Sprint 45 is the deadline, not a place to move the work. | None that close the gate | None | Do not start Sprint 45. Do not risk-accept the HIGH in this audit. |

## What moved, and what did not

No row changed class. SAST moved from absent to IMPLEMENTED-NOT-PROVEN inside R6. R6 stays PARTIAL because container vulnerability scanning and IaC security scanning are still absent. R1, R2, R3, R4, R5, R7, R8, R9, R11, R14, R17, R18, and R20 stay IMPLEMENTED-NOT-PROVEN. R10, R12, R13, R15, R16, R19, and R21 stay PARTIAL. R11 is not PROVEN. No row is PROVEN. No row is MISSING.

## R6 after SAST

| Class | Required for ENGINEERING COMPLETE | Status | Evidence |
|-------|-----------------------------------|--------|----------|
| Secrets | Yes | Present, narrow | `ci.yml` runs `scripts/secret_scan_25a.py`. Scan globs are `infra/**/*`, `.env*.example`, `scripts/**/*`, and `.github/workflows/**/*`. They omit `app/`. |
| Dependency | Yes | Present | `ci.yml` runs `scripts/check_pip_audit_baseline.py`. pip-audit 2.10.1. Empty exception list. Verified post-merge: 73 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | Yes | Present, not PROVEN | `ci.yml` runs `scripts/check_sast_baseline.py`. Bandit 1.9.4. Scope `app/**/*.py`. 649 files. 35 findings. 35 exact exceptions. 0 unbaselined. CI does not prove the capability. |
| Container vulnerability scanning | Yes | Absent | The CI image job builds `dealbrain:ci-<sha>` and smoke-imports. `build-image.yml` pushes `sha-<gitsha>` and records a digest. Neither scans the image for vulnerabilities. Build Image #178 is not a vulnerability scan. |
| Terraform / IaC security | Yes | Absent | `terraform fmt -check` and `terraform validate` with `-backend=false` run for account, staging, and production. They are syntax and configuration validation. No Checkov, tfsec, or Trivy config scan was found. |

Two present classes and one implemented-not-proven class do not complete a five-class requirement. R6 stays PARTIAL.

### SAST gate review

The merged gate matches the recorded design. This reconciliation re-read `scripts/check_sast_baseline.py`, `.github/workflows/ci.yml`, `pyproject.toml`, and `tests/security/baselines/bandit.baseline.json`.

| Check | Result |
|-------|--------|
| Pinned Bandit 1.9.4 | Yes. `bandit==1.9.4` in the dev extra. The gate requires module and CLI version 1.9.4. The baseline `scanner_version` is 1.9.4. |
| Scope `app/**/*.py` | Yes. The current tree still has 649 Python files under that scope. A `.bandit` file under `app/` fails the gate. |
| Fail-closed JSON parsing | Yes. Exit codes other than 0 or 1, empty output, invalid JSON, a non-object payload, and a missing `results`, `errors`, `metrics`, or `generated_at` field exit 2. |
| Exact source fingerprints | Yes. The hash covers the normalized `line_range` source, with line-number prefixes removed, plus Bandit's `issue_text`. Line numbers are not part of the identity. |
| Stale exception failure | Yes. `compare` reports a stale exception when one baseline object matches no current finding, and an unbaselined finding when a result matches no exception. One exception matches one finding. |
| No wildcard baseline entries | Yes. Path, test id, severity, and confidence reject `*`, `?`, and the words `all` and `any`. The 35 exceptions are exact. |
| No `# nosec` bypass | Yes. The command passes `--ignore-nosec`. A non-zero `nosec` metric fails the gate. No `# nosec` comment was found under `app/`. Skipped Bandit tests fail the gate. |
| No hosted scanner | Yes. The command is local `python -m bandit`. It does not call GitHub code scanning. No `codeql.yml` exists. |
| CI permissions | Workflow permissions stay `contents: read`. `security-events: write` is not used. The step has no `continue-on-error`. |

The 35 exceptions do not prevent calling the SAST capability IMPLEMENTED-NOT-PROVEN. The inventory is 0 HIGH, 6 MEDIUM, and 29 LOW. Rationales are 32 `false_positive`, 2 `safe_constant`, and 1 `framework_managed`. Current source still matches the recorded review of the six MEDIUM results: `app/core/config.py` `APP_HOST` default `"0.0.0.0"` is a settings string; `app/core/validation.py` lists `"0.0.0.0"` in the local database-host denylist; `app/ucp/agent_profile.py` lists `"0.0.0.0"` and `"127.0.0.1"` as internal-address markers; `app/research/public_web_extract.py` documents two private `/tmp` artifact paths; `app/research/shopify_global_catalog_ph_probe.py` documents `/tmp/piqsavi-shopify-global-ph`. None of those lines is a socket bind or a request-path temporary file. The two `safe_constant` rows remain the published launch-readiness demo gate string and the published in-memory demo password. This reconciliation does not reopen them. The baseline stores hashes, not the values. No exception is a Sprint 44 risk acceptance.

The SAST capability stays IMPLEMENTED-NOT-PROVEN. CI #499 is not staging proof and is not production proof.

## Container vulnerability scanning

The final runtime image is the deployment authority. It is not the CI validation tag.

| Artifact | What the tree does | Vulnerability scan |
|----------|--------------------|--------------------|
| A. PR/local validation image | `.github/workflows/ci.yml` job `image` builds `dealbrain:ci-${{ github.sha }}` and `dealbrain:ci-local` with `push: false` and `load: true`, then smoke-imports `httpx` and `app.auth.email_resend`. Permissions are `contents: read`. | Absent |
| B. Immutable releasable image | `.github/workflows/build-image.yml` rebuilds the same Dockerfile, pushes `sha-<gitsha>` in the same step, and records `sha256:<64 hex>` as deployment authority. `deploy-staging.yml` pulls that digest and does not rebuild. | Absent |

`Dockerfile` starts `FROM python:3.12-slim` and copies `/uv` and `/uvx` from `ghcr.io/astral-sh/uv:latest`. Neither reference is a digest pin. The runtime stage does not run `apt-get`. It copies the `--no-dev` virtualenv, application files, and those two binaries, creates user `dealbrain`, and starts `uvicorn` on `0.0.0.0:8000`. pip-audit sees the frozen Python closure. It does not see Debian packages in the slim base or the copied `uv` binary. Because the base tags float, the CI image and the published image are separate builds and can differ.

**What must be scanned:** B. The immutable releasable runtime image. A is not the artifact staging deploys, and a clean CI image build does not scan B. Dockerfile text is not a substitute for the built filesystem. Scanning both would be a second integration of the same capability and is not the smallest correct gate.

The scan has to inspect the locally built runtime image before publication. Build Image currently sets `push: true` on the build step, so a later slice has to build or load the image, scan it, and push only after the gate passes. A failed scan must not write the release manifest. Pulling the digest back from GHCR is not required and would scan bytes that are already published. GHCR login already exists for the push. The scan itself must not need a registry pull.

Publication of the releasable image should be blocked on an unbaselined finding. The CI validation job should keep `contents: read`. The publication workflow already has `contents: read`, `packages: write`, and `actions: read`. The slice must not add `security-events: write`. The scanner must not upload the image, the SBOM, or source metadata to an external service.

| Constraint | Required shape |
|------------|----------------|
| Pin | One scanner version, not a floating tag. |
| Determinism | An explicit baseline of exact findings. A vulnerability database that changes daily is not itself a stable pass/fail oracle. |
| Network | A vulnerability database is required for a useful result. Fetch it in the job or supply a pinned snapshot. Do not pretend the scan is offline when the database is missing. |
| Severity | Record severity. Do not use a severity word as a wildcard ignore. |
| Fix availability | Record whether a fix exists. An unfixed finding does not pass silently. |
| Baseline | One exact exception per reviewed finding. No wildcard package, CVE, or path. |
| Stale exceptions | A baseline entry that no longer matches a current finding fails the gate. |
| Local image | The scanner reads the image just built. It does not parse only the Dockerfile. |
| AWS | Not used. |
| IaC | Not included. |

Capability comparison, without selecting a brand:

| Need | Vulnerability-only image scanner | Multi-mode scanner that also reads IaC |
|------|----------------------------------|----------------------------------------|
| Local image filesystem | Yes, from a docker image, an OCI archive, or a docker archive. | Yes, from an image or an archive input. |
| IaC in the same binary | No. A container-only tool cannot be pointed at Terraform and still be this scan. | Yes, as a separate config mode. This slice must not invoke that mode. |
| Pinned release | Yes. | Yes. |
| First-class stale baseline matching this repository | No. The repository wrapper used by pip-audit and Bandit is still required. | Ignore files are not that wrapper. |
| Vulnerability database | Required. Offline only when a database snapshot is already present. | Required for vulnerability mode. Misconfiguration mode does not replace it. |
| External upload | Off unless a server URL is configured. Leave it off. | Off unless a cloud upload is configured. Leave it off. |
| GHCR pull | Not required for a local image. | Not required for a local image. |

Both shapes can scan the built image. A vulnerability-only scanner matches the rule that this slice does not bundle IaC. A multi-mode scanner is acceptable only when the invocation is image vulnerability mode and the change adds no Terraform scan. The slice is the capability. The implementation chooses one pinned tool that meets the table.

## IaC security scanning

`infra/terraform/` contains `account/`, `environments/staging/`, `environments/production/`, and `modules/`. CI uses Terraform 1.15.8. It runs `terraform fmt -check -recursive` and, in each root, `terraform init -backend=false` plus `terraform validate`. That job does not plan, apply, or use AWS credentials.

Current definitions that a policy scanner will see, and that this audit does not treat as a reason to skip the class:

- ALB ingress uses `allowed_ingress_cidrs`, whose staging and production variable default is `0.0.0.0/0` on ports 80 and 443.
- ALB and API egress use `0.0.0.0/0`.
- The API security group accepts port 8000 only from the ALB security group.
- RDS `publicly_accessible` is false. The RDS security group allows PostgreSQL only from the API security group and has empty egress.
- IAM allows the host to read its own secrets and denies the other environment's secret path. ECR is denied. SSM managed-instance attachment is present for later deploy commands.

`terraform fmt` and `terraform validate` do not evaluate those rules. They are not the Terraform scanning class.

The smallest required capability is one pinned local static policy scan of `infra/terraform/`. It does not run `terraform plan` or `terraform apply`. It does not use AWS credentials and does not read production state. Rule sets move between releases, so the version pin and an exact finding baseline are part of the capability. Stale exceptions fail. Wildcard check skips are rejected. Expected public-ingress and egress rules can be reviewed exceptions. They are not a silent ignore.

tfsec is deprecated and is not an appropriate new pin. A Checkov-class HCL policy tool and a Trivy-config-class misconfiguration mode can both run locally on this tree without AWS. This reconciliation does not select a brand and does not add the scan. It is not bundled with the container slice.

## Prompt and content isolation

Enabled or potentially enabled model prompt builders under `app/`:

| Builder | Call site | Availability gate | Transport actually constructed |
|---------|-----------|-------------------|--------------------------------|
| `build_shopping_prompts` | `TransportBackedShoppingProvider.explain` | `AI_SHOPPING_ENABLED`, `AI_SHOPPING_LIVE_HTTP`, and a non-empty API key. All default off. | `get_shopping_explanation_registry` always passes `DisabledTransport`. |
| `build_analysis_prompt` | `TransportBackedReviewProvider.analyze_reviews` | `AI_REVIEW_ENABLED`, `AI_REVIEW_LIVE_HTTP`, and a non-empty API key. All default off. | `get_ai_provider_registry` always passes `DisabledTransport`. |
| `build_community_prompts` | `TransportBackedCommunityProvider.summarize` | `AI_COMMUNITY_ENABLED`, `AI_COMMUNITY_LIVE_HTTP`, and a non-empty API key. All default off. | `get_community_summary_registry` always passes `DisabledTransport`. |

No other `You are` model prompt builder was found under `app/`. Research modules do not build a system or user prompt. `ProviderTransport.complete` accepts `system_prompt` and `user_prompt` only. There is no tools argument. `ScriptedTransport` is a test double. `DisabledTransport.complete` raises `AIProviderUnavailableError` and does not perform HTTP. No live AI HTTP transport class exists. Setting the flags without adding a transport still builds the strings and then fails the call. It does not send them.

How content enters those strings when a provider is available:

| Input | Where it goes | Delimited as data | Can change tool authority | Can request secrets | Can amplify provider cost |
|-------|---------------|-------------------|---------------------------|---------------------|---------------------------|
| Shopper query | `contains_prompt_injection` on the cleaned query, then the deterministic intent parser on every Ask. It is also placed in shopping user JSON under `structured.query` when that builder runs. | No. Six substrings add a warning. The query remains instruction-bearing user text. | No. The deterministic ranker uses it as a query. The transport has no tool list. | The warning does not remove the text. Shopping and community builders tell the model not to reveal secrets. That sentence is not a boundary. | Not on the current path. Query length is capped at 500 characters. |
| Merchant and product text | Shopping user JSON via candidates, evidence, and the top recommendation. Review user JSON includes `product` as a string. | No. It is concatenated into the user JSON next to the task. | No. | Shopping drops keys whose names contain `api_key`, `secret`, `token`, or `prompt`. The review schema has no such keys. | Not on the current path. |
| Reviews and community text | Review user JSON `reviews[].text`. Community user JSON `evidence` sliced to 40 items. | No. | No. Community connectors default to `MockCommunityTransport` and fixtures. | Review text is the evidence body. The review system string does not say to ignore instructions inside it. | `AI_MAX_REVIEW_INPUT` defaults to 40. The estimate cap runs after a provider returns a cost. |
| Research and public-web content | Not fetched into these builders. `LIVE_RESEARCH_EXECUTION_OPERATIONAL` is false. Public-web extract paths are local artifact files. | Not in a model prompt. | `live_start_claim` tool names are a fixed contract. The contract rejects `http_implemented=True`. | Not sent to a model. | Live research cannot spend. |
| Provider output | Parsed as JSON fields such as `answer` and `claims`. Processing records set `secrets_included` and `prompts_included` false. | It is not written back into the system prompt. | It cannot select a tool. The interface has none. | The response is not a secret store. | The 0.05 estimate cap compares a returned estimate on the review, shopping, and community orchestrators. It is not a pre-call live-research budget. |

`contains_prompt_injection` matches `ignore previous`, `ignore all instructions`, `system prompt`, `reveal the prompt`, `api key`, and `override safety`. Merchant text, review text, community text, and provider output are not passed through it.

Three boundaries:

1. Reachable PH public-beta risk now: none for a model following injected text. The model path is off. Deterministic ranking does not treat merchant text as instructions. Shopify stays disabled. Live research stays fail-closed.
2. Required implementation before AI or live-research activation: one bounded builder change. Keep system strings free of untrusted fields. Place the shopper query, product and merchant fields, review text, and community evidence in one delimited data object inside the user message. Add the missing refusal sentence to `build_analysis_prompt`. Do not add a transport, flip an AI flag, or enable research.
3. Provider-specific later work: vendor tool schemas, a live provider channel, and a live-research budget. Those wait until a provider exists.

That builder change is an executable Sprint 40 gap. It is not the selected slice. The public beta does not exercise the builders.

## R16 per-session limiting

`client_rate_limit_identity` returns `acct:<hmac>` for a verified account and `ip:<trusted client>` otherwise. A verified guest cookie does not create a bucket. Anonymous Ask uses the trusted IP. Auth failures and the durable lock use the email HMAC.

| Pattern | Trusted IP | Account HMAC | Per-session guest bucket |
|---------|------------|--------------|--------------------------|
| One stolen or copied guest cookie used from many IPs | Each address is limited. The cookie is not. | Not used for a guest. | Would limit that cookie. |
| Anonymous Ask with no guest identity | Limited. | Not used. | Would not apply. There is no session. |
| A newly minted guest cookie per request | Limited by IP. | Not used. | Would not add a limit. Each cookie is a new key. |
| Owner-cookie mutation | Origin policy still applies. | Used when the cookie is an account. | Would apply only to a guest cookie. |
| Deliberate distributed flooding from many addresses | Each address has its own bucket. | Each account has its own bucket. | A new cookie per address does not reduce the flood. |

The copied guest cookie across many addresses is the only pattern a session bucket would newly limit. The cookie is `HttpOnly`. The default CSP has no `'unsafe-inline'`. Live model spend and live research are off, so the extra requests are deterministic Ask traffic that each source IP already limits. The bucket is defense-in-depth. It is not a launch blocker for the floods that matter.

The Included sentence still names per-session, per-IP, and authenticated-principal limits as three controls. The per-IP and account controls exist. The per-session control does not. Equivalent IP and account limits do not erase that sentence, so R16 stays PARTIAL. This audit does not select the bucket.

## R13 ownerless non-decision context

Confirmed on the current tree:

- `CanonicalDecisionSnapshot.owner` is a required `ConversationOwner`. A decision snapshot cannot be ownerless.
- `ConversationContext.__post_init__` raises when `decision_context` is set and `owner` is `None`.
- `ShoppingAssistantService.query` loads a body `conversation_id` only through the verified owner. The comment and the call refuse an ownerless id. Stored `context.owner` is not adopted from the body.
- `get_for_owner` returns nothing when the stored owner is missing, so an ownerless row cannot expose another shopper's context.
- An ownerless row is not an authorization authority. Decision, research, and refinement paths require the verified owner.

Anonymous non-decision Ask can still call `create(owner=None)`. `_require_active_owner` allows that missing owner. The stored row has no decision context and cannot be continued. That is the Sprint 40.1 contract. It has no public security consequence.

R13 stays PARTIAL because the literal Included sentence says every conversation is bound to a guest session or an authenticated principal, and this row is not. It should not move to IMPLEMENTED-NOT-PROVEN while that sentence is unmet. It is not selected. Closing it requires a product decision to mint a guest owner for anonymous Ask. This audit does not make that decision.

## R15 guest to account

`claim_guest_conversation` rotates the cookie when no canonical UUID snapshot exists. When a canonical UUID snapshot exists, it returns `reason=immutable_snapshot_owner`, preserves the guest cookie, and does not rebind the snapshot.

Sprint 40 acceptance says the guest-to-authenticated transition preserves the active decision while rotating ownership credentials. Snapshot immutability forbids rebinding that canonical snapshot. This remains an unresolved product and security decision. It requires an owner decision. It is not executable engineering. This audit does not implement a rebind policy and does not change snapshot immutability. R15 stays PARTIAL.

## R12 and R21

These are gates, not runtime features. They stay PARTIAL because one existing finding is not closed.

| Historical finding | Current label | Why |
|--------------------|---------------|-----|
| HIGH: in-process rate limits only | IMPLEMENTED-NOT-PROVEN | Staging and production use the PostgreSQL `rate_limit_counters` store. Memory is rejected in those environments. Development stays in-process. Required staging evidence "Abuse controls exercised" is absent. The finding is not closed and not PROVEN. |
| MEDIUM: CSRF not enforced | IMPLEMENTED-NOT-PROVEN | Unsafe decision-owner-cookie requests and `POST /account/clear-device` reject a missing or untrusted Origin. Staging has not exercised the policy. The finding is not closed and not PROVEN. |
| MEDIUM: CSP `'unsafe-inline'` | IMPLEMENTED-NOT-PROVEN | The default policy no longer contains `'unsafe-inline'` or `'unsafe-eval'`. Staging has not exercised it. The finding is not closed and not PROVEN. |
| MEDIUM: No Dependabot/CodeQL/Trivy/pip-audit | CLOSED BY IMPLEMENTATION for the original no-scanner condition. SAST is a separate R6 capability and is IMPLEMENTED-NOT-PROVEN. Container scanning and IaC security scanning STILL OPEN as R6 capability gaps | The historical finding was the absence of a dependency scanner. pip-audit 2.10.1 is a required CI gate. The verified post-merge run reported 73 packages, 0 vulnerabilities, and 0 exceptions. That original condition stays closed. This reconciliation does not broaden the finding into a SAST, container, or IaC absence. Dependabot, CodeQL, and Trivy remain absent. Their product names are not the Sprint 40 requirement. |
| MEDIUM: URL validation / SSRF hardening incomplete | IMPLEMENTED-NOT-PROVEN | Server fetches and browser links are separate policies. Shopify and Resend are pinned and do not follow redirects. No current repository evidence proves a reachable SSRF. Staging has not exercised the policy. The finding is not closed and not PROVEN. |

What still prevents R12 and R21 closure is the HIGH "In-process rate limits only". The shared counter is implemented. The required staging exercise is absent. No historical MEDIUM is launch-blocking. The closed dependency-scanner finding does not keep the gates open. R6 can stay PARTIAL while that historical finding stays closed. No new severity is assigned. No risk acceptance is recorded.

Sprint 41 still owns the HIGHs for production isolation and production OIDC/SSM. Sprint 42 still owns the HIGH for CloudWatch and security paging. Those findings stay open. They are not Sprint 40 engineering.

## Which PARTIAL rows are which kind of work

| Item | Kind | Engineering now |
|------|------|-----------------|
| Item R6 | A. Executable Sprint 40 implementation gap. Container vulnerability scanning and IaC security scanning are absent. SAST is implemented and not proven. | Yes. One class only. Container vulnerability scanning of the releasable image is selected. |
| Item R10 | A. Executable Sprint 40 implementation gap on disabled prompt builders. Current public-beta model risk is absent. Required before AI or live-research activation. | Not selected. Do not enable a provider. |
| Item R12 | C. Staging or production proof only. The HIGH is implemented and not proven. | No. |
| Item R13 | B. Unresolved product decision. The literal sentence is unmet. No security consequence remains. | No. |
| Item R15 | B. Unresolved product and security decision. Canonical snapshot immutability conflicts with the acceptance sentence. An owner decision is required. | No. |
| Item R16 | E. Non-blocking defense-in-depth. The contract names the bucket, so the row stays PARTIAL. The bucket does not materially change protection for anonymous Ask, a new cookie per request, or a distributed flood. | Not selected. |
| Item R19 | A. Same pre-activation isolation gap as R10. Encoding and XSS are already implemented. | Not selected. |
| Item R21 | C. Same closure gate as R12. The blocking finding is the unclosed HIGH. | No. |

IMPLEMENTED-NOT-PROVEN rows that still need staging or production proof, and not more repository engineering, include R1, R2, R3, R4, R5, R7, R8, R9, R14, R17, and R18. R11 needs later use or rehearsal. R20 needs Sprint 44 acceptance. Those are not selected.

## Candidate comparison

| Candidate | Exact Sprint 40 requirement | Current repository evidence | Reachable beta risk | Public beta exercises the path | Size | External or network dependency | Product decision | Later proof | Launch relevance |
|-----------|-----------------------------|-----------------------------|---------------------|--------------------------------|------|--------------------------------|------------------|-------------|------------------|
| Container vulnerability scanning | Secret/dependency/SAST/container/Terraform scanning in CI. The container class. | CI builds a local image and does not scan it. Build Image #178 publishes a digest and does not scan it. Staging deploy pulls that digest. Base tags float. pip-audit does not see the OS packages or the copied `uv` binary. | No demonstrated image CVE. The published image is the runtime artifact staging can deploy. | The Ask path runs inside that image when an environment is deployed from the digest. Production is not deployed. | One pinned scan of the local runtime image before push, plus an exact baseline. | A vulnerability database, or a pinned database snapshot. No GHCR pull if the local image is scanned. No external upload. | No. | Sprint 41 owns the production pull. The gate itself is the publication job. | Yes for ENGINEERING COMPLETE. This is the artifact the beta runtime uses. |
| IaC security scanning | The Terraform class of the same sentence. | `terraform fmt` and `terraform validate` run with `-backend=false`. No policy scanner exists. Production apply is Sprint 41 and is UNSTARTED. | No current production apply. A bad plan matters before Sprint 41 apply. Staging definitions already describe a public ALB and a private RDS. | Terraform is not the request handler. The running image is. | One pinned static policy job and a baseline. | Rule packs are local once the tool is pinned. No AWS API. | No brand is required. Reviewed exceptions for intentional public ingress are part of the baseline, not a product decision. | Sprint 41 owns apply evidence. | Named, and lower current value than the image that serves requests. Not bundled with the container scan. |
| Prompt and content isolation | R10 and R19 review of prompt injection, merchant content, data minimization, and research cost. | Three builders embed untrusted text in user JSON. Review builder omits the refusal sentence. `DisabledTransport` is the only production transport. Flags default off. | None while AI flags, live HTTP, live research, and Shopify stay off. | No. Deterministic ranking serves Ask. | One builder change. No transport. | None. | No, for a delimiter that does not enable a provider. | Sprint 38 owns live-research proof and stays fail-closed. | Required before activation. Not the path the beta exercises. |
| Per-session limiting | R16 names per-session, per-IP, and authenticated-principal limits. | `client_rate_limit_identity` returns `ip:` or `acct:`. Guest `session_id` is not a key. | A copied guest cookie across many IPs is not session-limited. A new cookie per request and anonymous Ask are already IP-limited. | Yes for Ask traffic. The missing bucket does not cover the dominant flood. | One shared guest-session bucket. | None. PostgreSQL is already the staging and production limiter. | No. | Staging abuse exercise remains Sprint 40 evidence for the HIGH. | Defense-in-depth. Not selected. |
| Anonymous ownerless create | R13 literal binding sentence. | Ownerless non-decision rows cannot hold a decision, cannot be continued, and cannot authorize. | No demonstrated exposure of another shopper's context. | Anonymous Ask can create the row. | A guest mint would change the Sprint 40.1 contract. | None. | Yes. | Not proof. It is a product decision. | Not a concrete security issue. Not selected. |
| Guest-to-account rebind | R15 acceptance sentence versus snapshot immutability. | `immutable_snapshot_owner` keeps the guest cookie and does not rebind. | No code change can satisfy both sentences. | The claim path exists. | Not estimated. It is not executable. | None. | Yes. An owner must choose. | Not a sprint proof task. | Not selected. |

## Selected slice

**Choice:** B. Sprint 40 is not ENGINEERING COMPLETE. One bounded engineering slice is selected and is not implemented here.

A is not selected. R6 still lacks container vulnerability scanning and IaC security scanning, and all five classes are required for ENGINEERING COMPLETE. R10 and R19 still lack structural prompt isolation. R16 still names a per-session bucket. R13 and R15 still need decisions. R12 and R21 still wait on staging proof of the HIGH. Those facts are not all proof, later-sprint work, or unresolved decisions.

The guest-rebind conflict is not selected. Anonymous `create(owner=None)` is not selected. The SAST gate, the login lock, the submission ledger, and the security-readiness package are not selected again. They are already merged.

**Slice:** Add one deterministic container-vulnerability scan of the locally built runtime image, and fail publication before that image is pushed.

**Acceptance for the later slice:**

1. The scan reads the runtime image that Build Image would tag `sha-<gitsha>`, after that image is built locally and before it is pushed.
2. An unbaselined finding fails the publication job. The release manifest is not written for that image.
3. The CI validation tag `dealbrain:ci-<sha>` is not treated as this scan. Dockerfile text is not treated as this scan. `terraform validate` is not added as a substitute, and no IaC policy scanner is added.
4. The scanner version is pinned. Findings are compared to an explicit baseline. Stale exceptions fail. Wildcard ignores are rejected. Severity and fix availability are recorded and are not wildcard skips.
5. The job does not pull the published digest in order to scan it, does not upload image or source metadata, does not change CI permissions away from `contents: read`, and does not add `security-events: write`.
6. No runtime behavior, provider flag, Shopify call, routing change, Terraform apply, or deploy is included.

**Out of scope for the slice:** IaC security scanning, SAST changes, bot challenge, CAPTCHA, WAF, click-fraud detection, prompt isolation, per-session rate limits, guest revocation, guest rebind, anonymous ownerless create, CSRF tokens, a merchant-host allowlist, base-image digest pinning as a separate change, signed provenance, affiliate activation, Shopify calls, routing, and any deploy.

## Why this slice outranks the other gaps

The SAST gate now covers the application code that serves Ask, auth, cookies, and idempotency. The remaining scanner class whose subject is already on that path is the image staging deploys by digest. Debian packages in `python:3.12-slim` and the copied `uv` binary are in that image and are outside pip-audit. The base tags float, so the PR validation image is not those bytes. Scanning the local releasable image before push is the smallest gate that matches the container class.

IaC security scanning is a real missing class. It protects Terraform that Sprint 41 has not applied to production. `terraform validate` does not fill the class, and it is not selected as a substitute. Bundling it with the image scan would combine two capabilities.

Prompt isolation is a real pre-activation gap. `DisabledTransport` never delivers the prompts. Selecting it would harden builders the public beta does not call. This audit does not enable a provider.

The per-session bucket is a real R16 sentence and a weak control for a new cookie per request, anonymous Ask, and a distributed flood. The trusted-IP and account buckets already exist.

Guest rebind and anonymous ownerless create need decisions. They are not code slices.

Signed provenance is not a Sprint 40 blocker. The immutable tag, digest, and manifest checks are present. Sprint 41 owns the production pull.

## What this audit did not find

- No new HIGH, and no document that already marks a Sprint 40 MEDIUM launch-blocking.
- No SAST exception whose current source contradicts the recorded review.
- No reachable SSRF, SQLi, command injection, or XSS proof.
- No reachable public path that creates, continues, reads, or mutates a sensitive decision context through an ownerless conversation.
- No evidence that the message ledger lets body `user_id` or `profile_id` choose replay authority.
- No evidence that a replay calls `service.query` or `emit_ask_product_events`.
- No live AI HTTP transport and no model-chosen tool loop.
- No evidence that Sprint 38 engineering completeness, the Sprint 39 Class C count, or the Sprint 39 selected slice changed.
- No pen-test report, no paging configuration, no restore drill, and no written risk acceptance.
- No Sprint 44 approval. SECURITY GO remains NOT DECIDED.
