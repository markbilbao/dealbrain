# Sprint 40.6 — Content Security Policy hardening

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `c0c341187515d480bb4318c26c085d44a16af14e`

This record does not rewrite the Sprint 40 readiness audit or the Sprint 40.1, Sprint 40.2, Sprint 40.3, Sprint 40.4, or Sprint 40.5 records. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed. No Shopify call was made. Routing stays 0.

## Finding

The Sprint 40 MEDIUM CSP `'unsafe-inline'` is **IMPLEMENTED-NOT-PROVEN**. It is not closed and not PROVEN. Staging has not exercised the policy.

The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.4 CSRF/Origin MEDIUM remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.5 URL/SSRF MEDIUM remains IMPLEMENTED-NOT-PROVEN. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. Section I of the gap inventory is not rewritten.

## Old CSP

`app/core/config.py` defaulted to:

```
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

## New CSP

`DEFAULT_SECURITY_CSP` is now:

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'
```

`SecurityHeadersMiddleware` still copies `settings.security_csp` onto responses. `X-Frame-Options` stays `DENY`, which matches `frame-ancestors 'none'`.

The policy does not contain `'unsafe-inline'`, `'unsafe-eval'`, or `*`. It does not add a CSP report endpoint.

## Browser origins

No third-party browser origin is required by the current product surfaces.

| Source | Why it is in the policy |
|---|---|
| `'self'` on `default-src`, `script-src`, `style-src`, `img-src`, `font-src`, `connect-src`, `form-action`, and `base-uri` | Pages, scripts, stylesheets, logos, the web manifest, and `fetch` calls are same-origin. |
| `'none'` on `frame-ancestors` | The app must not be framed. This matches `X-Frame-Options: DENY`. |
| `'none'` on `object-src` | No plugin or embedded object content is served. |

`img-src` no longer allows `data:` or `https:`. Rendered pages load images from `/static/early_access/assets/` only. Product art is a CSS class, not a remote `<img>`. Stored merchant and marketplace image URLs are not placed in `<img src>`.

`font-src 'self'` covers a future same-origin font file. Current CSS uses system font stacks (`Inter`, `Segoe UI`, `system-ui`) and does not request a font file or a font host.

`connect-src 'self'` covers `fetch` to `/api/v1/...`, `/account/clear-device`, and `/consumer/claim-decision`. Server-side Resend (`https://api.resend.com/emails`) and Shopify (`https://catalog.shopify.com/api/ucp/mcp`) are not browser connections. They stay out of `connect-src`.

`form-action 'self'` covers `POST /consumer/shopping-market` and forms that omit `action` and therefore submit to the current same-origin URL. Account and Early Access forms are submitted with `fetch`, not a cross-origin form POST. Affiliate and merchant URLs are `<a href>` navigations. They are not script, style, or form-action sources. This slice does not set `navigate-to`.

## HTML inventory

Searched rendered and static HTML for inline `<script>`, inline `<style>`, `style=`, event-handler attributes (`onclick`, `onchange`, and the same `on*` form), `javascript:` URLs, `eval`, `new Function`, string-based timers, and third-party script, style, font, image, and frame origins.

| Surface | How it is produced | Inline execution found | What this slice did |
|---|---|---|---|
| Results, Compare, Why | `app/consumer/pages.py` | One external module, `/static/consumer/js/consumer.js`. Stylesheet `/static/consumer/css/piqsavi.css`. Logo `/static/early_access/assets/piqsavi-logo.png`. No inline script, style, or event handler. | Left the markup. `script-src 'self'` allows the module. |
| Account, login, register, reset, verify, confirm email change, support | `app/consumer/account_pages.py` | External module `/static/consumer/js/account.js`. Same consumer stylesheet. No inline script, style, or event handler. Forms have no cross-origin `action`. | Left the markup. |
| Early Access `GET /` | `app/static/early_access/index.html` plus `public_head_extras` | External `/static/early_access/early-access.js` and `early-access.css`. Local PNG assets. No event handlers and no `style=` attributes. | Left the executable markup. Two `application/ld+json` scripts stay inline. See below. |
| Privacy and Terms | `docs/legal/published/privacy-2026-09-11.html` and `terms-2026-09-11.html` | Each had the same inline `<style>` block. No script and no event handler. Legal prose is unchanged. | Moved the rules to `/static/legal/policy.css` and linked that file. |
| Internal demo `GET /demo` | `app/static/demo.html`, served when `app_env != production` | One inline `<script>`, one inline `<style>`, and 69 unique `style=` declarations in the page and in script-built markup. No event handlers, `javascript:` URLs, `eval`, or `new Function`. Production redirects `/demo` to `/`. | Moved the script to `/static/demo/demo.js` and the style block plus attribute rules to `/static/demo/demo.css`. Attribute rules use `!important` so they keep the priority inline styles had. |
| Error responses | `app/core/errors.py` | JSON. Not an HTML document. | CSP header still applied. No HTML change. |
| Merchant and admin APIs | JSON routers under `app/api/v1/` | No public merchant or admin HTML document. | No CSP exception. |
| HTML email | `app/auth/email_templates.py` | Out of browser-CSP scope. | Not changed. |
| FastAPI `/docs` and `/redoc` | FastAPI's bundled HTML, enabled in development and staging, and in production only when `OPENAPI_PUBLIC_DOCS` is true | `/docs` has an inline script plus `https://cdn.jsdelivr.net` script and CSS and a FastAPI favicon. `/redoc` has an inline script, jsDelivr, and `https://fonts.googleapis.com`. | Not given `'unsafe-inline'` or those origins. The strict header is still sent, so those pages do not execute. `/openapi.json` is unchanged. This is an operator surface, not a product surface, and it is not a reason to weaken the default policy. |

No browser JavaScript under `app/static/` calls `eval`, `new Function`, or a string timer. `setTimeout` uses function callbacks. `element.style` assignments in same-origin scripts are CSSOM writes, which `style-src 'self'` allows. `fetch` targets are same-origin paths.

### JSON-LD

Early Access injects two `<script type="application/ld+json">` blocks from `organization_json_ld` and `website_json_ld`. `application/ld+json` is not a JavaScript MIME type. Browsers do not execute it, and `script-src` does not require `'unsafe-inline'` for it. The blocks contain `https://schema.org` as structured-data context text, not as a script, style, or image request. The logo URL inside the JSON is the same-origin Early Access logo. No nonce was added.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- Sprint 40.3 distributed rate limits are unchanged.
- Sprint 40.4 Origin policy is unchanged.
- Sprint 40.5 URL trust policy is unchanged.
- Routing stays 0. The Shopify provider stays disabled. No live Shopify call was made.
- Affiliate activation, PiqScore, and ranking are unchanged.
- No deploy was performed.
