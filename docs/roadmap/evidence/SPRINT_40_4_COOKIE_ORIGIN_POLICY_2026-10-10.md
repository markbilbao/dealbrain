# Sprint 40.4 — CSRF / Origin policy for cookie transport

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `06a2c9da40c2bc49bf361569e887e64b1dccb8a6`

This record does not rewrite the Sprint 40 readiness audit or the Sprint 40.1, Sprint 40.2, or Sprint 40.3 records. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed.

## Selected policy

Strict `Origin` validation on the unsafe routes where the decision-owner cookie is an authorization credential, plus the one route that deletes that cookie.

`CsrfTokenService` stays an account-session preparation token. It is not enforced on these routes. Guest owner cookies are not issued with that token, and the browser callers (`consumer.js`, `account.js`, `product_feedback.js`, `product_analytics.js`) do not send a CSRF header. Same-origin `fetch` and form POST already send `Origin`. Adding a second token would be a larger client change and would not cover a missing or foreign `Origin` more strictly than this check.

SameSite=Lax stays as it is. It is not this control.

There is no middleware that rejects every unsafe API request. Bearer-only routes are not asked for an `Origin` merely because they are POST.

## Cookie-authorized unsafe routes

| Route | Authority | Policy |
|---|---|---|
| `POST /api/v1/shopping-assistant/query` | Decision-owner cookie authorizes continuation, refinement, research proposal/confirmation, and evidence answers. Delivery and shopping-market cookies on the same request are preferences, not the authority. | Enforce when `piqsavi_decision_owner` is present. |
| `POST /consumer/claim-decision` | Bearer token authorizes the account. The owner cookie authorizes which guest state may be rebound. | Enforce when the owner cookie is present. A bearer call with no owner cookie is unchanged. |
| `POST /api/v1/feedback/reports` | Owner cookie authorizes binding a report to that owner's decision. | Enforce when the owner cookie is present. |
| `POST /api/v1/analytics/events` | Owner cookie authorizes binding an event to that owner's decision. | Enforce when the owner cookie is present. |
| `POST /account/clear-device` | Does not read the cookie. The response deletes it, including when a cross-site response is processed. | Always enforce. |

## Not owner-cookie authorization

| Route | Why it is outside this policy |
|---|---|
| `GET /results/{id}`, `GET /compare/{id}`, `GET /why-best-piq/{id}`, `GET /support`, `GET /consumer/decisions/{id}/destination-reevaluation` | Safe methods. The cookie is a read credential for top-level navigation. |
| `POST /consumer/location`, `GET /consumer/location` | Writes the delivery preference cookie. It does not authorize a decision or conversation. |
| `POST /consumer/shopping-market` | Writes the shopping-market preference cookie. |
| `POST /api/v1/privacy/tracking-preference` | Writes the analytics preference and may rotate the analytics subject cookie. Those cookies are not the decision-owner credential. |
| `POST /api/v1/auth/*`, including logout, register, login, and account delete | Bearer token or an unauthenticated body. The browser does not attach the bearer token. Logout stays correct without an `Origin`. |
| Other `/api/v1` POST, PUT, PATCH, and DELETE routes | Bearer, staff, or unauthenticated API authority. A stray owner cookie on those requests does not make them cookie-authorized. |

The HTML ask form posts to the decision page and is intercepted by `consumer.js`, which calls `POST /api/v1/shopping-assistant/query`. That API call is the protected path.

## Trusted origins

The allow list is built only from server settings:

- the origin of `PUBLIC_APP_BASE_URL` (a path on that base URL is ignored; userinfo rejects the entry)
- each `CORS_ORIGINS` entry that parses as one concrete `http` or `https` origin

`*` is ignored. The request `Host`, the request URL, and `Referer` are not consulted. A forged `Host` cannot make a foreign `Origin` valid.

Staging and production keep only `https` origins. An `http` CORS entry is not a cookie-authority origin in those environments. CORS middleware `allow_origins` is not modified by this slice.

## Request behavior

| Case | Result |
|---|---|
| Owner-cookie mutation with `Origin` equal to `PUBLIC_APP_BASE_URL` | Allowed. Signed-owner authorization runs next. |
| Owner-cookie mutation with `Origin` equal to a configured CORS origin | Allowed. |
| Foreign `Origin` | 403 `origin_rejected`. |
| `Origin: null` | 403 `origin_rejected`. |
| Malformed `Origin`, including userinfo, a path, or a non-http(s) scheme | 403 `origin_rejected`. |
| Missing `Origin` | 403 `origin_rejected`. **Fail-closed** (`MISSING_ORIGIN_POLICY = fail_closed`). `Referer` does not fill the gap. |
| Bearer-only or cookieless API POST | Origin check does not run. |
| Preference/location POST, even with the owner cookie attached | Origin check does not run. |

The 403 body is `error=origin_rejected`, message `Origin is not allowed for this request.`, with the same legacy `detail`. It does not echo the cookie, the session id, or the supplied origin.

## What this changes in the finding map

The Sprint 40 MEDIUM "CSRF not enforced" is **IMPLEMENTED-NOT-PROVEN**. The cookie-authorized mutations above reject untrusted origins in this repository. The finding is not closed and not PROVEN. Staging has not exercised it. No deploy was performed.

CSP `'unsafe-inline'` and incomplete URL validation / SSRF hardening remain open MEDIUMs. The Sprint 40.3 distributed rate-limit HIGH remains IMPLEMENTED-NOT-PROVEN. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. Section I of the gap inventory is not rewritten.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate behavior was not changed.

Out of scope and not implemented here: CSP nonce or hash refactor, SSRF / URL validation, account lockout, CodeQL, Trivy, Dependabot, a pen-test package, incident-response documentation, Shopify calls, and routing or provider activation.
