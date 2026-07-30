# Security (Sprint 22 Launch)

**Status:** Sprint 22  
**Related:** [SECURITY_MODEL.md](SECURITY_MODEL.md), [MERCHANT_SECURITY.md](MERCHANT_SECURITY.md)

## Controls added this sprint

### Security headers

When `SECURITY_HEADERS_ENABLED=true`:

| Header | Purpose |
|--------|---------|
| `Content-Security-Policy` | Restrict script/style/connect sources |
| `Strict-Transport-Security` | Staging/production only (`SECURITY_HSTS_MAX_AGE`) |
| `X-Frame-Options` | Clickjacking protection (`DENY` default) |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Disable camera/mic/geo/payment |

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

- `ALLOW_DEMO_RESET_TOKENS` must be false in production; raw reset/verification
  tokens are omitted from API responses when disabled or in production.
- `DEMO_LAUNCHER_ENABLED` must be false in production.
- Production persistence backends must be `sqlalchemy` (no silent memory fallback).

### Error responses

Consistent JSON envelope (`error`, `message`, `status_code`) while retaining
legacy `detail` for prior clients/tests.

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
