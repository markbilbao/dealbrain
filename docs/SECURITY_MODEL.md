# Security Model

**Status:** Sprint 17
**Module:** `app/auth/security.py`
**Password hashing:** `app/auth/password.py`

## Overview

The User Platform's security posture in Sprint 17 is intentionally
demo-scale: enough structure (hashing, rate limiting, CSRF prep, audit
hooks, MFA/OAuth extension points) to demonstrate the architecture, without
claiming production-grade security guarantees.

## Password storage

- Algorithm: PBKDF2-HMAC-SHA256, stdlib-only (`hashlib.pbkdf2_hmac`), no
  third-party crypto dependency.
- 260,000 iterations by default (`PasswordHasher.DEFAULT_ITERATIONS`); the
  hasher refuses to run with fewer than 100,000 iterations.
- Per-password random 16-byte salt (`secrets.token_bytes`).
- Stored format: `pbkdf2_sha256$<iterations>$<salt-hex>$<digest-hex>` — the
  algorithm and iteration count travel with the hash so verification and
  future migration both stay correct even if defaults change.
- Verification uses `hmac.compare_digest` for constant-time comparison to
  resist timing attacks.
- Password policy (`AuthService._validate_password`): minimum 8 characters,
  must include both upper and lower case, must include at least one digit.

## Session tokens

- Raw tokens are generated with `secrets.token_urlsafe(48)` — cryptographically
  random, never derived from user-controllable input.
- Only `SHA-256(token)` (`AuthService.hash_token`) is persisted; the raw
  token is returned to the client exactly once and cannot be recomputed from
  storage.
- Sessions carry `expires_at` and `revoked`; both are checked on every
  validation (see [Session Management](SESSION_MANAGEMENT.md)).

## CSRF preparation

`CsrfTokenService` (`app/auth/security.py`) issues an opaque CSRF token
alongside every session and exposes `validate(expected, provided)` using
`hmac.compare_digest`. This is **double-submit-cookie-style architecture**:
Sprint 17 issues and can validate CSRF tokens, but no browser-cookie session
transport or CSRF-enforcing middleware is wired into the API layer yet —
today's API auth is header-based bearer tokens, which are not vulnerable to
classic CSRF in the same way cookie-based sessions are. The token is
returned in `AuthResponse.csrf_token` so a future cookie-based transport can
adopt it directly.

## Rate limiting

`RateLimiterHook` is an in-process sliding-window limiter (default: 20
attempts per 60-second window), keyed per action + normalized email (e.g.
`register:demo@example.com`, `login:demo@example.com`). It is explicitly
**not a production WAF or distributed rate limiter** — it only protects a
single process's memory and resets on restart. Exceeding the limit raises
`UserPlatformRateLimitError` (HTTP 429) and records a `rate_limited`
`SecurityEvent`.

## Audit logging

`AuditLogger` records `SecurityEvent` entries for register, login
success/failure, logout, session expiry, password reset/verification
requests, email-change request/delivery-failure/confirm, rate limiting,
CSRF rejection, MFA challenges, and OAuth link attempts. Without a configured `AuditLogRepository`, events are kept in an
in-process ring buffer (`InMemoryAuditLogRepository` when wired via
`InMemoryUserPlatformStore`) — there is no durable, queryable audit trail in
Sprint 17.

## MFA extension point

`MfaExtensionPoint` defines the shape multi-factor auth would take
(`is_enabled(user_id)`, `challenge(user_id)`) but every method is inert:
`is_enabled` always returns `False`, and `challenge` always reports
`status: "not_implemented"`. No TOTP, SMS, or WebAuthn support exists.

## OAuth extension point

`OAuthExtensionPoint` defines `begin_link(provider, user_id)` for a future
external identity provider (Google, Apple, etc.) integration. It always
returns `status: "not_implemented"` and never performs a real OAuth
handshake, redirect, or token exchange.

## Threat model caveats — read before considering production use

- **Demo users only.** Accounts created via `/auth/register` are not
  production identities and should not be treated as such.
- **No email sending.** Password reset and email verification tokens are
  returned directly in API responses for demo purposes
  (`*_token_demo_only`) instead of being emailed — this is a deliberate
  demo shortcut and **must never ship to real users**.
- **No MFA.** Accounts are single-factor (password only).
- **No OAuth / external identity providers.**
- **In-memory persistence only.** All users, sessions, hashes, and audit
  events reset on process restart and are not shared across processes or
  instances.
- **No production database adapter** is wired in Sprint 17; repository
  interfaces are storage-neutral so a durable adapter can be added later.
- **No payment integration** of any kind — nothing here handles PCI-scoped data.
- Rate limiting and audit logging are single-process, best-effort hooks, not
  hardened security controls.
