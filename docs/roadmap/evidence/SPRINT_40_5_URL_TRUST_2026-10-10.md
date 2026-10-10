# Sprint 40.5 — URL trust boundaries

**Slice status:** IMPLEMENTED-NOT-PROVEN.

**Sprint 40 status:** Planned. Not COMPLETE / CLOSED. Not ENGINEERING COMPLETE. Not PRODUCTION PROVEN. Not LAUNCH READY.

**Starting `main`:** `5dbc52295a38d056bca9347f7a69f605b3ad7414`

This record does not rewrite the Sprint 40 readiness audit or the Sprint 40.1, Sprint 40.2, Sprint 40.3, or Sprint 40.4 records. No Included requirement is PROVEN. Repository tests are not staging proof. No deploy was performed. No Shopify call was made. Routing stays 0.

No reachable SSRF exploit is demonstrated. The Sprint 40 audit recorded incomplete URL validation and did not prove a reachable SSRF. This slice does not claim that a historical exploit existed.

## Finding

The Sprint 40 MEDIUM "URL validation / SSRF hardening incomplete" is **IMPLEMENTED-NOT-PROVEN**. It is not closed and not PROVEN. Staging has not exercised the policy.

The Sprint 40.3 HIGH "In-process rate limits only" remains IMPLEMENTED-NOT-PROVEN. The Sprint 40.4 CSRF/Origin MEDIUM remains IMPLEMENTED-NOT-PROVEN. CSP `'unsafe-inline'` remains an open MEDIUM. Dependabot, CodeQL, and Trivy are still absent. R6 stays PARTIAL. Section I of the gap inventory is not rewritten.

## Trust-boundary inventory

Roles:

1. `SERVER_FETCH` — this process may open an HTTP connection to the URL.
2. `BROWSER_LINK` — rendered as a shopper or merchant click destination.
3. `BROWSER_RESOURCE` — a browser may load it, such as an image URL.
4. `SERVER_CONFIGURATION` — a fixed URL owned by PiqSavi or an approved provider.
5. `DATA_ONLY` — stored or displayed as provenance. Not fetched and not rendered as an active URL.

