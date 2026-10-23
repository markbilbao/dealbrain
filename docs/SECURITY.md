# Security (Sprint 22 Launch)

**Status:** Sprint 22  
**Related:** [SECURITY_MODEL.md](SECURITY_MODEL.md), [MERCHANT_SECURITY.md](MERCHANT_SECURITY.md)

## Controls added this sprint

### Security headers

When `SECURITY_HEADERS_ENABLED=true`:

| Header | Purpose |
|--------|---------|
| `Content-Security-Policy` | First-party scripts, styles, images, fonts, and connections. `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`, `form-action 'self'`. No `'unsafe-inline'` or `'unsafe-eval'`. |
| `Strict-Transport-Security` | Staging/production only (`SECURITY_HSTS_MAX_AGE`) |
| `X-Frame-Options` | Clickjacking protection (`DENY` default) |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disable camera/mic/geo/payment |

The default policy is `default-src 'self'`, `script-src 'self'`, `style-src 'self'`, `img-src 'self'`, `font-src 'self'`, `connect-src 'self'`, `form-action 'self'`, `frame-ancestors 'none'`, `base-uri 'self'`, and `object-src 'none'`. It does not use `'unsafe-inline'`, `'unsafe-eval'`, or `*`. FastAPI `/docs` and `/redoc`, when enabled outside production, still ship their own inline script and CDN references. The default policy does not allow those. This control is implemented and not staging-proven.

### CORS

Existing `CORSMiddleware` with explicit `CORS_ORIGINS`. Production validation
rejects `*`.

### Rate limiting

Configurable in-process limits for:

- login / registration
- affiliate endpoints
- merchant endpoints
- search / recommendations
- default bucket for other routes

### Demo token / reset token hardening (Sprint 23)

- `ALLOW_DEMO_RESET_TOKENS` must be false in staging and production; raw
  reset/verification/email-change tokens are omitted from API responses when
  disabled or outside development.
- `DEMO_LAUNCHER_ENABLED` must be false in production.
- Production persistence backends must be `sqlalchemy` (no silent memory fallback).

### Launch-readiness admin bearer

`LAUNCH_ADMIN_TOKEN` is a dedicated bearer for launch-admin routes. It is not
`APP_SECRET_KEY`. The default is empty and grants no staging or production
authority. Staging and production require an externally injected value from
Secrets Manager `dealbrain/<env>/launch_admin_token` while
`LAUNCH_READINESS_ENABLED=true`. Empty, placeholder, and the local development
bearer fail startup, including when staging `LAUNCH_STRICT_STARTUP` is false.
Request handling also rejects those values and does not fall back to the
development bearer. Development accepts that published bearer only when
`LAUNCH_ADMIN_TOKEN` is empty. Comparison uses `hmac.compare_digest`. The
value is not logged and is redacted from configuration export. Disabling
launch readiness still returns 404.

### Error responses

Consistent JSON envelope (`error`, `message`, `status_code`) while retaining
legacy `detail` for prior clients/tests.

### Decision-owner cookie origin

Unsafe requests that use the `piqsavi_decision_owner` cookie as authority, and
`POST /account/clear-device`, require an `Origin` from `PUBLIC_APP_BASE_URL`
or `CORS_ORIGINS`. Missing `Origin` is rejected. Bearer-token API calls are
not given this requirement. This is not a double-submit CSRF cookie. The
account bearer flow is unchanged. The control is implemented and not
staging-proven.

### Logging redaction

Tokens, passwords, API keys, Authorization headers, and similar fields are
never written to logs.

## Hard rules (unchanged)

- Merchants cannot alter organic DealScore or recommendation ranking
- Affiliate monetization is post-rank only
- Merchant org isolation is enforced
- No production secret material ships in the repo

## Explicit non-goals

- Real WAF / CDN rate limiting
- Production secret vault (AWS SM, GCP SM, Vault)
- CSRF cookie flows for SPA (bearer-header auth remains)
- Real payment / PII compliance certifications

## Sprint 40 security-readiness package (2026-10-14)

This section does not rewrite the Sprint 22 controls above. Sprint 40 prepared a security-readiness package from `main` `e088cba9a87175e387038afb98a1754fe8cc885e`. The package is documentation. Execution evidence and approval evidence are still pending. No penetration test has been executed. Production incident response is not operational. Sprint 44 security approval does not exist. Launch approval does not exist. R11 is IMPLEMENTED-NOT-PROVEN. R11 is not PROVEN. Sprint 40 stays Planned and is not ENGINEERING COMPLETE.

| Document | Role |
|----------|------|
| [security/PENETRATION_TEST_READINESS.md](security/PENETRATION_TEST_READINESS.md) | Pre-beta checklist. Every row is READY TO TEST. No row is TESTED / PASSED. |
| [runbooks/SECURITY_INCIDENT_RESPONSE.md](runbooks/SECURITY_INCIDENT_RESPONSE.md) | Security-response process. It does not configure paging. Sprint 42 owns paging and operational incident response. |
| [security/VULNERABILITY_RESPONSE.md](security/VULNERABILITY_RESPONSE.md) | Intake-to-close process. Closure requires a regression test and a retest for security-critical findings. |
| [roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md](roadmap/evidence/SPRINT_44_SECURITY_GO_NO_GO_DRAFT.md) | DRAFT / NOT APPROVED. SECURITY GO: NOT DECIDED. |

Evidence for the package: [roadmap/evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md](roadmap/evidence/SPRINT_40_SECURITY_READINESS_PACKAGE_2026-10-14.md).

## Scanner inventory (2026-10-14)

This section does not rewrite the Sprint 22 controls or the security-readiness package above. Sprint 40 stays Planned and is not ENGINEERING COMPLETE.

