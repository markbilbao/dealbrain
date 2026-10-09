# Sprint 40.3 — Distributed rate-limit MVP

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `81a4d6aef4e9b49bf3648245190588f87c51c152`

This record does not rewrite [`SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md`](SPRINT_40_SECURITY_READINESS_AUDIT_2026-10-09.md), [`SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md`](SPRINT_40_1_BODY_IDENTITY_IMPLEMENTATION_2026-10-09.md), or [`SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md`](SPRINT_40_2_DEPENDENCY_AUDIT_BASELINE_2026-10-09.md). The audit matrix classes stay as recorded there. No Included requirement is PROVEN. Repository tests are not staging proof.

## Shared-store decision

The shared counter is a PostgreSQL table, `rate_limit_counters`, reached through the existing sync SQLAlchemy engine. Staging and production already run RDS PostgreSQL. The deploy path already migrates that database before it replaces the API process. A fixed window per scope and opaque identity is one conditional `UPDATE`, with an insert only when the window row is absent. Concurrent writers cannot increment past the limit. Expired rows are deleted when a counter is consumed.

Redis, ElastiCache, and any other new paid cache were rejected. They are not in the Terraform or Compose topology, and PostgreSQL can enforce the atomic counter for the controlled PH beta. AWS WAF and a CDN limiter were rejected because full WAF/CDN work remains a Sprint 40 non-goal. Stuffing counters into `operational_entities` was rejected because that JSON document store does not provide an atomic increment. Keeping the process-local dictionary was the open HIGH and was rejected for staging and production.

Development and tests keep an in-memory sliding window only when `APP_ENV` is development and `RATE_LIMIT_BACKEND` is unset or `memory`. Setting `RATE_LIMIT_BACKEND=memory` in staging or production is a configuration error. Unset in those environments selects postgres. There is no code path that catches a postgres failure and constructs the in-memory store.

The shared window is fixed, not sliding. A client can be allowed the full limit at the end of one window and again at the start of the next. The in-memory development store keeps the previous sliding window. The public buckets and the 429 body and headers are unchanged.

## Identity-key policy

| Traffic | Stored key |
|---|---|
| No verified account credential | `ip:` plus the direct client host. `ip:unknown` when the host is absent. |
| Verified bearer session | `acct:` plus HMAC-SHA256 of the account id. The raw bearer token, its prefix, and the token hash are not stored. |
| Verified account owner cookie | Same `acct:` HMAC of the account principal. The cookie value and session id are not stored. |
| Guest owner cookie, invalid bearer, or invalid cookie | The IP key. A new cookie or a new bearer token does not open a new bucket. |
| Registration, login, password reset, verification, email change | `{action}:` plus HMAC-SHA256 of the normalized email or account id. |

The HMAC key is the same server secret used to sign owner cookies. Staging and production do not fall back to the development constant. If that secret is missing or a placeholder, identity derivation fails closed.

The first 8 characters of a bearer token are not a rate-limit identity.

## Failure mode

If the shared store cannot be read or written, the HTTP middleware returns 503 with `error=rate_limit_unavailable` and does not call the route. The auth abuse hook returns not allowed, so registration, login, password reset, verification, and email change are denied. Neither path switches to memory. Health, ready, and live probes stay outside the limiter.

`RATE_LIMITING_ENABLED=false` remains an explicit operator switch. It is not the store-failure path.

## What this changes in the finding map

The Sprint 40 HIGH "In-process rate limits only" is **IMPLEMENTED-NOT-PROVEN**. Staging and production no longer depend on a process-local counter. The finding is not closed. It is not PROVEN. Required Sprint 40 staging evidence still includes "Abuse controls exercised." That evidence is absent. No deploy was performed.

CSRF not enforced, CSP `'unsafe-inline'`, and incomplete URL validation / SSRF hardening remain the existing MEDIUMs. They are not relabeled launch-blocking. No risk acceptance is recorded. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. pip-audit remains the Sprint 40.2 gate.

Section I of the gap inventory is not rewritten. Account lockout was not added.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. `SHOPIFY_LIVE_CALL_PERMITTED` stays false. Real Shopify calls stay 0.
- Affiliate behavior was not changed.

Out of scope and not implemented here: account lockout, CSRF, CSP, SSRF / URL validation, CodeQL, Trivy, Dependabot, a pen-test package, incident-response documentation, Shopify calls, routing or provider activation, and Sprint 38, Sprint 39, or Sprint 41 production deployment.