| URL | Role | Where | What this slice does |
|---|---|---|---|
| Shopify `post_json` endpoint | `SERVER_FETCH` and `SERVER_CONFIGURATION` | `app/research/shopify_global_catalog_transport.py` | Exact match to `https://catalog.shopify.com/api/ucp/mcp`, then the server-fetch host policy. Redirects are refused. Production execution passes `GLOBAL_CATALOG_ENDPOINT`, the same constant. |
| Resend emails API | `SERVER_FETCH` and `SERVER_CONFIGURATION` | `app/auth/email_resend.py` `RESEND_EMAILS_URL` | Exact match to `https://api.resend.com/emails`, server-fetch host policy, `follow_redirects=False`. Callers cannot substitute a URL. |
| Merchant organization website | `BROWSER_LINK` | `validate_safe_url` in organization create/update | Browser policy. Not fetched. |
| Merchant logo reference | `BROWSER_RESOURCE` | same validator | Browser policy. Consumer HTML does not put this in an `<img src>`. |
| Merchant product image URLs | `BROWSER_RESOURCE` | `validate_image_urls` | Browser policy. Not fetched. |
| Merchant marketplace offer URL | `BROWSER_LINK` | `validate_safe_url` in offer create/update | Browser policy, including the existing secret-query rejection. Not fetched. |
| Canonical `offer_url` | `BROWSER_LINK` | `CanonicalProductPresentation`, rendered by `app/consumer/pages.py` `_offer_link` | Browser policy at write and again at render. A failed check omits the anchor. |
| Imported `marketplace_url` | `BROWSER_LINK` after import; raw row is data until then | import pipeline and `MarketplaceRecordNormalizer` | Browser policy. Source mode stays `imported`. Not relabeled live. Not fetched. |
| Imported `image_url` | `BROWSER_RESOURCE` | same path | Browser policy. Not fetched. Consumer product art uses a CSS visual, not this URL. |
| Imported or connector `seller_url` | `BROWSER_LINK` | normalizer `MarketplaceSeller.url` | Browser policy when present. Not fetched. |
| Connector `base_url` | `SERVER_CONFIGURATION` stored, not fetched | `ConnectorConfiguration` | Mock-live still requires the `https://simulated.` prefix. No connector under `app/` opens it. |
| Marketplace source record | `DATA_ONLY` | `MarketplaceSource` | Names a connector and a source mode. It has no fetch URL. |
| Shopee and Lazada connector URLs | `BROWSER_LINK` fixture data | mock connectors | Built from canned ids. No HTTP client. |
| Future official connector stubs | none | `app/marketplace/connectors/stubs.py` | `test_connection` returns not implemented. No HTTP. |
| Fixture and mock-live connectors | `DATA_ONLY` / simulated | `fixture.py`, `mock_live.py`, `imported.py` | In-memory records. `https://fixtures.dealbrain.local`, `https://simulated.dealbrain.local`, and `https://imported.dealbrain.local` stay hostnames, not live fetches. |
| Shopify catalog `seller.url`, `product.url`, `variant.checkout_url` | `DATA_ONLY` | normalization and the PH probe | Prefix check for `http://` or `https://` only. Not fetched, not rendered, and execution evidence still drops `checkout_url`. Not relabeled live. |
| Public-web `source_url` | `DATA_ONLY` | `app/research/public_web_extract.py` and benchmark models | Classified and stored. The library does not fetch the page. |
| Product catalog `image_url` | `BROWSER_RESOURCE` | `ProductCreate` / `ProductUpdate` | Browser policy. Not fetched. Not used as a consumer `<img src>`. |
| Affiliate template, deep link, and tracked URL | `BROWSER_LINK` | `AffiliateLinkBuilder` | Browser policy. The builder does not fetch. Affiliate activation is unchanged. |
| Email action links | `SERVER_CONFIGURATION` | identity mail built from `PUBLIC_APP_BASE_URL` | The host header does not choose the link. The only HTTP call is the Resend constant above. |
| Account and consumer `next` | same-origin path | `_safe_next` | Still limited to known app paths. Not an outbound URL. |
| `DATABASE_URL` | `SERVER_CONFIGURATION` | settings and SQLAlchemy | Database DSN, not an HTTP user URL. Unchanged. |
| AI provider transports | closed | `app/infrastructure/ai/transports.py` | `DisabledTransport` is the live path. No HTTP client is implemented in `app/`. |
| Operator probe scripts | `SERVER_CONFIGURATION` outside the request path | `scripts/shopify_global_catalog_ph_probe.py`, `scripts/shopify_global_catalog_normalization_validation.py`, `scripts/public_web_ph_benchmark.py` | Fixed provider endpoints. Not called by the app. The public-web script can ask Tavily Extract to fetch a URL list. That third-party fetch is not a production request path and was not changed. |

## Outbound network sinks under `app/`

These are the HTTP clients found under `app/`:

| Sink | User-controlled URL? | Policy |
|---|---|---|
| `UrllibJsonTransport.post_json` | No. Production passes the server constant. Any other value now returns `transport_unavailable` and does not open. | Exact endpoint, server-fetch check, no redirect. |
| `ResendEmailSender._default_http_post` | No. `send` passes `RESEND_EMAILS_URL`. | Exact URL, server-fetch check, `follow_redirects=False`. |

No other `urlopen`, `httpx`, `requests`, or `aiohttp` call was found under `app/`. Marketplace connectors do not open sockets. AI live HTTP remains disabled and has no client. No user-controlled URL currently reaches a server fetch.

## Validation policy

### Server fetch

`validate_server_fetch_url` fails closed:

- scheme is `https` only
- no userinfo
- host required and parseable
- no control characters, whitespace, backslash, quotes, or angle brackets
- no percent-encoding in the host
- no IPv4-mapped IPv6 address
- no unusual textual IP form that `ipaddress` rejects and the platform numeric parser accepts (`2130706433`, `0x7f000001`, `0177.0.0.1`, `127.1`, `0`)
- canonical loopback, private, link-local, unspecified, multicast, reserved, and other non-global addresses are rejected, including IPv4 and IPv6
- the names `localhost`, `localhost.localdomain`, and `*.localhost` are rejected
- those name and address checks use one canonical host. A DNS name is IDNA-normalized to ASCII before classification, so a Unicode spelling that canonicalizes to `localhost` or to a numeric address is judged as that canonical host

The check does not resolve DNS names. IDNA conversion is a local string mapping. `socket.getaddrinfo` is used only with `AI_NUMERICHOST`, and only for ASCII numeric text that `ipaddress` has already rejected. A name such as `127.0.0.1.example.com` is not treated as `127.0.0.1`. DNS rebinding, where a public name resolves to a private address at connect time, is not mitigated. That needs a connect-time pinning design and is out of scope. This slice does not add a half-implemented resolver.