| Scanner | Current gate |
|---------|----------------|
| Secrets | `scripts/secret_scan_25a.py` in CI. Scope is infra, env examples, scripts, workflows, and `app/**/*.py`. |
| Dependencies | `scripts/check_pip_audit_baseline.py` runs pip-audit 2.10.1. After the SAST pin, the frozen dev closure is 73 packages, 0 vulnerabilities, 0 exceptions. |
| SAST | `scripts/check_sast_baseline.py` runs bandit 1.9.4 over `app/**/*.py`. The capability is IMPLEMENTED-NOT-PROVEN. Evidence: [roadmap/evidence/SPRINT_40_SAST_GATE_2026-10-14.md](roadmap/evidence/SPRINT_40_SAST_GATE_2026-10-14.md). Starting `main` is `871e761685fe663c4d0ef4cf3b11094c32ed90b9`. |
| Container vulnerability scanning | Not present. |
| IaC security scanning | Not present. `terraform validate` is a syntax check. |

R6 stays PARTIAL. The SAST gate does not upload findings and does not use GitHub code scanning. No deploy was performed.

## Application secret scan (2026-10-16)

This section does not rewrite the Sprint 22 controls, the security-readiness package, or the 2026-10-14 scanner inventory above. Sprint 40 stays Planned and is not ENGINEERING COMPLETE.

`scripts/secret_scan_25a.py` now scans `app/**/*.py` with the existing infra, env-example, script, and workflow globs. The application rule parses Python with `ast.parse` and reports a non-empty literal assigned to a credential-sensitive name. Reviewed findings use one exact exception each in `tests/security/baselines/secret-scan.baseline.json`. After PR #206, the scan of current `main` reported 649 application files, 8 findings, and 8 exceptions. The removed launch-admin symbol has no exception. The output and the baseline do not contain the literal values. The secret-scanning capability is IMPLEMENTED-NOT-PROVEN. SAST stays IMPLEMENTED-NOT-PROVEN. Container vulnerability scanning and IaC security scanning remain absent. R6 stays PARTIAL. Evidence: [roadmap/evidence/SPRINT_40_APPLICATION_SECRET_SCAN_2026-10-16.md](roadmap/evidence/SPRINT_40_APPLICATION_SECRET_SCAN_2026-10-16.md). Starting `main` is `f7060de8ac1ef362bfb8df558762a148a6e1df59`. No deploy was performed.

## Container vulnerability gate (2026-10-17)

This section does not rewrite the scanner inventory or the application secret scan above. Sprint 40 stays Planned and is not ENGINEERING COMPLETE.

`scripts/check_container_vuln_baseline.py` runs Grype 0.120.1 against one local Docker image. `scripts/security/install_grype.sh` verifies the official linux/amd64 archive SHA-256 `0a9ee97ef5ae2ee953b0a80098105052e846cdbe319a57d808b519c33cd1343d` before extraction. CI scans `dealbrain:ci-<gitsha>` and does not publish. Build Image scans the final local `sha-<gitsha>` tag before GHCR authentication and `docker push`. The vulnerability database is updated on each run and is not committed. The maximum database age is 120 hours. Application update checks are disabled.

The scan of the current runtime image reported 1182 packages and 172 findings, including 55 HIGH. `tests/security/baselines/grype-image.baseline.json` has 0 exceptions. The gate fails closed. Those HIGH findings are unresolved. The capability is not PROVEN. IaC security scanning remains absent. R6 stays PARTIAL. Evidence: [roadmap/evidence/SPRINT_40_CONTAINER_VULNERABILITY_SCAN_2026-10-17.md](roadmap/evidence/SPRINT_40_CONTAINER_VULNERABILITY_SCAN_2026-10-17.md). Starting `main` is `6ed3662d520d9e41a4bdc3df5ccc56b49c520300`. No deploy was performed.

A base comparison did not find a glibc image with zero HIGH findings. Bookworm reported 3 Critical and 79 High. Alpine reported 1 High and uses musl. The Dockerfile stays `python:3.12-slim`. Evidence: [roadmap/evidence/SPRINT_40_CONTAINER_BASE_COMPARISON_2026-10-17.md](roadmap/evidence/SPRINT_40_CONTAINER_BASE_COMPARISON_2026-10-17.md).

## Committed Alpine runtime (2026-10-19)

This section does not rewrite the 2026-10-17 Debian scan above. The owner approved the minimized Alpine runtime. The committed Dockerfile is now `python:3.12-alpine3.24`. A local Grype 0.120.1 scan of `dealbrain:ci-local` reported 70 packages and 10 findings: 0 Critical, 0 High, 9 Medium, 0 Low, and 1 Negligible. The baseline holds the ten reviewed exact exceptions. The local gate printed `container_vuln_gate: OK`. GitHub CI run 39221691578 succeeded with the same gate result. Container vulnerability scanning is IMPLEMENTED-NOT-PROVEN. It is not production proof. IaC security scanning remains absent. R6 stays PARTIAL. Sprint 40 stays Planned and is not ENGINEERING COMPLETE. Evidence: [roadmap/evidence/SPRINT_40_ALPINE_RUNTIME_IMPLEMENTATION_2026-10-19.md](roadmap/evidence/SPRINT_40_ALPINE_RUNTIME_IMPLEMENTATION_2026-10-19.md). No deploy was performed.

On 2026-10-22 the same tag is pinned to manifest list `sha256:92abd2ba1bdfb48b1e2ac224b582dd1558d0d4bb11c903b126b5bf9c448fd656`. The verified image is CPython 3.12.15 on Alpine 3.24.3. Locked `certifi` is 2026.10.19. The three BusyBox CVE-2025-60876 exceptions now name `alpine-3.24.3` and keep their rationale.