Browser links do not use this policy. A canonical private or loopback address may still be a browser destination. See below.

### Shopify production transport

The narrowest rule is in front of the generic check:

- the URL must be exactly `https://catalog.shopify.com/api/ucp/mcp`
- a public `https` URL that is not that endpoint is refused
- redirects are not required by the documented catalog POST
- `_RefuseRedirectHandler.redirect_request` raises `HTTPError` before `OpenerDirector.open` can request the `Location`
- one attempt, caller timeout preserved, raw body not stored, no retry, production transport authority unchanged
- gates, routing, and provider activation are unchanged

### Resend

The default poster checks the server-fetch policy and then requires the exact Resend URL. `follow_redirects=False`, so a 3xx is a delivery failure and is not followed. Provider bodies stay unsurfaced. Injected test posters are unchanged.

### Browser link and browser resource

`validate_browser_destination` rejects:

- schemes other than `http` and `https`
- missing or malformed hosts
- embedded usernames or passwords
- control characters, whitespace, backslash, quotes, and angle brackets
- percent-encoded hosts
- IPv4-mapped addresses
- unusual textual IP forms, including a Unicode spelling that IDNA-normalizes into a numeric address

It allows:

- query strings, including marketplace tracking parameters
- CDN hostnames
- `.local` fixture hostnames such as `imported.dealbrain.local`
- canonical private, loopback, and link-local addresses that `ipaddress` accepts as written
- an ordinary internationalized public hostname, and a Unicode spelling whose IDNA form is the name `localhost`

Canonical private and loopback browser links are not rejected. The server does not fetch them. A compatibility spelling such as `127。0。0。1` is not that canonical address: IDNA turns it into a numeric address, and both classes reject that ambiguous form. A compatibility spelling of the name `localhost` is still a browser destination, because its canonical form is a name rather than a numeric address. Server fetch rejects that same canonical name. Consumer pages render `offer_url` only as an `<a href>`, and they do not load merchant or product images from remote URLs. Applying the server-fetch block list to those fields would treat a clickable merchant URL as a server target. There is no authoritative merchant-domain list in the repository, so this slice does not add one. The merchant secret-query check (`password=`, `api_key=`, `secret=`, `token=`) stays on merchant submissions only. Marketplace import URLs may keep ordinary query parameters.

`_offer_link` drops a value that fails the browser policy, including a relative `/` placeholder, `javascript:`, and embedded credentials. A query-bearing `https` merchant URL is still rendered.

Imported rows that fail the browser policy are rejected as row errors and stay `imported`. They are not fetched and not relabeled live.

## Redirect policy

| Client | Policy |
|---|---|
| Shopify `UrllibJsonTransport` | Redirects are not followed. A 301, 302, 303, 307, or 308 becomes an HTTP error from the redirect handler. The `Location` is not requested, including when it is a blocked host. |
| Resend `httpx.post` | `follow_redirects=False`. A 3xx fails delivery. The body is not returned to the caller. |
| Other `app/` code | No HTTP client, so no redirect follower. |

## DNS boundary

Not implemented, on purpose:

- no DNS lookup during validation
- no connect-time address pinning
- no rebinding cache

A hostname that is not a literal address can still resolve to a private address later. The production sinks do not accept that class of caller-supplied host: Shopify and Resend require their exact `https` URLs. Closing rebinding for a future arbitrary fetch needs a separate networking design.

## What this slice does not change

- Sprint 40 stays Planned. It is not ENGINEERING COMPLETE.
- Sprint 38 stays IN PROGRESS and ENGINEERING COMPLETE. Closure validation stays blocked on Sprint 41.
- Sprint 39 stays IN PROGRESS and is not ENGINEERING COMPLETE. The Class C count remains 19. The selected next engineering slice remains NONE.
- Sprint 41 stays UNSTARTED.
- No deploy was performed. No Shopify call was made. Routing stays 0. Affiliate activation is unchanged. Click URL validation uses the browser policy. Ranking and commission are unchanged.

Out of scope and not implemented here: CSP nonce or hash refactor, WAF, CDN controls, DNS pinning, account lockout, CodeQL, Trivy, Dependabot, a pen-test package, incident-response documentation, affiliate activation, Shopify activation, provider certification, routing changes, and Sprint 38, Sprint 39, or Sprint 41 production deployment.
